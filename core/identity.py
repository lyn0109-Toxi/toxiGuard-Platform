import urllib.parse

import requests

from .compendial import get_local_smiles
from .evidence import make_evidence


def get_smiles_from_name(name: str | None) -> dict | None:
    if not name:
        return None

    local = get_local_smiles(name)
    if local:
        local["evidence"] = [
            make_evidence(
                compound=name,
                evidence_type="identity",
                endpoint="chemical identity",
                result="SMILES resolved",
                source_tier="compendial",
                source_name=local["source"],
                reasoning="The compound was resolved from the local controlled compound library before external API lookup.",
                smiles=local["smiles"],
                regulatory_mapping=["ICH M7(R2)", "ICH Q3A/Q3B"],
            )
        ]
        return local

    clean_url_name = urllib.parse.quote(name.strip())

    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{clean_url_name}/property/IsomericSMILES,IUPACName,InChIKey/JSON"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            props = response.json()["PropertyTable"]["Properties"][0]
            smiles = props.get("IsomericSMILES")
            if smiles:
                cid = props.get("CID")
                return {
                    "smiles": smiles,
                    "source": "PubChem API",
                    "cid": cid,
                    "iupac": props.get("IUPACName"),
                    "inchikey": props.get("InChIKey"),
                    "source_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else None,
                    "evidence": [
                        make_evidence(
                            compound=name,
                            evidence_type="identity",
                            endpoint="chemical identity",
                            result="SMILES resolved",
                            source_tier="identity",
                            source_name="PubChem PUG REST",
                            source_url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else "https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest",
                            reasoning="PubChem resolved the submitted compound name to an isomeric SMILES and identifier record.",
                            smiles=smiles,
                            regulatory_mapping=["Identity support for ICH M7 assessment"],
                            details={"cid": cid, "iupac": props.get("IUPACName"), "inchikey": props.get("InChIKey")},
                        )
                    ],
                }
    except Exception as exc:
        print(f"PubChem Error: {exc}")

    try:
        url = f"https://cactus.nci.nih.gov/chemical/structure/{clean_url_name}/smiles"
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and response.text.strip():
            smiles = response.text.strip()
            return {
                "smiles": smiles,
                "source": "NIH CIR API",
                "evidence": [
                    make_evidence(
                        compound=name,
                        evidence_type="identity",
                        endpoint="chemical identity",
                        result="SMILES resolved",
                        source_tier="identity",
                        source_name="NIH/NCI Chemical Identifier Resolver",
                        source_url="https://cactus.nci.nih.gov/chemical/structure",
                        reasoning="NIH/NCI CIR resolved the submitted compound name after PubChem lookup did not return a usable result.",
                        smiles=smiles,
                        regulatory_mapping=["Identity support for ICH M7 assessment"],
                    )
                ],
            }
    except Exception as exc:
        print(f"NIH CIR Error: {exc}")

    return None

