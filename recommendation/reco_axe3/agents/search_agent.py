"""
Agent 7 - Product Search Agent.
Searches the web for alternative products in Tunisia.
Fetches and parses actual product details from search results.
Returns structured product data for manual safety verification.
"""

import time
from typing import Dict, List

from ..config.settings import get_settings
from ..scrapers.tunisia_scraper import TunisiaScraper
from ..utils.logger import get_logger, log_agent_action

logger = get_logger("search_agent")

SEARCH_TEMPLATES = {
    "face cleanser": [
        "nettoyant visage Tunisie",
        "face cleanser Tunisia",
        "savon nettoyant visage Tunisie",
        "facial wash Tunisie",
    ],
    "hair spray": [
        "spray capillaire Tunisie",
        "hair spray Tunisia",
        "laque cheveux Tunisie",
    ],
    "deodorant": [
        "déodorant Tunisie",
        "deodorant Tunisia",
        "anti-transpirant Tunisie",
    ],
    "shampoo": [
        "shampooing Tunisie",
        "shampoo Tunisia",
        "nettoyant cheveux Tunisie",
    ],
    "toothpaste": [
        "dentifrice Tunisie",
        "toothpaste Tunisia",
        "pâte dentaire Tunisie",
    ],
}


class ProductSearchAgent:
    """Searches for alternative products in Tunisia."""

    def __init__(self):
        self.settings = get_settings()
        self.tunisia_scraper = TunisiaScraper()

    def search_product_alternatives(self, product_name: str, product_type: str = "cosmetics", top_k: int = 5) -> Dict:
        """Search for alternative products available in Tunisia."""
        log_agent_action(
            "SearchAgent",
            f"Searching alternatives for '{product_name}'",
            f"(top_k={top_k})",
        )

        category = self._infer_category(product_name)
        search_queries = SEARCH_TEMPLATES.get(category, [f"{product_name} Tunisie"])

        all_results = []
        for query in search_queries:
            try:
                results = self.tunisia_scraper.search_product_tunisia(query)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Search failed for '{query}': {e}")

        seen_urls = set()
        deduplicated = []
        for r in all_results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduplicated.append(r)

        deduplicated.sort(key=lambda x: (not x.get("is_tunisian_store", False), x.get("price_tnd") or 999))

        enriched_results = []
        for result in deduplicated[:top_k]:
            try:
                parsed = self._fetch_product_details(result)
                enriched_results.append(parsed)
            except Exception as e:
                logger.warning(f"Failed to fetch details from {result.get('url')}: {e}")
                enriched_results.append(result)
            time.sleep(0.5)

        return {
            "query_product": {
                "name": product_name,
                "category": category,
            },
            "search_queries": search_queries,
            "all_results": enriched_results,
            "total_results_found": len(deduplicated),
        }

    def _fetch_product_details(self, search_result: Dict) -> Dict:
        """Fetch and parse actual product details from a search result URL."""
        url = search_result.get("url", "")
        if not url:
            return search_result

        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=(5, 15))
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            details = self._parse_product_html(soup, url)

            result = {**search_result}
            result.update({
                "product_name": details.get("name") or search_result.get("title"),
                "brand": details.get("brand", "Unknown"),
                "availability": details.get("availability", "Available"),
                "description": details.get("description") or search_result.get("snippet"),
                "detailed_title": details.get("name"),
                "product_image": details.get("image_url"),
                "product_url": details.get("product_link") or url,
            })
            return result

        except Exception as e:
            logger.debug(f"Could not fetch details from {url}: {e}")
            return search_result

    def _parse_product_html(self, soup, url: str) -> Dict:
        """Parse product HTML to extract name, brand, availability, and description."""
        details = {}

        name_selectors = ["h1", ".product-title", ".product-name", "[data-product-name]"]
        for selector in name_selectors:
            try:
                element = soup.select_one(selector)
                if element and element.get_text(strip=True):
                    details["name"] = element.get_text(strip=True)[:100]
                    break
            except:
                continue

        brand_selectors = [".brand", ".product-brand", "[data-brand]"]
        for selector in brand_selectors:
            try:
                element = soup.select_one(selector)
                if element and element.get_text(strip=True):
                    details["brand"] = element.get_text(strip=True)[:50]
                    break
            except:
                continue

        page_text = soup.get_text().lower()
        if "in stock" in page_text or "en stock" in page_text or "disponible" in page_text:
            details["availability"] = "In Stock ✅"
        elif "out of stock" in page_text or "rupture" in page_text:
            details["availability"] = "Out of Stock ❌"

        desc_selectors = [".product-description", ".description", "[data-description]"]
        for selector in desc_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)[:200]
                    if text:
                        details["description"] = text
                        break
            except:
                continue

        if "description" not in details:
            try:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc:
                    details["description"] = meta_desc.get("content", "")[:200]
            except:
                pass

        def _normalize_image_url(img_url):
            if img_url and not img_url.startswith("http"):
                from urllib.parse import urljoin
                return urljoin(url, img_url)
            return img_url

        def _extract_srcset(srcset):
            if not srcset:
                return None
            first_candidate = srcset.split(",")[0].strip().split(" ")[0]
            return first_candidate or None

        def _is_valid_image_url(img_url):
            if not img_url:
                return False
            lowered = img_url.lower()
            if len(lowered) < 12:
                return False
            return not any(token in lowered for token in ["logo", "icon", "badge", "seal", "watermark", "sprite", "button", "/spacer", "/blank"])

        image_candidates: list[str] = []

        meta_sources = [
            ("meta", {"property": "og:image"}, "content"),
            ("meta", {"property": "og:image:secure_url"}, "content"),
            ("meta", {"property": "twitter:image"}, "content"),
            ("meta", {"name": "twitter:image"}, "content"),
            ("meta", {"itemprop": "image"}, "content"),
            ("meta", {"name": "thumbnail"}, "content"),
            ("link", {"rel": "image_src"}, "href"),
        ]
        for tag_name, attrs, attr_name in meta_sources:
            try:
                element = soup.find(tag_name, attrs=attrs)
                if element:
                    candidate = element.get(attr_name)
                    if candidate:
                        image_candidates.append(candidate)
            except:
                continue

        img_selectors = [
            ".product-image img",
            ".product-photo img",
            "[data-product-image]",
            ".product-pic img",
            ".product-img img",
            ".woocommerce-product-gallery__image img",
            ".woocommerce-product-gallery img",
            ".wp-post-image",
            "picture img",
        ]
        for selector in img_selectors:
            try:
                element = soup.select_one(selector)
                if not element:
                    continue

                candidate = (
                    element.get("src")
                    or element.get("data-src")
                    or element.get("data-lazy-src")
                    or element.get("data-original")
                    or _extract_srcset(element.get("srcset"))
                    or _extract_srcset(element.get("data-srcset"))
                )
                if candidate:
                    image_candidates.append(candidate)
            except:
                continue

        for source in soup.select("picture source"):
            try:
                candidate = _extract_srcset(source.get("srcset")) or source.get("src")
                if candidate:
                    image_candidates.append(candidate)
            except:
                continue

        for img in soup.find_all("img"):
            try:
                candidate = (
                    img.get("src")
                    or img.get("data-src")
                    or img.get("data-lazy-src")
                    or img.get("data-original")
                    or _extract_srcset(img.get("srcset"))
                    or _extract_srcset(img.get("data-srcset"))
                )
                if candidate:
                    image_candidates.append(candidate)
            except:
                continue

        for candidate in image_candidates:
            candidate = _normalize_image_url(candidate)
            if _is_valid_image_url(candidate):
                details["image_url"] = candidate
                break

        product_link = self._extract_product_link(soup, url)
        if product_link:
            details["product_link"] = product_link

        return details

    def _extract_product_link(self, soup, base_url: str):
        """Extract a specific product link from a listing/category page."""
        try:
            from urllib.parse import urljoin

            link_selectors = [
                "a.product-link",
                "a.product-title",
                "a[data-product-url]",
                "h2 a",
                ".product-item a",
                ".product a",
                "a.woocommerce-LoopProduct-link",
            ]

            product_url_patterns = ["/product/", "/produit/", "/prix/", "/p/", "/item/", "/sku-"]

            for selector in link_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    href = elem.get("href", "")
                    if href and any(pattern in href.lower() for pattern in product_url_patterns):
                        if not href.startswith("http"):
                            href = urljoin(base_url, href)
                        if href != base_url and len(href) > len(base_url):
                            return href

            all_links = soup.find_all("a", href=True)
            for link in all_links:
                href = link.get("href", "")
                if href and any(pattern in href.lower() for pattern in product_url_patterns):
                    if not href.startswith("http"):
                        href = urljoin(base_url, href)
                    if href != base_url:
                        return href
        except:
            pass

        return None

    def _infer_category(self, product_name: str) -> str:
        """Infer product category from name."""
        product_lower = product_name.lower()

        if "cleanser" in product_lower or "wash" in product_lower:
            return "face cleanser"
        elif "spray" in product_lower:
            return "hair spray"
        elif "deodorant" in product_lower:
            return "deodorant"
        elif "shampoo" in product_lower:
            return "shampoo"
        elif "toothpaste" in product_lower or "dentifrice" in product_lower:
            return "toothpaste"

        return "face cleanser"

    def batch_search(self, products: List[Dict], top_k: int = 5) -> List[Dict]:
        """Search for alternatives for multiple products."""
        batch_results = []
        for product in products:
            product_name = product.get("product_name", "Unknown")
            result = self.search_product_alternatives(product_name, top_k=top_k)
            batch_results.append(result)
        return batch_results
