"""
organ_mapper.py — Map PubChem organ terms to KG TargetOrgan UIDs

PubChem returns terms like "hepatic", "renal", "pulmonary"
This module maps them to your KG's 19 specific organ IDs
"""
from typing import List, Dict
# Mapping from PubChem/common terms to KG TargetOrgan UIDs
ORGAN_TERM_TO_KG_UID = {
    # Liver
    "hepatic": "organ_liver",
    "liver": "organ_liver",
    "hepatocellular": "organ_liver",
    "hepatotoxicity": "organ_liver",
    "hepatotoxic": "organ_liver",
    
    # Kidneys
    "renal": "organ_kidneys",
    "kidney": "organ_kidneys",
    "nephrotoxic": "organ_kidneys",
    "nephrotoxicity": "organ_kidneys",
    
    # Skin
    "dermal": "organ_skin",
    "skin": "organ_skin",
    "dermatitis": "organ_skin",
    "cutaneous": "organ_skin",
    
    # Eyes
    "ocular": "organ_eyes",
    "eye": "organ_eyes",
    "conjunctival": "organ_eyes",
    "ophthalmic": "organ_eyes",
    
    # Respiratory System
    "pulmonary": "organ_respiratory_system",
    "lung": "organ_respiratory_system",
    "respiratory": "organ_respiratory_system",
    "bronchial": "organ_respiratory_system",
    "asthma": "organ_respiratory_system",
    
    # Central Nervous System
    "brain": "organ_central_nervous_system",
    "cns": "organ_central_nervous_system",
    "neurological": "organ_central_nervous_system",
    "neurotoxic": "organ_central_nervous_system",
    "neural": "organ_central_nervous_system",
    
    # Cardiovascular System
    "cardiac": "organ_cardiovascular_system",
    "heart": "organ_cardiovascular_system",
    "cardiovascular": "organ_cardiovascular_system",
    "myocardial": "organ_cardiovascular_system",
    
    # Reproductive System
    "reproductive": "organ_reproductive_system",
    "fertility": "organ_reproductive_system",
    "developmental": "organ_developmental",
    "teratogenic": "organ_developmental",
    "prenatal": "organ_developmental",
    
    # Endocrine
    "endocrine": "organ_endocrine",
    "hormone": "organ_endocrine",
    "thyroid": "organ_endocrine",
    
    # Gastrointestinal
    "gastrointestinal": "organ_gastrointestinal_tract",
    "stomach": "organ_gastrointestinal_tract",
    "intestinal": "organ_gastrointestinal_tract",
    "gi": "organ_gastrointestinal_tract",
    
    # Blood/Hematopoietic
    "hematopoietic": "organ_blood_haematopoietic_system",
    "blood": "organ_blood_haematopoietic_system",
    "bone marrow": "organ_blood_haematopoietic_system",
    
    # Immune System
    "immune": "organ_immune_system",
    "immunotoxicity": "organ_immune_system",
    "allergy": "organ_immune_system",
    
    # Urinary System
    "urinary": "organ_urinary_system",
    "bladder": "organ_urinary_system",
    
    # Cancer
    "carcinogenic": "organ_cancer",
    "carcinogen": "organ_cancer",
    "tumor": "organ_cancer",
    "neoplastic": "organ_cancer",
    
    # Nervous System (peripheral)
    "peripheral nerve": "organ_nervous_system",
    "neuropathy": "organ_nervous_system",
    
    # Other
    "systemic": None,  # Too vague, skip
    "local": None,
}


# Organ names for display (UID -> display name)
KG_ORGAN_DISPLAY = {
    "organ_liver": "Liver",
    "organ_kidneys": "Kidneys",
    "organ_skin": "Skin",
    "organ_eyes": "Eyes",
    "organ_respiratory_system": "Respiratory System",
    "organ_central_nervous_system": "Central Nervous System",
    "organ_cardiovascular_system": "Cardiovascular System",
    "organ_reproductive_system": "Reproductive System",
    "organ_developmental": "Developmental",
    "organ_endocrine": "Endocrine System",
    "organ_gastrointestinal_tract": "Gastrointestinal Tract",
    "organ_blood_haematopoietic_system": "Blood/Haematopoietic System",
    "organ_immune_system": "Immune System",
    "organ_urinary_system": "Urinary System",
    "organ_cancer": "Cancer",
    "organ_nervous_system": "Nervous System",
    "organ_blood_cholinesterase": "Blood Cholinesterase",
    "organ_ocular_eyes": "Ocular (Eyes)",
}


def map_organ_term_to_kg(term: str) -> str:
    """
    Map a single organ term to KG organ UID.
    Returns None if no mapping found.
    """
    term_lower = term.lower().strip()
    
    # Direct match
    if term_lower in ORGAN_TERM_TO_KG_UID:
        return ORGAN_TERM_TO_KG_UID[term_lower]
    
    # Partial match (e.g., "hepatic damage" -> "hepatic")
    for key, uid in ORGAN_TERM_TO_KG_UID.items():
        if key in term_lower:
            return uid
    
    return None


def map_organ_terms_to_kg(terms: List[str]) -> List[Dict]:
    """
    Map a list of organ terms to KG organ UIDs.
    Returns list of dicts with uid, name, original_term.
    """
    mapped = {}
    
    for term in terms:
        uid = map_organ_term_to_kg(term)
        if uid:
            if uid not in mapped:
                mapped[uid] = {
                    "uid": uid,
                    "name": KG_ORGAN_DISPLAY.get(uid, uid.replace("organ_", "").replace("_", " ").title()),
                    "original_terms": []
                }
            mapped[uid]["original_terms"].append(term)
    
    return list(mapped.values())


def filter_known_organs(organs: List[Dict]) -> List[Dict]:
    """
    Filter list of organs to only those that are in the KG (19 specific organs).
    Returns only organs that have valid UIDs in KG.
    """
    valid_uids = set(KG_ORGAN_DISPLAY.keys())
    return [o for o in organs if o.get("uid") in valid_uids]


def get_all_kg_organ_uids() -> List[str]:
    """Return list of all valid KG organ UIDs."""
    return list(KG_ORGAN_DISPLAY.keys())


def get_organ_display_name(uid: str) -> str:
    """Get display name for a KG organ UID."""
    return KG_ORGAN_DISPLAY.get(uid, uid.replace("organ_", "").replace("_", " ").title())


# Test function
if __name__ == "__main__":
    print("Testing Organ Mapper...")
    
    test_terms = ["hepatic", "renal", "pulmonary", "brain", "eye", "skin", "gastrointestinal", "unknown_organ"]
    
    for term in test_terms:
        uid = map_organ_term_to_kg(term)
        print(f"  '{term}' → {uid}")
    
    print("\nTesting batch mapping...")
    result = map_organ_terms_to_kg(test_terms)
    for organ in result:
        print(f"  {organ['uid']}: {organ['name']} (from: {organ['original_terms']})")