import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os
import urllib.parse
import requests

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.regulatory import (
        build_evidence_package,
        build_harnessed_evidence_package,
        generate_regulatory_narrative,
        get_smiles_from_name,
        assess_genotoxicity,
        predict_degradation_products,
        get_pharmacopeia_info,
        get_experimental_detail,
        match_known_impurities,
    )
except ImportError as e:
    st.error(f"Module Import Error: {e}")
    st.stop()

# Try importing RDKit. Keep core chemistry separate from drawing because
# Streamlit Cloud can have drawing-backend differences.
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors
    RDKIT_AVAILABLE = True
except ImportError as e:
    RDKIT_IMPORT_ERROR = str(e)
    RDKIT_AVAILABLE = False

try:
    from rdkit.Chem.Draw import rdMolDraw2D
    RDKIT_DRAW_AVAILABLE = True
except ImportError:
    RDKIT_DRAW_AVAILABLE = False

# --- Page Configuration ---
st.set_page_config(
    page_title="ToxiScope AI | Regulatory Intelligence",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS: Premium Design System ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

:root {
    --bg-dark: #0f172a;
    --accent: #0ea5e9;
    --accent-glow: rgba(14, 165, 233, 0.3);
    --glass: rgba(255, 255, 255, 0.03);
    --glass-border: rgba(255, 255, 255, 0.1);
    --text-main: #f1f5f9;
}

.stApp {
    background-color: var(--bg-dark);
    color: var(--text-main);
    font-family: 'Outfit', sans-serif;
}

.glass-card {
    background: var(--glass);
    backdrop-filter: blur(20px);
    border: 1px solid var(--glass-border);
    border-radius: 24px;
    padding: 2rem;
    margin-bottom: 1.5rem;
}

.hero-title {
    font-size: 4.5rem;
    font-weight: 900;
    background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
}

.accent-text {
    color: var(--accent);
    font-family: 'JetBrains Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.3em;
    font-weight: 700;
    font-size: 0.9rem;
}

.badge {
    padding: 0.4rem 1rem;
    border-radius: 100px;
    font-size: 0.8rem;
    font-weight: 800;
    text-transform: uppercase;
}

.badge-class1 { background: #ef4444; color: white; }
.badge-class3 { background: #f59e0b; color: white; }
.badge-class5 { background: #10b981; color: white; }

</style>
""", unsafe_allow_html=True)

# --- State Management ---
if "smiles" not in st.session_state:
    st.session_state.smiles = ""
if "results" not in st.session_state:
    st.session_state.results = None
if "degradants" not in st.session_state:
    st.session_state.degradants = []
if "identity" not in st.session_state:
    st.session_state.identity = {}
if "known_impurities" not in st.session_state:
    st.session_state.known_impurities = []
if "evidence_package" not in st.session_state:
    st.session_state.evidence_package = None

# --- UI Layout ---
with st.sidebar:
    st.markdown("<div class='accent-text'>Harness Active</div>", unsafe_allow_html=True)
    st.title("Project Scope")
    project_id = st.text_input("Project ID", value="TXS-2026-001")
    analyst = st.text_input("Expert Analyst", value="Lee Young-nam")
    daily_dose_mg = st.number_input("Daily Dose (mg/day)", min_value=0.001, value=10.0, step=1.0)
    st.markdown("---")
    st.markdown("### Compliance Rules")
    st.checkbox("ICH M7(R2) Guidelines", value=True, disabled=True)
    st.checkbox("ASHBY Structural Alerts", value=True, disabled=True)
    st.checkbox("Proactive Degradation", value=True)

def run_assessment(compound_name, smiles_value):
    package = build_harnessed_evidence_package(
        compound_name,
        smiles_value,
        daily_dose_mg=daily_dose_mg,
        project_id=project_id,
        analyst=analyst,
    )
    st.session_state.evidence_package = package
    st.session_state.results = package["assessment"]
    st.session_state.degradants = package["degradation_products"]
    st.session_state.known_impurities = package["known_impurity_matches"]

def build_structure_profile(smiles_value):
    if not RDKIT_AVAILABLE or not smiles_value:
        return None
    mol = Chem.MolFromSmiles(smiles_value)
    if not mol:
        return None
    return {
        "mol": mol,
        "canonical_smiles": Chem.MolToSmiles(mol, isomericSmiles=True),
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight": round(Descriptors.MolWt(mol), 2),
        "logp": round(Descriptors.MolLogP(mol), 2),
        "tpsa": round(Descriptors.TPSA(mol), 2),
        "hbd": Lipinski.NumHDonors(mol),
        "hba": Lipinski.NumHAcceptors(mol),
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
        "ring_count": Lipinski.RingCount(mol),
        "heavy_atoms": mol.GetNumHeavyAtoms(),
    }

def render_molecule_svg(mol, highlight_atoms=None, width=620, height=420):
    if not RDKIT_DRAW_AVAILABLE or mol is None:
        return None
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    options = drawer.drawOptions()
    options.clearBackground = False
    options.setBackgroundColour((0.06, 0.09, 0.16))
    options.legendFontSize = 16
    rdMolDraw2D.PrepareAndDrawMolecule(
        drawer,
        mol,
        highlightAtoms=highlight_atoms or [],
    )
    drawer.FinishDrawing()
    return drawer.GetDrawingText().replace("svg:", "")

def show_molecule(mol, highlight_atoms=None, width=620, height=420):
    svg = render_molecule_svg(mol, highlight_atoms=highlight_atoms, width=width, height=height)
    if not svg:
        st.warning("Structure drawing backend is not available in this deployment.")
        return
    st.components.v1.html(
        f"""
        <div style="width:100%; display:flex; justify-content:center;">
            {svg}
        </div>
        """,
        height=height + 24,
        scrolling=False,
    )

def collect_alert_atoms(result):
    atoms = set()
    for alert in result.get("expert_alerts", []) + result.get("statistical_alerts", []):
        for match in alert.get("matched_atoms", []) or []:
            atoms.update(match)
    return sorted(atoms)

def toxic_alerts(result):
    rows = []
    seen = set()
    for alert in result.get("expert_alerts", []) + result.get("statistical_alerts", []):
        key = (alert.get("method"), alert.get("alert"), str(alert.get("matched_atoms")))
        if key in seen:
            continue
        seen.add(key)
        rows.append(alert)
    return rows

def collect_evidence_alert_atoms(evidence_objects):
    atoms = set()
    for item in evidence_objects or []:
        details = item.get("details") or {}
        for match in details.get("matched_atoms", []) or []:
            atoms.update(match)
    return sorted(atoms)

def evidence_alert_rows(evidence_objects):
    rows = []
    for item in evidence_objects or []:
        if item.get("alert") or item.get("method"):
            details = item.get("details") or {}
            rows.append({
                "Method": item.get("method") or details.get("method"),
                "Alert": item.get("alert") or details.get("alert"),
                "Matched atoms": details.get("matched_atoms"),
                "Mechanism": item.get("mechanism") or details.get("mechanism"),
                "Reasoning": item.get("reasoning"),
            })
    return rows

st.markdown("<div class='accent-text'>Regulatory Intelligence Platform</div>", unsafe_allow_html=True)
st.markdown("<h1 class='hero-title'>ToxiScope AI</h1>", unsafe_allow_html=True)

col1, col2 = st.columns([1.5, 1])

with col1:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### 🔍 Chemical Identification")
    
    input_name = st.text_input("Compound Name", placeholder="e.g. Brivaracetam, Aniline...")
    
    if st.button("🔍 Search SMILES from Name", use_container_width=True):
        if input_name:
            with st.spinner(f"Resolving '{input_name}'..."):
                res = get_smiles_from_name(input_name)
                if res:
                    st.session_state.smiles = res['smiles']
                    st.session_state.identity = res
                    st.success(f"Found via {res['source']}")
                    with st.spinner("Running regulatory assessment..."):
                        run_assessment(input_name, res["smiles"])
                else:
                    st.error("Name resolution failed. Please input SMILES manually.")

    input_smiles = st.text_area("SMILES String", key="smiles", height=110)
    if input_smiles:
        st.caption("SMILES resolved. You can edit it manually and re-run the assessment.")

    if st.button("🚀 Run Regulatory Assessment", use_container_width=True):
        if input_smiles:
            with st.spinner("Analyzing toxicity and degradation..."):
                run_assessment(input_name, input_smiles)
        else:
            st.warning("Please provide a SMILES string.")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    if st.session_state.results:
        res = st.session_state.results
        status_color = "badge-class1" if "Class 1" in res['class'] or "Class 2" in res['class'] else "badge-class3" if "Class 3" in res['class'] else "badge-class5"
        st.markdown(f"""
        <div class='glass-card' style='text-align: center;'>
            <div class='accent-text'>Assessment Result</div>
            <h2 style='font-size: 3rem; margin-top: 1rem;'>{res['class']}</h2>
            <div class='badge {status_color}' style='display: inline-block; margin-top: 1rem;'>{res['status']}</div>
            <p style='margin-top: 1.5rem; color: #94a3b8;'>Validated through Harness R01-R13 gates</p>
        </div>
        """, unsafe_allow_html=True)

if st.session_state.results:
    st.markdown("---")
    structure_smiles = st.session_state.smiles or st.session_state.results.get("canonical_smiles")
    profile = build_structure_profile(structure_smiles)
    alert_list = toxic_alerts(st.session_state.results)
    highlighted_atoms = collect_alert_atoms(st.session_state.results)

    st.markdown("<div class='accent-text'>Toxicophore Map</div>", unsafe_allow_html=True)
    map_col1, map_col2 = st.columns([1.05, 1.25])
    with map_col1:
        if profile:
            show_molecule(profile["mol"], highlighted_atoms, width=620, height=420)
            st.caption("Highlighted atoms indicate mapped toxicophore / QSAR alert regions.")
        else:
            st.warning("Structure parsing is not available for the submitted SMILES.")
    with map_col2:
        st.markdown("#### Toxicity-Driving Structural Features")
        if alert_list:
            for idx, alert in enumerate(alert_list, 1):
                severity = "error" if alert.get("method") == "Historical Evidence" else "warning"
                message = f"**{idx}. {alert.get('alert')}**  \n{alert.get('mechanism') or alert.get('reasoning')}"
                if severity == "error":
                    st.error(message)
                else:
                    st.warning(message)
                with st.expander(f"Details: {alert.get('alert')}"):
                    st.write(f"**Method**: {alert.get('method', 'N/A')}")
                    st.write(f"**Matched atoms**: {alert.get('matched_atoms', 'N/A')}")
                    st.write(f"**Reference / Evidence**: {alert.get('reference') or alert.get('evidence') or 'N/A'}")
                    st.write(f"**Reasoning**: {alert.get('reasoning', 'N/A')}")
                    if alert.get("expert_comment"):
                        st.write(f"**Expert comment**: {alert.get('expert_comment')}")
        else:
            st.success("No toxicophore was mapped by the current expert/statistical screen.")

        exp_data = get_experimental_detail(st.session_state.results.get("canonical_smiles") or st.session_state.smiles)
        if exp_data:
            with st.expander("Experimental Toxicology Evidence"):
                st.write(exp_data.get("overall_conclusion", ""))
                st.dataframe(pd.DataFrame(exp_data.get("assay_data", [])), use_container_width=True, hide_index=True)

    ttc = st.session_state.results.get('ttc_info', {})
    q_col1, q_col2, q_col3 = st.columns(3)
    with q_col1: st.metric("TTC Limit (ug/day)", f"{ttc.get('limit_ug_day')} µg")
    with q_col2: st.metric("Max Conc. (ppm)", f"{ttc.get('limit_ppm')} ppm")
    with q_col3: st.metric("Regulatory Class", st.session_state.results['class'])

    tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs(["🧫 Structural Elucidation", "⚖️ Evidence Matrix", "🧬 Degradation Profile", "📚 USP/EP/DMF Ref", "📝 Regulatory Draft", "🧾 Harness Report"])

    with tab0:
        st.markdown("<div class='accent-text'>Structure-Based Read Across</div>", unsafe_allow_html=True)
        if profile:
            s_col1, s_col2 = st.columns([1, 1.25])
            with s_col1:
                show_molecule(profile["mol"], highlighted_atoms, width=520, height=360)
                st.caption("2D structure with QSAR alert atoms highlighted.")
            with s_col2:
                st.markdown("#### Identity & Physicochemical Profile")
                st.code(profile["canonical_smiles"], language="text")
                p1, p2, p3 = st.columns(3)
                p1.metric("Formula", profile["formula"])
                p2.metric("MW", profile["molecular_weight"])
                p3.metric("cLogP", profile["logp"])
                p4, p5, p6 = st.columns(3)
                p4.metric("TPSA", profile["tpsa"])
                p5.metric("HBD / HBA", f"{profile['hbd']} / {profile['hba']}")
                p6.metric("Rings", profile["ring_count"])
                st.caption(f"Heavy atoms: {profile['heavy_atoms']} | Rotatable bonds: {profile['rotatable_bonds']}")

            alert_rows = []
            for alert in st.session_state.results.get("expert_alerts", []) + st.session_state.results.get("statistical_alerts", []):
                alert_rows.append({
                    "Method": alert.get("method"),
                    "Structural alert": alert.get("alert"),
                    "Matched atoms": alert.get("matched_atoms"),
                    "Mechanistic interpretation": alert.get("mechanism") or alert.get("reasoning"),
                    "Reference": alert.get("reference"),
                })
            if alert_rows:
                st.markdown("#### Alert Mapping")
                st.dataframe(pd.DataFrame(alert_rows), use_container_width=True, hide_index=True)
            else:
                st.success("No DNA-reactive structural alert was mapped to this structure.")
            st.markdown("#### Regulatory Interpretation")
            st.info(st.session_state.results.get("structural_explanation", "No structural explanation available."))
        else:
            st.warning("Structure rendering is not available for the submitted SMILES.")
    
    with tab1:
        st.markdown("<div class='accent-text'>ICH M7 Evidence Object Matrix</div>", unsafe_allow_html=True)
        qsar = st.session_state.results.get("qsar_summary", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Expert QSAR", qsar.get("expert_call", "N/A"))
        c2.metric("Statistical SAR", qsar.get("statistical_call", "N/A"))
        c3.metric("Concordance", qsar.get("concordance", "N/A"))
        c4.metric("Evidence Items", len(st.session_state.results.get("evidence_objects", [])))

        st.markdown("#### Structural Explanation")
        st.info(st.session_state.results.get("structural_explanation", "No structural explanation available."))
        st.caption(qsar.get("applicability_domain", "Applicability domain not documented."))

        evidence_rows = []
        for item in st.session_state.results.get("evidence_objects", []):
            evidence_rows.append({
                "Tier": item.get("source_tier_label"),
                "Type": item.get("evidence_type"),
                "Endpoint": item.get("endpoint"),
                "Result": item.get("result"),
                "Source": item.get("source_name"),
                "Confidence": item.get("confidence"),
                "Reasoning": item.get("reasoning"),
                "URL": item.get("source_url") or "",
            })

        if evidence_rows:
            st.dataframe(pd.DataFrame(evidence_rows), use_container_width=True, hide_index=True)
        else:
            st.warning("No structured evidence objects were returned.")

        st.markdown("#### QSAR Dual-Method Detail")
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("##### Method 1: Expert rule-based")
            expert_alerts = st.session_state.results.get("expert_alerts", [])
            if expert_alerts:
                for alert in expert_alerts:
                    st.warning(f"**{alert.get('alert')}**")
                    st.write(alert.get("mechanism", ""))
                    st.caption(f"Matched atoms: {alert.get('matched_atoms', 'N/A')} | Ref: {alert.get('reference', 'N/A')}")
            else:
                st.success("No expert-rule structural alert identified.")
            st.markdown("</div>", unsafe_allow_html=True)

        with e_col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("##### Method 2: Statistical SAR")
            stat_alerts = st.session_state.results.get("statistical_alerts", [])
            if stat_alerts:
                for alert in stat_alerts:
                    st.error(f"**{alert.get('alert')}**")
                    st.write(alert.get("reasoning", ""))
                    st.caption(f"Probability: {int(alert.get('probability', 0) * 100)}% | Matched atoms: {alert.get('matched_atoms', 'N/A')}")
            else:
                st.success("No statistical fragment alert identified.")
            st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='accent-text'>Compendial / FDA-Anchored Degradation Evidence</div>", unsafe_allow_html=True)
        st.caption("Known pharmacopeial related substances and stability-literature degradation products are shown before purely predicted RDKit degradation products.")
        if st.session_state.degradants:
            for d in st.session_state.degradants:
                with st.expander(f"🚩 [{d['pathway']}] {d.get('name', 'Product Identification')}"):
                    d_evidence = d.get("evidence_objects", [])
                    d_profile = build_structure_profile(d.get("smiles"))
                    d_alert_atoms = collect_evidence_alert_atoms(d_evidence)
                    d_col1, d_col2 = st.columns([1, 1])
                    with d_col1:
                        if d_profile:
                            show_molecule(d_profile["mol"], d_alert_atoms, width=440, height=300)
                            st.caption("Degradation/impurity structure with QSAR alert atoms highlighted when available.")
                        else:
                            st.info("No drawable structure is loaded for this degradation product.")
                        st.write(f"**SMILES**: `{d.get('smiles')}`")
                        st.write(f"**ICH M7 Result**: {d.get('class')} ({d.get('status')})")
                        st.write(f"**Condition / Origin**: {d.get('condition')}")
                        st.write(f"**Risk Level**: {d.get('risk')}")
                    with d_col2:
                        if d.get("source_name"):
                            st.write(f"**Evidence Source**: {d.get('source_name')}")
                        if d.get("evidence_source_category"):
                            st.write(f"**Source Category**: {d.get('evidence_source_category')}")
                        st.write(f"**Rationale**: {d.get('rationale')}")
                        st.write(f"**Regulatory Significance**: {d.get('significance', 'N/A')}")
                        if d.get("source_url"):
                            st.markdown(f"[Source reference]({d['source_url']})")
                    st.markdown("**Structural/QSAR Interpretation**")
                    st.info(d.get("structural_explanation") or "No structural explanation available.")
                    d_alert_rows = evidence_alert_rows(d_evidence)
                    if d_alert_rows:
                        st.markdown("**Degradation Product Toxicophore Detail**")
                        st.dataframe(pd.DataFrame(d_alert_rows), use_container_width=True, hide_index=True)
                    if d_evidence:
                        st.dataframe(pd.DataFrame([{
                            "Tier": e.get("source_tier_label"),
                            "Type": e.get("evidence_type"),
                            "Result": e.get("result"),
                            "Source": e.get("source_name"),
                            "URL": e.get("source_url") or "",
                            "Reasoning": e.get("reasoning"),
                        } for e in d_evidence]), use_container_width=True, hide_index=True)
        else:
            st.info("No compound-specific degradation products are loaded or predicted yet. Use the source map below to complete targeted FDA/USP/literature review.")
            source_rows = (st.session_state.evidence_package or {}).get("regulatory_source_map", [])
            if source_rows:
                st.markdown("#### Source Review Queue")
                st.dataframe(pd.DataFrame(source_rows), use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("<div class='accent-text'>Known Impurity / Degradation Product Search</div>", unsafe_allow_html=True)
        pharma_info = (st.session_state.evidence_package or {}).get("regulatory_profile") or get_pharmacopeia_info(input_name)
        st.markdown("#### Parent Compound Reference")
        if pharma_info.get("profile_type") == "curated":
            st.success("Curated pharmacopeial/DMF-style profile loaded.")
        else:
            st.info("No curated compound-specific impurity profile is loaded yet. The app generated a source-review map for this compound.")
        st.write(f"**Monograph / Reference Context**: {pharma_info.get('monograph_ref')}")
        st.write(f"**DMF / Control Summary**: {pharma_info.get('dmf_summary')}")
        source_rows = pharma_info.get("regulatory_sources", [])
        if source_rows:
            st.markdown("#### FDA / Compendial Source Map")
            st.dataframe(pd.DataFrame(source_rows), use_container_width=True, hide_index=True)

        matches = st.session_state.known_impurities or match_known_impurities(input_name, st.session_state.smiles)
        if matches:
            match_rows = []
            for match in matches:
                match_rows.append({
                    "Parent": match.get("parent", input_name),
                    "Impurity ID": match.get("id"),
                    "Name": match.get("name"),
                    "Origin": match.get("origin"),
                    "Alert": match.get("alert"),
                    "Provisional Class": f"Class {match.get('class')}",
                    "CAS": match.get("cas") or "",
                    "Source": match.get("source_name"),
                    "URL": match.get("source_url") or "",
                    "Issue": match.get("issue"),
                })
            st.dataframe(pd.DataFrame(match_rows), use_container_width=True, hide_index=True)
        else:
            st.warning("No USP/EP/DMF-style impurity match found in the current curated library.")

    with tab4:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("#### Submission-Ready Regulatory Narrative")
        narrative = generate_regulatory_narrative(st.session_state.results, input_name or "the submitted compound")
        st.text_area("Narrative Preview", value=narrative, height=360)
        st.button("📥 Download PDF Report")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab5:
        package = st.session_state.evidence_package or {}
        report = package.get("worker_report", {})
        manifest = package.get("harness_manifest", {})
        validation = report.get("validation", {})

        st.markdown("<div class='accent-text'>worker-report.v1</div>", unsafe_allow_html=True)
        h_col1, h_col2, h_col3, h_col4 = st.columns(4)
        h_col1.metric("Harness", manifest.get("status", "N/A"))
        h_col2.metric("Policy", manifest.get("policy", "N/A"))
        h_col3.metric("Passed", validation.get("passed", 0))
        h_col4.metric("Review", validation.get("review", 0))

        gates = validation.get("gates") or package.get("validation_gates") or st.session_state.results.get("validation_gates", [])
        if gates:
            st.markdown("#### Validation Gates")
            st.dataframe(pd.DataFrame(gates), use_container_width=True, hide_index=True)

        if report:
            st.markdown("#### Harness Summary")
            st.json(report, expanded=False)
        else:
            st.warning("Harness report is not available for this run.")

else:
    st.image("./hero.png", use_container_width=True)
    st.markdown("<div style='text-align: center; color: #64748b;'>Precision regulatory decision support platform.</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption(f"ToxiScope AI v2.0 | Harness: {project_id} | Security Level: R01-R13")
