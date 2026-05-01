from __future__ import annotations

import logging

from scan.legacy.cache import SimpleTTLCache
from scan.legacy.config import Settings
from scan.legacy.http import HttpClient


logger = logging.getLogger(__name__)


class LensProvider:
    def __init__(self, http: HttpClient, settings: Settings, cache: SimpleTTLCache[dict]) -> None:
        self._http = http
        self._settings = settings
        self._cache = cache

    async def search_titles(
        self,
        image_url: str,
        max_results: int = 5,
        *,
        debug: dict[str, object] | None = None,
    ) -> list[str]:
        cache_key = f"lens::{image_url}::{max_results}"
        cached = self._cache.get(cache_key)
        if cached:
            titles = list(cached.get("titles", []))
            if debug is not None:
                debug["serpapi_status"] = "ok" if titles else "no_match"
                debug["serpapi_match_count"] = len(titles)
            return titles

        params = {
            "engine": "google_lens",
            "url": image_url,
            "api_key": self._settings.serpapi_key,
            "type": "products",
            "safe": self._settings.lens_safe,
        }
        if self._settings.lens_country:
            params["country"] = self._settings.lens_country
        data = await self._http.get_json("https://serpapi.com/search.json", params=params)
        if not data:
            if debug is not None:
                debug["serpapi_status"] = "error"
            return []

        visual_matches = data.get("visual_matches", [])
        titles = []
        for item in visual_matches[:max_results]:
            title = str(item.get("title") or "").strip()
            if title:
                titles.append(title)

        self._cache.set(cache_key, {"titles": titles})
        if debug is not None:
            debug["serpapi_status"] = "ok" if titles else "no_match"
            debug["serpapi_match_count"] = len(titles)
        logger.info("[LENS] Provider returned matches=%s", len(titles))
        return titles
