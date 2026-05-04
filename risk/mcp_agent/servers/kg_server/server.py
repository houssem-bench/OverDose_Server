"""
server.py — MCP Server for Neo4j Knowledge Graph
──────────────────────────────────────────────────
ADDED: get_complete_chemical_data tool
"""

import json
import os
import sys
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kg_client import KGClient

kg = KGClient()
kg.connect()

TOOLS = [
    {
        "name": "resolve_ingredient",
        "description": (
            "Convert an ingredient name to its Neo4j chemical UID. "
            "Always call this first before any other KG tool. "
            "Returns uid=None with unresolved=true if not found — "
            "unresolved means unknown risk, not safe."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ingredient_name": {
                    "type": "string",
                    "description": "Ingredient name as it appears on the product label"
                }
            },
            "required": ["ingredient_name"]
        }
    },
    {
        "name": "get_complete_chemical_data",
        "description": (
            "Get ALL chemical data in ONE call. Returns identity, hazards, "
            "GHS pictograms, target organs, chemical classes, use categories, "
            "exposure effects (skin/eyes/inhalation/ingestion), exposure limits, "
            "toxicity measures, and excretion routes. Use this instead of making "
            "multiple separate calls to get_hazard_profile, get_target_organs, "
            "get_full_profile, and get_exposure_limits."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "chemical_uid": {
                    "type": "string",
                    "description": "Chemical UID from resolve_ingredient"
                }
            },
            "required": ["chemical_uid"]
        }
    },
    {
        "name": "get_hazard_profile",
        "description": (
            "Get GHS hazard classification for a resolved chemical. "
            "Returns H-codes, highest signal (Danger/Warning/None), "
            "and whether the chemical has critical hazards. "
            "Call this after resolve_ingredient to decide investigation depth."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "chemical_uid": {
                    "type": "string",
                    "description": "Chemical UID from resolve_ingredient"
                }
            },
            "required": ["chemical_uid"]
        }
    },
    {
        "name": "get_full_profile",
        "description": (
            "Get complete chemical data in one call: identity, all hazards, "
            "target organs, chemical classes, toxicity measures, exposure limits, "
            "and all exposure route effects. Use for deep investigation of HIGH or CRITICAL chemicals."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "chemical_uid": {
                    "type": "string",
                    "description": "Chemical UID from resolve_ingredient"
                }
            },
            "required": ["chemical_uid"]
        }
    },
    {
        "name": "get_target_organs",
        "description": (
            "Get the list of organs this chemical affects. "
            "Use this when you need organ data for combination analysis "
            "without fetching the full profile."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "chemical_uid": {
                    "type": "string",
                    "description": "Chemical UID from resolve_ingredient"
                }
            },
            "required": ["chemical_uid"]
        }
    },
    {
        "name": "get_exposure_limits",
        "description": (
            "Get regulatory exposure limits (OSHA PEL, EU OEL, ACGIH TLV). "
            "Without dose data these limits cannot be compared directly, "
            "but their existence signals regulatory concern."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "chemical_uid": {
                    "type": "string",
                    "description": "Chemical UID from resolve_ingredient"
                }
            },
            "required": ["chemical_uid"]
        }
    },
]


def handle(request: dict) -> dict | None:
    method = request.get("method")
    rid = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": rid,
            "result": {
                "protocolVersion": "0.1.0",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "kg-server", "version": "2.1.0"},
            }
        }

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0", "id": rid,
            "result": {"tools": TOOLS}
        }

    if method == "tools/call":
        tool_name = request.get("params", {}).get("name")
        args = request.get("params", {}).get("arguments", {})

        dispatch = {
            "resolve_ingredient": lambda: kg.resolve_ingredient(args.get("ingredient_name")),
            "get_complete_chemical_data": lambda: kg.get_complete_chemical_data(args.get("chemical_uid")),
            "get_hazard_profile": lambda: kg.get_hazard_profile(args.get("chemical_uid")),
            "get_full_profile": lambda: kg.get_full_profile(args.get("chemical_uid")),
            "get_target_organs": lambda: kg.get_target_organs(args.get("chemical_uid")),
            "get_exposure_limits": lambda: kg.get_exposure_limits(args.get("chemical_uid")),
        }

        if tool_name not in dispatch:
            return {
                "jsonrpc": "2.0", "id": rid,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            }

        try:
            result = dispatch[tool_name]()
            return {
                "jsonrpc": "2.0", "id": rid,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": rid,
                "error": {
                    "code": -32000,
                    "message": str(e),
                    "data": traceback.format_exc()
                }
            }

    return {
        "jsonrpc": "2.0", "id": rid,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }


def main():
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            response = handle(json.loads(line))
            if response is not None:
                print(json.dumps(response), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)
    kg.close()


if __name__ == "__main__":
    main()