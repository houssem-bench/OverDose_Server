"""
kg_client.py — Neo4j Knowledge Graph Client - PRODUCTION VERSION
────────────────────────────────────────────────────────────────
ADDED: get_complete_chemical_data() - One call returns everything
"""

import os
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import traceback
from typing import Dict, List, Optional, Tuple

from neo4j import GraphDatabase
from dotenv import load_dotenv

from queries import (
    RESOLVE_INGREDIENT_EXACT,
    RESOLVE_INGREDIENT_CAS,
    RESOLVE_INGREDIENT_SYNONYM,
    GET_COMPLETE_CHEMICAL_DATA,
    GET_FULL_PROFILE,
    GET_HAZARDS_LIST,
    GET_ORGANS_LIST,
    GET_EXPOSURE_LIMITS_LIST,
    HAS_CRITICAL_HAZARD,
    GET_ORGAN_FOR_MULTIPLE_CHEMICALS,
    TEST_QUERY,
)

load_dotenv()

# Critical H-codes
CRITICAL_H_CODES = {"H340", "H341", "H350", "H351", "H360", "H361", "H362", "H370", "H372"}

# Confidence scores
CONFIDENCE_SCORES = {
    "exact_match": 0.95,
    "cas_match": 0.95,
    "synonym_match": 0.85,
    "not_found": 0.0
}


class KGClient:

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver = None

    def connect(self):
        if not self.uri or not self.user or not self.password:
            raise ValueError("Missing Neo4j credentials")
        
        self.driver = GraphDatabase.driver(
            self.uri, auth=(self.user, self.password)
        )
        try:
            with self.driver.session() as session:
                session.run("RETURN 1").single()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")
        return self.driver

    def close(self):
        if self.driver:
            self.driver.close()

    # ── internal helpers ──────────────────────────────────────────────────────

    def _is_cas(self, text: str) -> bool:
        return bool(re.match(r'^\d{2,7}-\d{2}-\d$', text.strip()))

    def _normalize_name(self, name: str) -> str:
        return name.strip().upper()

    def _one(self, query: str, params: dict) -> dict:
        with self.driver.session() as s:
            rec = s.run(query, params).single()
            return dict(rec) if rec else None

    def _collect(self, query: str, params: dict) -> list:
        with self.driver.session() as s:
            rec = s.run(query, params).single()
            return rec[0] if rec else []

    # ── TOOL 1: resolve_ingredient (NO PARTIAL MATCH) ─────────────────────────

    def resolve_ingredient(self, name: str) -> dict:
        original_name = name
        
        result = self._one(RESOLVE_INGREDIENT_EXACT, {"name": name})
        if result and result.get("uid"):
            result["match_strategy"] = "exact_match"
            result["confidence"] = CONFIDENCE_SCORES["exact_match"]
            result["original_name"] = original_name
            result["unresolved"] = False
            return result

        if self._is_cas(name):
            result = self._one(RESOLVE_INGREDIENT_CAS, {"name": name})
            if result and result.get("uid"):
                result["match_strategy"] = "cas_match"
                result["confidence"] = CONFIDENCE_SCORES["cas_match"]
                result["original_name"] = original_name
                result["unresolved"] = False
                return result

        result = self._one(RESOLVE_INGREDIENT_SYNONYM, {"name": name})
        if result and result.get("uid"):
            result["match_strategy"] = "synonym_match"
            result["confidence"] = CONFIDENCE_SCORES["synonym_match"]
            result["original_name"] = original_name
            result["unresolved"] = False
            return result

        return {
            "original_name": original_name,
            "uid": None,
            "match_strategy": "not_found",
            "confidence": CONFIDENCE_SCORES["not_found"],
            "unresolved": True,
            "error": f"Chemical not found in KG: {original_name}",
            "suggestion": self._get_search_suggestion(original_name)
        }

    def _get_search_suggestion(self, name: str) -> Optional[str]:
        name_upper = name.upper()
        suggestions = {
            "AQUA": "Try 'WATER' (water may not be in KG)",
            "WATER": "Try 'AQUA' (water may not be in KG)",
            "SLS": "Try 'SODIUM LAURYL SULFATE'",
            "SLES": "Try 'SODIUM LAURETH SULFATE'",
            "PARFUM": "Fragrance - may be mixture of multiple chemicals",
        }
        for key, suggestion in suggestions.items():
            if key in name_upper:
                return suggestion
        return "Chemical may not be in KG - will use LLM estimate"

    # ── TOOL 2: get_hazard_profile ────────────────────────────────────────────

    def get_hazard_profile(self, uid: str) -> dict:
        hazards = self._collect(GET_HAZARDS_LIST, {"uid": uid})
        h_codes = [h["code"] for h in hazards if h.get("code")]
        signals = [h["signal"] for h in hazards if h.get("signal")]
        critical_found = [c for c in h_codes if c in CRITICAL_H_CODES]

        return {
            "uid": uid,
            "h_codes": h_codes,
            "highest_signal": "Danger" if "Danger" in signals
                              else ("Warning" if signals else "None"),
            "has_danger": "Danger" in signals,
            "has_critical_hazard": len(critical_found) > 0,
            "critical_hazards": critical_found,
            "hazard_count": len(hazards),
            "hazards": hazards,
            "confidence": 0.9 if h_codes else (0.5 if hazards else 0.3)
        }

    # ── NEW TOOL: get_complete_chemical_data (ONE CALL RETURNS EVERYTHING) ────

    def get_complete_chemical_data(self, uid: str) -> dict:
        """
        Get ALL chemical data in ONE query.
        Returns identity, hazards, GHS pictograms, target organs,
        chemical classes, use categories, exposure effects, limits, etc.
        """
        result = self._one(GET_COMPLETE_CHEMICAL_DATA, {"uid": uid})
        
        if not result:
            return {
                "uid": uid, 
                "error": "Chemical not found", 
                "unresolved": True
            }
        
        # Extract hazards
        hazards = result.get("hazards") or []
        h_codes = [h["code"] for h in hazards if h.get("code")]
        signals = [h["signal"] for h in hazards if h.get("signal")]
        critical_h_codes = [c for c in h_codes if c in CRITICAL_H_CODES]
        
        # Calculate confidence based on data completeness
        confidence = 0.3  # base for having UID
        if h_codes:
            confidence += 0.25
        if result.get("target_organs"):
            confidence += 0.2
        if result.get("ghs_pictograms"):
            confidence += 0.15
        if result.get("chemical_classes"):
            confidence += 0.05
        if result.get("exposure_limits"):
            confidence += 0.05
        confidence = min(round(confidence, 2), 1.0)
        
        return {
            # Identity
            "uid": result.get("uid"),
            "name": result.get("name"),
            "preferred_name": result.get("preferred_name"),
            "cas": result.get("cas"),
            "molecular_formula": result.get("molecular_formula"),
            "molecular_weight": result.get("molecular_weight"),
            "description": result.get("description"),
            "synonyms": result.get("synonyms") or [],
            
            # Hazard
            "h_codes": h_codes,
            "highest_signal": "Danger" if "Danger" in signals 
                              else ("Warning" if signals else "None"),
            "has_critical_hazard": len(critical_h_codes) > 0,
            "critical_hazards": critical_h_codes,
            "hazards": hazards,
            
            # GHS Pictograms
            "ghs_pictograms": result.get("ghs_pictograms") or [],
            
            # Target Organs
            "target_organs": result.get("target_organs") or [],
            
            # Chemical Classes
            "chemical_classes": result.get("chemical_classes") or [],
            
            # Use Categories
            "use_categories": result.get("use_categories") or [],
            
            # Toxicity Measures
            "toxicity_measures": result.get("toxicity_measures") or [],
            
            # Exposure Limits
            "exposure_limits": result.get("exposure_limits") or [],
            
            # Exposure Effects
            "skin_effects": result.get("skin_effects") or [],
            "eye_effects": result.get("eye_effects") or [],
            "inhalation_effects": result.get("inhalation_effects") or [],
            "ingestion_effects": result.get("ingestion_effects") or [],
            
            # Excretion Routes
            "excretion_routes": result.get("excretion_routes") or [],
            
            # Metadata
            "data_confidence": confidence,
            "unresolved": False
        }

    # ── TOOL 3: get_full_profile (legacy, kept for compatibility) ─────────────

    def get_full_profile(self, uid: str) -> dict:
        r = self._one(GET_FULL_PROFILE, {"uid": uid})
        if not r:
            return {"uid": uid, "error": "Chemical not found", "unresolved": True}

        hazards = r.get("hazards") or []
        h_codes = [h["code"] for h in hazards if h.get("code")]
        signals = [h["signal"] for h in hazards if h.get("signal")]
        critical = [c for c in h_codes if c in CRITICAL_H_CODES]

        confidence = 0.3
        if h_codes:
            confidence += 0.4
        if r.get("target_organs"):
            confidence += 0.2
        if r.get("toxicity"):
            confidence += 0.1
        confidence = min(round(confidence, 2), 1.0)

        return {
            "uid": r.get("uid"),
            "name": r.get("name"),
            "preferred_name": r.get("preferred_name"),
            "cas": r.get("cas"),
            "molecular_formula": r.get("molecular_formula"),
            "molecular_weight": r.get("molecular_weight"),
            "description": r.get("description"),
            "synonyms": r.get("synonyms") or [],
            "highest_signal": "Danger" if "Danger" in signals
                              else ("Warning" if signals else "None"),
            "has_danger": "Danger" in signals,
            "has_critical_hazard": len(critical) > 0,
            "critical_hazards": critical,
            "h_codes": h_codes,
            "hazards": hazards,
            "target_organs": [o for o in (r.get("target_organs") or []) if o],
            "chemical_classes": [c for c in (r.get("chemical_classes") or []) if c],
            "toxicity": [t for t in (r.get("toxicity") or []) if t.get("type")],
            "exposure_limits": [e for e in (r.get("exposure_limits") or []) if e.get("standard")],
            "skin_effects": [e for e in (r.get("skin_effects") or []) if e],
            "eye_effects": [e for e in (r.get("eye_effects") or []) if e],
            "inhalation_effects": [e for e in (r.get("inhalation_effects") or []) if e],
            "ingestion_effects": [e for e in (r.get("ingestion_effects") or []) if e],
            "excretion_routes": [e for e in (r.get("excretion_routes") or []) if e],
            "data_confidence": confidence
        }

    # ── TOOL 4: get_target_organs ─────────────────────────────────────────────

    def get_target_organs(self, uid: str) -> dict:
        organs = self._collect(GET_ORGANS_LIST, {"uid": uid})
        return {
            "uid": uid,
            "organs": [o for o in organs if o],
            "count": len([o for o in organs if o]),
            "confidence": 0.8 if organs else 0.3
        }

    # ── TOOL 5: get_exposure_limits ───────────────────────────────────────────

    def get_exposure_limits(self, uid: str) -> dict:
        limits = self._collect(GET_EXPOSURE_LIMITS_LIST, {"uid": uid})
        valid_limits = [l for l in limits if l.get("standard")]
        return {
            "uid": uid,
            "exposure_limits": valid_limits,
            "count": len(valid_limits),
            "has_limits": len(valid_limits) > 0,
            "confidence": 0.8 if valid_limits else 0.2
        }

    # ── utility for combination server ───────────────────────────────────────

    def get_organs_for_multiple(self, uids: list) -> list:
        with self.driver.session() as s:
            return [dict(r) for r in
                    s.run(GET_ORGAN_FOR_MULTIPLE_CHEMICALS, {"uids": uids})]

    def test_connection(self) -> bool:
        try:
            with self.driver.session() as s:
                s.run("RETURN 1").single()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False


if __name__ == "__main__":
    client = KGClient()
    client.connect()

    print("=" * 60)
    print("KG CLIENT — PRODUCTION VERSION")
    print("=" * 60)

    r = client.resolve_ingredient("SODIUM LAURETH SULFATE")
    print(f"\n[TEST 1] resolve_ingredient('AQUA'):")
    print(f"  Strategy: {r.get('match_strategy')}")
    print(f"  Unresolved: {r.get('unresolved')}")

    r = client.resolve_ingredient("Sodium Laureth Sulfate")
    print(f"\n[TEST 2] resolve_ingredient('Sodium Laureth Sulfate'):")
    print(f"  Strategy: {r.get('match_strategy')}")
    print(f"  UID: {r.get('uid')}")
    print(f"  Confidence: {r.get('confidence')}")

    client.close()
    print("\n✅ KG CLIENT READY")