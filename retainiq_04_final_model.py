"""
retainiq_04_final_model.py
==========================
PHASE 21 – Train Final Model on Full Dataset
PHASE 22 – Interactive Employee Demo Interface

Trains Logistic Regression (the selected model) on ALL 1,470 employees
using the engineered feature set with sigmoid calibration.

IMPORTANT DISTINCTION
---------------------
The EVALUATION results (OOF predictions, all metrics) come from
retainiq_01_baseline.py and are based on held-out validation data.

This script produces a DEMO/DEPLOYABLE model artifact ONLY.
Predictions from this model are NOT used for research evaluation.
They are for demonstration purposes only.

DISCLAIMER
----------
RetainIQ is a benchmark research prototype on the IBM HR Analytics
synthetic dataset. This system must NOT be used to make real employment
decisions. No causal relationships are implied.

Run:
    python retainiq_04_final_model.py
    python retainiq_04_final_model.py --employee 1277
    python retainiq_04_final_model.py --top 20
    python retainiq_04_final_model.py --interactive
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
os.environ["OMP_NUM_THREADS"] = "4"
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
import retainiq_common as rc

# ============================================================================
# PHASE 21 – TRAIN FINAL MODEL ON FULL DATASET
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 21 – FINAL MODEL TRAINING (FULL DATASET)")
print("=" * 70)
print("\nIMPORTANT: This model is trained on ALL data for demo purposes.")
print("Research evaluation used OOF predictions from retainiq_01_baseline.py.")
print("Do NOT use this model's training-set predictions as unbiased estimates.\n")

# -- Load data ----------------------------------------------------------------
CSV_PATH = rc.DATA_DIR / "WA_Fn-UseC_-HR-Employee-Attrition.csv"
OOF_PATH = rc.OUT_DIR / "baseline_oof_predictions.csv"
EXP_PATH = rc.OUT_DIR / "employee_explanations.csv"
RAG_PATH = rc.OUT_DIR / "retention_briefs.csv"
PRI_PATH = rc.OUT_DIR / "employee_priority.csv"

for p in [CSV_PATH, OOF_PATH]:
    if not p.exists():
        sys.exit(f"\n[ERROR] Required file missing: {p}\n"
                 "Run retainiq_01_baseline.py and retainiq_02_priority.py first.")

raw = pd.read_csv(CSV_PATH)
oof = pd.read_csv(OOF_PATH)

raw["Attrition"] = raw["Attrition"].map({"Yes": 1, "No": 0})

# -- Build feature matrix (same logic as Phase 1) -------------------------
EXCLUDED = list(set(rc.EXPECTED_CONSTANT_COLS + rc.IDENTIFIER_COLS +
                    rc.AUDIT_COLS + [rc.TARGET_COL]))
df_model = raw.drop(columns=[c for c in EXCLUDED if c in raw.columns])

def add_engineered_features(df_in: pd.DataFrame,
                             income_median: float | None = None) -> pd.DataFrame:
    df_e = df_in.copy()
    eps = 1e-6
    if {"YearsAtCompany", "TotalWorkingYears"}.issubset(df_e.columns):
        df_e["YearsAtCompanyRatio"] = df_e["YearsAtCompany"] / (df_e["TotalWorkingYears"] + eps)
    if {"MonthlyIncome", "TotalWorkingYears"}.issubset(df_e.columns):
        df_e["IncomePerExperience"] = df_e["MonthlyIncome"] / (df_e["TotalWorkingYears"] + 1)
    if {"YearsAtCompany", "YearsSinceLastPromotion"}.issubset(df_e.columns):
        df_e["YearsSincePromotionActual"] = df_e["YearsAtCompany"] - df_e["YearsSinceLastPromotion"]
    if {"YearsSinceLastPromotion", "YearsAtCompany"}.issubset(df_e.columns):
        df_e["YearsSincePromotionRatio"] = df_e["YearsSinceLastPromotion"] / (df_e["YearsAtCompany"] + 1)
        df_e["PromotionGap"]             = df_e["YearsSinceLastPromotion"] / (df_e["YearsAtCompany"] + 1)
    if {"YearsWithCurrManager", "YearsAtCompany"}.issubset(df_e.columns):
        df_e["YearsWithManagerRatio"] = df_e["YearsWithCurrManager"] / (df_e["YearsAtCompany"] + 1)
    if {"JobLevel", "TotalWorkingYears"}.issubset(df_e.columns):
        df_e["JobLevelExperienceInteraction"] = df_e["JobLevel"] * df_e["TotalWorkingYears"]
    if "MonthlyIncome" in df_e.columns:
        med = income_median if income_median is not None else df_e["MonthlyIncome"].median()
        df_e["IncomeGrowthIndicator"] = (df_e["MonthlyIncome"] > med).astype(int)
    return df_e

# Compute full-dataset median (used for demo predictions)
FULL_MEDIAN_INCOME = df_model["MonthlyIncome"].median()
X_full = add_engineered_features(df_model, income_median=FULL_MEDIAN_INCOME)
y_full = raw["Attrition"]

nc = X_full.select_dtypes(include=[np.number]).columns.tolist()
cc = X_full.select_dtypes(include=["object", "category"]).columns.tolist()

num_pipe = Pipeline([
    ("imp", SimpleImputer(strategy="median")),
    ("scl", StandardScaler()),
])
cat_pipe = Pipeline([
    ("imp", SimpleImputer(strategy="most_frequent")),
    ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
])
parts = []
if nc: parts.append(("num", num_pipe, nc))
if cc: parts.append(("cat", cat_pipe, cc))
prep = ColumnTransformer(parts, remainder="drop")

base_lr = LogisticRegression(
    max_iter=2000,
    class_weight="balanced",
    random_state=rc.RANDOM_STATE,
    solver="lbfgs",
)
base_pipe = Pipeline([("prep", prep), ("clf", base_lr)])

# Calibrate using inner 3-fold CV on full dataset
cal_cv    = StratifiedKFold(n_splits=3, shuffle=True, random_state=rc.RANDOM_STATE)
final_cal = CalibratedClassifierCV(base_pipe, method="sigmoid", cv=cal_cv)
print("Fitting final model (LR + Sigmoid calibration) on all 1,470 employees ...")
final_cal.fit(X_full, y_full)
print("Done.\n")

# -- Save model with joblib ---------------------------------------------------
try:
    import joblib
    MODEL_PATH = rc.ROOT / "outputs" / "final_model.pkl"
    joblib.dump({
        "model":              final_cal,
        "feature_columns":    list(X_full.columns),
        "income_median":      float(FULL_MEDIAN_INCOME),
        "model_name":         "LogisticRegression",
        "calibration":        "sigmoid",
        "disclaimer":         "RetainIQ research prototype - synthetic benchmark only",
    }, MODEL_PATH)
    print(f"[saved] final_model.pkl -> {MODEL_PATH}")
except Exception as e:
    print(f"[warn] joblib save skipped: {e}")

# -- Save metadata update ------------------------------------------------------
meta_path = rc.OUT_DIR / "final_model_metadata.json"
if meta_path.exists():
    with open(meta_path) as f:
        meta = json.load(f)
    meta["final_demo_model"] = "LogisticRegression + Sigmoid CalibratedClassifierCV"
    meta["demo_note"]        = ("Trained on full dataset for demo only. "
                                "Research evaluation uses OOF predictions.")
    meta["income_median_full"] = float(FULL_MEDIAN_INCOME)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, default=str)

# -- Load supporting dataframes ------------------------------------------------
priority_df = pd.read_csv(PRI_PATH)   if PRI_PATH.exists() else pd.DataFrame()
oof_df      = pd.read_csv(OOF_PATH)
exp_df      = pd.read_csv(EXP_PATH)   if EXP_PATH.exists() else pd.DataFrame()
rag_df      = pd.read_csv(RAG_PATH)   if RAG_PATH.exists() else pd.DataFrame()

# Merge everything into one master lookup frame
master = raw.copy()
master = master.merge(
    oof_df[["EmployeeNumber", "calibrated_probability"]],
    on="EmployeeNumber", how="left"
)
if not priority_df.empty:
    master = master.merge(
        priority_df[["EmployeeNumber",
                     "AnnualSalary",
                     "replacement_cost_fixed_plus_salary",
                     "replacement_cost_seniority_scaled",
                     "ERL_fixed_plus_salary",
                     "ERL_seniority_scaled"]],
        on="EmployeeNumber", how="left"
    )

# Add ranks
master["rank_risk_only"]           = master["calibrated_probability"].rank(
    ascending=False, method="first").astype(int)
master["rank_risk_x_cost_fixed"]   = master["ERL_fixed_plus_salary"].rank(
    ascending=False, method="first").astype(int)
master["rank_risk_x_cost_seniority"] = master["ERL_seniority_scaled"].rank(
    ascending=False, method="first").astype(int)

# Risk category labels
def risk_label(p: float) -> str:
    if p >= 0.60: return "HIGH"
    if p >= 0.35: return "MODERATE"
    return "LOW"

master["risk_category"] = master["calibrated_probability"].apply(risk_label)

# ============================================================================
# DEMO HELPERS
# ============================================================================
BORDER = "-" * 70

def _get_employee(emp_id: int) -> pd.Series | None:
    row = master[master["EmployeeNumber"] == emp_id]
    if row.empty:
        return None
    return row.iloc[0]

def _get_factors(emp_id: int) -> str:
    if exp_df.empty:
        return "Factor analysis not available (run retainiq_02_priority.py)"
    row = exp_df[exp_df["EmployeeNumber"] == emp_id]
    if row.empty:
        return "Not in top-20 explanation set"
    return str(row.iloc[0].get("model_associated_factors", ""))

def _get_rag(emp_id: int) -> tuple[str, str, str, str]:
    if rag_df.empty:
        return ("", "", "", "")
    row = rag_df[rag_df["EmployeeNumber"] == emp_id]
    if row.empty:
        return ("", "", "", "")
    r = row.iloc[0]
    return (str(r.get("retrieved_passage_1", ""))[:300],
            str(r.get("citation_1", "")),
            str(r.get("retrieved_passage_2", ""))[:300],
            str(r.get("citation_2", "")))

def print_employee_card(emp_id: int) -> None:
    e = _get_employee(emp_id)
    if e is None:
        print(f"\n[ERROR] Employee #{emp_id} not found in dataset.")
        return

    prob      = e.get("calibrated_probability", float("nan"))
    erl_fixed = e.get("ERL_fixed_plus_salary", float("nan"))
    erl_sen   = e.get("ERL_seniority_scaled",   float("nan"))
    rc_fixed  = e.get("replacement_cost_fixed_plus_salary", float("nan"))
    ann_sal   = e.get("AnnualSalary", e.get("MonthlyIncome", 0) * 12)
    rank_risk = int(e.get("rank_risk_only", -1))
    rank_erl  = int(e.get("rank_risk_x_cost_fixed", -1))
    risk_cat  = e.get("risk_category", risk_label(prob))
    actual    = int(e["Attrition"])

    risk_colors = {"HIGH": "[!]", "MODERATE": "[~]", "LOW": "[OK]"}
    icon = risk_colors.get(risk_cat, "")

    print(f"\n{BORDER}")
    print(f"  RetainIQ Employee Profile  [BENCHMARK RESEARCH DEMO]")
    print(BORDER)
    print(f"  Employee # :        {int(e['EmployeeNumber'])}")
    print(f"  Department:         {e.get('Department', 'N/A')}")
    print(f"  Job Role:           {e.get('JobRole', 'N/A')}")
    print(f"  Job Level:          {int(e.get('JobLevel', 0))}")
    print(f"  Monthly Income:     ${e.get('MonthlyIncome', 0):,.0f}")
    print(f"  Annual Salary:      ${ann_sal:,.0f}")
    print(f"  Years at Company:   {e.get('YearsAtCompany', 'N/A')}")
    print(f"  OverTime:           {e.get('OverTime', 'N/A')}")
    print(f"  OOF Actual Label:   {'Yes (Left)' if actual else 'No (Stayed)'}")
    print(f"\n{BORDER}")
    print(f"  ATTRITION RISK ESTIMATE  (model output, not a guarantee)")
    print(BORDER)
    print(f"  Estimated Attrition Prob:  {prob:.3f}   {icon} {risk_cat} RISK")
    print(f"  Risk-Only Rank:            #{rank_risk} of 1,470")
    print()
    print(f"  COST SCENARIO (Researcher-assumed parameters)")
    print(f"  Replacement Cost (Sc.1):   ${rc_fixed:,.0f}   [FixedCost=$25k + 75% salary]")
    print(f"  Expected Replacement Loss: ${erl_fixed:,.0f}   [Scenario 1]")
    print(f"  ERL Seniority-scaled:      ${erl_sen:,.0f}   [Scenario 2]")
    print(f"  ERL Priority Rank:         #{rank_erl} of 1,470")
    print()
    print(f"  MODEL-ASSOCIATED FEATURES  (associations, NOT causes)")
    factors = _get_factors(int(e["EmployeeNumber"]))
    for line in factors.split(";"):
        line = line.strip()
        if line:
            print(f"    • {line}")
    p1, c1, p2, c2 = _get_rag(int(e["EmployeeNumber"]))
    if p1:
        print(f"\n  LITERATURE CONTEXT  (background only, not causal evidence)")
        print(f"  [{c1}]")
        print(f"    {p1}...")
        if p2:
            print(f"  [{c2}]")
            print(f"    {p2}...")
    print(f"\n  [!]  DISCLAIMER: Estimated probabilities and costs are model outputs")
    print(f"  under researcher-defined assumptions on a SYNTHETIC benchmark.")
    print(f"  This output must NOT be used to make real employment decisions.")
    print(BORDER)

def print_top_n(n: int = 20, strategy: str = "erl") -> None:
    col = "rank_risk_x_cost_fixed" if strategy == "erl" else "rank_risk_only"
    label = "Risk × Cost (Fixed+Salary)" if strategy == "erl" else "Risk-Only"
    sub = master.sort_values(col).head(n)

    print(f"\n{'=' * 70}")
    print(f"  TOP {n} EMPLOYEES BY {label.upper()}")
    print(f"  [BENCHMARK RESEARCH DEMO – NOT for real HR decisions]")
    print(f"{'=' * 70}")
    print(f"  {'Rank':<5} {'EmpNo':<8} {'Actual':<8} {'P(Att)':<8} "
          f"{'AnnSalary':<12} {'ERL($)':<12} {'Risk':<10} {'Dept':<20}")
    print(f"  {'-'*4} {'-'*7} {'-'*7} {'-'*7} {'-'*11} {'-'*11} {'-'*9} {'-'*19}")

    for _, row in sub.iterrows():
        actual_str = "[LEFT]" if row["Attrition"] == 1 else "[STAY]"
        prob       = row.get("calibrated_probability", 0)
        erl        = row.get("ERL_fixed_plus_salary", 0)
        ann        = row.get("AnnualSalary", row.get("MonthlyIncome", 0) * 12)
        rank       = int(row[col])
        dept       = str(row.get("Department", ""))[:18]
        risk       = risk_label(prob)
        print(f"  {rank:<5} {int(row['EmployeeNumber']):<8} {actual_str:<8} "
              f"{prob:<8.3f} ${ann:<11,.0f} ${erl:<11,.0f} {risk:<10} {dept:<20}")

    n_leavers = int(sub["Attrition"].sum())
    pct_leave  = n_leavers / n * 100
    total_erl  = sub["ERL_fixed_plus_salary"].sum()
    print(f"\n  Actual leavers in top {n}: {n_leavers}/{n} ({pct_leave:.0f}%)")
    print(f"  Total ERL in top {n}:       ${total_erl:,.0f}")
    print(f"\n  Note: Costs are researcher-assumed. Outcomes are realized OOF labels.")
    print("=" * 70)

def run_interactive() -> None:
    print("\n" + "=" * 70)
    print("  RetainIQ Interactive Demo")
    print("  IBM HR Analytics Benchmark — RESEARCH PROTOTYPE ONLY")
    print("=" * 70)
    print("  Commands:")
    print("    <EmployeeNumber>   – show employee card  (e.g. 1277)")
    print("    top [N]            – show top-N by ERL   (default 20)")
    print("    risk [N]           – show top-N by risk only")
    print("    quit / exit        – exit demo")
    print()

    while True:
        try:
            cmd = input("  RetainIQ> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Exiting demo.")
            break

        if not cmd:
            continue

        parts = cmd.split()
        token = parts[0].lower()

        if token in ("quit", "exit", "q"):
            print("  Exiting demo.")
            break

        elif token == "top":
            n = int(parts[1]) if len(parts) > 1 else 20
            print_top_n(n, strategy="erl")

        elif token == "risk":
            n = int(parts[1]) if len(parts) > 1 else 20
            print_top_n(n, strategy="risk")

        elif token.isdigit():
            print_employee_card(int(token))

        else:
            print("  Unknown command. Try: <EmployeeNumber>, top [N], risk [N], quit")

# ============================================================================
# PHASE 22 – CLI ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RetainIQ Demo Interface – RESEARCH PROTOTYPE ONLY"
    )
    parser.add_argument("--employee",    type=int,  help="Show card for one employee ID")
    parser.add_argument("--top",         type=int,  help="Show top-N employees by ERL")
    parser.add_argument("--risk",        type=int,  help="Show top-N employees by risk-only")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  RetainIQ — Final Model Demo")
    print(f"  Selected model: Logistic Regression (PR-AUC = 0.5983)")
    print(f"  Dataset: IBM HR Analytics (synthetic, 1,470 employees)")
    print(f"  Attrition rate: 16.1%  |  Random seed: 42")
    print("=" * 70)

    if args.employee:
        print_employee_card(args.employee)
    elif args.top:
        print_top_n(args.top, strategy="erl")
    elif args.risk:
        print_top_n(args.risk, strategy="risk")
    elif args.interactive:
        run_interactive()
    else:
        # Default: show top 20 by ERL + top employee card
        print_top_n(20, strategy="erl")
        print("\n[TIP] Run with --interactive for the full demo console.")
        print("[TIP] Run with --employee <ID> to inspect any employee.")
        print("[TIP] Run with --top <N> or --risk <N> for ranked lists.\n")
        print(f"\n{rc.DISCLAIMER}")
