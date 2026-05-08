FDA_GUIDANCE_MAP = [
    {
        "Area": "Toxicology / Mutagenic impurities",
        "Primary basis": "ICH M7(R2)",
        "Platform module": "QSAR & Genotoxicity",
        "Decision use": "Classify DNA-reactive impurity risk and identify required follow-up.",
    },
    {
        "Area": "Impurity / degradant control",
        "Primary basis": "ICH Q3A/Q3B, USP/EP where applicable",
        "Platform module": "Impurity & Degradation",
        "Decision use": "Map known and predicted impurities to control strategy and evidence needs.",
    },
    {
        "Area": "Bioequivalence",
        "Primary basis": "FDA/ICH M13A, FDA IR Dissolution Testing guidance",
        "Platform module": "Bioequivalence Strategy",
        "Decision use": "Compare reference/test dissolution profiles and support BE or biowaiver strategy.",
    },
    {
        "Area": "Submission narrative",
        "Primary basis": "FDA eCTD/CTD quality and nonclinical structure",
        "Platform module": "Report Builder",
        "Decision use": "Convert evidence into submission-ready regulatory language.",
    },
]


ROLE_GUIDANCE = {
    "Regulatory Affairs": {
        "focus": "Submission pathway, evidence gap, and FDA/ICH narrative readiness.",
        "next_action": "Confirm application route, target market, product-specific guidance, and required justification package.",
    },
    "CMC / Analytical": {
        "focus": "Impurity control, degradation pathway, dissolution method, and specification setting.",
        "next_action": "Align impurity/degradant controls with method validation, stability data, and dissolution acceptance criteria.",
    },
    "Nonclinical / Toxicology": {
        "focus": "ICH M7 class, QSAR concordance, toxicophore mapping, and experimental follow-up.",
        "next_action": "Review structural alerts, applicability domain, and need for Ames or expert review.",
    },
    "Executive / Portfolio": {
        "focus": "Development risk, timeline exposure, and go/no-go clarity.",
        "next_action": "Prioritize high-risk evidence gaps that could delay IND/ANDA/NDA decision gates.",
    },
}


def classify_toxicology_risk(results):
    if not results:
        return "Not started", "Run QSAR/genotoxicity assessment."
    ich_class = results.get("class", "")
    if "Class 1" in ich_class or "Class 2" in ich_class:
        return "High", "Known or probable mutagenic concern. Prepare expert review and control strategy."
    if "Class 3" in ich_class:
        return "Medium", "Structural alert detected. Confirm relevance, TTC control, and follow-up evidence."
    if "Class 4" in ich_class:
        return "Medium", "Alert shared with drug substance. Document read-across and justification."
    return "Low", "No structural alert identified within current model scope."


def classify_be_risk(be_result):
    if not be_result:
        return "Not started", "Enter reference/test dissolution data and calculate f2."
    if be_result.f2 >= 50 and be_result.cv_flag == "Acceptable":
        return "Low", "FDA-style f2 similarity rationale is supported by current dissolution profile."
    if be_result.f2 >= 50:
        return "Medium", "f2 is acceptable, but variability needs justification."
    return "High", "f2 is below 50. Review formulation/process or in vivo BE strategy."


def classify_degradation_risk(degradants):
    if not degradants:
        return "Not started", "Load or predict degradants and map pharmacopeial/FDA evidence."
    high_risk = [
        item
        for item in degradants
        if "Class 1" in str(item.get("class")) or "Class 2" in str(item.get("class")) or item.get("risk") == "High"
    ]
    if high_risk:
        return "High", "One or more degradants may require mutagenic impurity control strategy."
    review_items = [item for item in degradants if not item.get("smiles")]
    if review_items:
        return "Medium", "Some degradant structures are not loaded. Add qualified structures for QSAR review."
    return "Low", "No high-risk degradant signal in current curated/predicted profile."


def build_strategy_snapshot(results=None, degradants=None, be_result=None, role="Regulatory Affairs"):
    tox_risk, tox_action = classify_toxicology_risk(results)
    deg_risk, deg_action = classify_degradation_risk(degradants or [])
    be_risk, be_action = classify_be_risk(be_result)
    module_risks = [tox_risk, deg_risk, be_risk]
    if "High" in module_risks:
        overall = "High"
    elif "Medium" in module_risks:
        overall = "Medium"
    elif "Not started" in module_risks:
        overall = "Review needed"
    else:
        overall = "Low"
    role_item = ROLE_GUIDANCE.get(role, ROLE_GUIDANCE["Regulatory Affairs"])
    return {
        "overall_risk": overall,
        "toxicology_risk": tox_risk,
        "degradation_risk": deg_risk,
        "bioequivalence_risk": be_risk,
        "role_focus": role_item["focus"],
        "role_next_action": role_item["next_action"],
        "module_actions": [
            {"Module": "QSAR / Genotoxicity", "Risk": tox_risk, "Next action": tox_action},
            {"Module": "Impurity / Degradation", "Risk": deg_risk, "Next action": deg_action},
            {"Module": "Bioequivalence", "Risk": be_risk, "Next action": be_action},
            {"Module": "Regulatory Evidence", "Risk": "Review needed", "Next action": "Map FDA/ICH/USP sources to the selected submission pathway."},
        ],
    }


def build_submission_workflow(results=None, degradants=None, be_result=None):
    return [
        {"Step": "1. Product profile", "Status": "Ready", "Output": "Project, product, route, dosage form, and submission pathway defined."},
        {"Step": "2. QSAR / genotoxicity", "Status": "Ready" if results else "Pending", "Output": "ICH M7 class, toxicophore map, and evidence matrix."},
        {"Step": "3. Degradation / impurity", "Status": "Ready" if degradants else "Pending", "Output": "Known/predicted degradants, structure map, source review queue."},
        {"Step": "4. Bioequivalence", "Status": "Ready" if be_result else "Pending", "Output": "FDA f2/bootstrap result and BE strategy decision."},
        {"Step": "5. Source mapping", "Status": "In progress", "Output": "FDA/ICH/USP/EP/DMF evidence basis."},
        {"Step": "6. Submission narrative", "Status": "Draft", "Output": "Regulatory justification for internal review or agency package."},
    ]
