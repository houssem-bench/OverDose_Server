"""
ghs_mapper.py — Map H-codes to GHS Pictograms (Official UN GHS Mapping)

Based on UN Globally Harmonized System (GHS) Purple Book Revision 9
"""

# H-code patterns to GHS Pictogram UID mapping
H_CODE_TO_PICTOGRAM = {
    # Health Hazard (Carcinogen, Mutagen, Reproductive toxin, STOT)
    "H340": "ghs_health_hazard",
    "H341": "ghs_health_hazard",
    "H350": "ghs_health_hazard",
    "H351": "ghs_health_hazard",
    "H360": "ghs_health_hazard",
    "H361": "ghs_health_hazard",
    "H362": "ghs_health_hazard",
    "H370": "ghs_health_hazard",
    "H371": "ghs_health_hazard",
    "H372": "ghs_health_hazard",
    "H373": "ghs_health_hazard",
    
    # Acute Toxicity
    "H300": "ghs_acute_toxic",
    "H301": "ghs_acute_toxic",
    "H310": "ghs_acute_toxic",
    "H311": "ghs_acute_toxic",
    "H330": "ghs_acute_toxic",
    "H331": "ghs_acute_toxic",
    
    # Corrosive
    "H314": "ghs_corrosive",
    "H318": "ghs_corrosive",
    
    # Irritant
    "H315": "ghs_irritant",
    "H317": "ghs_irritant",
    "H319": "ghs_irritant",
    "H335": "ghs_irritant",
    "H336": "ghs_irritant",
    
    # Environmental Hazard
    "H400": "ghs_environmental_hazard",
    "H410": "ghs_environmental_hazard",
    "H411": "ghs_environmental_hazard",
    "H412": "ghs_environmental_hazard",
    "H413": "ghs_environmental_hazard",
    
    # Flammable
    "H220": "ghs_flammable",
    "H221": "ghs_flammable",
    "H222": "ghs_flammable",
    "H223": "ghs_flammable",
    "H224": "ghs_flammable",
    "H225": "ghs_flammable",
    "H226": "ghs_flammable",
    
    # Oxidizer
    "H270": "ghs_oxidizer",
    "H271": "ghs_oxidizer",
    "H272": "ghs_oxidizer",
    
    # Explosive
    "H200": "ghs_explosive",
    "H201": "ghs_explosive",
    "H202": "ghs_explosive",
    "H203": "ghs_explosive",
    "H204": "ghs_explosive",
    "H205": "ghs_explosive",
    
    # Compressed Gas
    "H280": "ghs_compressed_gas",
    "H281": "ghs_compressed_gas",
}

# GHS Pictogram to Hazard Score (0-5)
PICTOGRAM_TO_SCORE = {
    "ghs_health_hazard": 5,
    "ghs_acute_toxic": 5,
    "ghs_corrosive": 4,
    "ghs_irritant": 3,
    "ghs_environmental_hazard": 3,
    "ghs_flammable": 2,
    "ghs_oxidizer": 2,
    "ghs_compressed_gas": 1,
    "ghs_explosive": 1,
}

# Pictogram priority order for selection
PICTOGRAM_PRIORITY = [
    "ghs_health_hazard",
    "ghs_acute_toxic",
    "ghs_corrosive",
    "ghs_irritant",
    "ghs_environmental_hazard",
    "ghs_flammable",
    "ghs_oxidizer",
    "ghs_compressed_gas",
    "ghs_explosive"
]

DEFAULT_HAZARD_SCORE = 0


def h_codes_to_pictogram_uid(h_codes: list) -> str:
    """Map list of H-codes to highest severity GHS pictogram UID."""
    if not h_codes:
        return None
    
    found_pictograms = set()
    for h_code in h_codes:
        if h_code in H_CODE_TO_PICTOGRAM:
            found_pictograms.add(H_CODE_TO_PICTOGRAM[h_code])
    
    if not found_pictograms:
        return None
    
    for priority in PICTOGRAM_PRIORITY:
        if priority in found_pictograms:
            return priority
    
    return None


def get_hazard_score_from_pictograms(ghs_pictograms: list) -> tuple:
    """
    Get highest hazard score from list of GHS pictograms.
    Returns (score, source_pictogram_name)
    """
    if not ghs_pictograms:
        return DEFAULT_HAZARD_SCORE, None
    
    best_score = 0
    best_name = None
    
    for pictogram in ghs_pictograms:
        uid = pictogram.get("uid") if isinstance(pictogram, dict) else pictogram
        name = pictogram.get("name") if isinstance(pictogram, dict) else uid
        score = PICTOGRAM_TO_SCORE.get(uid, 0)
        
        if score > best_score:
            best_score = score
            best_name = name
    
    return best_score, best_name


def get_hazard_score_from_h_codes(h_codes: list) -> tuple:
    """Get hazard score and source pictogram from H-codes."""
    pictogram_uid = h_codes_to_pictogram_uid(h_codes)
    if pictogram_uid:
        score = PICTOGRAM_TO_SCORE.get(pictogram_uid, DEFAULT_HAZARD_SCORE)
        return score, pictogram_uid
    return DEFAULT_HAZARD_SCORE, None


def calculate_hazard_score(ghs_pictograms: list, h_codes: list) -> tuple:
    """
    Calculate hazard score using available data.
    Priority: 1. Direct GHS pictograms, 2. H-code mapping, 3. Default 0
    
    Returns: (score, source_description)
    """
    # Priority 1: Direct GHS pictograms from KG
    if ghs_pictograms:
        score, pictogram_name = get_hazard_score_from_pictograms(ghs_pictograms)
        if score > 0:
            return score, f"Direct GHS pictogram: {pictogram_name}"
    
    # Priority 2: Map H-codes to GHS pictogram
    if h_codes:
        score, pictogram_uid = get_hazard_score_from_h_codes(h_codes)
        if score > 0:
            return score, f"Mapped from H-codes {h_codes[:3]}... → {pictogram_uid}"
        elif h_codes:
            return DEFAULT_HAZARD_SCORE, f"H-codes present but no mapping found: {h_codes}"
    
    # Priority 3: No data
    return DEFAULT_HAZARD_SCORE, "No hazard data available"