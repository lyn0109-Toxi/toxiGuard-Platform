from __future__ import annotations

from typing import Any


GUIDELINE_SOURCES = [
    {
        "name": "FDA ICH M7(R2) Guidance / Q&A",
        "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/questions-and-answers-m7r2-assessment-and-control-dna-reactive-mutagenic-impurities-pharmaceuticals",
        "scope": "Assessment and control of DNA-reactive mutagenic impurities",
    },
    {
        "name": "EMA ICH M7(R2) Scientific Guideline",
        "url": "https://www.ema.europa.eu/en/ich-m7-assessment-control-dna-reactive-mutagenic-impurities-pharmaceuticals-limit-potential-carcinogenic-risk-scientific-guideline",
        "scope": "ICH M7(R2), addendum, and Q&A documents",
    },
    {
        "name": "USP Organic Impurities FAQ",
        "url": "https://www.usp.org/frequently-asked-questions/organic-impurities",
        "scope": "Terminology and treatment of organic impurities and degradation products",
    },
]


PHARMACOPEIA_DB: dict[str, dict[str, Any]] = {
    "Atorvastatin": {
        "smiles": "CC(C)c1c(C(=O)Nc2ccccc2)c(c(s1)c3ccc(F)cc3)C(O)CC(O)CC(=O)O",
        "monograph_ref": "USP / EP related substances framework; verify against current licensed monograph.",
        "dmf_summary": "Control strategy should connect oxidative degradation, lactonization, esterification-related impurities, and validated stability-indicating methods.",
        "impurities": [
            {
                "id": "EP Impurity D / USP Related Compound D",
                "name": "Atorvastatin epoxide / atorvastatin epoxydione impurity",
                "origin": "Oxidative degradation or low-level synthesis by-product",
                "alert": "Epoxide / Aziridine",
                "class": 3,
                "smiles": "CC(C)C(=O)C1(C(O1)(C2=CC=CC=C2)C(=O)C3=CC=C(C=C3)F)C(=O)NC4=CC=CC=C4",
                "cas": "148146-51-4",
                "source_name": "EP/USP reference-standard supplier listings; verify against USP/EP monograph",
                "source_url": "https://veeprho.com/impurities/atorvastatin-ep-impurity-d/",
                "issue": "Epoxide ring is an electrophilic structural alert; bacterial mutagenicity evidence or expert review is needed before downgrading.",
            },
            {
                "id": "Atorvastatin Pyrrolidone Lactone",
                "name": "Atorvastatin pyrrolidone lactone",
                "origin": "Lactonization / degradation product",
                "alert": "None",
                "class": 5,
                "smiles": None,
                "cas": "906552-19-0",
                "source_name": "USP Pharmaceutical Analytical Impurity listing",
                "source_url": "https://www.sigmaaldrich.cn/CN/en/product/usp/1a00820",
                "issue": "Known analytical impurity; assess under Q3A/Q3B and stability context unless a mutagenic alert is identified.",
            },
            {
                "id": "Atorvastatin Methyl Ester",
                "name": "Atorvastatin methyl ester",
                "origin": "Esterification process impurity",
                "alert": "None",
                "class": 5,
                "smiles": None,
                "cas": "345891-62-5",
                "source_name": "USP Pharmaceutical Analytical Impurity listing",
                "source_url": "https://www.sigmaaldrich.cn/CN/en/product/usp/1a00020",
                "issue": "Process impurity; specification justification should rely on purge, method validation, and Q3A/Q3B thresholds.",
            },
        ],
    },
    "Rosuvastatin": {
        "smiles": None,
        "monograph_ref": "USP / EP related substances framework; verify against current licensed monograph.",
        "dmf_summary": "Diastereomeric and lactone-related impurities are typically managed by stereochemical control and stability monitoring.",
        "impurities": [
            {
                "id": "USP Related Compound A",
                "name": "Rosuvastatin diastereomer",
                "origin": "Synthesis / stereochemical impurity",
                "alert": "None",
                "class": 5,
                "smiles": None,
                "cas": None,
                "source_name": "USP/EP related substance listing; verify exact standard",
                "source_url": None,
                "issue": "Usually a quality/stereochemical control issue rather than an ICH M7 alert unless structure-specific alert is present.",
            },
            {
                "id": "USP Related Compound B",
                "name": "Rosuvastatin lactone",
                "origin": "Degradation / lactonization",
                "alert": "None",
                "class": 5,
                "smiles": None,
                "cas": None,
                "source_name": "USP/EP related substance listing; verify exact standard",
                "source_url": None,
                "issue": "Assess as known degradation product under Q3B/stability controls.",
            },
        ],
    },
    "Brivaracetam": {
        "smiles": "CCCC1CN(C(=O)C1)C(C(N)=O)CC",
        "monograph_ref": "FDA approval and EP reference context; verify against current licensed monograph.",
        "dmf_summary": "Process-related intermediates and alkylating reagents should be controlled by purge justification under ICH M7 Option 4 where applicable.",
        "impurities": [
            {
                "id": "Impurity 1",
                "name": "4-Propyl-pyrrolidin-2-one",
                "origin": "Synthesis",
                "alert": "None",
                "class": 5,
                "smiles": None,
                "cas": None,
                "source_name": "Development/DMF-style process impurity library",
                "source_url": None,
                "issue": "Non-alerting process impurity in current demo library.",
            },
            {
                "id": "PGI-1",
                "name": "2-Bromobutyryl chloride",
                "origin": "Process reagent",
                "alert": "Alkyl Halide",
                "class": 3,
                "smiles": "CCCC(=O)Cl",
                "cas": None,
                "source_name": "Process impurity risk library",
                "source_url": None,
                "issue": "Potentially alerting electrophile; control by purge, specification, or confirmatory testing.",
            },
        ],
    },
}


def get_pharmacopeia_info(name: str | None) -> dict[str, Any] | None:
    if not name:
        return None
    query = name.strip().lower()
    for drug, data in PHARMACOPEIA_DB.items():
        if query in drug.lower() or drug.lower() in query:
            return data
    return None


def get_local_smiles(name: str | None) -> dict[str, str] | None:
    info = get_pharmacopeia_info(name)
    if info and info.get("smiles"):
        return {"smiles": info["smiles"], "source": "Local compendial/DMF library"}
    return None


def match_known_impurities(parent_name: str | None = None, smiles: str | None = None) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    info = get_pharmacopeia_info(parent_name)
    if info:
        for impurity in info.get("impurities", []):
            item = dict(impurity)
            item["parent"] = parent_name
            matches.append(item)

    if smiles:
        normalized = smiles.strip()
        for parent, data in PHARMACOPEIA_DB.items():
            for impurity in data.get("impurities", []):
                if impurity.get("smiles") and impurity["smiles"] == normalized:
                    item = dict(impurity)
                    item["parent"] = parent
                    item["match_type"] = "Exact SMILES"
                    matches.append(item)
    return matches

