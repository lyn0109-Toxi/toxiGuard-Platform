from __future__ import annotations

from urllib.parse import quote_plus
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
    {
        "name": "FDA ANDAs: Impurities in Drug Products",
        "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/andas-impurities-drug-products",
        "scope": "CMC information for reporting, identifying, and qualifying degradation products in ANDA drug products",
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
    "Telmisartan": {
        "smiles": "CCCc1nc2c(C)cc(cc2n1Cc3ccc(cc3)c4ccccc4C(O)=O)c5nc6ccccc6n5C",
        "monograph_ref": "USP-NF Telmisartan Tablets monograph identifies USP Telmisartan RS and USP Telmisartan Related Compound A RS; verify current licensed monograph before submission.",
        "dmf_summary": "For FDA submissions, degradation products should be reported, identified, and qualified under FDA ANDA impurity guidance and ICH Q3B/ICH M7 as applicable.",
        "regulatory_sources": [
            {
                "name": "USP-NF Telmisartan Tablets monograph DOI",
                "url": "https://doi.usp.org/USPNF/USPNF_M80815_07_01.html",
                "scope": "USP identity, assay, impurity, and reference-standard context for Telmisartan Tablets.",
            },
            {
                "name": "FDA ANDAs: Impurities in Drug Products",
                "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/andas-impurities-drug-products",
                "scope": "FDA expectations for degradation product reporting, identification, and qualification in ANDA submissions.",
            },
            {
                "name": "FDA GSRS / UNII Telmisartan",
                "url": "https://precision.fda.gov/uniisearch/srs/unii/u5syw473rq",
                "scope": "FDA substance identity record and regulatory synonyms/mappings.",
            },
        ],
        "impurities": [
            {
                "id": "USP Related Compound A / EP Impurity A",
                "name": "4-Methyl-6-(1-methyl-1H-1,3-benzodiazol-2-yl)-2-propyl-1H-1,3-benzodiazole",
                "origin": "Compendial related substance / process-related impurity",
                "alert": "None loaded",
                "class": 5,
                "smiles": None,
                "cas": "152628-02-9",
                "source_name": "USP-NF Telmisartan Tablets monograph; supplier identity listing for EP/USP impurity A",
                "source_url": "https://doi.usp.org/USPNF/USPNF_M80815_07_01.html",
                "issue": "USP identifies Related Compound A reference standard. Structure should be loaded from a qualified reference-standard COA or licensed monograph before final QSAR conclusion.",
                "evidence_source_category": "pharmacopeia",
            },
            {
                "id": "EP Impurity B / USP Related Compound B",
                "name": "Telmisartan Related Compound B",
                "origin": "Compendial related substance / commercial reference impurity",
                "alert": "None loaded",
                "class": 5,
                "smiles": "O=C(C1=C(C2=CC=C(CN3C(CCC)=NC4=C3C(C)=CC(C5=NC6=C(N5C)C=CC=C6)=C4)C=C2)C=CC=C1)O",
                "cas": "1026353-20-7",
                "source_name": "Reference standard supplier listing aligned to EP/USP related compound naming",
                "source_url": "https://clearsynth.com/product/Telmisartan-EP-Impurity-B",
                "issue": "Related compound identity can support targeted related-substance monitoring; final limits should be justified from licensed monograph/specification and batch/stability data.",
                "evidence_source_category": "pharmacopeia-style reference standard",
            },
            {
                "id": "Photo-acidic degradation product",
                "name": "Telmisartan photolytic degradation product",
                "origin": "Photolytic degradation under acidic stress",
                "alert": "Structure pending",
                "class": "review",
                "smiles": None,
                "cas": None,
                "source_name": "Journal of Pharmaceutical and Biomedical Analysis stability study",
                "source_url": "https://www.sciencedirect.com/science/article/pii/S0731708510002815",
                "issue": "Published stress study reports telmisartan lability under photo-acidic condition with a single degradation product characterized by LC-MS/TOF and related techniques. Load the assigned structure before final ICH M7 QSAR classification.",
                "evidence_source_category": "stability literature",
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


def build_regulatory_source_map(name: str | None, smiles: str | None = None) -> list[dict[str, Any]]:
    query = (name or smiles or "submitted compound").strip()
    encoded = quote_plus(query)
    return [
        {
            "name": "FDA ANDAs: Impurities in Drug Products",
            "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/andas-impurities-drug-products",
            "scope": "FDA CMC expectations for reporting, identifying, and qualifying degradation products.",
            "use_in_app": "Use as the FDA basis for degradation product evidence requirements.",
        },
        {
            "name": "FDA ICH M7(R2) Guidance / Q&A",
            "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/questions-and-answers-m7r2-assessment-and-control-dna-reactive-mutagenic-impurities-pharmaceuticals",
            "scope": "FDA-aligned ICH M7 basis for DNA-reactive impurity assessment and complementary QSAR methods.",
            "use_in_app": "Use as the basis for QSAR classification and alert interpretation.",
        },
        {
            "name": "FDA GSRS / UNII substance search",
            "url": f"https://precision.fda.gov/uniisearch/srs/unii/search?search={encoded}",
            "scope": "FDA substance identity, synonyms, regulatory mappings, and external database links.",
            "use_in_app": "Use to confirm identity, synonyms, salts, and regulatory substance mapping.",
        },
        {
            "name": "USP-NF public monograph search",
            "url": f"https://doi.usp.org/search?keyword={encoded}",
            "scope": "USP monograph and reference-standard discovery where public DOI pages are available.",
            "use_in_app": "Use to identify official reference standards and related compound naming.",
        },
        {
            "name": "PubChem compound record",
            "url": f"https://pubchem.ncbi.nlm.nih.gov/#query={encoded}",
            "scope": "Open chemical identity, identifiers, calculated properties, and linked safety resources.",
            "use_in_app": "Use as supporting identity evidence, not as final regulatory impurity qualification.",
        },
    ]


def get_regulatory_profile(name: str | None, smiles: str | None = None) -> dict[str, Any]:
    curated = get_pharmacopeia_info(name)
    if curated:
        profile = dict(curated)
        profile["profile_type"] = "curated"
        profile["regulatory_sources"] = curated.get("regulatory_sources") or build_regulatory_source_map(name, smiles)
        return profile

    return {
        "profile_type": "source-discovery",
        "smiles": smiles,
        "monograph_ref": "No curated pharmacopeial impurity profile is loaded yet. Use the source map below to check FDA GSRS, USP-NF, public monograph pages, and compound-specific stability literature.",
        "dmf_summary": "Until compound-specific impurity data are curated, apply FDA ANDA impurity guidance, ICH Q3A/Q3B, and ICH M7(R2) using structure-based QSAR plus targeted source review.",
        "regulatory_sources": build_regulatory_source_map(name, smiles),
        "impurities": [],
    }


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
