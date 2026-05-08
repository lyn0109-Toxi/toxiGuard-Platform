import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import base64
import sys
import os
import urllib.parse
import requests

# --- Robust Module Resolution ---
from pathlib import Path

def add_project_root():
    try:
        # Check script directory and working directory
        starts = [Path(__file__).resolve().parent, Path.cwd()]
        for start in starts:
            for parent in [start] + list(start.parents):
                if (parent / 'core').is_dir():
                    path_str = str(parent)
                    if path_str not in sys.path:
                        sys.path.insert(0, path_str)
                    return True
    except Exception:
        pass
    return False

if not add_project_root():
    st.error("Critical Error: 'core' module not found in any parent directories.")
    st.info(f"Current Working Directory: {os.getcwd()}")
    st.info(f"Script File: {__file__ if '__file__' in globals() else 'Unknown'}")
    st.stop()

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
    from core.bioequivalence import (
        DEFAULT_DISSOLUTION_PROFILE,
        calculate_f2,
        dissolution_profile_summary,
        FDA_BE_GUIDANCE_SOURCES,
        lookup_reference_product_package,
        sampling_times_to_profile,
        be_strategy_by_dosage_form,
    )
    from core.ontology import (
        FDA_GUIDANCE_MAP,
        ROLE_GUIDANCE,
        build_strategy_snapshot,
        build_submission_workflow,
    )
except ImportError as e:
    st.error(f"Module Import Error: {e}")
    st.stop()

# Try importing RDKit. Keep core chemistry separate from drawing because
# Streamlit Cloud can have drawing-backend differences.
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski, rdDepictor, rdMolDescriptors
    RDKIT_AVAILABLE = True
except ImportError as e:
    RDKIT_IMPORT_ERROR = str(e)
    RDKIT_AVAILABLE = False

try:
    from rdkit.Chem.Draw import rdMolDraw2D
    RDKIT_DRAW_AVAILABLE = True
    RDKIT_DRAW_ERROR = ""
except ImportError as e:
    RDKIT_DRAW_ERROR = str(e)
    RDKIT_DRAW_AVAILABLE = False

# --- Page Configuration ---
st.set_page_config(
    page_title="ToxiGuard-Platform | Regulatory Strategy",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

hero_path = Path(__file__).parent / "hero.png"
hero_bg_uri = ""
if hero_path.exists():
    hero_bg_uri = "data:image/png;base64," + base64.b64encode(hero_path.read_bytes()).decode("ascii")

ontology_map_path = Path(__file__).parent / "ontology_map.png"
ontology_map_uri = ""
if ontology_map_path.exists():
    ontology_map_uri = "data:image/png;base64," + base64.b64encode(ontology_map_path.read_bytes()).decode("ascii")

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

.brand-lockup {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    margin: 0.08rem 0 0.75rem;
}

.brand-mark {
    width: 5.2rem;
    height: 5.2rem;
    position: relative;
    flex: 0 0 5.2rem;
    overflow: hidden;
    border: 1.5px solid rgba(94, 234, 212, 0.86);
    border-radius: 16px;
    background:
        linear-gradient(135deg, rgba(20, 184, 166, 0.24), rgba(14, 165, 233, 0.12)),
        linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px),
        linear-gradient(0deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px),
        rgba(2, 6, 23, 0.72);
    background-size: auto, 1.35rem 1.35rem, 1.35rem 1.35rem, auto;
    box-shadow:
        0 0 0 1px rgba(251, 191, 36, 0.16) inset,
        0 18px 38px rgba(14, 165, 233, 0.26),
        0 0 34px rgba(94, 234, 212, 0.22);
}

.brand-mark::before {
    content: "";
    position: absolute;
    width: 0.72rem;
    height: 0.72rem;
    left: 0.78rem;
    top: 0.82rem;
    border-radius: 999px;
    background: #fbbf24;
    box-shadow: 0 0 22px rgba(251, 191, 36, 0.66);
    animation: orbitDotA 3.8s ease-in-out infinite alternate;
}

.brand-mark::after {
    content: "";
    position: absolute;
    width: 0.62rem;
    height: 0.62rem;
    right: 0.74rem;
    bottom: 0.8rem;
    border-radius: 999px;
    background: #5eead4;
    box-shadow:
        -2.6rem -1.15rem 0 #38bdf8,
        0 0 24px rgba(94, 234, 212, 0.58);
    animation: orbitDotB 4.6s ease-in-out infinite alternate;
}

.hero-title {
    font-size: clamp(4.5rem, 7.4vw, 6.35rem);
    font-weight: 900;
    background: linear-gradient(135deg, #ffffff 0%, #dbeafe 42%, #5eead4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 0.94;
    margin: 0;
    letter-spacing: 0;
    filter: drop-shadow(0 16px 34px rgba(14, 165, 233, 0.34));
}

@keyframes orbitDotA {
    0% { transform: translate3d(0, 0, 0) scale(1); }
    42% { transform: translate3d(2.75rem, 0.8rem, 0) scale(0.82); }
    100% { transform: translate3d(1.25rem, 3.05rem, 0) scale(1.15); }
}

@keyframes orbitDotB {
    0% { transform: translate3d(0, 0, 0) scale(1); }
    48% { transform: translate3d(-2.55rem, -0.9rem, 0) scale(1.14); }
    100% { transform: translate3d(-0.95rem, -3.05rem, 0) scale(0.86); }
}

.brand-rule {
    width: min(620px, 72%);
    height: 3px;
    margin: -0.32rem 0 0.9rem;
    border-radius: 999px;
    background: linear-gradient(90deg, #fbbf24 0%, #5eead4 38%, rgba(14, 165, 233, 0) 100%);
    box-shadow: 0 0 22px rgba(94, 234, 212, 0.28);
}

.accent-text {
    color: #5eead4;
    font-family: 'JetBrains Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.3em;
    font-weight: 900;
    font-size: 1.02rem;
    text-shadow: 0 0 22px rgba(94, 234, 212, 0.42);
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

section[data-testid="stSidebar"] h1 {
    font-size: 1.55rem;
    color: #f8fafc;
    margin-bottom: 0.4rem;
}

section[data-testid="stSidebar"] label {
    color: #a5b4fc !important;
    font-size: 0.78rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.02em;
}

section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea,
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    color: #f8fafc !important;
    background: rgba(15, 23, 42, 0.92) !important;
    border-color: rgba(148, 163, 184, 0.28) !important;
}

.sidebar-section {
    margin: 1.05rem 0 0.55rem;
    padding: 0.75rem 0.75rem 0.7rem;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-left: 4px solid #0ea5e9;
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.55);
}

.sidebar-section-title {
    color: #f8fafc;
    font-size: 0.92rem;
    font-weight: 900;
    line-height: 1.2;
    margin-bottom: 0.18rem;
}

.sidebar-section-caption {
    color: #94a3b8;
    font-size: 0.72rem;
    line-height: 1.25;
}

.primary-start {
    border: 1px solid rgba(56, 189, 248, 0.55);
    border-left: 6px solid #38bdf8;
    background: linear-gradient(135deg, rgba(14, 165, 233, 0.24), rgba(15, 23, 42, 0.82));
    box-shadow: 0 20px 50px rgba(14, 165, 233, 0.14);
    border-radius: 14px;
    padding: 1rem 1.15rem 0.95rem;
    margin: 0.45rem 0 0.8rem;
}

.primary-start-kicker {
    color: #7dd3fc;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 0.25rem;
}

.primary-start-title {
    color: #ffffff;
    font-size: 1.5rem;
    font-weight: 900;
    line-height: 1.1;
    margin-bottom: 0.3rem;
}

.primary-start-caption {
    color: #cbd5e1;
    font-size: 0.88rem;
    line-height: 1.35;
}

.developer-card {
    margin-top: 1rem;
    padding: 0.95rem;
    border: 1px solid rgba(56, 189, 248, 0.28);
    border-radius: 10px;
    background: rgba(2, 6, 23, 0.62);
}

.developer-name {
    color: #ffffff;
    font-size: 1rem;
    font-weight: 900;
    margin-bottom: 0.2rem;
}

.developer-role {
    color: #cbd5e1;
    font-size: 0.78rem;
    line-height: 1.35;
    margin-bottom: 0.45rem;
}

.developer-link {
    color: #7dd3fc !important;
    font-size: 0.8rem;
    font-weight: 800;
    text-decoration: none;
}

.be-product-card {
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 10px;
    padding: 1rem;
    margin: 0.65rem 0;
    background: rgba(15, 23, 42, 0.72);
}

.be-product-title {
    color: #ffffff;
    font-size: 1.18rem;
    font-weight: 900;
    line-height: 1.25;
    margin-bottom: 0.35rem;
    overflow-wrap: anywhere;
}

.be-product-line {
    color: #dbeafe;
    font-size: 0.92rem;
    line-height: 1.45;
    overflow-wrap: anywhere;
}

.be-product-label {
    color: #7dd3fc;
    font-weight: 900;
}

div[data-testid="stTextInput"] input[aria-label="Chemical / API name"] {
    border: 2px solid rgba(56, 189, 248, 0.9) !important;
    background: rgba(2, 6, 23, 0.88) !important;
    color: #ffffff !important;
    font-size: 1.08rem !important;
    font-weight: 800 !important;
    min-height: 3.1rem;
}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea {
    border: 1.5px solid rgba(45, 212, 191, 0.62) !important;
    border-radius: 10px !important;
    background: linear-gradient(135deg, rgba(2, 6, 23, 0.96), rgba(8, 47, 73, 0.74)) !important;
    color: #f8fafc !important;
    box-shadow: 0 0 0 1px rgba(45, 212, 191, 0.12) inset, 0 12px 28px rgba(2, 6, 23, 0.24);
    transition: border-color 140ms ease, box-shadow 140ms ease, background 140ms ease;
}

div[data-testid="stTextInput"] input:hover,
div[data-testid="stNumberInput"] input:hover,
div[data-testid="stTextArea"] textarea:hover {
    border-color: rgba(94, 234, 212, 0.95) !important;
    background: linear-gradient(135deg, rgba(8, 47, 73, 0.94), rgba(2, 6, 23, 0.98)) !important;
}

div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(251, 191, 36, 0.98) !important;
    box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.2), 0 0 0 1px rgba(251, 191, 36, 0.4) inset !important;
}

div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stNumberInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder {
    color: rgba(203, 213, 225, 0.62) !important;
}

div[data-testid="stTextInput"] label,
div[data-testid="stNumberInput"] label,
div[data-testid="stTextArea"] label {
    color: #fef3c7 !important;
    font-weight: 900 !important;
}

div[data-testid="stNumberInput"] button {
    border-color: rgba(45, 212, 191, 0.5) !important;
    color: #5eead4 !important;
    background: rgba(13, 148, 136, 0.12) !important;
}

.block-container {
    padding-top: 2.6rem !important;
}

div[data-testid="stButton"] > button,
div[data-testid="stFormSubmitButton"] > button {
    border: 1px solid rgba(251, 191, 36, 0.78) !important;
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.94), rgba(20, 184, 166, 0.88)) !important;
    color: #04111f !important;
    font-weight: 900 !important;
    letter-spacing: 0.01em;
    box-shadow: 0 14px 32px rgba(20, 184, 166, 0.18), 0 0 0 1px rgba(251, 191, 36, 0.18) inset;
    transition: transform 140ms ease, box-shadow 140ms ease, filter 140ms ease;
}

div[data-testid="stButton"] > button:hover,
div[data-testid="stFormSubmitButton"] > button:hover {
    border-color: rgba(253, 224, 71, 0.96) !important;
    filter: brightness(1.08) saturate(1.08);
    transform: translateY(-1px);
    box-shadow: 0 18px 40px rgba(20, 184, 166, 0.28), 0 0 0 2px rgba(253, 224, 71, 0.26) inset;
}

div[data-testid="stButton"] > button:focus,
div[data-testid="stFormSubmitButton"] > button:focus {
    box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.34), 0 18px 40px rgba(20, 184, 166, 0.22) !important;
}

div[role="radiogroup"] {
    gap: 0.45rem;
}

div[role="radiogroup"] label {
    border: 1px solid rgba(45, 212, 191, 0.28);
    border-radius: 10px;
    padding: 0.52rem 0.7rem;
    background: rgba(13, 148, 136, 0.12);
    color: #ccfbf1 !important;
    transition: background 140ms ease, border-color 140ms ease, transform 140ms ease;
}

div[role="radiogroup"] label:hover {
    border-color: rgba(251, 191, 36, 0.72);
    background: rgba(251, 191, 36, 0.14);
    transform: translateX(2px);
}

div[role="radiogroup"] label:has(input:checked) {
    border-color: rgba(251, 191, 36, 0.9);
    background: linear-gradient(135deg, rgba(251, 191, 36, 0.24), rgba(20, 184, 166, 0.2));
    box-shadow: 0 0 0 1px rgba(251, 191, 36, 0.25) inset;
}

div[data-baseweb="select"] > div {
    border: 1px solid rgba(45, 212, 191, 0.48) !important;
    background: rgba(13, 148, 136, 0.16) !important;
    box-shadow: 0 0 0 1px rgba(45, 212, 191, 0.08) inset;
}

div[data-baseweb="select"] > div:hover {
    border-color: rgba(251, 191, 36, 0.82) !important;
    background: rgba(251, 191, 36, 0.12) !important;
}

details[data-testid="stExpander"] {
    border: 1px solid rgba(45, 212, 191, 0.28) !important;
    border-radius: 10px;
    background: rgba(2, 44, 34, 0.24);
}

details[data-testid="stExpander"] summary {
    color: #fef3c7 !important;
    font-weight: 900;
}

details[data-testid="stExpander"]:hover {
    border-color: rgba(251, 191, 36, 0.7) !important;
    background: rgba(69, 26, 3, 0.18);
}

a {
    color: #fbbf24 !important;
    font-weight: 800;
}

a:hover {
    color: #5eead4 !important;
}

.landing-shell {
    min-height: calc(100vh - 2.2rem);
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    gap: 0.42rem;
    padding: 0 0 0.35rem;
}

.landing-brand {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.25rem 0 0.1rem;
}

.landing-brand .brand-mark {
    width: 4.1rem;
    height: 4.1rem;
    flex-basis: 4.1rem;
    border-radius: 14px;
    box-shadow:
        0 0 0 1px rgba(251, 191, 36, 0.18) inset,
        0 16px 34px rgba(14, 165, 233, 0.24),
        0 0 42px rgba(94, 234, 212, 0.22);
}

.landing-brand .brand-mark::before {
    width: 0.56rem;
    height: 0.56rem;
    left: 0.82rem;
    top: 1rem;
    animation: landingDotA 4.2s ease-in-out infinite alternate;
}

.landing-brand .brand-mark::after {
    width: 0.52rem;
    height: 0.52rem;
    right: 0.88rem;
    bottom: 0.95rem;
    box-shadow:
        -1.75rem -0.65rem 0 #38bdf8,
        0 0 24px rgba(94, 234, 212, 0.58);
    animation: landingDotB 4.8s ease-in-out infinite alternate;
}

.landing-title {
    font-size: clamp(3.35rem, 5.2vw, 5.45rem);
    line-height: 0.92;
    margin: 0;
    font-weight: 900;
    background: linear-gradient(135deg, #ffffff 0%, #dbeafe 36%, #5eead4 76%, #fbbf24 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 18px 42px rgba(14, 165, 233, 0.42));
}

.landing-subtitle {
    color: #dbeafe;
    font-size: 0.92rem;
    max-width: 1460px;
    line-height: 1.22;
    margin-bottom: 0;
    padding: 0.32rem 0.72rem;
    border-left: 3px solid rgba(251, 191, 36, 0.78);
    border-radius: 10px;
    background: linear-gradient(90deg, rgba(15, 23, 42, 0.58), rgba(15, 23, 42, 0.08));
}

.ontology-stage {
    position: relative;
    overflow: hidden;
    margin-top: 0;
    border: 1px solid rgba(94, 234, 212, 0.58);
    border-radius: 22px;
    background:
        linear-gradient(135deg, rgba(2, 6, 23, 0.9), rgba(8, 47, 73, 0.62)),
        rgba(15, 23, 42, 0.62);
    box-shadow:
        0 30px 80px rgba(2, 6, 23, 0.46),
        0 0 0 1px rgba(251, 191, 36, 0.12) inset,
        0 0 54px rgba(94, 234, 212, 0.13);
    padding: 0.5rem;
    max-height: 64vh;
}

.ontology-stage img {
    width: 100%;
    height: 100%;
    display: block;
    border-radius: 12px;
    object-fit: contain;
}

.ontology-animated-map {
    position: relative;
    overflow: hidden;
    border-radius: 17px;
    cursor: zoom-in;
    background:
        radial-gradient(circle at 18% 20%, rgba(94, 234, 212, 0.12), transparent 28%),
        radial-gradient(circle at 84% 72%, rgba(251, 191, 36, 0.08), transparent 30%),
        #f8fbfe;
    height: min(63vh, 49vw);
    max-height: 63vh;
}

.ontology-map-canvas {
    position: relative;
    width: 100%;
    height: 100%;
    transform-origin: 50% 46%;
    transition: transform 720ms cubic-bezier(0.2, 0.8, 0.2, 1), filter 720ms ease;
    will-change: transform;
}

.ontology-map-canvas:focus {
    outline: none;
}

.ontology-animated-map:hover .ontology-map-canvas,
.ontology-map-canvas:focus {
    transform: scale(1.14);
    filter: saturate(1.04) contrast(1.02);
    animation: ontologyInspectPan 18s ease-in-out infinite alternate;
}

.ontology-map-canvas img {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: contain;
    object-position: center top;
    transform: none;
}

.electron {
    position: absolute;
    width: 0.48rem;
    height: 0.48rem;
    border-radius: 999px;
    pointer-events: none;
    z-index: 2;
    opacity: 0;
    background: #5eead4;
    box-shadow:
        0 0 0 3px rgba(94, 234, 212, 0.18),
        0 0 18px rgba(94, 234, 212, 0.9),
        0 0 34px rgba(14, 165, 233, 0.55);
    animation-duration: 8.4s;
    animation-timing-function: cubic-bezier(0.42, 0, 0.22, 1);
    animation-iteration-count: infinite;
}

.electron::after {
    content: "";
    position: absolute;
    width: 1.55rem;
    height: 0.16rem;
    right: 0.16rem;
    top: 50%;
    border-radius: 999px;
    background: linear-gradient(90deg, transparent, rgba(94, 234, 212, 0.42));
    filter: blur(1px);
    transform: translateY(-50%);
    opacity: 0.68;
}

.electron.gold {
    background: #fbbf24;
    box-shadow:
        0 0 0 3px rgba(251, 191, 36, 0.18),
        0 0 18px rgba(251, 191, 36, 0.85),
        0 0 34px rgba(245, 158, 11, 0.52);
}

.electron.gold::after {
    background: linear-gradient(90deg, transparent, rgba(251, 191, 36, 0.44));
}

.electron.red {
    background: #fb7185;
    box-shadow:
        0 0 0 3px rgba(251, 113, 133, 0.18),
        0 0 18px rgba(251, 113, 133, 0.85),
        0 0 34px rgba(244, 63, 94, 0.48);
}

.electron.red::after {
    background: linear-gradient(90deg, transparent, rgba(251, 113, 133, 0.44));
}

.electron.e1 { animation-name: electronWhy; animation-delay: 0s; }
.electron.e2 { animation-name: electronProduct; animation-delay: 0.7s; }
.electron.e3 { animation-name: electronSafety; animation-delay: 1.2s; }
.electron.e4 { animation-name: electronRegulatory; animation-delay: 1.8s; }
.electron.e5 { animation-name: electronCmc; animation-delay: 2.4s; }
.electron.e6 { animation-name: electronBe; animation-delay: 3s; }

.node-glow {
    position: absolute;
    pointer-events: none;
    z-index: 1;
    border-radius: 14px;
    opacity: 0;
    background: rgba(94, 234, 212, 0.06);
    box-shadow:
        0 0 0 2px rgba(94, 234, 212, 0.34),
        0 0 28px rgba(94, 234, 212, 0.46),
        0 0 54px rgba(251, 191, 36, 0.16);
    animation-duration: 8.4s;
    animation-timing-function: ease-in-out;
    animation-iteration-count: infinite;
}

.node-glow.why { left: 12.2%; top: 15.9%; width: 11.2%; height: 5.4%; animation-name: glowNode; animation-delay: 0s; }
.node-glow.product { left: 13.6%; top: 42.5%; width: 12.7%; height: 5.4%; animation-name: glowNode; animation-delay: 0.7s; }
.node-glow.safety { left: 34.2%; top: 37.4%; width: 11.8%; height: 5.3%; animation-name: glowNode; animation-delay: 1.2s; }
.node-glow.impurity { left: 63.2%; top: 37.4%; width: 12%; height: 5.3%; animation-name: glowNode; animation-delay: 1.2s; }
.node-glow.regulatory { left: 83.1%; top: 51.2%; width: 12.6%; height: 5.3%; animation-name: glowNode; animation-delay: 1.8s; }
.node-glow.cmc { left: 19.2%; top: 67.3%; width: 12.4%; height: 5.3%; animation-name: glowNode; animation-delay: 2.4s; }
.node-glow.be { left: 66.4%; top: 67.4%; width: 12%; height: 5.3%; animation-name: glowNode; animation-delay: 3s; }
.node-glow.output { left: 48.6%; top: 80.2%; width: 11.6%; height: 5.2%; animation-name: glowNode; animation-delay: 3.1s; }

@keyframes glowNode {
    0%, 24%, 100% { opacity: 0; transform: scale(0.99); }
    36%, 58% { opacity: 1; transform: scale(1.012); }
    72% { opacity: 0; transform: scale(1); }
}

@keyframes ontologyInspectPan {
    0% { transform: scale(1.14) translate3d(0, 0, 0); }
    34% { transform: scale(1.16) translate3d(-1.6%, 0.8%, 0); }
    68% { transform: scale(1.15) translate3d(1.4%, -0.7%, 0); }
    100% { transform: scale(1.17) translate3d(-0.5%, -0.9%, 0); }
}

@keyframes electronWhy {
    0% { left: 24.8%; top: 18.3%; opacity: 0; transform: translate(-50%, -50%) scale(0.65) rotate(0deg); }
    14% { opacity: 0.92; }
    36% { left: 40%; top: 18.15%; opacity: 0.92; transform: translate(-50%, -50%) scale(0.94) rotate(4deg); }
    63% { left: 61%; top: 18.35%; opacity: 0.88; transform: translate(-50%, -50%) scale(1) rotate(-3deg); }
    86% { opacity: 0.82; }
    100% { left: 80%; top: 18.2%; opacity: 0; transform: translate(-50%, -50%) scale(0.65) rotate(0deg); }
}

@keyframes electronProduct {
    0% { left: 12.6%; top: 40.8%; opacity: 0; transform: translate(-50%, -50%) scale(0.62) rotate(18deg); }
    15% { opacity: 0.9; }
    38% { left: 22%; top: 45.2%; opacity: 0.88; transform: translate(-50%, -50%) scale(0.9) rotate(20deg); }
    68% { left: 34%; top: 50.6%; opacity: 0.86; transform: translate(-50%, -50%) scale(1) rotate(22deg); }
    100% { left: 45.5%; top: 55.7%; opacity: 0; transform: translate(-50%, -50%) scale(0.62) rotate(18deg); }
}

@keyframes electronSafety {
    0% { left: 38%; top: 36.1%; opacity: 0; transform: translate(-50%, -50%) scale(0.64) rotate(48deg); }
    16% { opacity: 0.9; }
    42% { left: 46%; top: 43.7%; opacity: 0.86; transform: translate(-50%, -50%) scale(0.98) rotate(48deg); }
    68% { left: 55.4%; top: 44%; opacity: 0.86; transform: translate(-50%, -50%) scale(1) rotate(-34deg); }
    100% { left: 63.8%; top: 36.2%; opacity: 0; transform: translate(-50%, -50%) scale(0.64) rotate(-34deg); }
}

@keyframes electronRegulatory {
    0% { left: 56%; top: 55.3%; opacity: 0; transform: translate(-50%, -50%) scale(0.64) rotate(0deg); }
    14% { opacity: 0.9; }
    46% { left: 71%; top: 55.1%; opacity: 0.88; transform: translate(-50%, -50%) scale(0.98) rotate(0deg); }
    74% { left: 84%; top: 53.2%; opacity: 0.84; transform: translate(-50%, -50%) scale(0.94) rotate(-15deg); }
    100% { left: 91%; top: 49%; opacity: 0; transform: translate(-50%, -50%) scale(0.64) rotate(-22deg); }
}

@keyframes electronCmc {
    0% { left: 25%; top: 70%; opacity: 0; transform: translate(-50%, -50%) scale(0.62) rotate(22deg); }
    16% { opacity: 0.9; }
    46% { left: 37%; top: 75%; opacity: 0.86; transform: translate(-50%, -50%) scale(0.96) rotate(22deg); }
    72% { left: 46.5%; top: 80.4%; opacity: 0.82; transform: translate(-50%, -50%) scale(0.92) rotate(34deg); }
    100% { left: 51%; top: 82%; opacity: 0; transform: translate(-50%, -50%) scale(0.62) rotate(34deg); }
}

@keyframes electronBe {
    0% { left: 72%; top: 70%; opacity: 0; transform: translate(-50%, -50%) scale(0.62) rotate(144deg); }
    16% { opacity: 0.9; }
    44% { left: 65.5%; top: 74.5%; opacity: 0.88; transform: translate(-50%, -50%) scale(0.96) rotate(144deg); }
    72% { left: 57.2%; top: 79.5%; opacity: 0.82; transform: translate(-50%, -50%) scale(0.92) rotate(150deg); }
    100% { left: 52%; top: 82%; opacity: 0; transform: translate(-50%, -50%) scale(0.62) rotate(150deg); }
}

.landing-note {
    color: #94a3b8;
    font-size: 0.76rem;
    line-height: 1.2;
    position: fixed;
    left: 2rem;
    bottom: 1.35rem;
    z-index: 7;
    max-width: 54rem;
    padding: 0.42rem 0.7rem;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 999px;
    background: rgba(2, 6, 23, 0.72);
    backdrop-filter: blur(10px);
}

@keyframes landingDotA {
    0% { transform: translate3d(0, 0, 0) scale(1); }
    48% { transform: translate3d(1.8rem, 0.72rem, 0) scale(0.88); }
    100% { transform: translate3d(0.72rem, 2.1rem, 0) scale(1.12); }
}

@keyframes landingDotB {
    0% { transform: translate3d(0, 0, 0) scale(1); }
    52% { transform: translate3d(-1.65rem, -0.68rem, 0) scale(1.12); }
    100% { transform: translate3d(-0.66rem, -2rem, 0) scale(0.86); }
}

</style>
""", unsafe_allow_html=True)

if hero_bg_uri:
    st.markdown(
        f"""
        <style>
        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            background-image:
                linear-gradient(90deg, rgba(2, 6, 23, 0.98) 0%, rgba(15, 23, 42, 0.94) 42%, rgba(15, 23, 42, 0.86) 100%),
                url("{hero_bg_uri}");
            background-size: 100% auto;
            background-repeat: no-repeat;
            background-position: center top;
            background-color: #0f172a;
            opacity: 0.5;
            transform: scale(1.01);
            animation: genotoxDrift 34s ease-in-out infinite alternate;
        }}

        .stApp::after {{
            content: "";
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            background:
                radial-gradient(circle at 20% 18%, rgba(14, 165, 233, 0.16), transparent 34%),
                radial-gradient(circle at 82% 72%, rgba(239, 68, 68, 0.10), transparent 32%);
        }}

        [data-testid="stAppViewContainer"] > .main,
        section[data-testid="stSidebar"],
        header[data-testid="stHeader"] {{
            position: relative;
            z-index: 1;
        }}

        header[data-testid="stHeader"] {{
            background: transparent;
        }}

        @keyframes genotoxDrift {{
            0% {{
                transform: scale(1.01) translate3d(-0.45%, -0.25%, 0);
                filter: saturate(1.03) brightness(0.92);
            }}
            50% {{
                transform: scale(1.035) translate3d(0.45%, 0.28%, 0);
                filter: saturate(1.14) brightness(1.02);
            }}
            100% {{
                transform: scale(1.02) translate3d(-0.18%, 0.48%, 0);
                filter: saturate(1.08) brightness(0.96);
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

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
if "be_profile" not in st.session_state:
    st.session_state.be_profile = DEFAULT_DISSOLUTION_PROFILE.copy()
if "fda_reference_package" not in st.session_state:
    st.session_state.fda_reference_package = None
if "primary_chemical_name" not in st.session_state:
    st.session_state.primary_chemical_name = ""
if "active_chemical_name" not in st.session_state:
    st.session_state.active_chemical_name = ""
if "integrated_run_log" not in st.session_state:
    st.session_state.integrated_run_log = []
if "active_screen" not in st.session_state:
    st.session_state.active_screen = "Strategy Dashboard"
if "entered_platform" not in st.session_state:
    st.session_state.entered_platform = False

if not st.session_state.entered_platform:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        .block-container {
            max-width: 1480px !important;
            padding-top: 0.4rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        div[data-testid="stButton"] {
            position: fixed;
            left: 50%;
            bottom: 1.05rem;
            z-index: 8;
            width: min(22rem, calc(100vw - 4rem));
            transform: translateX(-50%);
        }
        div[data-testid="stButton"] > button {
            min-height: 3rem;
            border-radius: 14px !important;
            font-size: 1rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

DEVELOPER_NAME = "Young-nam Lee"
DEVELOPER_EMAIL = "lyn0109@gmail.com"
DEVELOPER_LINKEDIN = "https://www.linkedin.com/in/youngnam-lee-b45016bb"

# --- UI Layout ---
with st.sidebar:
    st.title("Project Scope")
    project_id = st.text_input("Project ID", value="TXS-2026-001")
    analyst = st.text_input("Expert Analyst", value="Lee Young-nam")
    reference_product = st.text_input(
        "Reference Product / RLD Name",
        value="",
        help="Enter the comparator product name or RLD. Do not enter the API SMILES here.",
    )
    reference_smiles = st.text_area(
        "Reference API SMILES (optional)",
        value="",
        height=70,
        help="Optional. Use this only when you want to document the reference API structure separately.",
    )

    st.markdown(
        "<div class='sidebar-section'><div class='sidebar-section-title'>Development Factors</div><div class='sidebar-section-caption'>Regulatory pathway, role view, dosage form, and dose assumptions.</div></div>",
        unsafe_allow_html=True,
    )
    development_stage = st.selectbox(
        "Development Stage",
        ["Preformulation", "Preclinical", "IND-enabling", "Phase 1", "Phase 2/3", "ANDA / Generic", "NDA / 505(b)(2)", "Post-approval change"],
        index=5,
    )
    submission_path = st.selectbox(
        "Submission Pathway",
        ["ANDA", "NDA", "505(b)(2)", "IND", "DMF", "IMPD / CTA", "Post-approval variation"],
        index=0,
    )
    user_role = st.selectbox("Platform View", list(ROLE_GUIDANCE.keys()), index=0)
    dosage_form = st.selectbox(
        "Dosage Form",
        ["Immediate-release tablet/capsule", "Modified-release oral solid", "Oral solution", "Injectable", "Semisolid", "Other"],
        index=0,
    )
    daily_dose_mg = st.number_input("Daily Dose (mg/day)", min_value=0.001, value=10.0, step=1.0)

    st.markdown(
        "<div class='sidebar-section'><div class='sidebar-section-title'>Compliance Factors</div><div class='sidebar-section-caption'>Locked or active rules used to drive the assessment logic.</div></div>",
        unsafe_allow_html=True,
    )
    st.checkbox("ICH M7(R2) Guidelines", value=True, disabled=True)
    st.checkbox("ASHBY Structural Alerts", value=True, disabled=True)
    st.checkbox("Proactive Degradation", value=True)
    st.checkbox("Bioequivalence / f2 Strategy", value=True)

    st.markdown(
        f"""
        <div class='developer-card'>
            <div class='developer-name'>Developed by {DEVELOPER_NAME}</div>
            <div class='developer-role'>Regulatory science, CMC strategy, in silico toxicology, and bioequivalence decision support.</div>
            <a class='developer-link' href='mailto:{DEVELOPER_EMAIL}'>Request consulting: {DEVELOPER_EMAIL}</a><br>
            <a class='developer-link' href='{DEVELOPER_LINKEDIN}' target='_blank'>LinkedIn profile</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

def build_integrated_assessment(chemical_name):
    name = (chemical_name or "").strip()
    if not name:
        return ["Enter a chemical/API name first."]

    log = []
    st.session_state.active_chemical_name = name

    res = get_smiles_from_name(name)
    if res:
        st.session_state.smiles = res["smiles"]
        st.session_state.identity = res
        run_assessment(name, res["smiles"])
        log.append(f"Resolved SMILES from {res.get('source', 'identity source')}.")
        log.append("Completed QSAR, ICH M7, impurity, and degradation assessment.")
    else:
        log.append("SMILES resolution failed. Enter SMILES manually in the manual override panel.")

    fda_package = lookup_reference_product_package(name)
    st.session_state.fda_reference_package = fda_package
    dissolution_rows = (fda_package.get("dissolution") or {}).get("rows") or []
    if dissolution_rows:
        st.session_state.be_profile = sampling_times_to_profile(dissolution_rows[0])
        log.append("Found FDA dissolution method candidates and applied the first method's sampling times.")
    else:
        log.append("No FDA dissolution method was automatically matched; use the FDA source link or enter dissolution time points manually.")

    orange_book_rows = (fda_package.get("orange_book") or {}).get("rows") or []
    if orange_book_rows:
        log.append("Found Orange Book RLD/RS candidates.")
    else:
        log.append("No Orange Book RLD/RS candidate was automatically matched.")

    st.session_state.integrated_run_log = log
    return log

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

def _simple_svg_for_molecule(mol, highlight_atoms=None, width=620, height=420):
    if mol is None:
        return None
    highlight_atoms = set(highlight_atoms or [])
    work_mol = Chem.Mol(mol)
    try:
        rdDepictor.Compute2DCoords(work_mol)
    except Exception:
        return None

    conf = work_mol.GetConformer()
    drawable_atoms = [
        atom.GetIdx()
        for atom in work_mol.GetAtoms()
        if atom.GetDegree() > 0 or atom.GetIdx() in highlight_atoms
    ]
    if not drawable_atoms:
        drawable_atoms = [atom.GetIdx() for atom in work_mol.GetAtoms()]
    counter_ions = []
    for atom in work_mol.GetAtoms():
        if atom.GetIdx() not in drawable_atoms:
            symbol = atom.GetSymbol()
            charge = atom.GetFormalCharge()
            if charge > 0:
                symbol = f"{symbol}+"
            elif charge < 0:
                symbol = f"{symbol}-"
            counter_ions.append(symbol)

    coord_by_atom = {}
    for atom_idx in drawable_atoms:
        pos = conf.GetAtomPosition(atom_idx)
        coord_by_atom[atom_idx] = (pos.x, pos.y)
    if not coord_by_atom:
        return None

    min_x = min(x for x, _ in coord_by_atom.values())
    max_x = max(x for x, _ in coord_by_atom.values())
    min_y = min(y for _, y in coord_by_atom.values())
    max_y = max(y for _, y in coord_by_atom.values())
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    pad = 58
    scale = min((width - 2 * pad) / span_x, (height - 2 * pad) / span_y)
    scale = min(scale * 1.18, 150)

    def xy(atom_idx):
        x, y = coord_by_atom[atom_idx]
        return (
            width / 2 + (x - (min_x + max_x) / 2) * scale,
            height / 2 - (y - (min_y + max_y) / 2) * scale,
        )

    bond_parts = []
    alert_halo_parts = []
    if highlight_atoms:
        for atom_idx in highlight_atoms:
            if atom_idx in coord_by_atom:
                hx, hy = xy(atom_idx)
                alert_halo_parts.append(
                    f"<circle cx='{hx:.1f}' cy='{hy:.1f}' r='24' fill='#fee2e2' stroke='#ef4444' stroke-width='1.5' opacity='0.72' />"
                )
    for bond in work_mol.GetBonds():
        a1 = bond.GetBeginAtomIdx()
        a2 = bond.GetEndAtomIdx()
        if a1 not in coord_by_atom or a2 not in coord_by_atom:
            continue
        x1, y1 = xy(a1)
        x2, y2 = xy(a2)
        order = bond.GetBondTypeAsDouble()
        color = "#111827"
        stroke_width = 2.4
        if a1 in highlight_atoms or a2 in highlight_atoms:
            color = "#b91c1c"
            stroke_width = 3.2
        bond_parts.append(
            f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' stroke='{color}' stroke-width='{stroke_width}' stroke-linecap='round' />"
        )
        if order >= 2:
            dx = x2 - x1
            dy = y2 - y1
            length = max((dx * dx + dy * dy) ** 0.5, 1.0)
            off_x = -dy / length * 4
            off_y = dx / length * 4
            bond_parts.append(
                f"<line x1='{x1 + off_x:.1f}' y1='{y1 + off_y:.1f}' x2='{x2 + off_x:.1f}' y2='{y2 + off_y:.1f}' stroke='{color}' stroke-width='1.5' stroke-linecap='round' />"
            )

    atom_parts = []
    element_colors = {
        "N": "#1d4ed8",
        "O": "#dc2626",
        "S": "#ca8a04",
        "P": "#9333ea",
        "F": "#15803d",
        "Cl": "#15803d",
        "Br": "#92400e",
        "I": "#6b21a8",
    }
    for atom in work_mol.GetAtoms():
        idx = atom.GetIdx()
        if idx not in coord_by_atom:
            continue
        x, y = xy(idx)
        symbol = atom.GetSymbol()
        charge = atom.GetFormalCharge()
        total_h = atom.GetTotalNumHs()
        h_label = ""
        if symbol != "C" and total_h > 0:
            h_label = "H" if total_h == 1 else f"H{total_h}"
        if charge > 0:
            charge_label = "+"
        elif charge < 0:
            charge_label = "-"
        else:
            charge_label = ""
        atom_label = f"{symbol}{h_label}{charge_label}"
        is_hetero = symbol not in {"C", "H"}
        is_highlight = idx in highlight_atoms
        if is_highlight or is_hetero:
            text_color = "#b91c1c" if is_highlight else element_colors.get(symbol, "#111827")
            atom_parts.append(
                f"<text x='{x:.1f}' y='{y + 5:.1f}' text-anchor='middle' font-family='Arial, sans-serif' font-size='18' font-weight='700' fill='{text_color}' stroke='#ffffff' stroke-width='4' paint-order='stroke'>{atom_label}</text>"
            )
        elif atom.GetDegree() == 0:
            atom_parts.append(
                f"<text x='{x:.1f}' y='{y + 5:.1f}' text-anchor='middle' font-family='Arial, sans-serif' font-size='16' font-weight='700' fill='#111827'>{atom_label}</text>"
            )

    ion_parts = []
    if counter_ions:
        label = "Ion pair: " + ", ".join(counter_ions)
        ion_parts.append(
            f"<line x1='{width - 242}' y1='34' x2='{width - 212}' y2='34' stroke='#6d28d9' stroke-width='1.8' stroke-dasharray='4 5' />"
        )
        ion_parts.append(
            f"<rect x='{width - 212}' y='15' width='190' height='38' rx='19' fill='#f5f3ff' stroke='#6d28d9' stroke-width='1.4' opacity='0.98' />"
        )
        ion_parts.append(
            f"<text x='{width - 117}' y='39' text-anchor='middle' font-family='Arial, sans-serif' font-size='13' font-weight='700' fill='#4c1d95'>{label}</text>"
        )

    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' width='100%' height='100%' role='img'>"
        f"<rect width='100%' height='100%' rx='12' fill='#ffffff' />"
        f"<rect x='10' y='10' width='{width - 20}' height='{height - 20}' rx='18' fill='none' stroke='#d1d5db' stroke-width='1.2' />"
        + "".join(alert_halo_parts)
        + "".join(bond_parts)
        + "".join(atom_parts)
        + "".join(ion_parts)
        + "</svg>"
    )

def render_molecule_svg(mol, highlight_atoms=None, width=620, height=420):
    if mol is None:
        return None
    return _simple_svg_for_molecule(mol, highlight_atoms=highlight_atoms, width=width, height=height)

def show_molecule(mol, highlight_atoms=None, width=620, height=420):
    svg = render_molecule_svg(mol, highlight_atoms=highlight_atoms, width=width, height=height)
    if not svg:
        st.warning("Structure rendering failed for this molecule.")
        return
    st.markdown(
        f"""
        <div style="width:100%; height:{height}px; display:flex; justify-content:center; align-items:center; background:#ffffff; border:1px solid #d1d5db; border-radius:12px; overflow:hidden;">
            {svg}
        </div>
        """,
        unsafe_allow_html=True,
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

def genotoxic_alert_rows(result):
    rows = []
    for alert in toxic_alerts(result):
        if alert.get("alert") == "Known Mutagen/Carcinogen":
            link = "Experimental genotoxicity evidence"
            functional_group = "Whole molecule / known positive record"
            alert_type = "Historical positive"
        else:
            link = alert.get("mechanism") or alert.get("reasoning") or "Structural alert linked to DNA-reactive mutagenicity review."
            functional_group = alert.get("alert")
            alert_type = "Structural alert"
        rows.append(
            {
                "Type": alert_type,
                "Functional group / structural region": functional_group,
                "Genotoxicity linkage": link,
                "Matched atoms": alert.get("matched_atoms", "N/A"),
                "Evidence": alert.get("reference") or alert.get("evidence") or "N/A",
            }
        )
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

def risk_badge_html(label, value):
    color = {
        "High": "#ef4444",
        "Medium": "#f59e0b",
        "Low": "#10b981",
        "Not started": "#64748b",
        "Review needed": "#f59e0b",
    }.get(value, "#64748b")
    return f"""
    <div class='glass-card' style='padding:1.2rem; min-height:142px;'>
        <div style='color:#94a3b8; font-size:0.85rem; font-weight:700;'>{label}</div>
        <div style='font-size:2rem; font-weight:900; color:{color}; margin-top:0.4rem;'>{value}</div>
    </div>
    """

def render_strategy_dashboard():
    snapshot = build_strategy_snapshot(
        results=st.session_state.results,
        degradants=st.session_state.degradants,
        be_result=st.session_state.get("be_result"),
        role=user_role,
    )
    workflow = build_submission_workflow(
        results=st.session_state.results,
        degradants=st.session_state.degradants,
        be_result=st.session_state.get("be_result"),
    )

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### Strategy Dashboard")
    meta_cols = st.columns(5)
    meta_cols[0].metric("Stage", development_stage)
    meta_cols[1].metric("Pathway", submission_path)
    meta_cols[2].metric("Dosage form", dosage_form)
    meta_cols[3].metric("Role view", user_role)
    meta_cols[4].metric("RLD / Reference", reference_product or "TBD")
    st.markdown("</div>", unsafe_allow_html=True)

    r1, r2, r3, r4 = st.columns(4)
    r1.markdown(risk_badge_html("Overall Regulatory Risk", snapshot["overall_risk"]), unsafe_allow_html=True)
    r2.markdown(risk_badge_html("QSAR / Genotoxicity", snapshot["toxicology_risk"]), unsafe_allow_html=True)
    r3.markdown(risk_badge_html("Impurity / Degradation", snapshot["degradation_risk"]), unsafe_allow_html=True)
    r4.markdown(risk_badge_html("Bioequivalence", snapshot["bioequivalence_risk"]), unsafe_allow_html=True)

    nav1, nav2, nav3 = st.columns(3)
    if nav1.button("Open Genotoxicity QSAR Detail", use_container_width=True):
        st.session_state.active_screen = "Genotoxicity QSAR"
        st.rerun()
    if nav2.button("Open Bioequivalence Detail", use_container_width=True):
        st.session_state.active_screen = "Bioequivalence"
        st.rerun()
    if nav3.button("Open Integrated Evidence", use_container_width=True):
        st.session_state.active_screen = "Integrated Evidence"
        st.rerun()

    st.info(f"**{user_role} focus**: {snapshot['role_focus']}  \n\n**Recommended next action**: {snapshot['role_next_action']}")

    dash_tab1, dash_tab2, dash_tab3 = st.tabs(["Workflow", "Module Actions", "Guidance Map"])
    with dash_tab1:
        st.dataframe(pd.DataFrame(workflow), use_container_width=True, hide_index=True)
    with dash_tab2:
        st.dataframe(pd.DataFrame(snapshot["module_actions"]), use_container_width=True, hide_index=True)
    with dash_tab3:
        st.dataframe(pd.DataFrame(FDA_GUIDANCE_MAP), use_container_width=True, hide_index=True)

def render_platform_quick_start():
    with st.expander("How this platform works", expanded=False):
        q1, q2, q3, q4 = st.columns(4)
        q1.info("**1. Chemical name**\n\nEnter the API, impurity, or degradant once.")
        q2.info("**2. Identity + QSAR**\n\nResolve SMILES and run ICH M7 assessment.")
        q3.info("**3. Evidence**\n\nSearch impurity, degradation, FDA product, and dissolution sources.")
        q4.info("**4. BE profile**\n\nEnter dissolution values for f2 bootstrap.")

def render_primary_chemical_start():
    st.markdown(
        """
        <div class='primary-start'>
            <div class='primary-start-kicker'>Primary Platform Input</div>
            <div class='primary-start-title'>Start with Chemical / API Name</div>
            <div class='primary-start-caption'>Enter one API, impurity, or degradant name. This single input connects identity, QSAR, impurity/degradation, FDA reference product lookup, dissolution method search, and BE strategy.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    start_col1, start_col2 = st.columns([1.55, 0.45], vertical_alignment="bottom")
    with start_col1:
        st.text_input(
            "Chemical / API name",
            key="primary_chemical_name",
            placeholder="Type a drug or impurity name: amlodipine, telmisartan, acetaminophen...",
            help="Use the active ingredient name for product-level strategy, or an impurity/degradant name for targeted ICH M7 assessment.",
        )
    with start_col2:
        if st.button("Build Integrated Assessment", use_container_width=True):
            if st.session_state.primary_chemical_name.strip():
                with st.spinner("Resolving identity, running QSAR, and searching FDA reference sources..."):
                    build_integrated_assessment(st.session_state.primary_chemical_name)
            else:
                st.warning("Enter a chemical/API name first.")

    if st.session_state.integrated_run_log:
        st.markdown("#### Integrated run status")
        for item in st.session_state.integrated_run_log:
            st.write(f"- {item}")

def render_module_navigation():
    screens = ["Strategy Dashboard", "Genotoxicity QSAR", "Bioequivalence", "Integrated Evidence"]
    current = st.session_state.active_screen if st.session_state.active_screen in screens else "Strategy Dashboard"
    st.session_state.active_screen = st.radio(
        "Module detail view",
        screens,
        index=screens.index(current),
        horizontal=True,
        help="Select a detail screen. Genotoxicity QSAR and Bioequivalence open as focused module views.",
    )

def render_bioequivalence_module():
    st.markdown("---")
    st.markdown("<div class='accent-text'>Bioequivalence Strategy</div>", unsafe_allow_html=True)
    st.markdown("## Comparative Dissolution and Bioequivalence")
    st.caption("Search the FDA reference product and dissolution method first, then enter laboratory reference/test dissolution values for f2 bootstrap analysis.")

    dosage_strategy = be_strategy_by_dosage_form(dosage_form)
    st.markdown("#### Dosage Form Release-Type Strategy")
    ds1, ds2, ds3 = st.columns(3)
    ds1.metric("Selected dosage form", dosage_form)
    ds2.metric("BE release type", dosage_strategy["Release type"])
    ds3.metric("Submission path", submission_path)
    st.info(f"**Primary BE focus**: {dosage_strategy['Primary BE focus']}")
    with st.expander("Dosage-form-specific BE requirements"):
        st.write(f"**Recommended study design**: {dosage_strategy['Recommended study design']}")
        st.write(f"**Dissolution role**: {dosage_strategy['Dissolution role']}")
        st.write(f"**Key data needs**: {dosage_strategy['Key data needs']}")
        st.warning(dosage_strategy["Risk note"])

    st.markdown("#### FDA Reference Product and Method Lookup")
    lookup_col1, lookup_col2 = st.columns([1.2, 0.8], vertical_alignment="bottom")
    with lookup_col1:
        reference_lookup_query = st.text_input(
            "Reference product, RLD, or active ingredient",
            value=reference_product or input_name or "",
            placeholder="e.g. amlodipine, Norvasc, telmisartan",
            help="The lookup searches FDA Orange Book and FDA Dissolution Methods Database. Generic active ingredient names usually work best for dissolution methods.",
        )
    with lookup_col2:
        if st.button("Search FDA reference and dissolution method", use_container_width=True):
            if reference_lookup_query and len(reference_lookup_query.strip()) >= 3:
                with st.spinner("Searching FDA Orange Book and Dissolution Methods Database..."):
                    st.session_state.fda_reference_package = lookup_reference_product_package(reference_lookup_query.strip())
            else:
                st.warning("Enter at least three characters for FDA lookup.")

    package = st.session_state.get("fda_reference_package")
    if package:
        ob = package.get("orange_book", {})
        dissolution = package.get("dissolution", {})
        source_cols = st.columns(2)
        with source_cols[0]:
            st.markdown("##### Reference drug product details")
            if ob.get("rows"):
                display_rows = []
                for row in ob["rows"]:
                    display_rows.append(
                        {
                            "Trade Name": row.get("Trade name", ""),
                            "Product Name": row.get("Trade name", ""),
                            "Company / Applicant": row.get("Applicant", ""),
                            "Dosage Strength": row.get("Strength", ""),
                            "Dosage Form": (row.get("Dosage form / route", "").split(";")[0] or "").strip(),
                            "Route": (row.get("Dosage form / route", "").split(";")[1] if ";" in row.get("Dosage form / route", "") else "").strip(),
                            "Application": row.get("Application", ""),
                            "RLD": row.get("RLD", ""),
                            "RS": row.get("RS", ""),
                            "Source": row.get("Source", "FDA Orange Book"),
                        }
                    )
                with st.expander("View all FDA product candidates", expanded=True):
                    for idx, row in enumerate(display_rows[:8], 1):
                        st.markdown(
                            f"""
                            <div class='be-product-card'>
                                <div class='be-product-title'>{idx}. {row.get('Trade Name') or 'N/A'}</div>
                                <div class='be-product-line'><span class='be-product-label'>Product Name:</span> {row.get('Product Name') or 'N/A'}</div>
                                <div class='be-product-line'><span class='be-product-label'>Company / Applicant:</span> {row.get('Company / Applicant') or 'N/A'}</div>
                                <div class='be-product-line'><span class='be-product-label'>Dosage Strength:</span> {row.get('Dosage Strength') or 'Not listed in source'}</div>
                                <div class='be-product-line'><span class='be-product-label'>Dosage Form / Route:</span> {row.get('Dosage Form') or 'N/A'} / {row.get('Route') or 'N/A'}</div>
                                <div class='be-product-line'><span class='be-product-label'>Application:</span> {row.get('Application') or 'N/A'} | <span class='be-product-label'>RLD / RS:</span> {row.get('RLD') or 'No'} / {row.get('RS') or 'No'} | <span class='be-product-label'>Source:</span> {row.get('Source') or 'FDA'}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                preferred_rows = [
                    row for row in ob["rows"]
                    if str(row.get("RLD", "")).lower() == "yes" or str(row.get("RS", "")).lower() == "yes"
                ] or ob["rows"]
                product_options = [
                    f"{idx + 1}. {row.get('Trade name')} | {row.get('Strength') or 'Dosage strength not listed'} | {row.get('Applicant')} | {row.get('Dosage form / route')}"
                    for idx, row in enumerate(preferred_rows)
                ]
                selected_product = st.selectbox("Reference trade name / dosage strength for BE plan", product_options)
                selected_product_row = preferred_rows[product_options.index(selected_product)]
                st.markdown(
                    f"""
                    <div class='be-product-card'>
                        <div class='be-product-title'>Selected reference: {selected_product_row.get('Trade name') or 'N/A'}</div>
                        <div class='be-product-line'><span class='be-product-label'>Product Name:</span> {selected_product_row.get('Trade name') or 'N/A'}</div>
                        <div class='be-product-line'><span class='be-product-label'>Company / Applicant:</span> {selected_product_row.get('Applicant') or 'N/A'}</div>
                        <div class='be-product-line'><span class='be-product-label'>Dosage Strength:</span> {selected_product_row.get('Strength') or 'Not listed in source'}</div>
                        <div class='be-product-line'><span class='be-product-label'>Dosage Form / Route:</span> {selected_product_row.get('Dosage form / route') or 'N/A'}</div>
                        <div class='be-product-line'><span class='be-product-label'>Application:</span> {selected_product_row.get('Application') or 'N/A'} | <span class='be-product-label'>Product No.:</span> {selected_product_row.get('Product no.') or 'N/A'} | <span class='be-product-label'>RLD / RS:</span> {selected_product_row.get('RLD') or 'No'} / {selected_product_row.get('RS') or 'No'}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.caption(f"Reference detail source: {selected_product_row.get('Source') or 'FDA Orange Book'}")
                with st.expander("Dosage strength / dose strategy"):
                    st.caption("Dosage Strength is the amount of active ingredient per dosage unit listed for the reference product. Dose is the administered amount in a BE study. Both matter for BE strategy.")
                    d1, d2 = st.columns(2)
                    with d1:
                        st.text_input("Reference dosage strength selected", value=selected_product_row.get("Strength", ""), key="be_reference_strength")
                    with d2:
                        st.text_input("Proposed test dosage strength", value="", key="be_test_strength")
                    st.selectbox(
                        "Dose / dosage-strength strategy",
                        ["Same strength direct BE", "Additional strength biowaiver", "Dose-proportional formulation bridge", "Strength mismatch requires strategy review"],
                        key="be_strength_strategy",
                    )
                    st.write(f"**Reference company / applicant**: {selected_product_row.get('Applicant') or 'N/A'}")
                    st.write(f"**Reference dosage form / route**: {selected_product_row.get('Dosage form / route') or 'N/A'}")
                    st.write(f"**Reference application / product no.**: {selected_product_row.get('Application') or 'N/A'} / {selected_product_row.get('Product no.') or 'N/A'}")
                    st.info("For ANDA/generic strategy, confirm RLD/RS, strength, dosage form, and whether the proposed test strength is the same as the reference or requires additional-strength/biowaiver justification.")
            else:
                drug_products = (package.get("drug_products") or {}).get("rows") or []
                label_products = (package.get("label_products") or {}).get("rows") or []
                if drug_products:
                    st.dataframe(pd.DataFrame(drug_products), use_container_width=True, hide_index=True)
                elif label_products:
                    st.dataframe(pd.DataFrame(label_products), use_container_width=True, hide_index=True)
                else:
                    st.info(ob.get("error") or "No FDA product match returned. Try the active ingredient or proprietary name.")
            st.markdown(f"[Open FDA Orange Book search]({ob.get('source_url')})")
        with source_cols[1]:
            st.markdown("##### FDA dissolution method candidates")
            if dissolution.get("rows"):
                st.dataframe(pd.DataFrame(dissolution["rows"]), use_container_width=True, hide_index=True)
                method_options = [
                    f"{idx + 1}. {row.get('Drug name')} | {row.get('Dosage form')} | {row.get('Recommended sampling times')}"
                    for idx, row in enumerate(dissolution["rows"])
                ]
                selected_method = st.selectbox("Use sampling times from FDA method", method_options)
                selected_index = method_options.index(selected_method)
                if st.button("Apply FDA sampling times to dissolution table", use_container_width=True):
                    st.session_state.be_profile = sampling_times_to_profile(dissolution["rows"][selected_index])
                    st.success("FDA sampling times were applied. Enter observed reference/test dissolution percentages before calculating f2.")
            else:
                st.info(dissolution.get("error") or "No FDA dissolution method match returned. Try the generic active ingredient.")
            st.markdown(f"[Open FDA Dissolution Methods search]({dissolution.get('source_url')})")
        with st.expander("FDA lookup interpretation"):
            for note in package.get("notes", []):
                st.write(f"- {note}")

    be_col1, be_col2 = st.columns([1.15, 0.85])
    with be_col1:
        edited_profile = st.data_editor(
            st.session_state.be_profile,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Time (min)": st.column_config.NumberColumn("Time (min)", min_value=0.0, step=5.0),
                "Reference Mean (%)": st.column_config.NumberColumn("Reference Mean (%)", min_value=0.0, max_value=150.0, step=1.0),
                "Reference SD": st.column_config.NumberColumn("Reference SD", min_value=0.0, step=0.1),
                "Reference n": st.column_config.NumberColumn("Reference n", min_value=1, step=1),
                "Test Mean (%)": st.column_config.NumberColumn("Test Mean (%)", min_value=0.0, max_value=150.0, step=1.0),
                "Test SD": st.column_config.NumberColumn("Test SD", min_value=0.0, step=0.1),
                "Test n": st.column_config.NumberColumn("Test n", min_value=1, step=1),
            },
            key="be_profile_editor",
        )
        st.session_state.be_profile = edited_profile

        chart_df = dissolution_profile_summary(edited_profile)
        if not chart_df.empty:
            plot_df = chart_df.set_index("Time (min)")[["Reference Mean (%)", "Test Mean (%)"]]
            st.line_chart(plot_df, use_container_width=True)

    with be_col2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("#### Decision Snapshot")
        bootstrap_runs = st.slider("Bootstrap iterations", min_value=500, max_value=10000, value=2000, step=500)
        if st.button("Calculate f2 with Bootstrap", use_container_width=True):
            try:
                be_result = calculate_f2(edited_profile, bootstrap_runs=bootstrap_runs)
                st.session_state.be_result = be_result
            except Exception as exc:
                st.session_state.be_result = None
                st.error(f"f2 calculation failed: {exc}")

        be_result = st.session_state.get("be_result")
        if be_result:
            st.metric("f2 Similarity Factor", be_result.f2)
            st.metric("Bootstrap 95% CI", f"{be_result.ci_low} - {be_result.ci_high}")
            st.metric("Bootstrap P(f2 ≥ 50)", f"{be_result.probability_f2_ge_50}%")
            st.write(f"**FDA strategy decision**: {be_result.fda_decision}")
            st.write(f"**FDA submission risk**: {be_result.fda_risk}")
            if be_result.f2 >= 50:
                st.success("The reference and test dissolution profiles support an FDA-style f2 similarity rationale.")
            else:
                st.error("f2 is below 50. Comparative dissolution alone is not sufficient for a similarity rationale; review formulation, process, particle size, polymorph, dissolution method, or in vivo BE strategy.")
            st.info(be_result.fda_next_action)
            if be_result.cv_flag == "Acceptable":
                st.success("Time-point variability is within the screening threshold.")
            else:
                st.warning(f"Variability review: {be_result.cv_flag}")
            backend = "R backend" if be_result.r_backend_used else "Python fallback"
            st.caption(f"{backend}: {be_result.method_note}")
            with st.expander("Bootstrap distribution detail"):
                st.write(f"**Iterations**: {be_result.bootstrap_runs}")
                st.write(f"**Median f2**: {be_result.bootstrap_median}")
                st.write(f"**5th-95th percentile**: {be_result.bootstrap_p05} - {be_result.bootstrap_p95}")
                st.write(f"**2.5th-97.5th percentile**: {be_result.ci_low} - {be_result.ci_high}")
                st.info("Bootstrap repeatedly resamples reference/test dissolution values from each time point using the entered mean, SD, and n, then recalculates f2 for each iteration.")
        else:
            st.info("Enter dissolution data and run the f2 bootstrap calculation.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### FDA Bioequivalence Guidance Basis")
    st.dataframe(pd.DataFrame(FDA_BE_GUIDANCE_SOURCES), use_container_width=True, hide_index=True)
    st.caption("Primary basis: FDA/ICH M13A for immediate-release oral solid dosage forms, FDA IR dissolution testing guidance, and FDA Dissolution Methods Database for product-specific dissolution methods.")

    summary_df = dissolution_profile_summary(st.session_state.be_profile)
    if not summary_df.empty:
        with st.expander("Detailed dissolution statistics"):
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
            st.markdown(
                """
                **FDA-oriented regulatory interpretation**
                - f2 >= 50: supports a dissolution-profile similarity rationale under FDA-style interpretation.
                - f2 < 50: comparative dissolution alone is not enough; review the product-specific FDA method, USP method, or the need for in vivo BE.
                - Variability above 20% at early time points or above 10% at later time points should be justified.
                - Final strategy should be interpreted with product-specific FDA guidance, USP method, RLD characteristics, dosage form, BCS class, and formulation proportionality.
                """
            )

def render_consultation_request():
    st.markdown("---")
    st.markdown("<div class='accent-text'>Consulting Request</div>", unsafe_allow_html=True)
    st.markdown("## Regulatory / CMC / BE Consulting")
    st.caption("Request support for QSAR/ICH M7 strategy, impurity/degradation control, FDA bioequivalence planning, or integrated regulatory development.")

    with st.form("consulting_request_form"):
        c1, c2 = st.columns(2)
        with c1:
            requester_name = st.text_input("Your name / company")
            requester_email = st.text_input("Your email")
            topic = st.selectbox(
                "Consulting topic",
                [
                    "Regulatory development strategy",
                    "ICH M7 / QSAR toxicology",
                    "Impurity and degradation control",
                    "FDA bioequivalence / dissolution strategy",
                    "Integrated ToxiGuard-Platform demo",
                ],
            )
        with c2:
            compound = st.text_input("Product / compound", value=st.session_state.active_chemical_name or st.session_state.primary_chemical_name)
            timeline = st.selectbox("Timeline", ["Exploratory", "This month", "1-3 months", "Urgent review"])
            submission_context = st.selectbox("Submission context", ["ANDA", "NDA / 505(b)(2)", "IND", "DMF", "IMPD / CTA", "Post-approval change", "Other"])
        message = st.text_area("Brief request", height=120, placeholder="Describe the product, issue, target market, and decision you need to make.")
        submitted = st.form_submit_button("Prepare email request", use_container_width=True)

    if submitted:
        subject = f"ToxiGuard consulting request - {topic}"
        body = "\n".join(
            [
                f"Name / company: {requester_name}",
                f"Requester email: {requester_email}",
                f"Topic: {topic}",
                f"Product / compound: {compound}",
                f"Timeline: {timeline}",
                f"Submission context: {submission_context}",
                "",
                "Request:",
                message,
            ]
        )
        mailto = f"mailto:{DEVELOPER_EMAIL}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        st.success("Consulting request prepared.")
        st.markdown(f"[Send consulting request to {DEVELOPER_EMAIL}]({mailto})")

def render_legal_notice():
    with st.expander("Legal, license, and regulatory-use notice", expanded=False):
        st.markdown(
            """
            **ToxiGuard-Platform is a decision-support tool, not an official
            regulatory authority system.** It is not affiliated with, endorsed
            by, certified by, or approved by FDA, ICH, USP, EP, NIH, NCI,
            PubChem, or any other regulatory or standards organization.

            QSAR, ICH M7, impurity/degradation, and bioequivalence outputs are
            preliminary strategy-support results. Final use requires expert
            review, official source verification, validated laboratory data,
            and product-specific regulatory assessment.

            USP/EP and other pharmacopeial references must be verified against
            current official licensed monographs. Do not treat this app as an
            official compendial source. Public APIs and databases may be
            incomplete, unavailable, rate-limited, or delayed.

            Repository materials are governed by the project `LICENSE`,
            `NOTICE.md`, `DISCLAIMER.md`, and `ASSET_ATTRIBUTION.md` files.
            """
        )

def render_landing_page():
    if ontology_map_uri:
        st.markdown(
            f"""
            <div class='landing-shell'>
                <div class='accent-text'>Regulatory Development Strategy Platform</div>
                <div class='landing-brand'>
                    <div class='brand-mark'></div>
                    <h1 class='landing-title'>ToxiGuard-Platform</h1>
                </div>
                <div class='landing-subtitle'>
                    Built to turn fragmented toxicology, CMC, impurity, RLD,
                    dissolution, and regulatory evidence into one development
                    strategy plan.
                </div>
                <div class='ontology-stage'>
            <div class='ontology-animated-map'>
                <div class='ontology-map-canvas' tabindex='0'>
                <img src='{ontology_map_uri}' alt='ToxiGuard-Platform ontology map' />
                <span class='node-glow why'></span>
                <span class='node-glow product'></span>
                <span class='node-glow safety'></span>
                <span class='node-glow impurity'></span>
                <span class='node-glow regulatory'></span>
                <span class='node-glow cmc'></span>
                <span class='node-glow be'></span>
                <span class='node-glow output'></span>
                <span class='electron gold e1'></span>
                <span class='electron e2'></span>
                <span class='electron red e3'></span>
                <span class='electron gold e4'></span>
                <span class='electron e5'></span>
                <span class='electron e6'></span>
                </div>
            </div>
                </div>
                <div class='landing-note'>
                    Decision support only. Final regulatory use requires expert review,
                    official source verification, and product-specific evidence.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
        <div class='landing-shell'>
            <div class='accent-text'>Regulatory Development Strategy Platform</div>
            <div class='landing-brand'>
                <div class='brand-mark'></div>
                <h1 class='landing-title'>ToxiGuard-Platform</h1>
            </div>
            <div class='landing-subtitle'>
                Built to turn fragmented toxicology, CMC, impurity, RLD,
                dissolution, and regulatory evidence into one development
                strategy plan.
            </div>
            <div class='ontology-stage'>
            """,
            unsafe_allow_html=True,
        )
        st.image("ontology_map.png", use_container_width=True)
        st.markdown(
            """
            </div>
            <div class='landing-note'>
                Decision support only. Final regulatory use requires expert review,
                official source verification, and product-specific evidence.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    c1, c2, c3 = st.columns([0.35, 0.3, 0.35])
    with c2:
        if st.button("Enter ToxiGuard-Platform", use_container_width=True):
            st.session_state.entered_platform = True
            st.rerun()

if not st.session_state.entered_platform:
    render_landing_page()
    st.stop()

st.markdown("<div class='accent-text'>Regulatory Development Strategy Platform</div>", unsafe_allow_html=True)
st.markdown(
    """
    <div class='brand-lockup'>
        <div class='brand-mark'></div>
        <h1 class='hero-title'>ToxiGuard-Platform</h1>
    </div>
    <div class='brand-rule'></div>
    """,
    unsafe_allow_html=True,
)
st.caption("Ontology + ToxiGuard-AI + ToxiScope + Bioequivalence strategy are connected through one project-level decision workflow.")

render_primary_chemical_start()
render_platform_quick_start()
input_name = (st.session_state.active_chemical_name or st.session_state.primary_chemical_name).strip()
render_module_navigation()
render_strategy_dashboard()

if st.session_state.active_screen in {"Genotoxicity QSAR", "Integrated Evidence"}:
    st.markdown("---")
    st.markdown("<div class='accent-text'>Genotoxicity QSAR Detail</div>", unsafe_allow_html=True)
    st.markdown("## ICH M7 / QSAR Assessment")
    st.caption("This focused screen shows chemical identity, structural alerts, expert/statistical QSAR, impurity/degradation evidence, and the regulatory narrative.")

    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### Manual Identity Override")
        st.caption("Use this only when automatic name resolution fails or when you need to assess a specific impurity/degradation product SMILES directly.")
        st.write(f"**Current primary chemical**: {input_name or 'Not defined'}")

        input_smiles = st.text_area(
            "Compound SMILES",
            key="smiles",
            height=110,
            help="If name search fails, paste a valid SMILES here and run the assessment manually.",
        )
        if input_smiles:
            st.caption("SMILES resolved. You can edit it manually and re-run the assessment.")

        if st.button("Run QSAR / impurity / degradation assessment from SMILES", use_container_width=True):
            if input_smiles:
                with st.spinner("Analyzing toxicity and degradation..."):
                    run_assessment(input_name or "manually submitted compound", input_smiles)
            else:
                st.warning("Please provide a SMILES string.")
        st.info("Recommended workflow: enter the chemical/API name in Start Here, then use this panel only for manual SMILES correction.")
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

if st.session_state.active_screen in {"Bioequivalence", "Integrated Evidence"}:
    render_bioequivalence_module()

if st.session_state.results and st.session_state.active_screen in {"Genotoxicity QSAR", "Integrated Evidence"}:
    st.markdown("---")
    structure_smiles = st.session_state.smiles or st.session_state.results.get("canonical_smiles")
    profile = build_structure_profile(structure_smiles)
    alert_list = toxic_alerts(st.session_state.results)
    highlighted_atoms = collect_alert_atoms(st.session_state.results)

    st.markdown("<div class='accent-text'>Molecular Structure</div>", unsafe_allow_html=True)
    map_col1, map_col2 = st.columns([1.05, 1.25])
    with map_col1:
        if profile:
            show_molecule(profile["mol"], highlighted_atoms, width=620, height=420)
            st.caption("Wikipedia-style skeletal formula. Pale red halos mark genotoxic structural-alert regions when present.")
        else:
            st.warning("Structure parsing is not available for the submitted SMILES.")
    with map_col2:
        st.markdown("#### Genotoxicity-Linked Functional Groups")
        if alert_list:
            st.dataframe(pd.DataFrame(genotoxic_alert_rows(st.session_state.results)), use_container_width=True, hide_index=True)
            for idx, alert in enumerate(alert_list, 1):
                severity = "error" if alert.get("method") == "Historical Evidence" else "warning"
                mechanism = alert.get("mechanism") or alert.get("reasoning")
                label = "Experimental evidence" if alert.get("alert") == "Known Mutagen/Carcinogen" else "Structural alert"
                message = f"**{idx}. {alert.get('alert')}** ({label})  \n{mechanism}"
                if severity == "error":
                    st.error(message)
                else:
                    st.warning(message)
                with st.expander(f"Details: {alert.get('alert')}"):
                    st.write(f"**Method**: {alert.get('method', 'N/A')}")
                    st.write("**Interpretation**: This item is treated as genotoxicity-relevant under the current ICH M7/QSAR logic.")
                    st.write(f"**Matched atoms**: {alert.get('matched_atoms', 'N/A')}")
                    st.write(f"**Reference / Evidence**: {alert.get('reference') or alert.get('evidence') or 'N/A'}")
                    st.write(f"**Reasoning**: {alert.get('reasoning', 'N/A')}")
                    if alert.get("expert_comment"):
                        st.write(f"**Expert comment**: {alert.get('expert_comment')}")
        else:
            st.success("No genotoxic structural alert was mapped by the current expert/statistical screen.")
            st.info("Element labels and ion-pair labels describe structure/physicochemical form only. They are not treated as genotoxic alerts unless an ICH M7 structural alert is also mapped.")

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
        st.markdown("<div class='accent-text'>Encyclopedia-Style Structure View</div>", unsafe_allow_html=True)
        if profile:
            s_col1, s_col2 = st.columns([1, 1.25])
            with s_col1:
                show_molecule(profile["mol"], highlighted_atoms, width=520, height=360)
                st.caption("2D skeletal formula with genotoxic-alert regions highlighted only when mapped.")
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
            st.markdown("#### Degradation Structure Gallery")
            gallery_cols = st.columns(2)
            for idx, d in enumerate(st.session_state.degradants):
                d_evidence = d.get("evidence_objects", [])
                d_profile = build_structure_profile(d.get("smiles"))
                d_alert_atoms = collect_evidence_alert_atoms(d_evidence)
                with gallery_cols[idx % 2]:
                    st.markdown(f"**{d.get('name', 'Degradation product')}**")
                    if d_profile:
                        show_molecule(d_profile["mol"], d_alert_atoms, width=420, height=280)
                        st.caption("Pale red halo marks genotoxic alert region when mapped.")
                    else:
                        st.info("Structure not loaded. Add qualified SMILES/InChI to render this degradation product.")
                    st.write(f"**ICH M7**: {d.get('class')} ({d.get('status')})")
                    st.write(f"**Origin**: {d.get('condition')}")
                    if d.get("source_url"):
                        st.markdown(f"[Source]({d['source_url']})")
            st.markdown("---")

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

elif st.session_state.active_screen in {"Genotoxicity QSAR", "Integrated Evidence"}:
    st.image("./hero.png", use_container_width=True)
    st.markdown("<div style='text-align: center; color: #64748b;'>Enter a compound name above to begin QSAR, impurity, and degradation assessment.</div>", unsafe_allow_html=True)

render_consultation_request()
render_legal_notice()

st.markdown("---")
st.caption(f"ToxiGuard-Platform v1.0 | Project: {project_id} | Internal validation checks enabled | Decision support only; not FDA/USP/EP endorsed.")
