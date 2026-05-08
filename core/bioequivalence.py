import csv
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

import numpy as np
import pandas as pd


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
