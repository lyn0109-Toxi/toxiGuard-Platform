from .compendial import (
    GUIDELINE_SOURCES,
    PHARMACOPEIA_DB,
    get_pharmacopeia_info,
    get_regulatory_profile,
    match_known_impurities,
)
from .degradation import DEGRADATION_RULES, predict_degradation_products
from .identity import get_smiles_from_name
from .harness import build_worker_report, get_harness_manifest, validate_assessment, validate_package
from .qsar import (
    ASHBY_ALERTS,
    EXPERIMENTAL_DB,
    KNOWN_MUTAGENS,
    assess_mutagenicity,
    calculate_ttc_limit,
    get_experimental_detail,
    get_expert_rule_assessment,
    get_statistical_assessment,
)
from .reporting import generate_regulatory_narrative


def assess_genotoxicity(smiles, drug_substance_smiles=None, daily_dose_mg=10, compound_name="Submitted compound"):
    """
    Backward-compatible public function used by the Streamlit app.

    The implementation now returns a richer ICH M7 evidence package:
    - alerts
    - expert_alerts
    - statistical_alerts
    - qsar_summary
    - structural_explanation
    - evidence_objects
    - ttc_info
    """
    result = assess_mutagenicity(
        smiles=smiles,
        drug_substance_smiles=drug_substance_smiles,
        daily_dose_mg=daily_dose_mg,
        compound_name=compound_name,
    )
    result["harness_manifest"] = get_harness_manifest()
    result["validation_gates"] = validate_assessment(result)
    return result


def build_evidence_package(compound_name, smiles, daily_dose_mg=10):
    assessment = assess_genotoxicity(smiles, daily_dose_mg=daily_dose_mg, compound_name=compound_name or "Submitted compound")
    known_matches = match_known_impurities(compound_name, smiles)
    degradants = predict_degradation_products(smiles, parent_name=compound_name)
    regulatory_profile = get_regulatory_profile(compound_name, smiles)
    return {
        "assessment": assessment,
        "known_impurity_matches": known_matches,
        "degradation_products": degradants,
        "regulatory_profile": regulatory_profile,
        "regulatory_source_map": regulatory_profile.get("regulatory_sources", []),
        "guideline_sources": GUIDELINE_SOURCES,
        "narrative": generate_regulatory_narrative(assessment, compound_name or "the submitted compound"),
        "harness_manifest": get_harness_manifest(),
    }


def build_harnessed_evidence_package(compound_name, smiles, daily_dose_mg=10, project_id="TXS-2026-001", analyst="Lee Young-nam"):
    package = build_evidence_package(compound_name, smiles, daily_dose_mg=daily_dose_mg)
    package["validation_gates"] = validate_package(package)
    package["worker_report"] = build_worker_report(package, project_id=project_id, analyst=analyst)
    package["harness_manifest"] = package["worker_report"]["harness"]
    return package
