from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    host: str
    port: int

    request_timeout_seconds: float
    max_retries: int
    retry_backoff_seconds: float
    cache_ttl_seconds: int
    max_parallel_analyses: int

    off_user_agent: str
    serpapi_key: str
    public_base_url: str
    enable_ngrok: bool
    ngrok_auth_token: str
    ngrok_domain: str
    lens_max_matches: int
    lens_country: str
    lens_safe: str

    grok_api_key: str
    grok_model: str
    grok_base_url: str

    enable_barcode: bool
    enable_yolo: bool
    yolo_model_path: str
    yolo_conf_threshold: float
    tesseract_cmd: str
    enable_ocr: bool

    uploads_dir: Path
    incoming_dir: Path
    crops_dir: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    uploads_dir = PROJECT_ROOT / "uploads"
    incoming_dir = uploads_dir / "incoming"
    crops_dir = uploads_dir / "crops"

    incoming_dir.mkdir(parents=True, exist_ok=True)
    crops_dir.mkdir(parents=True, exist_ok=True)

    default_model_path = str((PROJECT_ROOT / "yolov8l-world.pt").resolve())

    return Settings(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
        max_retries=int(os.getenv("MAX_RETRIES", "2")),
        retry_backoff_seconds=float(os.getenv("RETRY_BACKOFF_SECONDS", "0.5")),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "900")),
        max_parallel_analyses=max(1, int(os.getenv("MAX_PARALLEL_ANALYSES", "4"))),
        off_user_agent=os.getenv("OFF_USER_AGENT", "ProductIntelligenceV2/1.0"),
        serpapi_key=os.getenv("SERPAPI_KEY", "").strip(),
        public_base_url=(os.getenv("PUBLIC_BASE_URL") or os.getenv("NGROK_BASE_URL", "")).rstrip("/"),
        enable_ngrok=_to_bool(os.getenv("ENABLE_NGROK"), default=False),
        ngrok_auth_token=os.getenv("NGROK_AUTHTOKEN", "").strip(),
        ngrok_domain=os.getenv("NGROK_DOMAIN", "").strip(),
        lens_max_matches=max(1, int(os.getenv("LENS_MAX_MATCHES", "5"))),
        lens_country=os.getenv("LENS_COUNTRY", "TN").strip(),
        lens_safe=os.getenv("LENS_SAFE", "off").strip().lower(),
        grok_api_key=(os.getenv("GROK_API_KEY") or os.getenv("GROQ_API_KEY", "")).strip(),
        grok_model=(os.getenv("GROK_MODEL") or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")).strip(),
        grok_base_url=(os.getenv("GROK_BASE_URL") or os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")).strip().rstrip("/"),
        enable_barcode=_to_bool(os.getenv("ENABLE_BARCODE"), default=True),
        enable_yolo=_to_bool(os.getenv("ENABLE_YOLO"), default=True),
        yolo_model_path=os.getenv("YOLO_MODEL_PATH", default_model_path),
        yolo_conf_threshold=float(os.getenv("YOLO_CONF_THRESHOLD", "0.02")),
        tesseract_cmd=os.getenv("TESSERACT_CMD", "").strip(),
        enable_ocr=_to_bool(os.getenv("ENABLE_OCR"), default=True),
        uploads_dir=uploads_dir,
        incoming_dir=incoming_dir,
        crops_dir=crops_dir,
    )
