from __future__ import annotations

from typing import Any

from .evidence import make_evidence, sort_evidence, summarize_concordance


ASHBY_ALERTS: dict[str, dict[str, Any]] = {
    "Aromatic Amine": {
        "smarts": "[NX3;H2,H1;!$(NC=O)]-c1ccccc1",
        "likelihood": "Certain",
        "mechanism": "Metabolic activation to nitrenium ions, causing DNA adducts.",
        "reference": "ICH M7(R2); Ashby & Tennant structural alert framework",
        "priority": "Critical",
        "expert_comment": "Primary aromatic amines/anilines are key structural alerts for bacterial mutagenicity.",
    },
    "Fused-Ring Aromatic Amine": {
        "smarts": "[NX3;H2,H1;!$(NC=O)]-c1ccc2ccccc2c1",
        "likelihood": "Certain",
        "mechanism": "Planar fused rings may enhance DNA interaction; amine activation can form DNA-reactive species.",
        "reference": "IARC monograph context; ICH M7 expert review principle",
        "priority": "Critical",
        "expert_comment": "Naphthylamine-like fused systems warrant conservative expert review.",
    },
    "Nitro Group": {
        "smarts": "[N+](=O)[O-]",
        "likelihood": "Plausible",
        "mechanism": "Reductive metabolism can form hydroxylamine/nitrenium-like DNA-reactive intermediates.",
        "reference": "ICH M7(R2); Kazius et al. structural alert literature",
        "priority": "High",
        "expert_comment": "Aromatic nitro groups require context-specific review and often confirmatory Ames evidence.",
    },
    "Epoxide / Aziridine": {
        "smarts": "C1[O,N]C1",
        "likelihood": "Certain",
        "mechanism": "Strained three-membered rings can directly alkylate nucleophilic DNA sites via ring opening.",
        "reference": "ICH M7(R2) DNA-reactive alert principle; Miller & Miller electrophile framework",
        "priority": "Critical",
        "expert_comment": "Epoxides and aziridines are direct electrophile alerts unless deactivated by local structure.",
    },
    "Alkyl Halide / Acyl Halide": {
        "smarts": "[CX4,CX3][Cl,Br,I]",
        "likelihood": "Plausible",
        "mechanism": "Electrophilic carbon-halogen centers can alkylate biological nucleophiles depending on stability and exposure.",
        "reference": "ICH M7(R2) expert review principle",
        "priority": "High",
        "expert_comment": "Assess reactivity, purge, and exposure before assigning final class.",
    },
}


EXPERIMENTAL_DB = {
    "Nc1ccccc1": {
        "name": "Aniline",
        "assay_data": [
            {"test": "Ames (TA98)", "result": "Positive", "condition": "+S9 activation", "source": "NTP TR-211"},
            {"test": "Ames (TA100)", "result": "Positive", "condition": "+S9 activation", "source": "NTP TR-211"},
            {"test": "In vitro micronucleus", "result": "Positive", "condition": "Human lymphocytes", "source": "IARC Vol. 77"},
        ],
        "overall_conclusion": "Mutagenic under metabolic activation in the local evidence dossier.",
    }
}


KNOWN_MUTAGENS = {
    "Nc1ccccc1": {"class": 2, "name": "Aniline", "evidence": "Positive Ames evidence in local NTP dossier"},
    "c1ccc2c(c1)ccc3c2ccc4c3ccc5c4cccc5": {
        "class": 1,
        "name": "Benzo[a]pyrene",
        "evidence": "Known carcinogen/mutagen reference in local dossier",
    },
}


def canonicalize_smiles(smiles: str | None) -> str | None:
    if not smiles:
        return None
    try:
        from rdkit import Chem

        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return None
        return Chem.MolToSmiles(mol, isomericSmiles=True)
    except Exception:
        return smiles


def calculate_ttc_limit(daily_dose_mg: float, duration_days: int = 3650) -> dict[str, Any]:
    if duration_days <= 30:
        limit_ug = 120
    elif duration_days <= 365:
        limit_ug = 20
    elif duration_days <= 3650:
        limit_ug = 10
    else:
        limit_ug = 1.5

    if daily_dose_mg > 0:
        return {"limit_ug_day": limit_ug, "limit_ppm": round(limit_ug / daily_dose_mg, 2), "duration_days": duration_days}
    return {"limit_ug_day": limit_ug, "limit_ppm": "N/A", "duration_days": duration_days}


def _matched_atoms(mol: Any, pattern: Any) -> list[list[int]]:
    return [list(match) for match in mol.GetSubstructMatches(pattern)]


def get_expert_rule_assessment(smiles: str) -> list[dict[str, Any]]:
    try:
        from rdkit import Chem
    except ImportError:
        return []

    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        return []

    results = []
    for name, data in ASHBY_ALERTS.items():
        pattern = Chem.MolFromSmarts(data["smarts"])
        if pattern and mol.HasSubstructMatch(pattern):
            atoms = _matched_atoms(mol, pattern)
            results.append(
                {
                    "method": "Expert Rule-based",
                    "alert": name,
                    "likelihood": data["likelihood"],
                    "mechanism": data["mechanism"],
                    "reference": data["reference"],
                    "priority": data["priority"],
                    "expert_comment": data["expert_comment"],
                    "matched_atoms": atoms,
                    "reasoning": f"{name} SMARTS matched atom index set(s): {atoms}. {data['expert_comment']}",
                }
            )
    return results


def get_statistical_assessment(smiles: str) -> list[dict[str, Any]]:
    try:
        from rdkit import Chem
    except ImportError:
        return []

    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        return []

    statistical_rules = [
        ("Aromatic Amine", "[NX3;H2,H1;!$(NC=O)]-c1ccccc1", 0.82),
        ("Nitro Group", "[N+](=O)[O-]", 0.75),
        ("Epoxide / Aziridine", "C1[O,N]C1", 0.79),
        ("Alkyl Halide / Acyl Halide", "[CX4,CX3][Cl,Br,I]", 0.67),
    ]
    results = []
    for alert, smarts, probability in statistical_rules:
        pattern = Chem.MolFromSmarts(smarts)
        if pattern and mol.HasSubstructMatch(pattern):
            results.append(
                {
                    "method": "Statistical (SAR)",
                    "alert": alert,
                    "probability": probability,
                    "reference": "Internal transparent fragment model; replace with validated statistical QSAR engine for production use",
                    "reasoning": f"Fragment associated with bacterial mutagenicity model signal was present; estimated probability {int(probability * 100)}%.",
                    "matched_atoms": _matched_atoms(mol, pattern),
                }
            )
    return results


def get_experimental_detail(smiles: str | None) -> dict[str, Any] | None:
    can_smiles = canonicalize_smiles(smiles)
    if not can_smiles:
        return None
    return EXPERIMENTAL_DB.get(can_smiles) or EXPERIMENTAL_DB.get(smiles or "")


def _experimental_evidence(smiles: str, compound: str) -> list[dict[str, Any]]:
    exp = get_experimental_detail(smiles)
    if not exp:
        return []
    evidence = []
    for assay in exp["assay_data"]:
        evidence.append(
            make_evidence(
                compound=exp["name"],
                smiles=smiles,
                evidence_type="experimental assay",
                endpoint=assay["test"],
                result=assay["result"],
                source_tier="experimental",
                source_name=assay["source"],
                reasoning=f"{assay['test']} result was {assay['result']} under {assay['condition']}.",
                confidence="High",
                regulatory_mapping=["ICH M7(R2)", "Bacterial mutagenicity evidence"],
                details=assay,
            )
        )
    return evidence


def assess_mutagenicity(
    smiles: str,
    drug_substance_smiles: str | None = None,
    daily_dose_mg: float = 10,
    compound_name: str = "Submitted compound",
) -> dict[str, Any]:
    try:
        from rdkit import Chem
    except ImportError:
        return {"status": "error", "message": "RDKit not installed", "alerts": [], "evidence_objects": []}

    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        return {"status": "error", "message": "Invalid SMILES", "alerts": [], "evidence_objects": []}

    can_smiles = Chem.MolToSmiles(mol, isomericSmiles=True)
    ttc_info = calculate_ttc_limit(daily_dose_mg)
    evidence = [
        make_evidence(
            compound=compound_name,
            smiles=can_smiles,
            evidence_type="guideline",
            endpoint="ICH M7 scope",
            result="Assessment initiated",
            source_tier="guideline",
            source_name="ICH M7(R2)",
            source_url="https://www.fda.gov/regulatory-information/search-fda-guidance-documents/questions-and-answers-m7r2-assessment-and-control-dna-reactive-mutagenic-impurities-pharmaceuticals",
            reasoning="ICH M7 focuses on DNA-reactive mutagenic impurities and accepts complementary QSAR methods as an initial assessment.",
            confidence="High",
            regulatory_mapping=["ICH M7(R2)", "ICH Q3A/Q3B interface"],
        )
    ]

    if can_smiles in KNOWN_MUTAGENS:
        known = KNOWN_MUTAGENS[can_smiles]
        alert = {
            "method": "Historical Evidence",
            "alert": "Known Mutagen/Carcinogen",
            "evidence": known["evidence"],
            "mechanism": "Confirmed in historical toxicology studies.",
            "reference": known["evidence"],
            "reasoning": known["evidence"],
        }
        evidence.append(
            make_evidence(
                compound=known["name"],
                smiles=can_smiles,
                evidence_type="historical toxicology",
                endpoint="bacterial mutagenicity / carcinogenicity",
                result="Known positive",
                source_tier="experimental",
                source_name=known["evidence"],
                reasoning="The submitted structure matched a known mutagen/carcinogen record in the local evidence dossier.",
                confidence="High",
                method="Historical Evidence",
                alert="Known Mutagen/Carcinogen",
                mechanism=alert["mechanism"],
                regulatory_mapping=["ICH M7 Class 1/2 logic"],
            )
        )
        return {
            "status": "alert",
            "class": f"ICH M7 Class {known['class']}",
            "alerts": [alert],
            "expert_alerts": [alert],
            "statistical_alerts": [],
            "qsar_summary": {"concordance": "Historical positive", "expert_call": "Positive", "statistical_call": "Not required"},
            "structural_explanation": alert["reasoning"],
            "evidence_objects": sort_evidence(evidence + _experimental_evidence(can_smiles, compound_name)),
            "ttc_info": ttc_info,
            "canonical_smiles": can_smiles,
        }

    expert_alerts = get_expert_rule_assessment(can_smiles)
    stat_alerts = get_statistical_assessment(can_smiles)
    all_alerts = expert_alerts + stat_alerts

    for alert in expert_alerts:
        evidence.append(
            make_evidence(
                compound=compound_name,
                smiles=can_smiles,
                evidence_type="QSAR alert",
                endpoint="bacterial mutagenicity",
                result="Alert",
                source_tier="qsar",
                source_name="Expert rule-based QSAR",
                reasoning=alert["reasoning"],
                confidence="Medium",
                method=alert["method"],
                alert=alert["alert"],
                mechanism=alert["mechanism"],
                regulatory_mapping=["ICH M7(R2) complementary QSAR Method 1"],
                details=alert,
            )
        )

    for alert in stat_alerts:
        evidence.append(
            make_evidence(
                compound=compound_name,
                smiles=can_smiles,
                evidence_type="QSAR alert",
                endpoint="bacterial mutagenicity",
                result="Alert",
                source_tier="qsar",
                source_name="Statistical SAR model",
                reasoning=alert["reasoning"],
                confidence="Medium",
                method=alert["method"],
                alert=alert["alert"],
                regulatory_mapping=["ICH M7(R2) complementary QSAR Method 2"],
                details=alert,
            )
        )

    evidence.extend(_experimental_evidence(can_smiles, compound_name))

    if not all_alerts:
        evidence.append(
            make_evidence(
                compound=compound_name,
                smiles=can_smiles,
                evidence_type="QSAR conclusion",
                endpoint="bacterial mutagenicity",
                result="No alert identified",
                source_tier="qsar",
                source_name="Dual-method QSAR screen",
                reasoning="No expert-rule or transparent statistical fragment alert was identified. This supports ICH M7 Class 5 only within model applicability and source limitations.",
                confidence="Medium",
                regulatory_mapping=["ICH M7 Class 5"],
            )
        )
        final_class = "ICH M7 Class 5"
        status = "safe"
    else:
        final_class = "ICH M7 Class 3"
        status = "alert"
        note = "Alerting structure is not demonstrated to be shared with the drug substance; treat as Class 3 pending expert review or negative bacterial mutagenicity evidence."
        if drug_substance_smiles:
            ds_mol = Chem.MolFromSmiles(drug_substance_smiles)
            if ds_mol:
                for alert in expert_alerts:
                    pattern = Chem.MolFromSmarts(ASHBY_ALERTS[alert["alert"]]["smarts"])
                    if pattern and ds_mol.HasSubstructMatch(pattern):
                        final_class = "ICH M7 Class 4"
                        status = "controlled"
                        note = f"Alerting feature '{alert['alert']}' is also present in the drug substance; provisional ICH M7 Class 4 logic applied pending expert review."
                        break

    structural_explanation = "No DNA-reactive structural alert was identified."
    if expert_alerts:
        structural_explanation = " | ".join(f"{a['alert']}: {a['mechanism']}" for a in expert_alerts)
    elif stat_alerts:
        structural_explanation = " | ".join(f"{a['alert']}: statistical fragment signal only" for a in stat_alerts)

    return {
        "status": status,
        "class": final_class,
        "alerts": all_alerts,
        "expert_alerts": expert_alerts,
        "statistical_alerts": stat_alerts,
        "qsar_summary": {
            "expert_call": "Positive" if expert_alerts else "Negative",
            "statistical_call": "Positive" if stat_alerts else "Negative",
            "concordance": summarize_concordance(expert_alerts, stat_alerts),
            "applicability_domain": "Transparent SMARTS/fragment domain; production use requires validated model AD documentation.",
        },
        "structural_explanation": structural_explanation,
        "evidence_objects": sort_evidence(evidence),
        "ttc_info": ttc_info,
        "canonical_smiles": can_smiles,
        "note": note if all_alerts else "No alert identified by the current expert/statistical screen; provisional ICH M7 Class 5 within model limitations.",
    }
