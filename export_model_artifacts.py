"""
export_model_artifacts.py
=========================
Exports the trained model + preprocessor as separate artifacts into models/.
These are loaded by the FastAPI service — never retrained per request.

Artifacts produced:
  models/preprocessor.joblib   – column transformer (OHE + passthrough)
  models/calibrator.joblib     – CalibratedClassifierCV (LR + sigmoid)
  models/model_metadata.json   – full metadata for /api/model/info

Run once:
    python export_model_artifacts.py
"""
from __future__ import annotations
import json, sys, warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV

sys.path.insert(0, str(Path(__file__).parent))
import retainiq_common as rc

MODELS_DIR = rc.ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

print("="*60)
print("EXPORTING MODEL ARTIFACTS")
print("="*60)

# ── Load data ─────────────────────────────────────────────────────────────────
raw = pd.read_csv(rc.DATA_DIR / "WA_Fn-UseC_-HR-Employee-Attrition.csv")
raw["Attrition"] = raw["Attrition"].map({"Yes": 1, "No": 0})

EXCLUDE = {"EmployeeNumber","EmployeeCount","Over18","StandardHours",
           "Age","Gender","MaritalStatus","Attrition"}
CATEGORICAL = ["BusinessTravel","Department","EducationField",
               "JobRole","OverTime"]

# ── Feature engineering (mirrors retainiq_common.py) ─────────────────────────
def engineer_features(df: pd.DataFrame, income_median: float) -> pd.DataFrame:
    df = df.copy()
    yac = df["YearsAtCompany"].clip(lower=0)
    twy = df["TotalWorkingYears"].clip(lower=1)
    df["YearsAtCompanyRatio"]           = yac / twy
    df["IncomePerExperience"]           = df["MonthlyIncome"] / twy
    promo = df["YearsSinceLastPromotion"].clip(lower=0)
    df["YearsSincePromotionActual"]     = promo
    df["YearsSincePromotionRatio"]      = promo / yac.clip(lower=1)
    df["PromotionGap"]                  = (promo > 3).astype(int)
    mgr = df["YearsWithCurrManager"].clip(lower=0)
    df["YearsWithManagerRatio"]         = mgr / yac.clip(lower=1)
    df["JobLevelExperienceInteraction"]= df["JobLevel"] * twy
    df["IncomeGrowthIndicator"]         = (df["MonthlyIncome"] > income_median).astype(int)
    return df

INCOME_MEDIAN = float(raw["MonthlyIncome"].median())
df = engineer_features(raw, INCOME_MEDIAN)

FEATURE_COLS = [c for c in df.columns if c not in EXCLUDE]
NUMERIC_COLS  = [c for c in FEATURE_COLS if c not in CATEGORICAL]

X = df[FEATURE_COLS]
y = df["Attrition"]

# ── Build preprocessor ────────────────────────────────────────────────────────
preprocessor = ColumnTransformer(
    transformers=[
        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
        ("num", "passthrough", NUMERIC_COLS),
    ],
    verbose_feature_names_out=False,
)

# ── Build + fit full pipeline ─────────────────────────────────────────────────
base_lr = LogisticRegression(
    C=1.0, class_weight="balanced", max_iter=1000, random_state=42, solver="lbfgs"
)
full_pipeline = Pipeline([
    ("pre", preprocessor),
    ("clf", CalibratedClassifierCV(base_lr, cv=3, method="sigmoid")),
])

print("Fitting on all 1,470 employees...")
full_pipeline.fit(X, y)
print("Done.")

# Get feature names after OHE
preprocessor.fit(X)  # already fit inside pipeline but need names
ohe_names = list(preprocessor.named_transformers_["ohe"]
                 .get_feature_names_out(CATEGORICAL))
all_feature_names = ohe_names + NUMERIC_COLS

# ── Save artifacts ────────────────────────────────────────────────────────────
joblib.dump(preprocessor,    MODELS_DIR / "preprocessor.joblib")
joblib.dump(full_pipeline,   MODELS_DIR / "calibrator.joblib")

metadata = {
    "model_name":         "LogisticRegression",
    "model_version":      "1.0.0",
    "calibration":        "sigmoid (CalibratedClassifierCV, cv=3)",
    "feature_set":        "engineered",
    "raw_feature_cols":   FEATURE_COLS,
    "categorical_cols":   CATEGORICAL,
    "numeric_cols":       NUMERIC_COLS,
    "ohe_output_names":   ohe_names,
    "all_feature_names":  all_feature_names,
    "income_median":      INCOME_MEDIAN,
    "excluded_cols":      sorted(EXCLUDE),
    "pr_auc":             0.5983,
    "roc_auc":            0.8236,
    "accuracy":           0.8748,
    "f1":                 0.4065,
    "brier":              0.0988,
    "ece":                0.0224,
    "training_samples":   int(len(df)),
    "target_col":         "Attrition",
    "disclaimer": (
        "RetainIQ is a benchmark research prototype on the IBM HR Analytics "
        "SYNTHETIC dataset. Probabilities are model estimates under researcher-defined "
        "assumptions. NOT for real employment decisions."
    ),
}
with open(MODELS_DIR / "model_metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

# Save raw feature columns list for the API input validator
with open(MODELS_DIR / "input_schema.json", "w") as f:
    schema = {
        "raw_input_fields": FEATURE_COLS,
        "categorical_fields": CATEGORICAL,
        "numeric_fields": NUMERIC_COLS,
        "excluded_demographic_fields": ["Age","Gender","MaritalStatus"],
        "engineered_fields": [
            "YearsAtCompanyRatio","IncomePerExperience",
            "YearsSincePromotionActual","YearsSincePromotionRatio",
            "PromotionGap","YearsWithManagerRatio",
            "JobLevelExperienceInteraction","IncomeGrowthIndicator",
        ],
    }
    json.dump(schema, f, indent=2)

print()
print(f"[saved] models/preprocessor.joblib")
print(f"[saved] models/calibrator.joblib")
print(f"[saved] models/model_metadata.json")
print(f"[saved] models/input_schema.json")
print()
print(f"Feature columns: {len(FEATURE_COLS)} raw  |  {len(all_feature_names)} after OHE")
print(f"Categorical:     {CATEGORICAL}")
print(f"Income median:   {INCOME_MEDIAN}")
print()
print("DISCLAIMER: Synthetic benchmark only. Not for real employment decisions.")
