from risk.mcp_agent.agent_runner import get_agent
agent = get_agent()

products_list = [
    {
        "product_id": "hair_smoother_001",
        "product_name": "Professional Hair Smoothing Treatment",
        "product_usage": "cosmetic",
        "exposure_type": "dermal",
        "ingredient_list": [
            {"name": "Formaldehyde"},
            {"name": "Fragrance (Parfum)"},
            {"name": "Water"},
            {"name": "Hydrolyzed Keratin"}
        ]
    },
    {
        "product_id": "sugar_scrub_002",
        "product_name": "Brown Sugar Body Scrub",
        "product_usage": "cosmetic",
        "exposure_type": "dermal",
        "ingredient_list": [
            {"name": "Water"},
            {"name": "Sucrose"},
            {"name": "Coconut Oil"},
            {"name": "Vitamin E"}
        ]
    },
    {
        "product_id": "preserved_lemonade_003",
        "product_name": "Homestyle Lemonade",
        "product_usage": "food",
        "exposure_type": "ingestion",
        "ingredient_list": [
            {"name": "Formaldehyde"},
            {"name": "Water"},
            {"name": "Sugar"},
            {"name": "Lemon Juice"}
        ]
    }
]

result = agent.run_sync(products_list, user_type="diabetes")
print(result["report"]["global_summary"]["total_products"])