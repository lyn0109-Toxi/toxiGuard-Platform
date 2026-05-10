import csv
import io
import math
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser

import numpy as np
import pandas as pd
import requests


DEFAULT_DISSOLUTION_PROFILE = pd.DataFrame(
    [
        {"Time (min)": 5, "Reference Mean (%)": 32.0, "Reference SD": 4.5, "Reference n": 12, "Test Mean (%)": 30.0, "Test SD": 5.0, "Test n": 12},
        {"Time (min)": 10, "Reference Mean (%)": 51.0, "Reference SD": 5.2, "Reference n": 12, "Test Mean (%)": 49.0, "Test SD": 5.6, "Test n": 12},
        {"Time (min)": 15, "Reference Mean (%)": 68.0, "Reference SD": 6.0, "Reference n": 12, "Test Mean (%)": 66.0, "Test SD": 6.4, "Test n": 12},
        {"Time (min)": 30, "Reference Mean (%)": 86.0, "Reference SD": 5.5, "Reference n": 12, "Test Mean (%)": 84.0, "Test SD": 6.0, "Test n": 12},
        {"Time (min)": 45, "Reference Mean (%)": 93.0, "Reference SD": 4.0, "Reference n": 12, "Test Mean (%)": 91.0, "Test SD": 4.7, "Test n": 12},
    ]
)
FDA_BE_GUIDANCE_SOURCES = [
    {
        "Guidance": "M13A Bioequivalence for Immediate-Release Solid Oral Dosage Forms",
        "Status": "Final",
        "Date": "October 2024",
        "Use in platform": "Primary BE study framework for orally administered immediate-release solid oral dosage forms.",
        "URL": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/m13a-bioequivalence-immediate-release-solid-oral-dosage-forms",
    },
    {
        "Guidance": "Dissolution Testing of Immediate Release Solid Oral Dosage Forms",
        "Status": "Final",
        "Date": "August 1997",
        "Use in platform": "Dissolution profile comparison, f2 strategy, and dissolution-based biowaiver support.",
        "URL": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/dissolution-testing-immediate-release-solid-oral-dosage-forms",
    },
    {
        "Guidance": "FDA Dissolution Methods Database",
        "Status": "FDA database",
        "Date": "Quarterly update",
        "Use in platform": "Product-specific method search when no USP dissolution method is available.",
        "URL": "https://www.fda.gov/drugs/drug-approvals-and-databases/dissolution-methods-database",
    },
    {
        "Guidance": "Dissolution Testing and Acceptance Criteria for IR Drug Products Containing High Solubility Drug Substances",
        "Status": "Final",
        "Date": "August 2018",
        "Use in platform": "High-solubility IR product dissolution acceptance strategy.",
        "URL": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/dissolution-testing-and-acceptance-criteria-immediate-release-solid-oral-dosage-form-drug-products",
    },
]

ORANGE_BOOK_ZIP_URL = "https://www.fda.gov/media/76860/download?attachment="
ORANGE_BOOK_SEARCH_URL = "https://www.accessdata.fda.gov/scripts/cder/ob/index.cfm"
FDA_DISSOLUTION_ALL_URL = "https://www.accessdata.fda.gov/scripts/cder/dissolution/dsp_getallData.cfm"
FDA_DISSOLUTION_SEARCH_URL = "https://www.accessdata.fda.gov/scripts/cder/dissolution/index.cfm"
OPENFDA_DRUGSFDA_URL = "https://api.fda.gov/drug/drugsfda.json"
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

CURATED_REFERENCE_PRODUCTS = {
    "vivitrol": {
        "Ingredient": "NALTREXONE",
        "Trade name": "VIVITROL",
        "Applicant": "ALKERMES",
        "Strength": "380 mg/vial",
        "Dosage form / route": "EXTENDED-RELEASE INJECTABLE SUSPENSION; INTRAMUSCULAR",
        "Application": "NDA021897",
        "Product no.": "",
        "TE code": "",
        "RLD": "Yes",
        "RS": "Yes",
        "Approval date": "",
        "Marketing status": "Prescription",
        "Source": "Curated FDA label / Orange Book context",
        "Dose regimen": "380 mg by deep intramuscular gluteal injection every 4 weeks or once monthly",
        "BE strategy override": "Long-acting injectable / product-specific review",
        "Dissolution f2 applicable": "No",
        "Rationale": "Vivitrol is naltrexone for extended-release injectable suspension, not an immediate-release oral solid dosage form.",
        "Source URL": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2022/021897s057lbl.pdf",
    }
}


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            value = " ".join(" ".join(self._cell).split())
            self._row.append(value)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(self._row)
            self._row = None


def _contains_query(value, query):
    return query.lower() in str(value or "").lower()


def _curated_reference_rows(query):
    query_norm = str(query or "").strip().lower()
    if not query_norm:
        return []
    rows = []
    for key, row in CURATED_REFERENCE_PRODUCTS.items():
        if (
            query_norm in key
            or query_norm in row.get("Trade name", "").lower()
            or query_norm in row.get("Ingredient", "").lower()
        ):
            rows.append(dict(row))
    return rows


def _read_orange_book_products(timeout=20):
    response = requests.get(ORANGE_BOOK_ZIP_URL, timeout=timeout)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        product_file = next(name for name in archive.namelist() if name.lower().endswith("products.txt"))
        with archive.open(product_file) as handle:
            return pd.read_csv(handle, sep="~", dtype=str).fillna("")


def search_orange_book_reference(query, limit=12):
    if not query or len(query.strip()) < 3:
        return {"rows": [], "error": "Enter at least three characters.", "source_url": ORANGE_BOOK_SEARCH_URL}
    try:
        products = _read_orange_book_products()
        mask = products.apply(
            lambda row: _contains_query(row.get("Ingredient"), query) or _contains_query(row.get("Trade_Name"), query),
            axis=1,
        )
        matches = products.loc[mask].copy()
        if matches.empty:
            return {"rows": [], "error": "", "source_url": ORANGE_BOOK_SEARCH_URL}
        priority = matches.get("RLD", "").eq("Yes").astype(int) + matches.get("RS", "").eq("Yes").astype(int)
        matches = matches.assign(_priority=priority).sort_values(["_priority", "Trade_Name"], ascending=[False, True])
        rows = []
        for _, item in matches.head(limit).iterrows():
            rows.append(
                {
                    "Ingredient": item.get("Ingredient", ""),
                    "Trade name": item.get("Trade_Name", ""),
                    "Applicant": item.get("Applicant_Full_Name", item.get("Applicant", "")),
                    "Strength": item.get("Strength", ""),
                    "Dosage form / route": item.get("DF;Route", ""),
                    "Application": f"{item.get('Appl_Type', '')}{item.get('Appl_No', '')}",
                    "Product no.": item.get("Product_No", ""),
                    "TE code": item.get("TE_Code", ""),
                    "RLD": item.get("RLD", ""),
                    "RS": item.get("RS", ""),
                    "Approval date": item.get("Approval_Date", ""),
                    "Marketing status": item.get("Type", ""),
                }
            )
        return {"rows": rows, "error": "", "source_url": ORANGE_BOOK_SEARCH_URL}
    except Exception as exc:
        return {"rows": [], "error": _friendly_fda_error(exc, "Orange Book"), "source_url": ORANGE_BOOK_SEARCH_URL}



def _first_list_value(value):
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def _join_list(value):
    if isinstance(value, list):
        return "; ".join([str(item) for item in value if item])
    return value or ""


def _friendly_fda_error(exc, source_name):
    message = str(exc)
    if "apology_objects" in message or "abuse-detection" in message:
        return f"{source_name} direct lookup was blocked by FDA access protection. openFDA fallback will be used when available."
    return f"{source_name} lookup unavailable: {exc}"


def _openfda_search_terms(query):
    escaped = str(query).replace('"', '')
    return [
        f'openfda.generic_name:"{escaped}"',
        f'openfda.brand_name:"{escaped}"',
        f'products.active_ingredients.name:"{escaped}"',
        escaped,
    ]


def search_openfda_drug_products(query, limit=12):
    if not query or len(query.strip()) < 3:
        return {"rows": [], "error": "Enter at least three characters.", "source_url": "https://open.fda.gov/apis/drug/drugsfda/"}
    errors = []
    for term in _openfda_search_terms(query.strip()):
        try:
            params = {"search": term, "limit": 100}
            response = requests.get(OPENFDA_DRUGSFDA_URL, params=params, timeout=20)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            data = response.json()
            rows = []
            for app in data.get("results", []):
                openfda = app.get("openfda") or {}
                sponsor = app.get("sponsor_name") or _first_list_value(openfda.get("manufacturer_name"))
                application = app.get("application_number", "")
                for product in app.get("products", []) or []:
                    active_ingredients = product.get("active_ingredients") or []
                    strengths = "; ".join(
                        [f"{item.get('name', '')} {item.get('strength', '')}".strip() for item in active_ingredients]
                    )
                    rows.append(
                        {
                            "Ingredient": "; ".join([item.get("name", "") for item in active_ingredients]) or _first_list_value(openfda.get("generic_name")),
                            "Trade name": product.get("brand_name") or _first_list_value(openfda.get("brand_name")),
                            "Applicant": sponsor,
                            "Strength": strengths,
                            "Dosage form / route": "; ".join([product.get("dosage_form", ""), product.get("route", "")]).strip("; "),
                            "Application": application,
                            "Product no.": product.get("product_number", ""),
                            "TE code": product.get("te_code", ""),
                            "RLD": product.get("reference_drug", ""),
                            "RS": product.get("reference_standard", ""),
                            "Approval date": product.get("approval_date", ""),
                            "Marketing status": product.get("marketing_status", ""),
                            "Source": "openFDA Drugs@FDA",
                        }
                    )
            if rows:
                query_norm = query.strip().upper()
                def priority(row):
                    application = str(row.get("Application", "")).upper()
                    rld = str(row.get("RLD", "")).lower()
                    rs = str(row.get("RS", "")).lower()
                    te = str(row.get("TE code", "")).strip()
                    ingredient = str(row.get("Ingredient", "")).upper()
                    is_exact_single = ingredient == query_norm
                    is_single = ";" not in ingredient and "/" not in ingredient
                    return (
                        1 if is_exact_single else 0,
                        1 if is_single else 0,
                        1 if application.startswith("NDA") else 0,
                        1 if rld in {"yes", "true", "1"} else 0,
                        1 if rs in {"yes", "true", "1"} else 0,
                        0 if te else 1,
                    )
                rows = sorted(rows, key=priority, reverse=True)
                return {"rows": rows[:limit], "error": "", "source_url": "https://open.fda.gov/apis/drug/drugsfda/"}
        except Exception as exc:
            errors.append(str(exc))
    return {
        "rows": [],
        "error": "openFDA Drugs@FDA lookup unavailable" + (f": {errors[-1]}" if errors else "."),
        "source_url": "https://open.fda.gov/apis/drug/drugsfda/",
    }


def search_openfda_label_products(query, limit=12):
    if not query or len(query.strip()) < 3:
        return {"rows": [], "error": "Enter at least three characters.", "source_url": "https://open.fda.gov/apis/drug/label/"}
    rows = []
    errors = []
    for term in _openfda_search_terms(query.strip()):
        try:
            response = requests.get(
                OPENFDA_LABEL_URL,
                params={"search": term, "limit": min(max(limit, 1), 100)},
                timeout=20,
            )
            if response.status_code == 404:
                continue
            response.raise_for_status()
            for item in response.json().get("results", []):
                openfda = item.get("openfda") or {}
                rows.append(
                    {
                        "Ingredient": _join_list(openfda.get("substance_name")) or _join_list(openfda.get("generic_name")),
                        "Trade name": _join_list(openfda.get("brand_name")),
                        "Applicant": _join_list(openfda.get("manufacturer_name")),
                        "Strength": _join_list(item.get("active_ingredient")),
                        "Dosage form / route": "; ".join(
                            [value for value in [_join_list(openfda.get("dosage_form")), _join_list(openfda.get("route"))] if value]
                        ),
                        "Application": _join_list(openfda.get("application_number")),
                        "Product no.": _join_list(openfda.get("product_ndc")),
                        "TE code": "",
                        "RLD": "Not specified",
                        "RS": "Not specified",
                        "Approval date": "",
                        "Marketing status": _join_list(openfda.get("product_type")),
                        "Source": "openFDA Drug Label",
                    }
                )
            if rows:
                return {"rows": rows[:limit], "error": "", "source_url": "https://open.fda.gov/apis/drug/label/"}
        except Exception as exc:
            errors.append(str(exc))
    return {
        "rows": [],
        "error": "openFDA Drug Label lookup unavailable" + (f": {errors[-1]}" if errors else "."),
        "source_url": "https://open.fda.gov/apis/drug/label/",
    }


def _dissolution_rows_from_html(html):
    parser = _TableParser()
    parser.feed(html)
    rows = []
    for row in parser.rows:
        if len(row) >= 8 and row[0].lower() != "drug name":
            rows.append(
                {
                    "Drug name": row[0],
                    "Dosage form": row[1],
                    "USP apparatus": row[2],
                    "Speed (RPM)": row[3],
                    "Medium": row[4],
                    "Volume (mL)": row[5],
                    "Recommended sampling times": row[6],
                    "Date updated": row[7],
                }
            )
    return rows


def search_fda_dissolution_methods(query, limit=12):
    if not query or len(query.strip()) < 3:
        return {"rows": [], "error": "Enter at least three characters.", "source_url": FDA_DISSOLUTION_SEARCH_URL}
    try:
        response = requests.get(FDA_DISSOLUTION_ALL_URL, timeout=20)
        response.raise_for_status()
        rows = _dissolution_rows_from_html(response.text)
        matches = [row for row in rows if _contains_query(row.get("Drug name"), query)]
        return {"rows": matches[:limit], "error": "", "source_url": FDA_DISSOLUTION_SEARCH_URL}
    except Exception as exc:
        return {"rows": [], "error": _friendly_fda_error(exc, "FDA Dissolution Methods"), "source_url": FDA_DISSOLUTION_SEARCH_URL}


def sampling_times_to_profile(method_row, default_n=12):
    time_text = method_row.get("Recommended sampling times", "") if method_row else ""
    numbers = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", time_text)]
    if "hour" in time_text.lower():
        numbers = [value * 60 for value in numbers]
    times = sorted({int(value) if float(value).is_integer() else value for value in numbers if value > 0})
    if not times:
        return DEFAULT_DISSOLUTION_PROFILE.copy()
    return pd.DataFrame(
        [
            {
                "Time (min)": time,
                "Reference Mean (%)": 0.0,
                "Reference SD": 0.0,
                "Reference n": default_n,
                "Test Mean (%)": 0.0,
                "Test SD": 0.0,
                "Test n": default_n,
            }
            for time in times
        ]
    )


def lookup_reference_product_package(query):
    curated_rows = _curated_reference_rows(query)
    orange_book = search_orange_book_reference(query)
    drug_products = search_openfda_drug_products(query)
    label_products = search_openfda_label_products(query) if not drug_products.get("rows") else {"rows": [], "error": "", "source_url": "https://open.fda.gov/apis/drug/label/"}
    if not orange_book.get("rows") and drug_products.get("rows"):
        orange_book = {**orange_book, "rows": drug_products["rows"], "error": ""}
    if not orange_book.get("rows") and label_products.get("rows"):
        orange_book = {**orange_book, "rows": label_products["rows"], "error": ""}
    if curated_rows:
        existing = orange_book.get("rows") or []
        seen = {str(row.get("Trade name", "")).lower() + "|" + str(row.get("Application", "")).lower() for row in existing}
        merged = []
        for row in curated_rows:
            key = str(row.get("Trade name", "")).lower() + "|" + str(row.get("Application", "")).lower()
            if key not in seen:
                merged.append(row)
        orange_book = {**orange_book, "rows": merged + existing, "error": ""}
    dissolution = search_fda_dissolution_methods(query)
    return {
        "query": query,
        "orange_book": orange_book,
        "drug_products": drug_products,
        "label_products": label_products,
        "dissolution": dissolution,
        "notes": [
            "Orange Book identifies approved drug products, RLD, RS, TE code, strength, and application information.",
            "If Orange Book download is unavailable, openFDA Drugs@FDA is used to display product name, sponsor/company, strength, dosage form, route, and application details.",
            "If Drugs@FDA does not return a match, openFDA Drug Label is used as a broader fallback for marketed product name, manufacturer, route, and active ingredient details.",
            "FDA Dissolution Methods Database provides recommended method conditions and sampling times.",
            "Actual reference/test dissolution percentages are generally not published as a structured FDA dataset; enter laboratory or internal profile data for f2 calculation.",
        ],
    }


def classify_be_dosage_form(dosage_form):
    label = (dosage_form or "").lower()
    if "injectable" in label and any(term in label for term in ["extended", "long-acting", "depot", "suspension"]):
        return "Long-acting injectable / extended release"
    if any(term in label for term in ["modified", "sustained", "extended", "controlled", "delayed", "depot"]):
        return "Modified / sustained / extended release"
    if "immediate" in label or "tablet" in label or "capsule" in label:
        return "Immediate release"
    if any(term in label for term in ["solution", "injectable"]):
        return "Solution / non-oral-solid"
    return "Other / requires product-specific review"


def be_strategy_by_dosage_form(dosage_form):
    release_type = classify_be_dosage_form(dosage_form)
    if release_type == "Long-acting injectable / extended release":
        return {
            "Release type": release_type,
            "Primary BE focus": "Product-specific long-acting injectable strategy; release kinetics, formulation sameness, PK exposure, injection-site tolerability, and device/administration factors require explicit review.",
            "Dissolution role": "Oral IR f2 dissolution logic is not the primary BE basis. Use in vitro release or product-specific methods only when justified for the dosage form.",
            "Recommended study design": "Confirm FDA product-specific guidance. Strategy may require comparative PK with extended sampling, formulation/device comparability, in vitro release, residual solvent/polymer controls, and injection-site safety review.",
            "Key data needs": "RLD/RS, strength per vial, release-controlling excipients or microsphere/polymer attributes, route/site of administration, PK sampling duration, in vitro release method, CMC sameness, device/kit components.",
            "Risk note": "Do not apply immediate-release oral f2 criteria to long-acting injectable products. Treat as product-specific BE and CMC strategy review.",
        }
    if release_type == "Immediate release":
        return {
            "Release type": release_type,
            "Primary BE focus": "Single-dose fasting BE; fed BE when product-specific guidance or food-effect concern applies.",
            "Dissolution role": "Comparative dissolution and f2 can support sameness/biowaiver strategy when method and variability are acceptable.",
            "Recommended study design": "Usually randomized single-dose 2-way crossover; analyte and fed/fasted design should follow product-specific guidance.",
            "Key data needs": "RLD/RS, same strength or strength bridge, product-specific dissolution method, pH media profile, f2, assay method, PK endpoint plan.",
            "Risk note": "IR products may use f2 as a supportive dissolution similarity tool, but f2 alone does not replace required in vivo BE unless a waiver pathway is justified.",
        }
    if release_type == "Modified / sustained / extended release":
        return {
            "Release type": release_type,
            "Primary BE focus": "Both fasting and fed BE are commonly important; dose dumping and alcohol/food effect risks require explicit review.",
            "Dissolution role": "Multi-time-point dissolution profile is critical, but f2 is supportive rather than sufficient for release-mechanism equivalence.",
            "Recommended study design": "Product-specific design may include fasting, fed, multiple-dose steady-state, partial AUC, or replicate design for high variability.",
            "Key data needs": "Release mechanism, matrix/coating comparison, dose dumping risk, alcohol-induced dose dumping screen, multiple strengths, partial AUC, fed/fasted PK plan.",
            "Risk note": "MR/ER products have higher BE risk. Confirm FDA product-specific guidance before relying on f2 or biowaiver arguments.",
        }
    if release_type == "Solution / non-oral-solid":
        return {
            "Release type": release_type,
            "Primary BE focus": "Dosage-form-specific waiver or clinical/PK bridge depends on route, formulation sameness, and product-specific guidance.",
            "Dissolution role": "Dissolution f2 may be not applicable or secondary depending on route and formulation.",
            "Recommended study design": "Review route-specific FDA guidance and formulation sameness before selecting BE design.",
            "Key data needs": "Route, excipients, concentration, osmolality/pH where relevant, formulation sameness, product-specific FDA guidance.",
            "Risk note": "Do not apply oral solid f2 logic directly to non-oral-solid products.",
        }
    return {
        "Release type": release_type,
        "Primary BE focus": "Requires product-specific review.",
        "Dissolution role": "Do not assume f2 applies without dosage-form confirmation.",
        "Recommended study design": "Check FDA product-specific guidance and dosage-form-specific BE recommendations.",
        "Key data needs": "RLD/RS, dosage form, route, strength, formulation design, product-specific guidance.",
        "Risk note": "Insufficient dosage-form information for default BE strategy.",
    }


def infer_reference_product_context(reference_row=None, selected_dosage_form="", reference_query=""):
    row = reference_row or {}
    dosage_route = row.get("Dosage form / route", "")
    product_name = row.get("Trade name", "") or reference_query or ""
    combined = " ".join(
        [
            product_name,
            row.get("Ingredient", ""),
            row.get("Strength", ""),
            dosage_route,
            row.get("BE strategy override", ""),
            row.get("Rationale", ""),
        ]
    ).lower()
    effective_dosage_form = dosage_route or selected_dosage_form or "Not specified"
    effective_release_type = classify_be_dosage_form(effective_dosage_form)
    is_vivitrol_like = "vivitrol" in combined or ("naltrexone" in combined and "inject" in combined and "extended" in combined)
    is_long_acting_injectable = is_vivitrol_like or (
        "inject" in combined and any(term in combined for term in ["extended", "long-acting", "depot", "microsphere", "suspension"])
    )
    if is_long_acting_injectable:
        effective_release_type = "Long-acting injectable / extended release"
    selected_release_type = classify_be_dosage_form(selected_dosage_form)
    mismatch = (
        selected_dosage_form
        and effective_release_type != selected_release_type
        and selected_release_type == "Immediate release"
        and effective_release_type != "Immediate release"
    )
    f2_applicable = effective_release_type == "Immediate release"
    if str(row.get("Dissolution f2 applicable", "")).lower() == "no":
        f2_applicable = False
    return {
        "product_name": product_name or "Reference product",
        "ingredient": row.get("Ingredient", ""),
        "strength": row.get("Strength", ""),
        "dose_regimen": row.get("Dose regimen", ""),
        "dosage_form_route": effective_dosage_form,
        "selected_dosage_form": selected_dosage_form,
        "effective_release_type": effective_release_type,
        "selected_release_type": selected_release_type,
        "dosage_form_mismatch": bool(mismatch),
        "f2_applicable": bool(f2_applicable),
        "strategy": be_strategy_by_dosage_form(effective_release_type),
        "rationale": row.get("Rationale", ""),
        "source": row.get("Source", ""),
        "source_url": row.get("Source URL", ""),
    }


@dataclass
class BioequivalenceResult:
    f2: float
    conclusion: str
    r_backend_used: bool
    ci_low: float | None = None
    ci_high: float | None = None
    bootstrap_median: float | None = None
    bootstrap_p05: float | None = None
    bootstrap_p95: float | None = None
    probability_f2_ge_50: float | None = None
    bootstrap_runs: int = 0
    cv_flag: str = "Not assessed"
    method_note: str = ""
    fda_decision: str = ""
    fda_risk: str = ""
    fda_next_action: str = ""


def _clean_profile(profile_df):
    required = [
        "Time (min)",
        "Reference Mean (%)",
        "Reference SD",
        "Reference n",
        "Test Mean (%)",
        "Test SD",
        "Test n",
    ]
    df = profile_df.copy()
    for column in required:
        if column not in df.columns:
            df[column] = np.nan
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["Time (min)", "Reference Mean (%)", "Test Mean (%)"])
    df = df.sort_values("Time (min)").reset_index(drop=True)
    return df[required]


def _f2_from_means(ref_values, test_values):
    ref = np.asarray(ref_values, dtype=float)
    test = np.asarray(test_values, dtype=float)
    if len(ref) < 3:
        raise ValueError("At least three dissolution time points are required for f2.")
    mean_square_diff = np.mean((ref - test) ** 2)
    return float(50 * math.log10(100 / math.sqrt(1 + mean_square_diff)))


def _cv_flag(df):
    flags = []
    for _, row in df.iterrows():
        time_point = row["Time (min)"]
        for arm in ("Reference", "Test"):
            mean = row[f"{arm} Mean (%)"]
            sd = row[f"{arm} SD"]
            if mean and mean > 0 and not pd.isna(sd):
                cv = sd / mean * 100
                threshold = 20 if time_point <= 15 else 10
                if cv > threshold:
                    flags.append(f"{arm} CV {cv:.1f}% at {time_point:g} min")
    return "Acceptable" if not flags else "; ".join(flags)


def _bootstrap_stats(values):
    arr = np.asarray(values, dtype=float)
    return {
        "ci_low": float(np.percentile(arr, 2.5)),
        "ci_high": float(np.percentile(arr, 97.5)),
        "median": float(np.percentile(arr, 50)),
        "p05": float(np.percentile(arr, 5)),
        "p95": float(np.percentile(arr, 95)),
        "probability_f2_ge_50": float(np.mean(arr >= 50) * 100),
    }


def _python_bootstrap_stats(df, bootstrap_runs=1000, seed=1729):
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(max(int(bootstrap_runs), 1)):
        ref_draw = []
        test_draw = []
        for _, row in df.iterrows():
            ref_n = max(int(row.get("Reference n", 12) or 12), 1)
            test_n = max(int(row.get("Test n", 12) or 12), 1)
            ref_sd = max(float(row.get("Reference SD", 0) or 0), 0)
            test_sd = max(float(row.get("Test SD", 0) or 0), 0)
            ref_draw.append(rng.normal(row["Reference Mean (%)"], ref_sd, ref_n).mean())
            test_draw.append(rng.normal(row["Test Mean (%)"], test_sd, test_n).mean())
        values.append(_f2_from_means(ref_draw, test_draw))
    return _bootstrap_stats(values)


def _run_r_backend(df, bootstrap_runs=1000, seed=1729):
    if not shutil.which("Rscript"):
        return None

    r_code = """
args <- commandArgs(trailingOnly = TRUE)
input_csv <- args[1]
output_csv <- args[2]
n_boot <- as.integer(args[3])
seed <- as.integer(args[4])
d <- read.csv(input_csv, check.names = FALSE)
f2_calc <- function(ref, test) {
  50 * log10(100 / sqrt(1 + mean((ref - test)^2)))
}
set.seed(seed)
f2 <- f2_calc(d[["Reference Mean (%)"]], d[["Test Mean (%)"]])
boot <- replicate(n_boot, {
  ref_draw <- mapply(function(mu, sd, n) mean(rnorm(max(as.integer(n), 1), mu, max(sd, 0))),
                     d[["Reference Mean (%)"]], d[["Reference SD"]], d[["Reference n"]])
  test_draw <- mapply(function(mu, sd, n) mean(rnorm(max(as.integer(n), 1), mu, max(sd, 0))),
                      d[["Test Mean (%)"]], d[["Test SD"]], d[["Test n"]])
  f2_calc(ref_draw, test_draw)
})
out <- data.frame(
  f2 = f2,
  ci_low = unname(quantile(boot, 0.025)),
  ci_high = unname(quantile(boot, 0.975)),
  median = unname(quantile(boot, 0.5)),
  p05 = unname(quantile(boot, 0.05)),
  p95 = unname(quantile(boot, 0.95)),
  probability_f2_ge_50 = mean(boot >= 50) * 100
)
write.csv(out, output_csv, row.names = FALSE)
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "be_profile.csv")
        output_path = os.path.join(tmpdir, "be_result.csv")
        script_path = os.path.join(tmpdir, "f2_bootstrap.R")
        df.to_csv(input_path, index=False, quoting=csv.QUOTE_MINIMAL)
        with open(script_path, "w", encoding="utf-8") as handle:
            handle.write(r_code)
        subprocess.run(
            ["Rscript", script_path, input_path, output_path, str(int(bootstrap_runs)), str(int(seed))],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        result = pd.read_csv(output_path).iloc[0]
        return {
            "f2": float(result["f2"]),
            "ci_low": float(result["ci_low"]),
            "ci_high": float(result["ci_high"]),
            "median": float(result["median"]),
            "p05": float(result["p05"]),
            "p95": float(result["p95"]),
            "probability_f2_ge_50": float(result["probability_f2_ge_50"]),
        }


def calculate_f2(profile_df, bootstrap_runs=1000, seed=1729):
    df = _clean_profile(profile_df)
    f2 = _f2_from_means(df["Reference Mean (%)"], df["Test Mean (%)"])
    cv_flag = _cv_flag(df)
    conclusion = "Similar dissolution profile" if f2 >= 50 else "Not similar by f2 criterion"
    fda_decision = (
        "Supports FDA-style comparative dissolution similarity rationale"
        if f2 >= 50
        else "Does not support FDA-style f2 similarity rationale"
    )
    fda_risk = "Low" if f2 >= 50 and cv_flag == "Acceptable" else "Review needed"
    fda_next_action = (
        "Check product-specific FDA dissolution method or USP method, then align media, apparatus, rpm, and sampling time points before submission."
        if f2 >= 50
        else "Review formulation/process variables and consider additional dissolution method development or in vivo BE strategy."
    )

    try:
        r_result = _run_r_backend(df, bootstrap_runs=bootstrap_runs, seed=seed)
    except Exception:
        r_result = None

    if r_result:
        f2 = r_result["f2"]
        return BioequivalenceResult(
            f2=round(f2, 2),
            ci_low=round(r_result["ci_low"], 2),
            ci_high=round(r_result["ci_high"], 2),
            bootstrap_median=round(r_result["median"], 2),
            bootstrap_p05=round(r_result["p05"], 2),
            bootstrap_p95=round(r_result["p95"], 2),
            probability_f2_ge_50=round(r_result["probability_f2_ge_50"], 1),
            bootstrap_runs=int(bootstrap_runs),
            conclusion=conclusion,
            cv_flag=cv_flag,
            r_backend_used=True,
            method_note="f2, bootstrap percentiles, and f2 >= 50 probability calculated with R.",
            fda_decision=fda_decision,
            fda_risk=fda_risk,
            fda_next_action=fda_next_action,
        )

    py_stats = _python_bootstrap_stats(df, bootstrap_runs=bootstrap_runs, seed=seed)
    return BioequivalenceResult(
        f2=round(f2, 2),
        ci_low=round(py_stats["ci_low"], 2),
        ci_high=round(py_stats["ci_high"], 2),
        bootstrap_median=round(py_stats["median"], 2),
        bootstrap_p05=round(py_stats["p05"], 2),
        bootstrap_p95=round(py_stats["p95"], 2),
        probability_f2_ge_50=round(py_stats["probability_f2_ge_50"], 1),
        bootstrap_runs=int(bootstrap_runs),
        conclusion=conclusion,
        cv_flag=cv_flag,
        r_backend_used=False,
        method_note="Rscript was not available; Python fallback used the same f2 formula and bootstrap approach.",
        fda_decision=fda_decision,
        fda_risk=fda_risk,
        fda_next_action=fda_next_action,
    )


def dissolution_profile_summary(profile_df):
    df = _clean_profile(profile_df)
    df["Difference (%)"] = df["Test Mean (%)"] - df["Reference Mean (%)"]
    df["Reference CV (%)"] = np.where(
        df["Reference Mean (%)"] > 0,
        df["Reference SD"] / df["Reference Mean (%)"] * 100,
        np.nan,
    )
    df["Test CV (%)"] = np.where(
        df["Test Mean (%)"] > 0,
        df["Test SD"] / df["Test Mean (%)"] * 100,
        np.nan,
    )
    return df.round(2)
