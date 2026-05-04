"""
Report Parser - Converts toxicity reports (e.g., test.json) to product risk profiles.

Supports multiple report formats:
- EDC-only reports (binary detection)
- Comprehensive toxicity reports (CRITICAL/HIGH/MODERATE/LOW with exposure routes)
- Combination risk assessments

Output: Unified product profile with:
- danger_level: Overall product risk (CRITICAL/HIGH/MODERATE/LOW)
- exposure_routes: [skin, inhalation, ingestion, eyes]
- chemical_verdicts: List of individual chemical risks
- organ_overlaps: Cross-chemical toxicity flags
- recommendation_override: Medical safety threshold
"""

import json
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .logger import get_logger

logger = get_logger("report_parser")


class DangerLevel(Enum):
    """Risk categorization matching test.json format."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    SAFE = "SAFE"
    UNKNOWN = "UNKNOWN"


class ExposureRoute(Enum):
    """How chemicals enter the body."""

    SKIN = "skin"
    INHALATION = "inhalation"
    INGESTION = "ingestion"
    EYES = "eyes"


class ReportParser:
    """Parses toxicity reports and converts to normalized product profiles."""

    DANGER_SCORES = {
        "CRITICAL": 1.0,
        "HIGH": 0.7,
        "MODERATE": 0.4,
        "LOW": 0.2,
        "SAFE": 0.0,
        "UNKNOWN": 0.3,
    }

    RISK_THRESHOLDS = {
        "eliminate": 0.8,
        "substitute": 0.4,
        "reduce": 0.2,
        "keep": 0.0,
    }

    def parse_report(self, report: Dict) -> Dict:
        """Parse a comprehensive toxicity report and extract product profiles."""
        try:
            parsed_products = []

            for product in report.get("products", []):
                parsed_product = self._parse_product(product)
                parsed_products.append(parsed_product)

            return {
                "report_id": report.get("report_id", "unknown"),
                "analyzed_at": report.get("analyzed_at"),
                "agent_version": report.get("agent_version"),
                "products": parsed_products,
            }

        except Exception as e:
            logger.error(f"Report parsing failed: {e}")
            raise

    def _parse_product(self, product: Dict) -> Dict:
        """Parse individual product from report."""
        ingredients = product.get("ingredients", {})
        chemicals_evaluated = ingredients.get("chemicals_evaluated", [])

        chemical_verdicts = []
        critical_count = 0
        high_count = 0
        moderate_count = 0
        low_count = 0
        safe_count = 0

        for chemical in chemicals_evaluated:
            verdict = self._parse_chemical_verdict(chemical)
            chemical_verdicts.append(verdict)

            level = verdict["danger_level"]
            if level == "CRITICAL":
                critical_count += 1
            elif level == "HIGH":
                high_count += 1
            elif level == "MODERATE":
                moderate_count += 1
            elif level == "LOW":
                low_count += 1
            elif level == "SAFE":
                safe_count += 1

        safe_skipped = ingredients.get("safe_skipped", [])
        safe_count += len(safe_skipped)

        product_danger = self._aggregate_danger_level(
            critical_count, high_count, moderate_count, low_count
        )

        exposure_routes = set(product.get("exposure_type", []))
        for chemical in chemical_verdicts:
            for route, effect in chemical.get("exposure_effects", {}).items():
                if effect.get("relevant"):
                    exposure_routes.add(route)

        combination_risks = product.get("combination_risks", {})
        organ_overlap = combination_risks.get("organ_overlap", {})
        has_organ_overlap = organ_overlap.get("has_overlap", False)
        overlapping_organs = organ_overlap.get("overlapping_organs")
        organ_overlap_flags = product.get("summary", {}).get("organ_overlap_flags", 0)

        override = self._get_recommendation_override(
            product_danger,
            critical_count,
            product.get("usage", "cosmetics")
        )

        return {
            "product_id": product.get("product_id"),
            "product_name": product.get("product_name"),
            "usage": product.get("usage"),
            "drivers": product.get("drivers", []),
            "danger_level": product_danger,
            "danger_score": self.DANGER_SCORES.get(product_danger, 0.3),
            "exposure_routes": list(exposure_routes),
            "chemical_verdicts": chemical_verdicts,
            "summary": {
                "total_ingredients": product.get("summary", {}).get("total_ingredients", 0),
                "chemicals_evaluated": len(chemicals_evaluated),
                "critical_count": critical_count,
                "high_count": high_count,
                "moderate_count": moderate_count,
                "low_count": low_count,
                "safe_count": safe_count,
                "organ_overlap_flags": organ_overlap_flags,
            },
            "combination_risks": {
                "has_organ_overlap": has_organ_overlap,
                "has_cumulative_presence": (
                    combination_risks.get("cumulative_presence", {}).get("checked", False)
                ),
                "overlapping_organs": overlapping_organs,
            },
            "recommendation_override": override,
        }

    def _parse_chemical_verdict(self, chemical: Dict) -> Dict:
        """Parse individual chemical verdict from report."""
        verdict_data = chemical.get("verdict", {})
        danger_level = verdict_data.get("danger_level", "UNKNOWN")

        body_effects = chemical.get("body_effects", {})
        exposure_effects = body_effects.get("exposure_effects", {})

        normalized_effects = {}
        for route, effect_data in exposure_effects.items():
            if isinstance(effect_data, dict):
                normalized_effects[route] = {
                    "name": effect_data.get("name"),
                    "relevant": effect_data.get("relevant", False),
                }

        hazard = chemical.get("hazard", {})

        return {
            "name": chemical.get("name"),
            "uid": chemical.get("uid"),
            "cas": chemical.get("cas"),
            "danger_level": danger_level,
            "danger_score": self.DANGER_SCORES.get(danger_level, 0.3),
            "justification": verdict_data.get("justification", []),
            "target_organs": body_effects.get("target_organs", []),
            "exposure_effects": normalized_effects,
            "hazard_codes": hazard.get("h_codes", []),
            "chemical_class": chemical.get("identity", {}).get("chemical_classes", []),
        }

    def _aggregate_danger_level(
        self, critical: int, high: int, moderate: int, low: int
    ) -> str:
        """Aggregate individual chemical risks to product-level danger."""
        if critical > 0:
            return "CRITICAL"
        elif high > 0:
            return "HIGH"
        elif moderate > 0:
            return "MODERATE"
        elif low > 0:
            return "LOW"
        else:
            return "SAFE"

    def _get_recommendation_override(
        self, product_danger: str, critical_count: int, usage: str
    ) -> Optional[str]:
        """Determine if automatic action override is needed."""
        if product_danger == "CRITICAL" and critical_count > 0:
            return "ELIMINATE"
        elif product_danger == "HIGH":
            if usage in ["spray", "aerosol"]:
                return "ELIMINATE"
            return "SUBSTITUTE"
        return None

    def product_to_rl_input(self, product: Dict, user_profile: Dict = None) -> Dict:
        """Convert parsed product to RL environment input format."""
        summary = product["summary"]

        max_severity = summary["critical_count"] * 2 + summary["high_count"]
        max_severity = min(max_severity, 5)

        verdicts = product["chemical_verdicts"]
        avg_risk = (
            sum(v["danger_score"] for v in verdicts) / len(verdicts)
            if verdicts
            else 0.0
        )

        has_fragrance = any(
            "fragrance" in v["name"].lower() or "parfum" in v["name"].lower()
            for v in verdicts
        )

        exposure_routes = product["exposure_routes"]
        dominant_route = exposure_routes[0] if exposure_routes else "skin"

        return {
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "edc_count": summary["critical_count"],
            "avg_risk": avg_risk,
            "max_severity": max_severity,
            "ingredient_count": summary["total_ingredients"],
            "has_fragrance": float(has_fragrance),
            "exposure_type": dominant_route,
            "exposure_routes": exposure_routes,
            "danger_level": product["danger_level"],
            "danger_score": product["danger_score"],
            "organ_overlap": float(product["combination_risks"]["has_organ_overlap"]),
            "recommendation_override": product.get("recommendation_override"),
        }

    def load_and_parse_report(self, report_path: Path) -> Dict:
        """Load JSON report file and parse it."""
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        return self.parse_report(report)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        report_path = Path(sys.argv[1])
    else:
        report_path = Path("test.json")

    parser = ReportParser()
    parsed = parser.load_and_parse_report(report_path)

    print(json.dumps(parsed, indent=2, ensure_ascii=False))
