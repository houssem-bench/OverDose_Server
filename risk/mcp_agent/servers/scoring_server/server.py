"""
scoring_server/server.py
MCP SERVER — Chemical Risk Agent (INTEGRATED VERSION)
Transport: stdio (JSON-RPC 2.0)
"""

import json
import os
import sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import traceback
# Make sibling modules importable
sys.path.insert(0, str(Path(__file__).parent))
import traceback
import contextlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from risk import (
    load_organ_kb,
    score_ingredient_risk,
    score_recurrence_risk,
    score_organ_overlap,
    score_product_risk,
    rank_products,
    run_pipeline,
    apply_user_adjustment,
)

# ------------------------------------------------------------------
# Load KB once at startup, with robust error handling
# ------------------------------------------------------------------
KB_PATH = Path(__file__).parent / "organ_priority_data.json"

try:
    if not KB_PATH.exists():
        print(f"[Risk Server] ERROR: KB file not found at {KB_PATH}", file=sys.stderr)
        sys.exit(1)

    # Suppress any stdout output from ChromaDB / load_organ_kb
    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stdout(devnull):
            load_organ_kb(str(KB_PATH))

    print(f"[Risk Server] Organ KB loaded from {KB_PATH}", file=sys.stderr)

except Exception as e:
    print(f"[Risk Server] FATAL: Failed to load organ KB: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

print(f"[Risk Server] Ready for requests", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# Tool definitions (added user_type to run_full_pipeline)
# ─────────────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "score_ingredient_risk",
        "description": (
            "Score a single chemical ingredient from its evaluated verdict. "
            "Returns danger_level, base_score (0-4), and justification list."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "chemical": {
                    "type": "object",
                    "description": (
                        "A chemicals_evaluated entry from FinalReport with keys: "
                        "name, uid, cas, verdict (danger_level + justification)"
                    ),
                }
            },
            "required": ["chemical"],
        },
    },
    {
        "name": "score_recurrence_risk",
        "description": (
            "Identify chemicals that appear in multiple products and compute "
            "their cross-product recurrence risk score. "
            "Input is the global_summary block from FinalReport."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "global_summary": {
                    "type": "object",
                    "description": "The global_summary field from FinalReport",
                }
            },
            "required": ["global_summary"],
        },
    },
    {
        "name": "score_organ_overlap",
        "description": (
            "Compute cumulative organ overlap risk for a product using EPA HI method. "
            "Looks up organ priority weights and cumulation multipliers from the KB. "
            "Applies synergy factor when ≥2 chemicals target the same organ."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "organ_overlap_data": {
                    "type": "object",
                    "description": "combination_risks.organ_overlap from a product in FinalReport",
                },
                "chemicals_evaluated": {
                    "type": "array",
                    "description": "ingredients.chemicals_evaluated list for the same product",
                    "items": {"type": "object"},
                },
            },
            "required": ["organ_overlap_data", "chemicals_evaluated"],
        },
    },
    {
        "name": "score_product_risk",
        "description": (
            "Compute the full risk score for a single product. "
            "Aggregates ingredient scores + organ overlap scores into a "
            "total_product_score and verdict (LOW / MODERATE / HIGH / CRITICAL)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "product": {
                    "type": "object",
                    "description": "A single product entry from FinalReport products array",
                },
            },
            "required": ["product"],
        },
    },
    {
        "name": "rank_products",
        "description": (
            "Rank a list of product risk result dicts by total_product_score descending. "
            "Returns the sorted list with rank numbers and identifies the highest-risk product."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_risk_results": {
                    "type": "array",
                    "description": "List of outputs from score_product_risk",
                    "items": {"type": "object"},
                }
            },
            "required": ["product_risk_results"],
        },
    },
    {
        "name": "run_full_pipeline",
        "description": (
            "Run the complete chemical risk analysis pipeline on the full FinalReport data. "
            "Steps: score ingredients → recurrence risk → organ overlaps → "
            "product scores → ranking → optional LLM narrative report. "
            "Returns all results in a single structured response."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_data": {
                    "type": "object",
                    "description": "Full contents of FinalReport (products array + global_summary)",
                },
                "user_type": {
                    "type": "string",
                    "description": "Optional: 'asthma', 'diabetes', 'newborn', 'fetal'",
                    "enum": ["asthma", "diabetes", "newborn", "fetal"],
                },
                "generate_llm_report": {
                    "type": "boolean",
                    "description": "Whether to generate a narrative report (default: true)",
                },
            },
            "required": ["input_data"],
        },
    },
    {
        "name": "apply_user_adjustment",
        "description": (
            "Apply user-specific adjustments to organ risk scores. "
            "Asthma → lungs weight increased, Diabetes → pancreas weight increased, "
            "Newborn → brain weight increased, Fetal → reproductive weight increased."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "organ_scores": {
                    "type": "object",
                    "description": "Dictionary of organ → score",
                },
                "user_type": {
                    "type": "string",
                    "description": "'asthma', 'diabetes', 'newborn', or 'fetal'",
                    "enum": ["asthma", "diabetes", "newborn", "fetal"],
                },
            },
            "required": ["organ_scores", "user_type"],
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Request handler (unchanged logic, just uses pre-loaded KB)
# ─────────────────────────────────────────────────────────────────────────────

def handle(request: dict) -> dict | None:
    method = request.get("method")
    rid = request.get("id")

    # MCP lifecycle
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": "0.1.0",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "risk-server", "version": "2.0.0"},
            },
        }

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}

    # Tool dispatch
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
    """Dispatch to the appropriate risk function. NO KB LOADING here."""
    
    if tool_name == "score_ingredient_risk":
        return score_ingredient_risk(args["chemical"])

    if tool_name == "score_recurrence_risk":
        return {"recurrence_risks": score_recurrence_risk(args["global_summary"])}

    if tool_name == "score_organ_overlap":
        results = score_organ_overlap(
            args["organ_overlap_data"],
            args["chemicals_evaluated"],
        )
        return {"organ_overlap_results": results}

    if tool_name == "score_product_risk":
        return score_product_risk(args["product"])

    if tool_name == "rank_products":
        ranked = rank_products(args["product_risk_results"])
        return {
            "ranked_products": [
                {
                    "rank": i + 1,
                    "product_id": p["product_id"],
                    "product_name": p["product_name"],
                    "total_product_score": p["total_product_score"],
                    "verdict": p["verdict"],
                }
                for i, p in enumerate(ranked)
            ],
            "highest_risk_product": {
                "product_id": ranked[0]["product_id"],
                "product_name": ranked[0]["product_name"],
                "score": ranked[0]["total_product_score"],
                "verdict": ranked[0]["verdict"],
            } if ranked else None,
        }

    if tool_name == "run_full_pipeline":
        # Pass user_type to pipeline
        return run_pipeline(
            input_data=args["input_data"],
            user_type=args.get("user_type"),
            generate_llm=args.get("generate_llm_report", True),
        )

    if tool_name == "apply_user_adjustment":
        return apply_user_adjustment(args["organ_scores"], args["user_type"])

    raise ValueError(f"Unknown tool: {tool_name}")


# ─────────────────────────────────────────────────────────────────────────────
# stdio JSON-RPC loop (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

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

if __name__ == "__main__":
    main()