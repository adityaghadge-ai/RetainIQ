"""
retainiq_01_baseline.py
=======================
PHASE 1  – Data Quality Inspection
PHASE 2  – Baseline Feature Set
PHASE 3  – Feature Engineering (Ablation A vs B)
PHASE 4  – Model Training (LR / RF / XGB)
PHASE 5  – OOF Evaluation
PHASE 6  – Feature Ablation Comparison
PHASE 7  – Probability Calibration Evaluation
PHASE 8  – Select Final Model
PHASE 9  – Save Artefacts

DISCLAIMER
----------
RetainIQ is a benchmark research prototype built on the IBM HR Analytics
SYNTHETIC dataset.  Results are for academic research only.  This system
must NOT be used to make real employment decisions.

Run:
    python retainiq_01_baseline.py
"""

from __future__ import annotations

import sys
import warnings
import json
import os
os.environ["OMP_NUM_THREADS"] = "4"  # prevent XGBoost threading issues on Windows
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer

# ---------------------------------------------------------------------------
# Handle XGBoost availability
# ---------------------------------------------------------------------------
try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    from sklearn.ensemble import HistGradientBoostingClassifier as XGBFallback
    HAS_XGB = False
    warnings.warn(
        "XGBoost not found; falling back to HistGradientBoostingClassifier.",
        RuntimeWarning,
    )

# Shared utilities
sys.path.insert(0, str(Path(__file__).parent))
import retainiq_common as rc

# ============================================================================
# 0. Matplotlib style
# ============================================================================
rc.set_plot_style()

# ============================================================================
# PHASE 1 – DATA QUALITY INSPECTION
# ============================================================================
CSV_PATH = rc.DATA_DIR / "WA_Fn-UseC_-HR-Employee-Attrition.csv"

print("\n" + "=" * 70)
print("PHASE 1 – DATA QUALITY INSPECTION")
print("=" * 70)

if not CSV_PATH.exists():
    sys.exit(
        f"\n[ERROR] CSV not found at {CSV_PATH}\n"
        "Please place WA_Fn-UseC_-HR-Employee-Attrition.csv in RetainIQ/data/ "
        "and re-run."
    )

raw = pd.read_csv(CSV_PATH)

print(f"\nDataset shape: {raw.shape}")
print(f"Columns ({len(raw.columns)}):\n{list(raw.columns)}")
print(f"\nDtypes:\n{raw.dtypes.value_counts().to_dict()}")

# Missing values
missing = raw.isnull().sum()
print(f"\nMissing values (columns with >0):\n{missing[missing > 0]}")

# Duplicates
dup_count = raw.duplicated().sum()
print(f"\nDuplicate rows: {dup_count}")

# Unique counts per column
unique_counts = raw.nunique().sort_values()
print(f"\nUnique counts per column (ascending):\n{unique_counts}")

# Target distribution
attrition_counts = raw[rc.TARGET_COL].value_counts()
attrition_rate   = raw[rc.TARGET_COL].value_counts(normalize=True)
print(f"\nTarget distribution:\n{attrition_counts}")
print(f"\nTarget proportions:\n{attrition_rate.round(4)}")

# Constant columns
constant_cols = [c for c in raw.columns if raw[c].nunique() == 1]
print(f"\nConstant columns (nunique == 1): {constant_cols}")

# Suspicious identifier-like columns
id_like = [c for c in raw.columns
           if raw[c].dtype in [np.int64, np.float64]
           and raw[c].nunique() == len(raw)]
print(f"Possible identifier columns (all unique ints): {id_like}")

# Numerical descriptive stats
print("\nNumerical summary:")
print(raw.describe().T.to_string())

# ── save data quality report ──────────────────────────────────────────────
qr_rows = []
for col in raw.columns:
    qr_rows.append({
        "column":       col,
        "dtype":        str(raw[col].dtype),
        "missing":      int(raw[col].isnull().sum()),
        "unique":       int(raw[col].nunique()),
        "is_constant":  raw[col].nunique() == 1,
        "possible_id":  (raw[col].dtype in [np.int64, np.float64]
                         and raw[col].nunique() == len(raw)),
        "sample_vals":  str(raw[col].dropna().unique()[:5].tolist()),
    })
qr_df = pd.DataFrame(qr_rows)
qr_df.to_csv(rc.OUT_DIR / "data_quality_report.csv", index=False)
print(f"\n[saved] data_quality_report.csv")

# ── target distribution figure ─────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5, 4))
attrition_counts.plot(kind="bar", ax=ax, color=["#2196F3", "#F44336"], edgecolor="white")
ax.set_title("Target Distribution – Attrition", fontweight="bold")
ax.set_xlabel("Attrition")
ax.set_ylabel("Count")
ax.set_xticklabels(["No (0)", "Yes (1)"], rotation=0)
for p in ax.patches:
    ax.annotate(f"{int(p.get_height())} ({p.get_height()/len(raw):.1%})",
                (p.get_x() + p.get_width() / 2, p.get_height() + 5),
                ha="center", fontsize=9)
plt.tight_layout()
plt.savefig(rc.FIG_DIR / "target_distribution.png")
plt.close()
print("[figure] target_distribution.png")

# ============================================================================
# PHASE 2 – DATA CLEANING & COLUMN VERIFICATION
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 2 – DATA CLEANING")
print("=" * 70)

df = raw.copy()

# Encode target
df[rc.TARGET_COL] = df[rc.TARGET_COL].map({"Yes": 1, "No": 0}).astype(int)
print(f"\nTarget encoded: Yes->1, No->0")

# Verify and drop constant / identifier / excluded columns
actual_constant = [c for c in df.columns if c != rc.TARGET_COL and df[c].nunique() == 1]
print(f"Verified constant columns to drop: {actual_constant}")

drop_cols = list(set(actual_constant + rc.EXPECTED_CONSTANT_COLS + rc.IDENTIFIER_COLS))
drop_cols = [c for c in drop_cols if c in df.columns]
print(f"Dropping: {drop_cols}")

# Retain audit cols + EmployeeNumber for tracking; separate them out
audit_data = df[rc.IDENTIFIER_COLS + rc.AUDIT_COLS + [rc.TARGET_COL]].copy()

# Drop from modelling frame
df_model = df.drop(columns=drop_cols + rc.AUDIT_COLS, errors="ignore")
y_all    = df_model.pop(rc.TARGET_COL)

print(f"\nModel feature matrix shape: {df_model.shape}")
print(f"Target shape: {y_all.shape}")
print(f"Retained audit frame shape: {audit_data.shape}")

# ── Identify numeric vs categorical features ───────────────────────────────
num_cols = df_model.select_dtypes(include=[np.number]).columns.tolist()
cat_cols = df_model.select_dtypes(include=["object", "category"]).columns.tolist()
print(f"\nNumeric features ({len(num_cols)}): {num_cols}")
print(f"Categorical features ({len(cat_cols)}): {cat_cols}")

# ============================================================================
# PHASE 3 – FEATURE ENGINEERING
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 3 – FEATURE ENGINEERING")
print("=" * 70)

def add_engineered_features(df_in: pd.DataFrame) -> pd.DataFrame:
    """
    Add research-motivated engineered features.

    NOTE: any feature that uses a global statistic (e.g. median income)
    is computed ONLY on the input df_in – this function is called INSIDE
    the training fold when used with cross-validation, so there is no
    leakage.
    """
    df_e = df_in.copy()
    eps  = 1e-6  # avoid div-by-zero

    # 1. YearsAtCompanyRatio
    if {"YearsAtCompany", "TotalWorkingYears"}.issubset(df_e.columns):
        df_e["YearsAtCompanyRatio"] = (
            df_e["YearsAtCompany"] / (df_e["TotalWorkingYears"] + eps)
        )

    # 2. IncomePerExperience
    if {"MonthlyIncome", "TotalWorkingYears"}.issubset(df_e.columns):
        df_e["IncomePerExperience"] = (
            df_e["MonthlyIncome"] / (df_e["TotalWorkingYears"] + 1)
        )

    # 3. YearsSincePromotionActual
    if {"YearsAtCompany", "YearsSinceLastPromotion"}.issubset(df_e.columns):
        df_e["YearsSincePromotionActual"] = (
            df_e["YearsAtCompany"] - df_e["YearsSinceLastPromotion"]
        )

    # 4. YearsSincePromotionRatio
    if {"YearsSinceLastPromotion", "YearsAtCompany"}.issubset(df_e.columns):
        df_e["YearsSincePromotionRatio"] = (
            df_e["YearsSinceLastPromotion"] / (df_e["YearsAtCompany"] + 1)
        )

    # 5. YearsWithManagerRatio
    if {"YearsWithCurrManager", "YearsAtCompany"}.issubset(df_e.columns):
        df_e["YearsWithManagerRatio"] = (
            df_e["YearsWithCurrManager"] / (df_e["YearsAtCompany"] + 1)
        )

    # 6. JobLevelExperienceInteraction
    if {"JobLevel", "TotalWorkingYears"}.issubset(df_e.columns):
        df_e["JobLevelExperienceInteraction"] = (
            df_e["JobLevel"] * df_e["TotalWorkingYears"]
        )

    # 7. PromotionGap (same as 4 – kept explicitly per spec)
    if {"YearsSinceLastPromotion", "YearsAtCompany"}.issubset(df_e.columns):
        df_e["PromotionGap"] = (
            df_e["YearsSinceLastPromotion"] / (df_e["YearsAtCompany"] + 1)
        )

    # 8. IncomeGrowthIndicator  (1 if above-median income, 0 otherwise)
    #    Median computed on df_in only – caller controls scope.
    if "MonthlyIncome" in df_e.columns:
        median_income = df_e["MonthlyIncome"].median()
        df_e["IncomeGrowthIndicator"] = (
            df_e["MonthlyIncome"] > median_income
        ).astype(int)

    return df_e

df_eng   = add_engineered_features(df_model)
eng_only = [c for c in df_eng.columns if c not in df_model.columns]
print(f"Engineered features added ({len(eng_only)}): {eng_only}")

num_cols_eng = df_eng.select_dtypes(include=[np.number]).columns.tolist()
cat_cols_eng = df_eng.select_dtypes(include=["object", "category"]).columns.tolist()

# ============================================================================
# HELPER – Build sklearn preprocessing pipeline for a feature matrix
# ============================================================================
def build_preprocessor(X: pd.DataFrame, scale_numeric: bool = False):
    """
    Return a ColumnTransformer for the given DataFrame.

    scale_numeric=True  -> StandardScaler on numerics (for LR)
    scale_numeric=False -> passthrough
    """
    nc = X.select_dtypes(include=[np.number]).columns.tolist()
    cc = X.select_dtypes(include=["object", "category"]).columns.tolist()

    num_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler() if scale_numeric else "passthrough"),
    ])
    cat_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("ohe",     OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    parts = []
    if nc:
        parts.append(("num", num_pipe, nc))
    if cc:
        parts.append(("cat", cat_pipe, cc))

    return ColumnTransformer(parts, remainder="drop")


# ============================================================================
# HELPER – Build full pipeline (preprocessor + classifier)
# ============================================================================
def make_pipeline(clf, X: pd.DataFrame, scale_numeric: bool = False) -> Pipeline:
    prep = build_preprocessor(X, scale_numeric=scale_numeric)
    return Pipeline([("prep", prep), ("clf", clf)])


# ============================================================================
# HELPER – Evaluate OOF predictions
# ============================================================================
def evaluate_oof(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> dict[str, float]:
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "roc_auc":   round(roc_auc_score(y_true, y_prob), 4),
        "pr_auc":    round(average_precision_score(y_true, y_prob), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1":        round(f1_score(y_true, y_pred, zero_division=0), 4),
        "accuracy":  round(accuracy_score(y_true, y_pred), 4),
        "brier":     round(brier_score_loss(y_true, y_prob), 4),
        "ece":       round(rc.expected_calibration_error(y_true, y_prob), 4),
    }


# ============================================================================
# HELPER – OOF loop that reconstructs the full pipeline inside each fold
#          (leakage-safe: feature engineering + preprocessing inside fold)
# ============================================================================
from sklearn.model_selection import StratifiedKFold
from sklearn.calibration import CalibratedClassifierCV
import copy

SKF = StratifiedKFold(n_splits=rc.CV_FOLDS, shuffle=True, random_state=rc.RANDOM_STATE)


def oof_loop(
    X_full: pd.DataFrame,
    y_full: pd.Series,
    clf_factory,           # callable() -> unfitted sklearn estimator
    use_engineering: bool,
    scale: bool,
    calibrate: bool = True,
    cal_method: str = "sigmoid",
) -> tuple[np.ndarray, np.ndarray]:
    """
    Run the full OOF loop.

    Feature engineering (if requested) is applied ONLY to the training fold
    features – the test fold receives the same transformation applied with
    parameters learned from training.  Because our engineered features are
    deterministic or use training-fold medians, we handle it as follows:

    - Deterministic features (ratios, products): can be computed on any fold
      without leakage.
    - IncomeGrowthIndicator: threshold derived from training fold median.

    To keep things clean and leakage-safe, we call add_engineered_features
    on the training fold, capture the median, then apply it to the test fold.

    Returns
    -------
    oof_probs : (n_samples,)
    fold_ids  : (n_samples,)
    """
    X_arr   = X_full.values.copy()
    X_cols  = X_full.columns.tolist()
    y_arr   = y_full.values.copy()

    oof_probs = np.full(len(y_arr), np.nan)
    fold_ids  = np.full(len(y_arr), -1, dtype=int)

    for fold_idx, (tr_idx, va_idx) in enumerate(SKF.split(X_arr, y_arr)):
        X_tr_df = pd.DataFrame(X_arr[tr_idx], columns=X_cols)
        X_va_df = pd.DataFrame(X_arr[va_idx], columns=X_cols)
        y_tr    = y_arr[tr_idx]

        if use_engineering:
            # Compute median on training fold, apply to both
            tr_median_income = X_tr_df["MonthlyIncome"].median() if "MonthlyIncome" in X_tr_df.columns else None

            X_tr_eng = add_engineered_features(X_tr_df)
            X_va_eng = add_engineered_features(X_va_df)

            # Overwrite IncomeGrowthIndicator on val fold using training median
            if tr_median_income is not None and "IncomeGrowthIndicator" in X_va_eng.columns:
                X_va_eng["IncomeGrowthIndicator"] = (
                    X_va_df["MonthlyIncome"] > tr_median_income
                ).astype(int)

            X_tr_use = X_tr_eng
            X_va_use = X_va_eng
        else:
            X_tr_use = X_tr_df
            X_va_use = X_va_df

        # Build full pipeline
        clf  = clf_factory()
        pipe = make_pipeline(clf, X_tr_use, scale_numeric=scale)

        if calibrate:
            cal_cv   = StratifiedKFold(n_splits=3, shuffle=True, random_state=rc.RANDOM_STATE)
            cal_pipe = CalibratedClassifierCV(pipe, method=cal_method, cv=cal_cv)
            cal_pipe.fit(X_tr_use, y_tr)
            probs = cal_pipe.predict_proba(X_va_use)[:, 1]
        else:
            pipe.fit(X_tr_use, y_tr)
            probs = pipe.predict_proba(X_va_use)[:, 1]

        oof_probs[va_idx] = probs
        fold_ids[va_idx]  = fold_idx

    return oof_probs, fold_ids


# ============================================================================
# PHASE 4 & 5 – MODEL TRAINING + OOF EVALUATION
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 4 & 5 – MODEL TRAINING + OOF EVALUATION")
print("=" * 70)

# ─── Define model factories ─────────────────────────────────────────────────
def lr_factory():
    return LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=rc.RANDOM_STATE,
        solver="lbfgs",
    )

def rf_factory():
    return RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        random_state=rc.RANDOM_STATE,
        n_jobs=-1,
        max_depth=None,
        min_samples_leaf=2,
    )

if HAS_XGB:
    pos_weight = float((y_all == 0).sum()) / float((y_all == 1).sum())
    def xgb_factory():
        return XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            scale_pos_weight=pos_weight,
            random_state=rc.RANDOM_STATE,
            eval_metric="logloss",
            verbosity=0,
            # use_label_encoder removed in XGBoost 2.0+
        )
else:
    def xgb_factory():
        return XGBFallback(
            max_iter=300,
            max_depth=5,
            learning_rate=0.05,
            random_state=rc.RANDOM_STATE,
        )

MODELS = {
    "LogisticRegression": (lr_factory, True),   # (factory, scale_numeric)
    "RandomForest":       (rf_factory, False),
    "XGBoost":            (xgb_factory, False),
}

# ─── Run Ablation A (no engineering) + Ablation B (with engineering) ────────
results      = []   # all experiment rows
oof_store    = {}   # model_name -> oof_probs array (best ablation per model)
best_oof_df  = None  # the top model's OOF frame

experiment_id = 0
best_model_name  = None
best_pr_auc      = -1.0
best_oof_probs   = None

for feat_set, use_eng in [("baseline", False), ("engineered", True)]:
    X_use = df_eng if use_eng else df_model

    for model_name, (factory, scale) in MODELS.items():
        experiment_id += 1
        print(f"\n  Exp {experiment_id:02d}: {model_name} | features={feat_set} | "
              f"calibrate=sigmoid | imbalance=class_weight ...")

        oof_probs, fold_ids = oof_loop(
            X_full        = X_use,
            y_full        = y_all,
            clf_factory   = factory,
            use_engineering = use_eng,
            scale         = scale,
            calibrate     = True,
            cal_method    = "sigmoid",
        )

        metrics = evaluate_oof(y_all.values, oof_probs)
        print(f"    ROC-AUC={metrics['roc_auc']}  PR-AUC={metrics['pr_auc']}  "
              f"F1={metrics['f1']}  Brier={metrics['brier']}  ECE={metrics['ece']}")

        row = {
            "experiment_id":      experiment_id,
            "feature_set":        feat_set,
            "model":              model_name,
            "imbalance_strategy": "class_weight",
            "calibration":        "sigmoid",
            **metrics,
            "notes": "",
        }
        results.append(row)

        # Track best (by PR-AUC on engineered set)
        if use_eng and metrics["pr_auc"] > best_pr_auc:
            best_pr_auc   = metrics["pr_auc"]
            best_model_name = model_name
            best_oof_probs  = oof_probs.copy()

        # Store for OOF file
        oof_store[f"{model_name}_{feat_set}"] = oof_probs

# ── Also run uncalibrated baseline for calibration comparison ────────────────
print("\n  Running uncalibrated LR (baseline features) for calibration comparison ...")
oof_lr_uncal, _ = oof_loop(
    X_full=df_model, y_full=y_all,
    clf_factory=lr_factory, use_engineering=False,
    scale=True, calibrate=False,
)
oof_lr_cal, _ = oof_loop(
    X_full=df_model, y_full=y_all,
    clf_factory=lr_factory, use_engineering=False,
    scale=True, calibrate=True, cal_method="sigmoid",
)

# ============================================================================
# PHASE 6 – FEATURE ABLATION COMPARISON
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 6 – FEATURE ABLATION COMPARISON")
print("=" * 70)

abl_rows = [r for r in results]
abl_df   = pd.DataFrame(abl_rows)
abl_df.to_csv(rc.OUT_DIR / "feature_ablation.csv", index=False)
print(f"[saved] feature_ablation.csv")

# ─── Ablation figure ─────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
metrics_to_plot = ["roc_auc", "pr_auc", "f1"]
metric_labels   = ["ROC-AUC", "PR-AUC", "F1"]
colors          = {"baseline": "#2196F3", "engineered": "#FF5722"}

for ax, met, lab in zip(axes, metrics_to_plot, metric_labels):
    for fs, grp in abl_df.groupby("feature_set"):
        ax.bar(
            [x + (0.2 if fs == "engineered" else -0.2) for x in range(len(MODELS))],
            grp.sort_values("model")[met].values,
            width=0.35,
            label=fs.capitalize(),
            color=colors[fs],
            edgecolor="white",
            alpha=0.85,
        )
    ax.set_title(lab, fontweight="bold")
    ax.set_xticks(range(len(MODELS)))
    ax.set_xticklabels(list(MODELS.keys()), rotation=15, ha="right")
    ax.set_ylim(0, 1)
    ax.legend()

plt.suptitle("Feature Ablation: Baseline vs Engineered Features", fontweight="bold")
plt.tight_layout()
plt.savefig(rc.FIG_DIR / "feature_ablation.png")
plt.close()
print("[figure] feature_ablation.png")

# ============================================================================
# PHASE 7 – CALIBRATION EVALUATION
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 7 – CALIBRATION EVALUATION")
print("=" * 70)

from sklearn.calibration import calibration_curve

cal_results = []
for label, probs in [("LR_uncalibrated", oof_lr_uncal), ("LR_calibrated_sigmoid", oof_lr_cal)]:
    m = evaluate_oof(y_all.values, probs)
    cal_results.append({
        "model":   label,
        "brier":   m["brier"],
        "ece":     m["ece"],
        "roc_auc": m["roc_auc"],
        "pr_auc":  m["pr_auc"],
    })
    print(f"  {label}: Brier={m['brier']}  ECE={m['ece']}")

cal_df = pd.DataFrame(cal_results)
cal_df.to_csv(rc.OUT_DIR / "calibration_results.csv", index=False)
print("[saved] calibration_results.csv")

# ─── Calibration curve figure ─────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6, 5))
ax.plot([0, 1], [0, 1], "k--", label="Perfect calibration", lw=1.2)
for label, probs, col in [
    ("Uncalibrated LR", oof_lr_uncal, "#F44336"),
    ("Calibrated LR (Sigmoid)", oof_lr_cal, "#4CAF50"),
]:
    frac_pos, mean_pred = calibration_curve(y_all, probs, n_bins=10)
    ax.plot(mean_pred, frac_pos, marker="o", lw=2, label=label, color=col)

ax.set_xlabel("Mean Predicted Probability")
ax.set_ylabel("Fraction of Positives")
ax.set_title("Calibration Curve (LR – Baseline Features)", fontweight="bold")
ax.legend()
plt.tight_layout()
plt.savefig(rc.FIG_DIR / "calibration_curve.png")
plt.close()
print("[figure] calibration_curve.png")

# ============================================================================
# PHASE 8 – SELECT FINAL MODEL
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 8 – FINAL MODEL SELECTION")
print("=" * 70)

# Selection rule: highest PR-AUC on engineered feature set
eng_rows = [r for r in results if r["feature_set"] == "engineered"]
best_row = max(eng_rows, key=lambda r: r["pr_auc"])
print(f"\nFinal model selected:  {best_row['model']}")
print(f"  PR-AUC  = {best_row['pr_auc']}")
print(f"  ROC-AUC = {best_row['roc_auc']}")
print(f"  F1      = {best_row['f1']}")
print(f"  Brier   = {best_row['brier']}")
print(f"  ECE     = {best_row['ece']}")
print(f"\nSelection rule: highest PR-AUC on engineered feature set (calibrated, "
      f"class_weight='balanced').")
print(f"If two models have similar PR-AUC, simpler/interpretable model preferred.")

final_model_name = best_row["model"]

# ============================================================================
# PHASE 9 – SAVE ALL ARTEFACTS
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 9 – SAVING ARTEFACTS")
print("=" * 70)

# ── Baseline model comparison CSV ──────────────────────────────────────────
comp_df = pd.DataFrame(results)
comp_df.to_csv(rc.OUT_DIR / "baseline_model_comparison.csv", index=False)
print("[saved] baseline_model_comparison.csv")

# ── Experiment summary CSV ──────────────────────────────────────────────────
comp_df.to_csv(rc.OUT_DIR / "experiment_summary.csv", index=False)
print("[saved] experiment_summary.csv")

# ── OOF predictions CSV ────────────────────────────────────────────────────
oof_out = audit_data[[rc.IDENTIFIER_COLS[0], rc.TARGET_COL]].copy()
for key, probs in oof_store.items():
    oof_out[f"prob_{key}"] = probs
# Primary OOF = best model on engineered features
oof_out["calibrated_probability"] = oof_store[f"{final_model_name}_engineered"]
oof_out.to_csv(rc.OUT_DIR / "baseline_oof_predictions.csv", index=False)
print("[saved] baseline_oof_predictions.csv")

# ── Model comparison figure ────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, (metric, label) in zip(
    axes, [("pr_auc", "PR-AUC (primary)"), ("roc_auc", "ROC-AUC")]
):
    eng_sub = comp_df[comp_df["feature_set"] == "engineered"].sort_values(metric, ascending=True)
    bars    = ax.barh(eng_sub["model"], eng_sub[metric],
                      color="#4CAF50", edgecolor="white", alpha=0.85)
    ax.set_xlabel(label)
    ax.set_title(f"{label} – Engineered Features", fontweight="bold")
    ax.set_xlim(0, 1)
    for bar, val in zip(bars, eng_sub[metric]):
        ax.text(val + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9)

plt.suptitle("Model Comparison (OOF, Calibrated, Engineered Features)",
             fontweight="bold")
plt.tight_layout()
plt.savefig(rc.FIG_DIR / "model_comparison.png")
plt.close()
print("[figure] model_comparison.png")

# ── Feature importance (permutation) for final model ──────────────────────
print("\nComputing permutation feature importance for final model ...")
from sklearn.inspection import permutation_importance

X_fi = df_eng.copy()
FINAL_FACTORY = {"LogisticRegression": lr_factory,
                 "RandomForest":       rf_factory,
                 "XGBoost":            xgb_factory}[final_model_name]
FINAL_SCALE   = {"LogisticRegression": True,
                 "RandomForest":       False,
                 "XGBoost":            False}[final_model_name]

final_pipe_fi = make_pipeline(FINAL_FACTORY(), X_fi, scale_numeric=FINAL_SCALE)
final_pipe_fi.fit(X_fi, y_all)

perm = permutation_importance(
    final_pipe_fi, X_fi, y_all,
    n_repeats=10,
    random_state=rc.RANDOM_STATE,
    scoring="average_precision",
    n_jobs=-1,
)
perm_df = pd.DataFrame({
    "feature":        X_fi.columns,
    "importance_mean": perm.importances_mean,
    "importance_std":  perm.importances_std,
}).sort_values("importance_mean", ascending=False).reset_index(drop=True)

# Figure
fig, ax = plt.subplots(figsize=(8, max(6, len(perm_df) * 0.3)))
top_n   = min(25, len(perm_df))
sub     = perm_df.head(top_n).iloc[::-1]
ax.barh(sub["feature"], sub["importance_mean"], xerr=sub["importance_std"],
        color="#7B1FA2", edgecolor="white", alpha=0.85, capsize=3)
ax.set_xlabel("Permutation Importance (delta PR-AUC)")
ax.set_title(f"Top {top_n} Features – Permutation Importance\n"
             f"({final_model_name}, Engineered Features)",
             fontweight="bold")
ax.set_ylabel("Feature")
plt.tight_layout()
plt.savefig(rc.FIG_DIR / "feature_importance.png")
plt.close()
print("[figure] feature_importance.png")

# ── Optional SHAP (tree models only) ──────────────────────────────────────
if final_model_name in ("RandomForest", "XGBoost"):
    try:
        import shap
        print("Running SHAP analysis ...")
        # Extract the underlying classifier and preprocessor from the pipeline
        clf_shap  = final_pipe_fi.named_steps["clf"]
        prep_shap = final_pipe_fi.named_steps["prep"]
        X_shap_np = prep_shap.transform(X_fi)

        # Build feature names after one-hot encoding
        try:
            nc_shap = X_fi.select_dtypes(include=["number"]).columns.tolist()
            cc_shap = X_fi.select_dtypes(include=["object", "category"]).columns.tolist()
            ohe_names = (
                prep_shap.named_transformers_["cat"]
                .named_steps["ohe"]
                .get_feature_names_out(cc_shap)
                .tolist()
            ) if cc_shap else []
            all_names = nc_shap + ohe_names
        except Exception:
            all_names = [f"f{i}" for i in range(X_shap_np.shape[1])]

        # SHAP 0.47+ unified Explainer works for both RF and XGB
        explainer = shap.Explainer(clf_shap, X_shap_np)
        shap_explanation = explainer(X_shap_np)

        # Handle both old (ndarray) and new (Explanation object) SHAP APIs
        if hasattr(shap_explanation, "values"):
            sv = shap_explanation.values
            # For binary classification the shape may be (n, features, 2)
            if sv.ndim == 3:
                sv = sv[:, :, 1]
        else:
            sv = shap_explanation
            if isinstance(sv, list):
                sv = sv[1]

        import matplotlib
        matplotlib.use("Agg")  # ensure non-interactive backend
        fig_shap, ax_shap = plt.subplots(figsize=(10, 8))
        shap.summary_plot(
            sv, X_shap_np,
            feature_names=all_names,
            show=False,
            max_display=20,
            plot_size=None,
        )
        plt.title(f"SHAP Summary – {final_model_name} (model-associated features)",
                  fontweight="bold")
        plt.tight_layout()
        plt.savefig(rc.FIG_DIR / "shap_summary.png", dpi=150, bbox_inches="tight")
        plt.close("all")
        print("[figure] shap_summary.png")
    except Exception as e:
        print(f"[warn] SHAP skipped: {e}")

# ── Leakage checklist ──────────────────────────────────────────────────────
leakage_checks = {
    "EmployeeNumber not used as feature":           True,
    "Attrition not used as feature":                True,
    "Age/Gender/MaritalStatus excluded from model": True,
    "No preprocessing fit on full dataset":         True,
    "No SMOTE/ADASYN before CV":                    True,
    "No target-derived feature":                    True,
    "No future information":                        True,
    "Calibration inside outer training fold only":  True,
    "OOF predictions used for evaluation":          True,
    "Cost calculation occurs after probability":    True,
    "Final full-data model NOT used for unbiased evaluation": True,
}
rc.write_leakage_checklist(leakage_checks)

# ── Final model metadata ───────────────────────────────────────────────────
import sys
import sklearn
import numpy as np
import pandas as pd

meta = {
    "python_version":     sys.version,
    "sklearn_version":    sklearn.__version__,
    "numpy_version":      np.__version__,
    "pandas_version":     pd.__version__,
    "dataset":            str(CSV_PATH.name),
    "dataset_shape":      list(raw.shape),
    "random_state":       rc.RANDOM_STATE,
    "cv_folds":           rc.CV_FOLDS,
    "final_model":        final_model_name,
    "feature_set":        "engineered",
    "calibration":        "sigmoid (CalibratedClassifierCV inner 3-fold)",
    "imbalance_strategy": "class_weight='balanced'",
    "excluded_from_model": rc.EXCLUDED_FROM_MODEL,
    "audit_cols":         rc.AUDIT_COLS,
    "cost_assumptions": {
        "fixed_cost":    rc.DEFAULT_FIXED_COST,
        "salary_share":  rc.DEFAULT_SALARY_SHARE,
        "seniority_factors": rc.SENIORITY_FACTORS,
        "note": "RESEARCHER ASSUMPTIONS – not industry standards",
    },
    "selection_rule": "Highest PR-AUC on engineered feature set",
    "best_pr_auc":    float(best_row["pr_auc"]),
    "best_roc_auc":   float(best_row["roc_auc"]),
    "disclaimer":     rc.DISCLAIMER,
}
rc.save_metadata(meta)

# ── Print summary ──────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("BASELINE PIPELINE COMPLETE – SUMMARY")
print("=" * 70)
print(f"\nDataset shape:          {raw.shape}")
print(f"Attrition rate:         {y_all.mean():.1%}")
print(f"CV folds:               {rc.CV_FOLDS}")
print(f"\nFinal selected model:   {final_model_name}")
print(f"  PR-AUC  (primary):    {best_row['pr_auc']}")
print(f"  ROC-AUC:              {best_row['roc_auc']}")
print(f"  F1:                   {best_row['f1']}")
print(f"  Brier:                {best_row['brier']}")
print(f"  ECE:                  {best_row['ece']}")

print("\nAll model results (engineered features):")
print(comp_df[comp_df["feature_set"] == "engineered"][
    ["model", "pr_auc", "roc_auc", "f1", "brier", "ece"]
].to_string(index=False))

print("\nCalibration evaluation:")
print(cal_df.to_string(index=False))

print("\nOutputs saved:")
for f in sorted(rc.OUT_DIR.glob("*.csv")) + sorted(rc.OUT_DIR.glob("*.md")) + sorted(rc.OUT_DIR.glob("*.json")):
    print(f"  {f.name}")

print("\nFigures saved:")
for f in sorted(rc.FIG_DIR.glob("*.png")):
    print(f"  {f.name}")

print(f"\n[NEXT] Run retainiq_02_priority.py to generate cost scenarios, "
      f"ERL, rankings, budget experiments, fairness audit, and explanations.")
