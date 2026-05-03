# risk/mcp_agent/agent_runner.py
import logging
from .agent.agent import BiologicalAgent
logger = logging.getLogger(__name__)

_AGENT = None

def get_agent():
    global _AGENT
    if _AGENT is None:
        logger.info("Initialising BiologicalAgent (starting MCP servers)...")
        _AGENT = BiologicalAgent(start_servers=True)
        logger.info("BiologicalAgent ready")
    return _AGENT

def analyze_product(ingredients_list, user_type=None):
    """
    Synchronous entry point for Django.
    ingredients_list: list of strings (ingredient names)
    user_type: optional 'asthma', 'diabetes', 'newborn', 'fetal', 'pcos'
    Returns: (risk_items, full_report_dict)
        risk_items = [{"ingredient": name, "level": "low"/"medium"/"high"}, ...]
    """
    agent = get_agent()

    product = {
        "product_id": "django_scan",
        "product_name": "Product from Scan",
        "product_usage": "cosmetic",
        "exposure_type": "skin",
        "ingredient_list": [{"name": ing} for ing in ingredients_list]
    }

    result = agent.run_sync([product], user_type=user_type)
    report = result.get("report", {})

    risk_items = []
    for product_out in report.get("products", []):
        for chem in product_out.get("ingredients", {}).get("chemicals_evaluated", []):
            name = chem.get("name")
            danger = chem.get("verdict", {}).get("danger_level", "UNKNOWN")
            if danger in ("CRITICAL", "HIGH"):
                level = "high"
            elif danger == "MODERATE":
                level = "medium"
            else:
                level = "low"
            risk_items.append({"ingredient": name, "level": level})

    return risk_items, report