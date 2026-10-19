"""
retainiq_common.py
==================
Shared utilities for the RetainIQ research framework.

IMPORTANT DISCLAIMER
--------------------
RetainIQ is a benchmark-validated research prototype built on the IBM HR
Analytics synthetic dataset.  All results are for research/academic purposes
only.  The system must NOT be used to make real employment decisions.  All
probability and cost estimates are model outputs under researcher-defined
assumptions, not guaranteed predictions or industry standards.
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.resolve()
DATA_DIR  = ROOT / "data"
KB_DIR    = ROOT / "kb"
OUT_DIR   = ROOT / "outputs"
FIG_DIR   = ROOT / "figures"
REP_DIR   = ROOT / "reports"

for _d in [OUT_DIR, FIG_DIR, REP_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Reproducibility seed
# ---------------------------------------------------------------------------
RANDOM_STATE: int = 42

# ---------------------------------------------------------------------------
# Dataset column taxonomy
# ---------------------------------------------------------------------------
TARGET_COL = "Attrition"

# Columns that identify rows but carry no predictive signal
IDENTIFIER_COLS = ["EmployeeNumber"]

# Columns expected to be constant in the IBM dataset
EXPECTED_CONSTANT_COLS = ["EmployeeCount", "Over18", "StandardHours"]

# Demographic audit variables – EXCLUDED from model training
AUDIT_COLS = ["Age", "Gender", "MaritalStatus"]

# All excluded from the model feature matrix
EXCLUDED_FROM_MODEL = IDENTIFIER_COLS + EXPECTED_CONSTANT_COLS + AUDIT_COLS + [TARGET_COL]

# ---------------------------------------------------------------------------
# Cross-validation configuration
# ---------------------------------------------------------------------------
CV_FOLDS: int = 5

# ---------------------------------------------------------------------------
# Cost-scenario researcher assumptions (clearly labelled)
# ---------------------------------------------------------------------------
# Scenario 1 – Fixed + salary share
DEFAULT_FIXED_COST   = 25_000.0          # researcher assumption
DEFAULT_SALARY_SHARE = 0.75              # researcher assumption

FIXED_COST_GRID   = [0, 10_000, 25_000, 50_000]
SALARY_SHARE_GRID = [0.50, 0.75, 1.00, 1.25]

# Scenario 2 – Seniority-scaled factors (researcher assumptions)
SENIORITY_FACTORS = {1: 0.60, 2: 0.75, 3: 1.00, 4: 1.25, 5: 1.50}

# ---------------------------------------------------------------------------
# Intervention capacity budgets
# ---------------------------------------------------------------------------
BUDGETS = [10, 25, 50, 100]

# Number of random-baseline repetitions
RANDOM_REPS = 1_000

# ---------------------------------------------------------------------------
# Calibration disclaimer text (append to all output tables)
# ---------------------------------------------------------------------------
DISCLAIMER = (
    "DISCLAIMER: RetainIQ is a benchmark research prototype built on the "
    "IBM HR Analytics synthetic dataset.  Probabilities, costs, and rankings "
    "are model estimates under researcher-defined assumptions.  They are NOT "
    "suitable for real employment decisions and do NOT imply causal "
    "relationships between features and attrition."
)

# ---------------------------------------------------------------------------
# Figure style helpers
# ---------------------------------------------------------------------------
def set_plot_style() -> None:
    """Apply a consistent, publication-friendly matplotlib style."""
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    available = plt.style.available
    for style in ["seaborn-v0_8-whitegrid", "seaborn-whitegrid", "ggplot", "bmh"]:
        if style in available:
            plt.style.use(style)
            break
    mpl.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "font.family": "DejaVu Sans",
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 15,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------
def expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Compute Expected Calibration Error (ECE) using equal-width bins.

    Parameters
    ----------
    y_true : array-like of {0, 1}
    y_prob : array-like of floats in [0, 1]
    n_bins : int

    Returns
    -------
    ece : float
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    bins   = np.linspace(0.0, 1.0, n_bins + 1)
    ece    = 0.0
    n      = len(y_true)
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (y_prob >= lo) & (y_prob < hi)
        if mask.sum() == 0:
            continue
        bin_acc  = y_true[mask].mean()
        bin_conf = y_prob[mask].mean()
        ece += (mask.sum() / n) * abs(bin_acc - bin_conf)
    return float(ece)


# ---------------------------------------------------------------------------
# Leakage-safe OOF probability generation with fold-safe calibration
# ---------------------------------------------------------------------------
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold


def generate_oof_predictions(
    estimator,
    X: pd.DataFrame,
    y: pd.Series,
    calibrate: bool = True,
    calibration_method: str = "sigmoid",
    cv_folds: int = CV_FOLDS,
    random_state: int = RANDOM_STATE,
) -> tuple[np.ndarray, np.ndarray, list]:
    """
    Generate leakage-safe out-of-fold (OOF) predictions.

    Calibration is performed *inside* each outer training fold using an
    additional inner StratifiedKFold, so the validation employee never
    influences either the base model or the calibration fitting.

    Parameters
    ----------
    estimator   : sklearn-compatible estimator (unfitted)
    X           : feature matrix (full dataset)
    y           : target vector (full dataset)
    calibrate   : whether to apply fold-safe Platt / isotonic calibration
    calibration_method : 'sigmoid' (Platt) or 'isotonic'
    cv_folds    : number of outer folds
    random_state: RNG seed

    Returns
    -------
    oof_probs   : np.ndarray of shape (n_samples,) – calibrated probabilities
    oof_labels  : np.ndarray of shape (n_samples,) – fold-membership indices
    fitted_models : list of fitted (calibrated) estimators, one per fold
    """
    import copy
    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    oof_probs  = np.full(len(y), np.nan)
    oof_labels = np.full(len(y), -1, dtype=int)
    fitted_models = []

    X_arr = X.values if hasattr(X, "values") else np.asarray(X)
    y_arr = np.asarray(y)

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X_arr, y_arr)):
        X_train, X_val = X_arr[train_idx], X_arr[val_idx]
        y_train        = y_arr[train_idx]

        base = copy.deepcopy(estimator)

        if calibrate:
            # Inner CV for calibration – uses only training fold data
            cal_cv = StratifiedKFold(
                n_splits=3, shuffle=True, random_state=random_state
            )
            cal_model = CalibratedClassifierCV(
                base,
                method=calibration_method,
                cv=cal_cv,
            )
            cal_model.fit(X_train, y_train)
            probs = cal_model.predict_proba(X_val)[:, 1]
            fitted_models.append(cal_model)
        else:
            base.fit(X_train, y_train)
            probs = base.predict_proba(X_val)[:, 1]
            fitted_models.append(base)

        oof_probs[val_idx]  = probs
        oof_labels[val_idx] = fold_idx

    return oof_probs, oof_labels, fitted_models


# ---------------------------------------------------------------------------
# Annual salary helper
# ---------------------------------------------------------------------------
def annual_salary(monthly_income: pd.Series) -> pd.Series:
    """Return AnnualSalary = MonthlyIncome x 12."""
    return monthly_income * 12


def replacement_cost_fixed_salary(
    monthly_income: pd.Series,
    fixed_cost: float = DEFAULT_FIXED_COST,
    salary_share: float = DEFAULT_SALARY_SHARE,
) -> pd.Series:
    """
    Scenario 1 replacement cost.

    ReplacementCost = FixedCost + SalaryShare x AnnualSalary

    RESEARCHER ASSUMPTION - not an industry standard.
    """
    return fixed_cost + salary_share * annual_salary(monthly_income)


def replacement_cost_seniority(
    monthly_income: pd.Series,
    job_level: pd.Series,
    factors: dict | None = None,
) -> pd.Series:
    """
    Scenario 2 replacement cost.

    ReplacementCost = AnnualSalary x SeniorityFactor[JobLevel]

    RESEARCHER ASSUMPTION - not an industry standard.
    """
    if factors is None:
        factors = SENIORITY_FACTORS
    ann = annual_salary(monthly_income)
    sen = job_level.map(factors).fillna(1.0)
    return ann * sen


# ---------------------------------------------------------------------------
# Age-band helper
# ---------------------------------------------------------------------------
def age_band(age_series: pd.Series) -> pd.Series:
    """Bin Age into <30 / 30-39 / 40-49 / 50+ labels."""
    return pd.cut(
        age_series,
        bins=[0, 29, 39, 49, 200],
        labels=["<30", "30-39", "40-49", "50+"],
        right=True,
    )


# ---------------------------------------------------------------------------
# Leakage checklist writer
# ---------------------------------------------------------------------------
def write_leakage_checklist(results: dict) -> None:
    """
    Write outputs/leakage_checklist.md.

    Parameters
    ----------
    results : dict mapping checklist item -> True (passed) / False (failed)
    """
    lines = [
        "# RetainIQ - Data Leakage Checklist\n",
        "Generated automatically. Review each item carefully.\n\n",
        "| Item | Status |\n",
        "|------|--------|\n",
    ]
    for item, passed in results.items():
        icon = "PASS" if passed else "FAIL"
        lines.append(f"| {item} | {icon} |\n")

    path = OUT_DIR / "leakage_checklist.md"
    path.write_text("".join(lines), encoding="utf-8")
    print(f"[leakage] checklist written -> {path}")


# ---------------------------------------------------------------------------
# Metadata saver
# ---------------------------------------------------------------------------
def save_metadata(meta: dict, path: Path | None = None) -> None:
    if path is None:
        path = OUT_DIR / "final_model_metadata.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, default=str)
    print(f"[meta] metadata written -> {path}")
