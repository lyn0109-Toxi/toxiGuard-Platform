from __future__ import annotations

from typing import Any

from .compendial import match_known_impurities
from .evidence import make_evidence, sort_evidence
from .qsar import assess_mutagenicity


DEGRADATION_RULES = {
    "Acid Hydrolysis (Ester)": {
        "smarts": "[CX3:1](=[OX1:2])[OX2:3][CX4:4]>>[CX3:1](=[OX1:2])[OX2:3].[OX2][CX4:4]",
        "condition": "Acidic stress (pH < 2), heat",
        "rationale": "Acid-catalyzed substitution at the carbonyl center; relevant to prodrugs, esters, and lactone-forming systems.",
        "reg_significance": "Evaluate under ICH Q3A/Q3B thresholds and stability-indicating method expectations.",
        "risk_level": "High",
    },
    "Base Hydrolysis (Amide)": {
        "smarts": "[CX3:1](=[OX1:2])[NX3:3][CX4:4]>>[CX3:1](=[OX1:2])[OX2].[NX3:3][CX4:4]",
        "condition": "Basic stress (pH > 10), prolonged heat",
        "rationale": "Base-promoted amide cleavage can produce amines/acids that require identity and impurity qualification.",
        "reg_significance": "Potential process or degradation impurity depending on formation route.",
        "risk_level": "Medium",
    },
    "Aromatic Nitro Reduction": {
        "smarts": "[N+:1](=[O:2])[O-:3]>>[NX3:1]([H])[H]",
        "condition": "Reducing agents or anaerobic conditions",
        "rationale": "Nitro-to-amine reduction can create aromatic amine alerts and should trigger ICH M7 review.",
        "reg_significance": "Potential Class 2/3 alert formation pathway.",
        "risk_level": "Critical",
    },
    "Decarboxylation": {
        "smarts": "[CX3:1](=[OX1:2])[OX2:3][H:4]>>[CX4:1].[OX1]=[CX3]=[OX1]",
        "condition": "Thermal stress or acid catalysis",
        "rationale": "Loss of carbon dioxide may change potency and impurity profile.",
        "reg_significance": "Usually Q3A/Q3B qualification unless a mutagenic alert is introduced.",
        "risk_level": "Medium",
    },
}


def known_degradation_products(parent_name: str | None) -> list[dict[str, Any]]:
    products = []
    for match in match_known_impurities(parent_name):
        origin = (match.get("origin") or "").lower()
        if "degradation" in origin or "oxidative" in origin or "lactone" in match.get("name", "").lower():
            products.append(match)
    return products


def _known_product_result(item: dict[str, Any]) -> dict[str, Any]:
    smiles = item.get("smiles")
    toxicity = assess_mutagenicity(smiles, compound_name=item["name"]) if smiles else {
        "class": f"ICH M7 Class {item.get('class', 'N/A')}",
        "status": "review",
        "alerts": [],
        "evidence_objects": [],
        "structural_explanation": item.get("issue", "Structure not loaded; QSAR cannot be run."),
    }
    evidence = list(toxicity.get("evidence_objects", []))
    evidence.append(
        make_evidence(
            compound=item["name"],
            smiles=smiles,
            evidence_type="known degradation product",
            endpoint="impurity identity and origin",
            result="Known/reference impurity match",
            source_tier="compendial",
            source_name=item.get("source_name") or "Compendial impurity library",
            source_url=item.get("source_url"),
            reasoning=item.get("issue") or "Known impurity/degradation product match found in the curated library.",
            confidence="High" if item.get("source_url") else "Medium",
            regulatory_mapping=["ICH Q3A/Q3B", "ICH M7(R2) if mutagenic alert is present"],
            details=item,
        )
    )
    return {
        "pathway": "Known USP/EP/DMF degradation or related impurity",
        "condition": item.get("origin", "Known impurity profile"),
        "rationale": item.get("issue", ""),
        "significance": "Known/reference impurity should be tied to monograph, stability data, and CTD 3.2.P.5.5/3.2.P.8 justification.",
        "risk": "High" if item.get("class") == 3 else "Medium",
        "name": item["name"],
        "source_url": item.get("source_url"),
        "smiles": smiles or "Structure not loaded",
        "class": toxicity.get("class"),
        "status": toxicity.get("status"),
        "known_match": item,
        "evidence_objects": sort_evidence(evidence),
        "structural_explanation": toxicity.get("structural_explanation"),
    }


def predict_degradation_products(smiles: str, parent_name: str | None = None) -> list[dict[str, Any]]:
    products = [_known_product_result(item) for item in known_degradation_products(parent_name)]

    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        from rdkit import RDLogger
    except ImportError:
        return products

    RDLogger.DisableLog("rdApp.warning")

    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        return products

    seen_smiles = {Chem.MolToSmiles(mol)}
    for product in products:
        if product.get("smiles") and product["smiles"] != "Structure not loaded":
            seen_smiles.add(product["smiles"])

    for name, data in DEGRADATION_RULES.items():
        rxn = AllChem.ReactionFromSmarts(data["smarts"])
        if rxn is None:
            continue
        outcomes = rxn.RunReactants((mol,))
        for outcome in outcomes:
            for prod_mol in outcome:
                try:
                    Chem.SanitizeMol(prod_mol)
                    product_smiles = Chem.MolToSmiles(prod_mol)
                except Exception:
                    continue
                if product_smiles in seen_smiles:
                    continue
                toxicity = assess_mutagenicity(product_smiles, compound_name=f"{name} product")
                pathway_evidence = make_evidence(
                    compound=f"{name} product",
                    smiles=product_smiles,
                    evidence_type="predicted degradation product",
                    endpoint="forced degradation pathway",
                    result="Predicted product",
                    source_tier="inference",
                    source_name="RDKit reaction SMARTS degradation rule",
                    reasoning=data["rationale"],
                    confidence="Low",
                    regulatory_mapping=["ICH Q1A/Q1B/Q1E", "ICH Q3A/Q3B", "ICH M7(R2) if alerting"],
                    details=data,
                )
                products.append(
                    {
                        "pathway": name,
                        "condition": data["condition"],
                        "rationale": data["rationale"],
                        "significance": data["reg_significance"],
                        "risk": data["risk_level"],
                        "name": f"{name} product",
                        "smiles": product_smiles,
                        "class": toxicity.get("class"),
                        "status": toxicity.get("status"),
                        "evidence_objects": sort_evidence([pathway_evidence] + toxicity.get("evidence_objects", [])),
                        "structural_explanation": toxicity.get("structural_explanation"),
                    }
                )
                seen_smiles.add(product_smiles)
    return products
