"""
queries.py — Cypher queries for Neo4j KG - PRODUCTION VERSION
──────────────────────────────────────────────────────────────
ADDED: GET_COMPLETE_CHEMICAL_DATA - One query returns all chemical data
"""

# ============================================================
# RESOLUTION QUERIES (NO PARTIAL MATCH)
# ============================================================

RESOLVE_INGREDIENT_EXACT = """
MATCH (c:Chemical)
WHERE toLower(c.name) = toLower($name)
   OR toLower(c.preferred_name) = toLower($name)
RETURN c.uid AS uid,
       c.name AS name,
       c.preferred_name AS preferred_name,
       c.cas AS cas,
       c.molecular_formula AS molecular_formula,
       c.molecular_weight AS molecular_weight,
       c.description AS description,
       c.synonyms AS synonyms
LIMIT 1
"""

RESOLVE_INGREDIENT_CAS = """
MATCH (c:Chemical)
WHERE c.cas = $name
RETURN c.uid AS uid,
       c.name AS name,
       c.preferred_name AS preferred_name,
       c.cas AS cas,
       c.molecular_formula AS molecular_formula,
       c.molecular_weight AS molecular_weight,
       c.description AS description,
       c.synonyms AS synonyms
LIMIT 1
"""

RESOLVE_INGREDIENT_SYNONYM = """
MATCH (c:Chemical)
WHERE ANY(synonym IN c.synonyms WHERE toLower(synonym) = toLower($name))
RETURN c.uid AS uid,
       c.name AS name,
       c.preferred_name AS preferred_name,
       c.cas AS cas,
       c.molecular_formula AS molecular_formula,
       c.molecular_weight AS molecular_weight,
       c.description AS description,
       c.synonyms AS synonyms
LIMIT 1
"""

# ============================================================
# COMPLETE CHEMICAL DATA - ONE QUERY RETURNS EVERYTHING
# ============================================================

GET_COMPLETE_CHEMICAL_DATA = """
MATCH (c:Chemical {uid: $uid})
OPTIONAL MATCH (c)-[:HAS_HAZARD_STATEMENT]->(h:HazardStatement)
OPTIONAL MATCH (c)-[:REQUIRES_PICTOGRAM]->(p:GHSPictogram)
OPTIONAL MATCH (c)-[:AFFECTS_ORGAN]->(o:TargetOrgan)
OPTIONAL MATCH (c)-[:CLASSIFIED_AS]->(cc:ChemicalClass)
OPTIONAL MATCH (c)-[:USED_IN]->(uc:UseCategory)
OPTIONAL MATCH (c)-[:HAS_TOXICITY_PROFILE]->(t:ToxicityMeasure)
OPTIONAL MATCH (c)-[:SUBJECT_TO_EXPOSURE_LIMIT]->(e:ExposureLimit)
OPTIONAL MATCH (c)-[:CAUSES_SKIN_EFFECT]->(sk:SkinExposure)
OPTIONAL MATCH (c)-[:CAUSES_EYE_EFFECT]->(ey:EyeExposure)
OPTIONAL MATCH (c)-[:CAUSES_INHALATION_EFFECT]->(ih:InhalationExposure)
OPTIONAL MATCH (c)-[:CAUSES_INGESTION_EFFECT]->(ig:IngestionExposure)
OPTIONAL MATCH (c)-[:EXCRETED_VIA]->(ex:ExcretionRoute)

RETURN
    // Identity
    c.uid AS uid,
    c.name AS name,
    c.preferred_name AS preferred_name,
    c.cas AS cas,
    c.molecular_formula AS molecular_formula,
    c.molecular_weight AS molecular_weight,
    c.description AS description,
    c.synonyms AS synonyms,
    
    // Hazard Statements
    collect(DISTINCT {
        code: h.code, 
        signal: h.signal, 
        meaning: h.meaning, 
        category: h.category
    }) AS hazards,
    
    // GHS Pictograms
    collect(DISTINCT {
        uid: p.uid,
        name: p.name,
        meaning: p.meaning
    }) AS ghs_pictograms,
    
    // Target Organs
    collect(DISTINCT {
        uid: o.uid,
        name: o.name
    }) AS target_organs,
    
    // Chemical Classes
    collect(DISTINCT cc.class) AS chemical_classes,
    
    // Use Categories
    collect(DISTINCT {
        name: uc.name,
        consumer_count: uc.consumer_count,
        industry_count: uc.industry_count,
        source: uc.source
    }) AS use_categories,
    
    // Toxicity Measures
    collect(DISTINCT {
        name: t.name,
        value: t.value
    }) AS toxicity_measures,
    
    // Exposure Limits
    collect(DISTINCT {
        standard: e.standard,
        value: e.value,
        unit: e.unit,
        type: e.type
    }) AS exposure_limits,
    
    // Exposure Effects
    collect(DISTINCT sk.name) AS skin_effects,
    collect(DISTINCT ey.name) AS eye_effects,
    collect(DISTINCT ih.name) AS inhalation_effects,
    collect(DISTINCT ig.name) AS ingestion_effects,
    
    // Excretion Routes
    collect(DISTINCT ex.name) AS excretion_routes
"""

# ============================================================
# LEGACY QUERIES (Keep for backward compatibility)
# ============================================================

GET_FULL_PROFILE = """
MATCH (c:Chemical {uid: $uid})
OPTIONAL MATCH (c)-[:HAS_HAZARD_STATEMENT]->(h:HazardStatement)
OPTIONAL MATCH (c)-[:AFFECTS_ORGAN]->(o:TargetOrgan)
OPTIONAL MATCH (c)-[:CLASSIFIED_AS]->(cc:ChemicalClass)
OPTIONAL MATCH (c)-[:HAS_TOXICITY_PROFILE]->(t:ToxicityMeasure)
OPTIONAL MATCH (c)-[:SUBJECT_TO_EXPOSURE_LIMIT]->(e:ExposureLimit)
OPTIONAL MATCH (c)-[:CAUSES_SKIN_EFFECT]->(sk:SkinExposure)
OPTIONAL MATCH (c)-[:CAUSES_EYE_EFFECT]->(ey:EyeExposure)
OPTIONAL MATCH (c)-[:CAUSES_INHALATION_EFFECT]->(ih:InhalationExposure)
OPTIONAL MATCH (c)-[:CAUSES_INGESTION_EFFECT]->(ig:IngestionExposure)
OPTIONAL MATCH (c)-[:EXCRETED_VIA]->(ex:ExcretionRoute)
RETURN
    c.uid AS uid,
    c.name AS name,
    c.preferred_name AS preferred_name,
    c.cas AS cas,
    c.molecular_formula AS molecular_formula,
    c.molecular_weight AS molecular_weight,
    c.description AS description,
    c.synonyms AS synonyms,
    collect(DISTINCT {
        code: h.code, signal: h.signal, meaning: h.meaning, category: h.category
    }) AS hazards,
    collect(DISTINCT o.name) AS target_organs,
    collect(DISTINCT cc.class) AS chemical_classes,
    collect(DISTINCT {type: t.name, value: t.value}) AS toxicity,
    collect(DISTINCT {standard: e.standard, value: e.value,
                      unit: e.unit, type: e.type}) AS exposure_limits,
    collect(DISTINCT sk.name) AS skin_effects,
    collect(DISTINCT ey.name) AS eye_effects,
    collect(DISTINCT ih.name) AS inhalation_effects,
    collect(DISTINCT ig.name) AS ingestion_effects,
    collect(DISTINCT ex.name) AS excretion_routes
"""

GET_HAZARDS_LIST = """
MATCH (c:Chemical {uid: $uid})
MATCH (c)-[:HAS_HAZARD_STATEMENT]->(h:HazardStatement)
RETURN collect(DISTINCT {
    code: h.code, signal: h.signal,
    meaning: h.meaning, category: h.category
}) AS hazards
"""

GET_ORGANS_LIST = """
MATCH (c:Chemical {uid: $uid})
MATCH (c)-[:AFFECTS_ORGAN]->(o:TargetOrgan)
RETURN collect(DISTINCT o.name) AS organs
"""

GET_EXPOSURE_LIMITS_LIST = """
MATCH (c:Chemical {uid: $uid})
MATCH (c)-[:SUBJECT_TO_EXPOSURE_LIMIT]->(e:ExposureLimit)
RETURN collect(DISTINCT {
    standard: e.standard, value: e.value,
    unit: e.unit, type: e.type
}) AS limits
"""

HAS_CRITICAL_HAZARD = """
MATCH (c:Chemical {uid: $uid})
MATCH (c)-[:HAS_HAZARD_STATEMENT]->(h:HazardStatement)
WHERE h.code IN ['H340', 'H341', 'H350', 'H351',
                 'H360', 'H361', 'H362',
                 'H370', 'H372']
RETURN collect(DISTINCT h.code) AS critical_hazards
"""

GET_ORGAN_FOR_MULTIPLE_CHEMICALS = """
UNWIND $uids AS uid
MATCH (c:Chemical {uid: uid})
OPTIONAL MATCH (c)-[:AFFECTS_ORGAN]->(o:TargetOrgan)
RETURN uid AS chemical_uid,
       collect(DISTINCT o.name) AS organs
"""

TEST_QUERY = """
MATCH (c:Chemical)
RETURN c.name, c.preferred_name, c.uid
LIMIT 5
"""