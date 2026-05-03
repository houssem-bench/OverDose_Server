# risk/services.py
import logging
from .mcp_agent.agent_runner import get_agent

logger = logging.getLogger(__name__)

def analyze_ingredients_risks(ingredients_list, user_type=None):
    """
    Returns a list of risk dicts and the full agent report.
    
    Args:
        ingredients_list: list of strings (ingredient names)
        user_type: optional 'asthma', 'diabetes', 'newborn', 'fetal', 'pcos'
    
    Returns:
        (risk_items, full_report)
        risk_items = [{"ingredient": name, "level": "low"/"medium"/"high"}, ...]
    """
    if not ingredients_list:
        logger.info("No ingredients provided, returning empty risks")
        return [], {}

    logger.info(f"Analyzing {len(ingredients_list)} ingredients with agent")
    agent = get_agent()  # initializes MCP servers lazily
    risk_items, full_report = agent.analyze_product(ingredients_list, user_type=user_type)
    logger.info(f"Agent returned {len(risk_items)} risk items")
    return risk_items, full_report