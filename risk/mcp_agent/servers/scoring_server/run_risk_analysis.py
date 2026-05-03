"""
servers/risk_server/run_risk_analysis.py
─────────────────────────────────────────────────────────────────────────────
STANDALONE TEST SCRIPT - For development only.

This script is NOT used by the MCP agent. It exists ONLY for:
  - Manual testing of the risk engine
  - Debugging organ KB loading
  - Validating risk calculations

To run: python servers/risk_server/run_risk_analysis.py [--no-llm]

When the agent uses this server via MCP, it calls server.py directly.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Path setup
THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(ROOT))

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

DEFAULT_INPUT_PATH = THIS_DIR / "Input.json"
DEFAULT_KB_PATH = THIS_DIR / "organ_priority_data.json"


def _banner(title: str) -> None:
    print(f"\n{'═' * 65}\n  {title}\n{'═' * 65}")


def _section(title: str) -> None:
    print(f"\n{'─' * 65}\n  {title}\n{'─' * 65}")


def _badge(level: str) -> str:
    return {
        "CRITICAL": "🔴 CRITICAL",
        "HIGH": "🟠 HIGH",
        "MODERATE": "🟡 MODERATE",
        "LOW": "🟢 LOW",
        "SAFE": "🟢 SAFE",
        "UNKNOWN": "⚪ UNKNOWN",
    }.get(level, f"⚪ {level}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chemical Risk Analysis Pipeline (Test)")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Path to Input.json")
    parser.add_argument("--kb", default=str(DEFAULT_KB_PATH), help="Path to organ_priority_data.json")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM report generation")
    parser.add_argument("--user-type", choices=["asthma", "diabetes", "newborn", "fetal"], 
                        help="Apply user-specific adjustments")
    args = parser.parse_args()

    _banner("CHEMICAL RISK ANALYSIS PIPELINE (TEST MODE)")
    print(f"  Input     : {args.input}")
    print(f"  KB        : {args.kb}")
    print(f"  LLM       : {'disabled' if args.no_llm else 'enabled → Groq'}")
    print(f"  User type : {args.user_type or 'none'}")

    # Load data
    with open(args.input, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    products = input_data.get("products", [])
    global_summary = input_data.get("global_summary", {})

    # Load KB
    print("\n  Loading organ Knowledge Base into ChromaDB...")
    load_organ_kb(args.kb)
    print("  ✅ KB loaded.\n")

    # Run full pipeline
    result = run_pipeline(
        input_data=input_data,
        user_type=args.user_type,
        generate_llm=not args.no_llm,
    )

    # Display results
    _section("RESULTS")
    
    print("\n  Product Rankings:")
    for r in result.get("ranked_products", []):
        print(f"    #{r['rank']}: {r['product_name']} - {_badge(r['verdict'])} (score: {r['total_product_score']})")

    if result.get("user_type_applied"):
        print(f"\n  ✅ User adjustments applied: {result['user_type_applied']}")

    if result.get("llm_report"):
        _section("LLM NARRATIVE REPORT (Groq)")
        print("\n" + result["llm_report"])

    # Save full result
    out_path = THIS_DIR / "risk_analysis_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n  ✅ Full result saved → {out_path}")

    _banner("TEST COMPLETE")


if __name__ == "__main__":
    main()