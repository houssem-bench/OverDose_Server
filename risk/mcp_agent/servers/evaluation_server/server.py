"""
servers/evaluation_server/server.py
──────────────────────────────────────
MCP SERVER — Evaluation / Investigation Metrics
Transport: stdio (JSON-RPC 2.0)

ADDED: judge_pubchem_data — LLM judge for PubChem data validation
"""

import json
import os
import sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import traceback
import re
from groq import Groq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config
from servers.evaluation_server.evaluator import (
    get_investigation_metrics,
    assess_data_completeness
)
from servers.evaluation_server.judge_prompts import (
    JUDGE_SYSTEM_PROMPT,
    build_judge_user_prompt,
    validate_judge_output
)

# Initialize Groq client for LLM tools
_groq = None

def _get_groq():
    global _groq
    if _groq is None:
        _groq = Groq(api_key=config.GROQ_API_KEY)
    return _groq


def _estimate_hazards_with_llm(chemical_name: str, reason: str = "") -> dict:
    """LLM-based hazard estimation - called only when KG has no data"""
    prompt = f"""Estimate likely GHS hazards for this chemical based ONLY on its name.

Chemical: {chemical_name}
Context: {reason if reason else "No hazard data in Knowledge Graph"}

GHS Hazard Categories (return ONLY H-codes from this list):
- H315: Causes skin irritation
- H317: May cause allergic skin reaction
- H318: Causes serious eye damage
- H319: Causes serious eye irritation
- H334: May cause allergy or asthma symptoms
- H335: May cause respiratory irritation
- H340: May cause genetic defects
- H350: May cause cancer
- H360: May damage fertility or the unborn child
- H370: Causes damage to organs
- H372: Causes damage to organs through prolonged exposure

Return ONLY valid JSON:
{{
    "estimated_h_codes": ["H315", "H317"],
    "confidence": 0.7,
    "reasoning": "Common irritant based on name pattern"
}}

If completely unknown, return {{"estimated_h_codes": [], "confidence": 0.2, "reasoning": "No information available"}}"""
    
    try:
        response = _get_groq().chat.completions.create(
            model=config.GROQ_MODEL,
            temperature=0.1,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
        result = json.loads(clean)
        return {
            "source": "LLM_ESTIMATE",
            "estimated_h_codes": result.get("estimated_h_codes", []),
            "confidence": result.get("confidence", 0.3),
            "reasoning": result.get("reasoning", "")
        }
    except Exception as e:
        return {
            "source": "ERROR",
            "estimated_h_codes": [],
            "confidence": 0.1,
            "reasoning": f"LLM call failed: {str(e)[:100]}"
        }


def _estimate_organs_with_llm(chemical_name: str, hazard_codes: list) -> dict:
    """LLM-based organ estimation - called when KG has no organ data"""
    prompt = f"""Estimate likely target organs for this chemical.

Chemical: {chemical_name}
Known hazards: {hazard_codes if hazard_codes else "None specified"}

Common target organs: skin, eyes, respiratory system, liver, kidneys, nervous system

Mapping H-codes to likely organs:
- H315/H317/H318/H319 → skin, eyes
- H334/H335 → respiratory system
- H340/H350/H360 → reproductive system
- H370/H372 → liver, kidneys, nervous system

Return ONLY valid JSON:
{{
    "estimated_organs": ["skin", "eyes"],
    "confidence": 0.7,
    "reasoning": "Based on irritation hazards"
}}

If no information available, return {{"estimated_organs": [], "confidence": 0.2, "reasoning": "Cannot estimate"}}"""
    
    try:
        response = _get_groq().chat.completions.create(
            model=config.GROQ_MODEL,
            temperature=0.1,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
        result = json.loads(clean)
        return {
            "source": "LLM_ESTIMATE",
            "estimated_organs": result.get("estimated_organs", []),
            "confidence": result.get("confidence", 0.3),
            "reasoning": result.get("reasoning", "")
        }
    except Exception as e:
        return {
            "source": "ERROR",
            "estimated_organs": [],
            "confidence": 0.1,
            "reasoning": f"LLM call failed: {str(e)[:100]}"
        }


def _judge_pubchem_data(chemical_name: str, pubchem_classifications: list, pubchem_organs: list) -> dict:
    """
    LLM Judge for PubChem data validation.
    Validates and filters classifications and organs.
    """
    user_prompt = build_judge_user_prompt(chemical_name, pubchem_classifications, pubchem_organs)
    
    try:
        response = _get_groq().chat.completions.create(
            model=config.GROQ_MODEL,
            temperature=0.1,
            max_tokens=800,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )
        content = response.choices[0].message.content
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
        result = json.loads(clean)
        
        # Validate and sanitize output
        validated = validate_judge_output(result, chemical_name)
        
        return {
            "source": "LLM_JUDGE",
            "validated_classifications": validated["validated_classifications"],
            "removed_classifications": validated["removed_classifications"],
            "validated_organs": validated["validated_organs"],
            "removed_organs": validated["removed_organs"],
            "confidence": validated["confidence"],
            "reasoning": validated["reasoning"]
        }
    except Exception as e:
        return {
            "source": "ERROR",
            "validated_classifications": [],
            "removed_classifications": [],
            "validated_organs": [],
            "removed_organs": [],
            "confidence": 0.1,
            "reasoning": f"LLM judge failed: {str(e)[:100]}"
        }


TOOLS = [
    {
        "name": "get_investigation_metrics",
        "description": (
            "Analyze KG results and return structured signals to guide investigation depth. "
            "Pure Python - no LLM."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "chemical_name": {"type": "string"},
                "resolution_result": {"type": "object"},
                "hazard_result": {"type": "object"}
            },
            "required": ["chemical_name", "resolution_result", "hazard_result"]
        }
    },
    {
        "name": "assess_data_completeness",
        "description": "Assess per-field completeness of KG data. Pure Python - no LLM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "resolution_result": {"type": "object"},
                "hazard_result": {"type": "object"},
                "organs_result": {"type": "object"}
            },
            "required": ["resolution_result"]
        }
    },
    {
        "name": "estimate_missing_hazards",
        "description": "Estimate likely GHS hazards when KG has no data. Uses LLM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chemical_name": {"type": "string"},
                "reason": {"type": "string"}
            },
            "required": ["chemical_name"]
        }
    },
    {
        "name": "estimate_missing_organs",
        "description": "Estimate likely target organs when KG has no organ data. Uses LLM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chemical_name": {"type": "string"},
                "hazard_codes": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["chemical_name"]
        }
    },
    {
        "name": "judge_pubchem_data",
        "description": (
            "Validate and filter PubChem API results for chemicals not in KG. "
            "Uses LLM to remove nonsense and assign confidence. "
            "Returns validated classifications and organs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "chemical_name": {"type": "string"},
                "pubchem_classifications": {"type": "array", "items": {"type": "string"}},
                "pubchem_organs": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["chemical_name", "pubchem_classifications", "pubchem_organs"]
        }
    }
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
                "serverInfo": {"name": "evaluation-server", "version": "2.1.0"}
            }
        }

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = request.get("params", {}).get("name")
        args = request.get("params", {}).get("arguments", {})

        try:
            if tool_name == "get_investigation_metrics":
                result = get_investigation_metrics(
                    chemical_name=args.get("chemical_name", ""),
                    resolution_result=args.get("resolution_result", {}),
                    hazard_result=args.get("hazard_result", {})
                )
            elif tool_name == "assess_data_completeness":
                result = assess_data_completeness(
                    resolution_result=args.get("resolution_result", {}),
                    hazard_result=args.get("hazard_result", {}),
                    organs_result=args.get("organs_result")
                )
            elif tool_name == "estimate_missing_hazards":
                result = _estimate_hazards_with_llm(
                    chemical_name=args.get("chemical_name", ""),
                    reason=args.get("reason", "")
                )
            elif tool_name == "estimate_missing_organs":
                result = _estimate_organs_with_llm(
                    chemical_name=args.get("chemical_name", ""),
                    hazard_codes=args.get("hazard_codes", [])
                )
            elif tool_name == "judge_pubchem_data":
                result = _judge_pubchem_data(
                    chemical_name=args.get("chemical_name", ""),
                    pubchem_classifications=args.get("pubchem_classifications", []),
                    pubchem_organs=args.get("pubchem_organs", [])
                )
            else:
                return {
                    "jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }

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


if __name__ == "__main__":
    main()