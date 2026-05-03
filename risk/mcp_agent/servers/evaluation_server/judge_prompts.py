"""
judge_prompts.py — LLM Judge Prompts for PubChem Data Validation

Used to validate and filter PubChem API results for chemicals not in KG.
"""

# System prompt for LLM Judge
JUDGE_SYSTEM_PROMPT = """You are a chemical safety expert and data validator. Your job is to review PubChem API results and determine if the chemical classification and organ impact data are accurate and reasonable.

You will receive:
- Chemical name
- PubChem classifications (list of categories)
- PubChem target organs (list of organ terms)

Your tasks:
1. Validate classifications: Remove any that are clearly wrong or nonsense
2. Keep only classifications from this allowed list:
   - Cosmetics, CosIng, Drugs, Drug Clinical Phase, Endocrine Disruptors
   - Food Additives, Food Contact Substances, Pesticides, EU Pesticide Approval
   - Pesticide Type, Flavouring Agents, Fragrances, Lipids, Polymers

3. Validate organs: Remove any that cannot be mapped to these standard organs:
   - liver, kidneys, skin, eyes, respiratory_system, central_nervous_system
   - cardiovascular_system, reproductive_system, developmental, endocrine
   - gastrointestinal_tract, blood_haematopoietic_system, immune_system
   - urinary_system, cancer, nervous_system

4. Assign confidence score (0.0-1.0) based on data quality:
   - 0.8-1.0: Clear, specific, multiple sources
   - 0.6-0.7: Plausible, reasonable inference
   - 0.4-0.5: Vague or uncertain, some doubt
   - 0.2-0.3: Very uncertain, likely guess
   - 0.0-0.1: Clearly wrong or no data

5. Provide brief reasoning for decisions.

Return ONLY valid JSON with this structure:
{
    "validated_classifications": ["class1", "class2"],
    "removed_classifications": ["bad_class"],
    "validated_organs": ["organ1", "organ2"],
    "removed_organs": ["bad_organ"],
    "confidence": 0.85,
    "reasoning": "Brief explanation of decisions"
}

If the data is completely unusable, return:
{
    "validated_classifications": [],
    "removed_classifications": [],
    "validated_organs": [],
    "removed_organs": [],
    "confidence": 0.1,
    "reasoning": "Data is incomplete or nonsense"
}"""


def build_judge_user_prompt(
    chemical_name: str,
    pubchem_classifications: list,
    pubchem_organs: list
) -> str:
    """Build user prompt for LLM judge."""
    
    classifications_str = "\n".join(f"  - {c}" for c in pubchem_classifications) if pubchem_classifications else "  (none)"
    organs_str = "\n".join(f"  - {o}" for o in pubchem_organs) if pubchem_organs else "  (none)"
    
    return f"""Chemical Name: {chemical_name}

PubChem Classifications:
{classifications_str}

PubChem Target Organs:
{organs_str}

Validate this data. Remove nonsense entries. Return JSON only."""


# Allowed classifications (from KG ChemicalClass nodes)
ALLOWED_CLASSIFICATIONS = {
    "Cosmetics", "CosIng", "Drugs", "Drug Clinical Phase", "Endocrine Disruptors",
    "Food Additives", "Food Contact Substances", "Pesticides", "EU Pesticide Approval",
    "Pesticide Type", "Flavouring Agents", "Fragrances", "Lipids", "Polymers"
}

# Valid organs for mapping (to KG TargetOrgan UIDs)
VALID_ORGANS = {
    "liver", "kidneys", "skin", "eyes", "respiratory_system", "central_nervous_system",
    "cardiovascular_system", "reproductive_system", "developmental", "endocrine",
    "gastrointestinal_tract", "blood_haematopoietic_system", "immune_system",
    "urinary_system", "cancer", "nervous_system", "blood_cholinesterase", "ocular_eyes"
}


def validate_judge_output(output: dict, chemical_name: str) -> dict:
    """
    Validate and sanitize LLM judge output to ensure it matches expected format.
    """
    if not isinstance(output, dict):
        return {
            "validated_classifications": [],
            "removed_classifications": [],
            "validated_organs": [],
            "removed_organs": [],
            "confidence": 0.2,
            "reasoning": f"Invalid output format for {chemical_name}"
        }
    
    # Ensure all expected keys exist
    result = {
        "validated_classifications": output.get("validated_classifications", []),
        "removed_classifications": output.get("removed_classifications", []),
        "validated_organs": output.get("validated_organs", []),
        "removed_organs": output.get("removed_organs", []),
        "confidence": max(0.0, min(1.0, output.get("confidence", 0.5))),
        "reasoning": output.get("reasoning", "No reasoning provided")
    }
    
    # Filter to only allowed classifications
    result["validated_classifications"] = [
        c for c in result["validated_classifications"] 
        if c in ALLOWED_CLASSIFICATIONS
    ]
    
    # Filter to only valid organs
    result["validated_organs"] = [
        o for o in result["validated_organs"] 
        if o in VALID_ORGANS
    ]
    
    return result