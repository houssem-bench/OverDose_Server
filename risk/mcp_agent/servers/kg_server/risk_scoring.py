"""
risk_scoring.py — Multi-factor chemical risk scoring

Formula:
Total Risk Score = (Hazard_Score × 0.35) + (Organ_Score × 0.35) + (Class_Score × 0.20) + (Usage_Score × 0.10)

Output: score (0-5) and verdict (CRITICAL/HIGH/MODERATE/LOW/SAFE)
"""

from typing import List, Dict, Any, Tuple

# Organ scores (based on KG TargetOrgan UIDs)
ORGAN_SCORES = {
    # Score 5: Irreversible, vital organs
    "organ_central_nervous_system": 5,
    "organ_liver": 5,
    "organ_kidneys": 5,
    "organ_cancer": 5,
    
    # Score 4: Vital, limited repair
    "organ_reproductive_system": 4,
    "organ_developmental": 4,
    "organ_cardiovascular_system": 4,
    "organ_blood_haematopoietic_system": 4,
    
    # Score 3: Systemic, function-critical
    "organ_respiratory_system": 3,
    "organ_endocrine": 3,
    "organ_immune_system": 3,
    "organ_nervous_system": 3,
    
    # Score 2: Local, potential permanent damage
    "organ_eyes": 2,
    "organ_ocular_eyes": 2,
    "organ_skin": 2,
    "organ_gastrointestinal_tract": 2,
    "organ_urinary_system": 2,
    
    # Score 1: Low criticality (default)
    "organ_blood_cholinesterase": 1,
}

DEFAULT_ORGAN_SCORE = 0


# Chemical class scores (based on KG ChemicalClass values)
CLASS_SCORES = {
    "Endocrine Disruptors": 5,
    "Drugs": 4,
    "Drug Clinical Phase": 4,
    "Pesticides": 4,
    "EU Pesticide Approval": 4,
    "Pesticide Type": 4,
    "Food Contact Substances": 3,
    "Fragrances": 2,
    "Cosmetics": 2,
    "CosIng": 2,
    "Flavouring Agents": 2,
    "Polymers": 1,
    "Lipids": 1,
}
DEFAULT_CLASS_SCORE = 0


# Usage scores based on product_usage value
USAGE_SCORES = {
    "detergent": 4,
    "cosmetics": 3,
    "cosmetic": 3,
    "food": 3,
    "household": 4,
    "professional": 4,
    "industrial": 2,
}

DEFAULT_USAGE_SCORE = 2


# Risk thresholds
RISK_THRESHOLDS = [
    (5.0, "CRITICAL"),
    (4.5, "HIGH"),
    (3.0, "MODERATE"),
    (2.0, "LOW"),
    (0.0, "SAFE"),
]

def calculate_organ_score(target_organs: List[Dict]) -> Tuple[int, str]:
    if not target_organs:
        return DEFAULT_ORGAN_SCORE, "No target organs identified"
    
    scores = []
    organ_names = []
    for organ in target_organs:
        uid = organ.get("uid") if isinstance(organ, dict) else None
        name = organ.get("name") if isinstance(organ, dict) else organ
        # Skip if name is None or empty
        if not name:
            continue
        if uid:
            score = ORGAN_SCORES.get(uid, DEFAULT_ORGAN_SCORE)
            scores.append(score)
            organ_names.append(name)
        else:
            scores.append(DEFAULT_ORGAN_SCORE)
            organ_names.append(name)
    
    if not scores:
        return DEFAULT_ORGAN_SCORE, "No valid target organs with names"
    
    avg_score = round(sum(scores) / len(scores), 1)
    justification = f"Organs affected: {', '.join(organ_names[:5])} (average severity: {avg_score})"
    return int(avg_score), justification
def calculate_class_score(chemical_classes: List[str]) -> Tuple[int, str]:
    """
    Calculate class score from list of chemical classes.
    Returns (score, justification)
    """
    if not chemical_classes:
        return DEFAULT_CLASS_SCORE, "No chemical class information available"
    
    highest_score = 0
    highest_class = None
    for cls in chemical_classes:
        score = CLASS_SCORES.get(cls, DEFAULT_CLASS_SCORE)
        if score > highest_score:
            highest_score = score
            highest_class = cls
    
    justification = f"Chemical class: {highest_class} (score: {highest_score})" if highest_class else "No recognizable chemical class"
    return highest_score, justification


def calculate_usage_score(product_usage: str) -> Tuple[int, str]:
    """
    Calculate usage score from product usage string.
    Returns (score, justification)
    """
    usage_lower = product_usage.lower() if product_usage else ""
    score = USAGE_SCORES.get(usage_lower, DEFAULT_USAGE_SCORE)
    justification = f"Product usage: {product_usage or 'unknown'} (exposure relevance: {score})"
    return score, justification


def get_verdict_from_score(total_score: float) -> str:
    """Convert numeric score to verdict string."""
    for threshold, verdict in RISK_THRESHOLDS:
        if total_score >= threshold:
            return verdict
    return "UNKNOWN"


def calculate_total_risk(
    hazard_score: int,
    hazard_justification: str,
    organ_score: int,
    organ_justification: str,
    class_score: int,
    class_justification: str,
    usage_score: int,
    usage_justification: str,
) -> Dict[str, Any]:
    """
    Calculate total risk score using weighted formula.
    
    Formula: (H × 0.35) + (O × 0.35) + (C × 0.20) + (U × 0.10)
    """
    hazard_contribution = round(hazard_score * 0.35, 3)
    organ_contribution = round(organ_score * 0.35, 3)
    class_contribution = round(class_score * 0.20, 3)
    usage_contribution = round(usage_score * 0.10, 3)
    
    total_score = round(hazard_contribution + organ_contribution + class_contribution + usage_contribution, 2)
    verdict = get_verdict_from_score(total_score)
    
    return {
        "total_score": total_score,
        "verdict": verdict,
        "breakdown": {
            "hazard": {
                "raw_score": hazard_score,
                "weight": 0.35,
                "contribution": hazard_contribution,
                "justification": hazard_justification
            },
            "organ": {
                "raw_score": organ_score,
                "weight": 0.35,
                "contribution": organ_contribution,
                "justification": organ_justification
            },
            "class": {
                "raw_score": class_score,
                "weight": 0.20,
                "contribution": class_contribution,
                "justification": class_justification
            },
            "usage": {
                "raw_score": usage_score,
                "weight": 0.10,
                "contribution": usage_contribution,
                "justification": usage_justification
            }
        }
    }


def calculate_risk_for_chemical(
    ghs_pictograms: List[Dict],
    h_codes: List[str],
    target_organs: List[Dict],
    chemical_classes: List[str],
    product_usage: str,
) -> Dict[str, Any]:
    """
    Calculate complete risk for a chemical using all available data.
    
    Returns:
    {
        "total_score": float,
        "verdict": str,
        "breakdown": {...},
        "hazard_score": int,
        "organ_score": int,
        "class_score": int,
        "usage_score": int
    }
    """
    from .ghs_mapper import calculate_hazard_score
    
    # Calculate hazard score
    hazard_score, hazard_justification = calculate_hazard_score(ghs_pictograms, h_codes)
    
    # Calculate organ score
    organ_score, organ_justification = calculate_organ_score(target_organs)
    
    # Calculate class score
    class_score, class_justification = calculate_class_score(chemical_classes)
    
    # Calculate usage score
    usage_score, usage_justification = calculate_usage_score(product_usage)
    
    # Calculate total
    result = calculate_total_risk(
        hazard_score, hazard_justification,
        organ_score, organ_justification,
        class_score, class_justification,
        usage_score, usage_justification
    )
    
    result.update({
        "hazard_score": hazard_score,
        "organ_score": organ_score,
        "class_score": class_score,
        "usage_score": usage_score,
    })
    
    return result