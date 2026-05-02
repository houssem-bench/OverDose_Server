from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

from scan.legacy.cache import SimpleTTLCache
from scan.legacy.config import get_settings
from scan.legacy.http import HttpClient
from scan.legacy.orchestrator import PipelineOrchestrator
from scan.legacy.providers.lens_provider import LensProvider
from scan.legacy.providers.product_facts_provider import ProductFactsProvider
from scan.legacy.schemas import ProductAnalysis
from scan.legacy.services.barcode_service import BarcodeService
from scan.legacy.services.cloudinary_service import CloudinaryService
from scan.legacy.services.grok_service import GrokService
from scan.legacy.services.lens_service import LensService
from scan.legacy.services.ocr_service import OCRService
from scan.legacy.services.segmentation_service import SegmentationService


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_pipeline_orchestrator() -> PipelineOrchestrator:
    settings = get_settings()
    cache = SimpleTTLCache[dict](ttl_seconds=settings.cache_ttl_seconds)
    http = HttpClient(settings)

    product_facts_provider = ProductFactsProvider(http, settings, cache)
    lens_provider = LensProvider(http, settings, cache)

    barcode_service = BarcodeService(enabled=settings.enable_barcode)
    lens_service = LensService(lens_provider, settings)
    ocr_service = OCRService(settings)
    grok_service = GrokService(http, settings)

    return PipelineOrchestrator(
        barcode_service=barcode_service,
        lens_service=lens_service,
        ocr_service=ocr_service,
        facts_provider=product_facts_provider,
        product_cache_service=None,
        grok_service=grok_service,
    )


@lru_cache(maxsize=1)
def get_segmentation_service() -> SegmentationService:
    settings = get_settings()
    return SegmentationService(settings)


@lru_cache(maxsize=1)
def get_cloudinary_service() -> CloudinaryService:
    settings = get_settings()
    return CloudinaryService(settings)


def should_cleanup_cloudinary(debug: dict[str, object] | None) -> bool:
    if not isinstance(debug, dict):
        return False

    status_keys = ("serpapi_status", "off_status", "obf_status", "grok_status")
    for key in status_keys:
        if debug.get(key) == "error":
            return False

    return True


def analyze_image(*, scan_id: int, image_path: str, image_url: str | None) -> ProductAnalysis:
    orchestrator = get_pipeline_orchestrator()
    crop_url = image_url or image_path

    result = asyncio.run(
        orchestrator.analyze_product(
            product_id=str(scan_id),
            image_path=image_path,
            original_image_path=image_path,
            crop_url=crop_url,
            detected_label="product",
        )
    )
    return result


def analyze_ingredients_from_image(*, scan_id: int, image_path: str, image_url: str | None) -> list[str]:
    return analyze_image(scan_id=scan_id, image_path=image_path, image_url=image_url).ingredients


def segment_image(
    *,
    image_bytes: bytes,
    filename: str,
    segmentation_mode: str,
    expected_products: int | None,
) -> tuple[str, list[dict[str, object]]]:
    service = get_segmentation_service()
    return service.segment_upload(
        image_bytes,
        filename=filename,
        segmentation_mode=segmentation_mode,
        expected_products=expected_products,
    )


def analyze_selected_products(*, session_id: str, product_ids: list[str]) -> list[dict[str, object]]:
    settings = get_settings()
    segmentation_service = get_segmentation_service()
    orchestrator = get_pipeline_orchestrator()
    cloudinary_service = get_cloudinary_service()
    cloudinary_ready, _ = cloudinary_service.get_readiness()
    cloudinary_folder = settings.cloudinary_folder or None

    session_products = segmentation_service.get_session_products(session_id)
    if session_products is None:
        raise LookupError("Session not found")

    invalid_ids = [pid for pid in product_ids if pid not in session_products]
    if invalid_ids:
        raise ValueError(f"Invalid product IDs: {invalid_ids}")

    async def _run() -> list[dict[str, object]]:
        semaphore = asyncio.Semaphore(settings.max_parallel_analyses)

        async def run_one(product_id: str) -> dict[str, object]:
            async with semaphore:
                product = session_products[product_id]
                upload_result = None
                crop_url = product.crop_url

                if cloudinary_ready:
                    upload_result = await asyncio.to_thread(
                        cloudinary_service.upload_file,
                        product.crop_path,
                        folder=cloudinary_folder,
                    )
                    if upload_result:
                        crop_url = upload_result.url
                    else:
                        logger.warning(
                            "[CLOUDINARY] Upload failed for product_id=%s",
                            product.product_id,
                        )
                try:
                    result = await orchestrator.analyze_product(
                        product_id=product.product_id,
                        image_path=product.crop_path,
                        original_image_path=product.source_image_path,
                        crop_url=crop_url,
                        detected_label=product.label,
                    )
                    if upload_result and should_cleanup_cloudinary(result.debug):
                        await asyncio.to_thread(
                            cloudinary_service.destroy,
                            upload_result.public_id,
                        )
                    return result.model_dump()
                except Exception as exc:  # pylint: disable=broad-except
                    return {
                        "product_id": product.product_id,
                        "source": "failed",
                        "confidence": 0.0,
                        "category": "unknown",
                        "name": product.label,
                        "brand": None,
                        "ingredients": [],
                        "additives": [],
                        "barcode": None,
                        "lens_title": None,
                        "debug": {"error": str(exc)},
                    }

        return await asyncio.gather(*(run_one(pid) for pid in product_ids))

    return asyncio.run(_run())
