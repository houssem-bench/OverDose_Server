"""
profile_server/server.py – MCP Server for IngredientGuard
Transport: stdio (JSON-RPC 2.0)
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import traceback

import traceback
import traceback
from pathlib import Path

# Ensure we can import profile_logic from the same directory
sys.path.insert(0, str(Path(__file__).parent))

from profile_logic import (
    list_user_types,
    get_kb_stats,
    retrieve,
    get_risk_level,
    analyze_ingredient,
    USER_TYPE_MAP,
    DEFAULT_KB_PATH,
    DEFAULT_CHROMA_DIR,
)

# -----------------------------------------------------------------------------
# Tool definitions (unchanged except minor description clarifications)
# -----------------------------------------------------------------------------
TOOLS = [
    {
        "name": "list_user_types",
        "description": "Return all supported user-type labels. Use this to discover valid values for the user_type parameter before calling other tools.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_kb_stats",
        "description": "Return the number of chemicals indexed in the knowledge base for each user type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_path": {"type": "string", "description": "Path to User_Types.json (optional)"},
                "chroma_dir": {"type": "string", "description": "Path to ChromaDB persistence directory (optional)"},
            },
            "required": [],
        },
    },
    {
        "name": "retrieve_ingredient",
        "description": "Search the knowledge base for a specific ingredient and user type. Returns raw KB record or null. No LLM call.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_type": {"type": "string", "description": "Short user-type label, e.g. 'Asthma', 'Diabetes', 'Newborn', 'Fetal', 'Cardiovascular', 'PCOS'."},
                "ingredient": {"type": "string", "description": "Ingredient or chemical name to search, e.g. 'Aspirin'."},
                "kb_path": {"type": "string", "description": "Path to User_Types.json (optional)"},
                "chroma_dir": {"type": "string", "description": "Path to ChromaDB persistence directory (optional)"},
            },
            "required": ["user_type", "ingredient"],
        },
    },
    {
        "name": "get_risk_level",
        "description": "Convert a raw Inference Score (numeric string or number) to risk level: 'High' (>50), 'Moderate' (20-50), 'Low' (<20).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "inference_score": {"description": "The Inference Score value from the KB record (string or number)."},
            },
            "required": ["inference_score"],
        },
    },
    {
        "name": "analyze_ingredient",
        "description": "Full IngredientGuard pipeline: KB lookup + risk level + optional LLM patient-friendly explanation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_type": {"type": "string", "description": "Short user-type label, e.g. 'Asthma', 'Diabetes', ..."},
                "ingredient": {"type": "string", "description": "Ingredient or chemical name to analyze."},
                "generate_llm": {"type": "boolean", "description": "Whether to call the LLM for narrative report. Default false."},
                "kb_path": {"type": "string", "description": "Path to User_Types.json (optional)."},
                "chroma_dir": {"type": "string", "description": "Path to ChromaDB persistence directory (optional)."},
            },
            "required": ["user_type", "ingredient"],
        },
    },
]

# -----------------------------------------------------------------------------
# Request handler
# -----------------------------------------------------------------------------
def handle(request: dict) -> dict | None:
    method = request.get("method")
    rid = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": "0.1.0",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ingredient-guard-server", "version": "1.0.0"},
            },
        }

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = request.get("params", {}).get("name")
        args = request.get("params", {}).get("arguments", {})

        try:
            result = _dispatch(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {
                    "code": -32000,
                    "message": str(e),
                    "data": traceback.format_exc(),
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": rid,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }

def _dispatch(tool_name: str, args: dict) -> dict:
    kb_path    = args.get("kb_path", DEFAULT_KB_PATH)
    chroma_dir = args.get("chroma_dir", DEFAULT_CHROMA_DIR)

    if tool_name == "list_user_types":
        return {
            "user_types": list_user_types(),
            "valid_short_labels": list(USER_TYPE_MAP.keys()),
        }

    if tool_name == "get_kb_stats":
        stats = get_kb_stats(kb_path=kb_path, chroma_dir=chroma_dir)
        return {"kb_stats": stats}

    if tool_name == "retrieve_ingredient":
        user_type = args["user_type"]
        ingredient = args["ingredient"]
        if user_type not in USER_TYPE_MAP:
            raise ValueError(f"Unknown user_type '{user_type}'. Valid: {list(USER_TYPE_MAP.keys())}")
        # Pass the short key directly (no conversion)
        entry = retrieve(
            user_type_kb_key=user_type,
            ingredient=ingredient,
            kb_path=kb_path,
            chroma_dir=chroma_dir,
        )
        return {
            "found": entry is not None,
            "user_type": USER_TYPE_MAP[user_type],
            "ingredient": ingredient,
            "kb_entry": entry,
        }

    if tool_name == "get_risk_level":
        risk_level = get_risk_level(args["inference_score"])
        return {
            "inference_score": args["inference_score"],
            "risk_level": risk_level,
        }

    if tool_name == "analyze_ingredient":
        # Note: no api_key / groq_model arguments – they are handled inside profile_logic via env
        return analyze_ingredient(
            user_type=args["user_type"],
            ingredient=args["ingredient"],
            generate_llm=args.get("generate_llm", False),
            kb_path=kb_path,
            chroma_dir=chroma_dir,
        )

    raise ValueError(f"Unknown tool: {tool_name}")

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
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
            # In case of catastrophic error, print to stderr (won't break JSON-RPC)
            print(f"Server error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()