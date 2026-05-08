import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.regulatory import (
    build_harnessed_evidence_package,
    get_smiles_from_name,
    assess_genotoxicity,
    predict_degradation_products,
)

def test_sync():
    print("🧪 Testing ToxiGuard-AI Sync...")
    
    # 1. Test Name Resolution
    name = "Atorvastatin"
    print(f"--- Resolving: {name} ---")
    res = get_smiles_from_name(name)
    if res:
        ator_smiles = res['smiles']
        print(f"✅ Success! SMILES: {ator_smiles}")
        
        # 2. Test Degradation for Atorvastatin
        print(f"--- Simulating Degradation for Atorvastatin ---")
        degradants = predict_degradation_products(ator_smiles, parent_name=name)
        if degradants:
            print(f"✅ Predicted {len(degradants)} potential degradants.")
            for d in degradants:
                print(f"  - [{d['pathway']}] {d['smiles']} -> {d['class']}")
        else:
            print("❌ No degradants predicted for Atorvastatin (Check SMARTS rules)")
    else:
        print(f"❌ Failed to resolve {name}")

    # 2. Test Genotoxicity Alert (Nitro Group)
    nitro_smiles = "c1ccc(cc1)[N+](=O)[O-]" # Nitrobenzene
    print(f"--- Assessing: {nitro_smiles} (Nitrobenzene) ---")
    eval_res = assess_genotoxicity(nitro_smiles)
    if eval_res["status"] == "alert":
        print(f"✅ Correct Alert Detected: {eval_res['alerts'][0]['alert']}")
        print(f"Class: {eval_res['class']}")
    elif eval_res["status"] == "error":
        print(f"⚠️ RDKit Note: {eval_res['message']}")
    else:
        print("❌ Failed to detect Nitro Group alert")

    # 3. Test Safe Compound
    safe_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O" # Aspirin
    print(f"--- Assessing: {safe_smiles} (Aspirin) ---")
    eval_res = assess_genotoxicity(safe_smiles)
    if eval_res["status"] == "safe":
        print("✅ Correct: No alerts for Aspirin.")
        print(f"Class: {eval_res['class']}")
    elif eval_res["status"] == "error":
        print(f"⚠️ RDKit Note: {eval_res['message']}")
    # 4. Test Class 2 (Aniline)
    aniline_smiles = "c1ccc(N)cc1"
    print(f"--- Assessing: {aniline_smiles} (Aniline) ---")
    eval_res = assess_genotoxicity(aniline_smiles)
    if "Class 2" in eval_res["class"]:
        print(f"✅ Correct Class 2 Detected: {eval_res['alerts'][0]['evidence']}")
    else:
        print(f"❌ Failed to detect Class 2. Got: {eval_res['class']}")

    # 5. Test Class 4 (Alert shared with Drug Substance)
    # Let's say DS has a nitro group, and impurity also has a nitro group.
    ds_nitro = "c1ccc(cc1)CC[N+](=O)[O-]"
    imp_nitro = "c1ccc(cc1)[N+](=O)[O-]"
    print(f"--- Assessing Impurity vs Drug Substance (Class 4 Case) ---")
    eval_res = assess_genotoxicity(imp_nitro, drug_substance_smiles=ds_nitro)
    if "Class 4" in eval_res["class"]:
        print(f"✅ Correct Class 4 Detected: {eval_res['note']}")
    else:
        print(f"❌ Failed to detect Class 4. Got: {eval_res['class']}")

    # 6. Test Harnessed Evidence Package
    print("--- Building Harnessed Evidence Package ---")
    package = build_harnessed_evidence_package("Atorvastatin", ator_smiles)
    report = package.get("worker_report", {})
    if report.get("schema") == "worker-report.v1" and report.get("validation", {}).get("passed", 0) >= 3:
        print("✅ Harness worker-report.v1 generated.")
    else:
        print("❌ Harness worker-report.v1 missing or insufficient.")

if __name__ == "__main__":
    test_sync()
