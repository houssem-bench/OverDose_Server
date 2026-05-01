from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import cloudinary
import cloudinary.uploader

from scan.legacy.config import Settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CloudinaryUploadResult:
    url: str
    public_id: str


class CloudinaryService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._enabled = bool(
            settings.cloudinary_cloud_name
            and settings.cloudinary_api_key
            and settings.cloudinary_api_secret
        )

        if self._enabled:
            cloudinary.config(
                cloud_name=settings.cloudinary_cloud_name,
                api_key=settings.cloudinary_api_key,
                api_secret=settings.cloudinary_api_secret,
                secure=bool(settings.cloudinary_secure),
            )

    def get_readiness(self) -> tuple[bool, str]:
        if not self._enabled:
            return False, "missing_cloudinary_credentials"
        return True, "ready"

    def upload_file(self, file_path: str, *, folder: str | None = None) -> CloudinaryUploadResult | None:
        ready, _ = self.get_readiness()
        if not ready:
            return None

        options: dict[str, Any] = {"resource_type": "image"}
        if folder:
            options["folder"] = folder

        try:
            result = cloudinary.uploader.upload(file_path, **options)
        except Exception as exc:
            logger.error("[CLOUDINARY] Upload failed path=%s error=%s", file_path, exc)
            return None

        url = result.get("secure_url") or result.get("url")
        public_id = result.get("public_id")
        if not url or not public_id:
            logger.error("[CLOUDINARY] Upload missing url/public_id path=%s", file_path)
            return None

        return CloudinaryUploadResult(url=str(url), public_id=str(public_id))

    def destroy(self, public_id: str) -> bool:
        if not public_id:
            return False

        ready, _ = self.get_readiness()
        if not ready:
            return False

        try:
            result = cloudinary.uploader.destroy(public_id)
        except Exception as exc:
            logger.error("[CLOUDINARY] Delete failed public_id=%s error=%s", public_id, exc)
            return False

        return result.get("result") == "ok"
