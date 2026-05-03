"""
Tunisia Product Scraper.
Searches for product availability and prices in Tunisian stores
using DuckDuckGo search (free, no API key needed).
"""

import json
import re
import time
from pathlib import Path
from typing import Optional

from ..config.settings import get_settings
from ..utils.logger import get_logger, log_scraper_action

logger = get_logger("tunisia_scraper")

TUNISIAN_STORES = [
    "coquette.tn",
    "tunisianet.com.tn",
    "pharmavie.tn",
    "beautystore.tn",
]


class TunisiaScraper:
    """Searches for alternative products in Tunisia."""

    def __init__(self):
        self.settings = get_settings()

    def search_product_tunisia(self, product_name: str, brand: str = "") -> list[dict]:
        """Search for a product's availability and price in Tunisia."""
        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                from duckduckgo_search import DDGS

                query = f"{brand} {product_name} prix Tunisie TND"
                results = []

                with DDGS() as ddgs:
                    search_results = list(ddgs.text(query, max_results=8, region="tn-fr"))

                    for r in search_results:
                        url = r.get("href", "")
                        title = r.get("title", "")
                        body = r.get("body", "")

                        is_tunisian = any(store in url.lower() for store in TUNISIAN_STORES)
                        price = self._extract_price(title + " " + body)

                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": body,
                            "price_tnd": price,
                            "is_tunisian_store": is_tunisian,
                            "store": self._extract_store(url),
                        })

                results.sort(key=lambda x: (not x["is_tunisian_store"], x["price_tnd"] or 999))
                return results

            except ImportError:
                logger.warning("duckduckgo-search not installed. Skipping Tunisia search.")
                return []
            except Exception as e:
                if attempt < max_retries:
                    wait = (attempt + 1) * 2
                    logger.warning(f"Tunisia search attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.warning(f"Tunisia search failed after {max_retries+1} attempts for '{product_name}': {e}")
                    return []

    def search_alternatives_tunisia(self, product_category: str, avoid_ingredients: list[str]) -> list[dict]:
        """Search for safer alternative products available in Tunisia."""
        try:
            from duckduckgo_search import DDGS

            safe_terms = "sans paraben sans phthalate bio naturel"
            query = f"{product_category} {safe_terms} Tunisie"
            alternatives = []

            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=10, region="tn-fr"))

                for r in search_results:
                    url = r.get("href", "")
                    title = r.get("title", "")
                    body = r.get("body", "")
                    price = self._extract_price(title + " " + body)

                    combined = (title + " " + body).lower()
                    contains_harmful = any(ing.lower() in combined for ing in avoid_ingredients)

                    if not contains_harmful:
                        alternatives.append({
                            "title": title,
                            "url": url,
                            "snippet": body,
                            "price_tnd": price,
                            "is_tunisian_store": any(s in url.lower() for s in TUNISIAN_STORES),
                            "store": self._extract_store(url),
                            "is_bio": any(kw in combined for kw in ["bio", "naturel", "organic", "sans paraben"]),
                        })

            return alternatives

        except Exception as e:
            logger.warning(f"Tunisia alternatives search failed: {e}")
            return []

    def batch_search(self, products: list[dict]) -> list[dict]:
        """Search Tunisia availability for a batch of products."""
        enriched = []
        for i, product in enumerate(products):
            name = product.get("name", "")
            brand = product.get("brand", "")

            logger.info(f"[{i+1}/{len(products)}] Searching Tunisia: {brand} {name}")

            tunisia_results = self.search_product_tunisia(name, brand)

            product_enriched = {**product}
            if tunisia_results:
                best = tunisia_results[0]
                product_enriched["tunisia"] = {
                    "available": True,
                    "price_tnd": best["price_tnd"],
                    "store": best["store"],
                    "url": best["url"],
                    "results_count": len(tunisia_results),
                }
            else:
                product_enriched["tunisia"] = {
                    "available": False,
                    "price_tnd": None,
                    "store": None,
                    "url": None,
                    "results_count": 0,
                }

            enriched.append(product_enriched)
            time.sleep(self.settings.SCRAPE_DELAY * 2)

        log_scraper_action("DuckDuckGo/Tunisia", "Products searched", len(enriched))
        return enriched

    def _extract_price(self, text: str) -> Optional[float]:
        """Extract TND price from text using regex."""
        patterns = [
            r'(\d+[\.,]\d{3})\s*(?:TND|DT|dinars?)',
            r'(\d+[\.,]\d{2})\s*(?:TND|DT|dinars?)',
            r'(\d+)\s*(?:TND|DT|dinars?)',
            r'(?:TND|DT|prix)\s*:?\s*(\d+[\.,]?\d*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(",", ".")
                try:
                    price = float(price_str)
                    if price > 500:
                        price = price / 1000
                    return round(price, 2)
                except ValueError:
                    continue

        return None

    def _extract_store(self, url: str) -> str:
        """Extract store name from URL."""
        for store in TUNISIAN_STORES:
            if store in url.lower():
                return store
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except Exception:
            return "unknown"

    def save_results(self, results: list[dict], path: Optional[Path] = None):
        """Save Tunisia search results."""
        path = path or self.settings.tunisia_products_path
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(results)} Tunisia results to {path}")

    def load_results(self, path: Optional[Path] = None) -> list[dict]:
        """Load Tunisia search results."""
        path = path or self.settings.tunisia_products_path
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
