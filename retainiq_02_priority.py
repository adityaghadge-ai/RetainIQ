"""
retainiq_02_priority.py
=======================
PHASE 10 – Generate Calibrated Probabilities
PHASE 11 – Generate Cost Scenarios
PHASE 12 – Calculate Expected Replacement Loss (ERL)
PHASE 13 – Create Rankings (Risk-only / Cost-only / Risk x Cost)
PHASE 14 – Capacity-Constrained Intervention Budget Experiments
PHASE 15 – Realized Outcomes vs Random Baseline
PHASE 16 – Ranking Stability / Sensitivity Analysis
PHASE 17 – Fairness Audit
PHASE 18 – Employee-Level Explanations
PHASE 19 – Figures

PREREQUISITES
-------------
retainiq_01_baseline.py must have been run first.
Required files:
  outputs/baseline_oof_predictions.csv
  outputs/final_model_metadata.json

DISCLAIMER
----------
RetainIQ is a benchmark research prototype on the IBM HR Analytics synthetic
dataset.  All probability, cost, and ranking estimates are model outputs under
researcher-defined assumptions.  NOT suitable for real employment decisions.
No causal relationships are implied.

Run:
    python retainiq_02_priority.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy.stats import spearmanr, kendalltau

sys.path.insert(0, str(Path(__file__).parent))
import retainiq_common as rc

rc.set_plot_style()

# ============================================================================
# LOAD PREREQUISITES
# ============================================================================
print("\n" + "=" * 70)
print("LOADING PREREQUISITES")
print("=" * 70)

CSV_PATH = rc.DATA_DIR / "WA_Fn-UseC_-HR-Employee-Attrition.csv"
OOF_PATH = rc.OUT_DIR / "baseline_oof_predictions.csv"
META_PATH = rc.OUT_DIR / "final_model_metadata.json"

for p in [CSV_PATH, OOF_PATH, META_PATH]:
    if not p.exists():
        sys.exit(f"\n[ERROR] Required file not found: {p}\n"
                 "Please run retainiq_01_baseline.py first.")

raw  = pd.read_csv(CSV_PATH)
oof  = pd.read_csv(OOF_PATH)
with open(META_PATH) as f:
    meta = json.load(f)

print(f"Original dataset:  {raw.shape}")
print(f"OOF predictions:   {oof.shape}")
print(f"Final model:       {meta['final_model']}")

# ============================================================================
# PHASE 10 – CALIBRATED PROBABILITIES
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 10 – CALIBRATED PROBABILITIES")
print("=" * 70)

# Merge OOF probability with original dataset on EmployeeNumber
raw_enc = raw.copy()
raw_enc[rc.TARGET_COL] = raw_enc[rc.TARGET_COL].map({"Yes": 1, "No": 0})

base = raw_enc.merge(
    oof[["EmployeeNumber", "calibrated_probability"]],
    on="EmployeeNumber",
    how="inner",
)
print(f"Merged dataframe shape: {base.shape}")
print(f"Calibrated probability – describe:\n"
      f"{base['calibrated_probability'].describe().round(4)}")

# Verify no NaN probabilities
nan_probs = base["calibrated_probability"].isna().sum()
print(f"NaN probabilities: {nan_probs}")
assert nan_probs == 0, "Missing OOF probabilities detected – re-run Phase 1."

# ============================================================================
# PHASE 11 – COST SCENARIOS
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 11 – COST SCENARIOS (Researcher Assumptions)")
print("=" * 70)

# Annual salary
base["AnnualSalary"] = rc.annual_salary(base["MonthlyIncome"])

# Scenario 1: Fixed + salary share (default params)
base["replacement_cost_fixed_plus_salary"] = rc.replacement_cost_fixed_salary(
    base["MonthlyIncome"],
    fixed_cost  = rc.DEFAULT_FIXED_COST,
    salary_share= rc.DEFAULT_SALARY_SHARE,
)

# Scenario 2: Seniority-scaled
base["replacement_cost_seniority_scaled"] = rc.replacement_cost_seniority(
    base["MonthlyIncome"],
    base["JobLevel"],
)

print("RESEARCHER ASSUMPTION NOTE:")
print(f"  Scenario 1: FixedCost={rc.DEFAULT_FIXED_COST:,}  "
      f"SalaryShare={rc.DEFAULT_SALARY_SHARE}")
print(f"  Scenario 2: SeniorityFactors={rc.SENIORITY_FACTORS}")
print(f"  These are hypothetical assumptions for research sensitivity analysis.")
print(f"  They are NOT empirical industry standards.")
print()
print(f"Replacement cost Scenario 1 – describe:\n"
      f"{base['replacement_cost_fixed_plus_salary'].describe().round(0)}")
print(f"\nReplacement cost Scenario 2 – describe:\n"
      f"{base['replacement_cost_seniority_scaled'].describe().round(0)}")

# ============================================================================
# PHASE 12 – EXPECTED REPLACEMENT LOSS (ERL)
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 12 – EXPECTED REPLACEMENT LOSS (ERL)")
print("=" * 70)

p = base["calibrated_probability"]
base["ERL_fixed_plus_salary"]     = p * base["replacement_cost_fixed_plus_salary"]
base["ERL_seniority_scaled"]      = p * base["replacement_cost_seniority_scaled"]
base["ERL_risk_only"]             = p                                  # proxy rank
base["ERL_cost_only"]             = base["replacement_cost_fixed_plus_salary"]

print("ERL_fixed_plus_salary – describe:")
print(base["ERL_fixed_plus_salary"].describe().round(0))

print("\nERL_seniority_scaled – describe:")
print(base["ERL_seniority_scaled"].describe().round(0))

# ── employee_priority.csv ──────────────────────────────────────────────────
priority_cols = [
    "EmployeeNumber", "Attrition", "calibrated_probability",
    "MonthlyIncome", "AnnualSalary", "JobLevel",
    "replacement_cost_fixed_plus_salary", "replacement_cost_seniority_scaled",
    "ERL_fixed_plus_salary", "ERL_seniority_scaled",
]
priority_df = base[priority_cols].copy()
priority_df.to_csv(rc.OUT_DIR / "employee_priority.csv", index=False)
print("\n[saved] employee_priority.csv")

# ── Risk vs Cost scatter figure ────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))
sc = ax.scatter(
    base["calibrated_probability"],
    base["ERL_fixed_plus_salary"] / 1_000,
    c=base["Attrition"],
    cmap="RdYlGn_r",
    alpha=0.55,
    s=30,
    edgecolors="none",
)
plt.colorbar(sc, ax=ax, label="Actual Attrition (1=Yes)")
ax.set_xlabel("Calibrated Attrition Probability")
ax.set_ylabel("ERL – Fixed+Salary Cost ($ thousands)")
ax.set_title("Risk vs Expected Replacement Loss\n(researcher-assumed cost parameters)",
             fontweight="bold")
plt.tight_layout()
plt.savefig(rc.FIG_DIR / "risk_vs_cost.png")
plt.close()
print("[figure] risk_vs_cost.png")

# ============================================================================
# PHASE 13 – CORE RANKINGS
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 13 – CORE RANKINGS")
print("=" * 70)

RANKINGS = {
    "risk_only":              "calibrated_probability",
    "cost_only":              "replacement_cost_fixed_plus_salary",
    "risk_x_cost_fixed":      "ERL_fixed_plus_salary",
    "risk_x_cost_seniority":  "ERL_seniority_scaled",
}

for name, sort_col in RANKINGS.items():
    base[f"rank_{name}"] = base[sort_col].rank(ascending=False, method="first").astype(int)
    print(f"  Ranking '{name}' – sorted by '{sort_col}'")

print("\nTop 10 by Risk x Cost (fixed+salary) ERL:")
top10_cols = ["EmployeeNumber", "Attrition", "calibrated_probability",
              "AnnualSalary", "JobLevel", "ERL_fixed_plus_salary",
              "rank_risk_x_cost_fixed"]
print(
    base.sort_values("rank_risk_x_cost_fixed")
        .head(10)[top10_cols]
        .to_string(index=False)
)

# ============================================================================
# PHASE 14 & 15 – BUDGET EXPERIMENTS + RANDOM BASELINE
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 14-15 – CAPACITY-CONSTRAINED BUDGET EXPERIMENTS")
print("=" * 70)

# Ground truth: actual leavers and their realized replacement costs
n_total_leavers       = base["Attrition"].sum()
total_realized_cost_1 = (base["Attrition"] * base["replacement_cost_fixed_plus_salary"]).sum()
total_realized_cost_2 = (base["Attrition"] * base["replacement_cost_seniority_scaled"]).sum()

print(f"Total actual leavers:          {int(n_total_leavers)}")
print(f"Total realized cost scenario1: ${total_realized_cost_1:,.0f}")
print(f"Total realized cost scenario2: ${total_realized_cost_2:,.0f}")

rng = np.random.default_rng(rc.RANDOM_STATE)
budget_rows = []

for budget in rc.BUDGETS:
    row = {"budget": budget}

    # ── Strategy results ───────────────────────────────────────────────────
    for strat, rank_col in [
        ("risk_only",           "rank_risk_only"),
        ("cost_only",           "rank_cost_only"),
        ("risk_x_cost_fixed",   "rank_risk_x_cost_fixed"),
        ("risk_x_cost_seniority","rank_risk_x_cost_seniority"),
    ]:
        selected = base[base[rank_col] <= budget]
        n_leavers_captured = selected["Attrition"].sum()
        cost_captured_1    = (selected["Attrition"] * selected["replacement_cost_fixed_plus_salary"]).sum()

        row[f"{strat}_leavers_captured"]      = int(n_leavers_captured)
        row[f"{strat}_pct_leavers_captured"]  = round(n_leavers_captured / n_total_leavers * 100, 1)
        row[f"{strat}_cost_captured"]         = round(cost_captured_1, 0)
        row[f"{strat}_pct_cost_captured"]     = round(cost_captured_1 / total_realized_cost_1 * 100, 1)

    # ── Random baseline (1000 repetitions) ────────────────────────────────
    rand_leavers = []
    rand_costs   = []
    for _ in range(rc.RANDOM_REPS):
        idx    = rng.choice(len(base), size=budget, replace=False)
        sel    = base.iloc[idx]
        rand_leavers.append(sel["Attrition"].sum())
        rand_costs.append(
            (sel["Attrition"] * sel["replacement_cost_fixed_plus_salary"]).sum()
        )
    row["random_mean_leavers_captured"] = round(np.mean(rand_leavers), 2)
    row["random_pct_leavers_captured"]  = round(np.mean(rand_leavers) / n_total_leavers * 100, 1)
    row["random_mean_cost_captured"]    = round(np.mean(rand_costs), 0)
    row["random_pct_cost_captured"]     = round(np.mean(rand_costs) / total_realized_cost_1 * 100, 1)

    budget_rows.append(row)
    print(f"\nBudget={budget}")
    for strat in ["risk_only", "cost_only", "risk_x_cost_fixed", "risk_x_cost_seniority"]:
        print(f"  {strat:<28} leavers={row[f'{strat}_leavers_captured']}  "
              f"({row[f'{strat}_pct_leavers_captured']:.1f}%)  "
              f"cost_captured=${row[f'{strat}_cost_captured']:,.0f}")
    print(f"  {'random_baseline':<28} leavers={row['random_mean_leavers_captured']:.1f}  "
          f"({row['random_pct_leavers_captured']:.1f}%)")

budget_df = pd.DataFrame(budget_rows)
budget_df.to_csv(rc.OUT_DIR / "budget_results.csv", index=False)
print("\n[saved] budget_results.csv")

# ── Budget curve figure – leavers captured ────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
strat_styles = {
    "risk_only":             ("#2196F3", "o-", "Risk-Only"),
    "cost_only":             ("#FF9800", "s-", "Cost-Only"),
    "risk_x_cost_fixed":     ("#4CAF50", "^-", "Risk x Cost (Fixed+Salary)"),
    "risk_x_cost_seniority": ("#9C27B0", "D-", "Risk x Cost (Seniority)"),
}
for strat, (col, mk, lbl) in strat_styles.items():
    ax.plot(budget_df["budget"],
            budget_df[f"{strat}_leavers_captured"],
            mk, color=col, lw=2, ms=7, label=lbl)
ax.plot(budget_df["budget"],
        budget_df["random_mean_leavers_captured"],
        "k--", lw=1.5, ms=5, label="Random Baseline (mean)")
ax.set_xlabel("Intervention Capacity (# employees)")
ax.set_ylabel("Actual Leavers Captured (OOF realized)")
ax.set_title("Budget Curve – Actual Leavers Captured\n"
             "(Realized Out-of-Fold Outcomes; researcher-assumed costs)",
             fontweight="bold")
ax.legend(loc="upper left", fontsize=9)
ax.set_xticks(rc.BUDGETS)
plt.tight_layout()
plt.savefig(rc.FIG_DIR / "budget_curve.png")
plt.close()
print("[figure] budget_curve.png")

# ── Budget cost curve – realized cost exposure ────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
for strat, (col, mk, lbl) in strat_styles.items():
    ax.plot(budget_df["budget"],
            budget_df[f"{strat}_cost_captured"] / 1_000,
            mk, color=col, lw=2, ms=7, label=lbl)
ax.plot(budget_df["budget"],
        budget_df["random_mean_cost_captured"] / 1_000,
        "k--", lw=1.5, ms=5, label="Random Baseline (mean)")
ax.set_xlabel("Intervention Capacity (# employees)")
ax.set_ylabel("Realized Replacement-Cost Exposure ($ thousands)\n"
              "[researcher-assumed cost parameters]")
ax.set_title("Budget Curve – Realized Cost Exposure Captured\n"
             "(Researcher-assumed cost; realized OOF outcomes)",
             fontweight="bold")
ax.legend(loc="upper left", fontsize=9)
ax.set_xticks(rc.BUDGETS)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}k"))
plt.tight_layout()
plt.savefig(rc.FIG_DIR / "budget_cost_curve.png")
plt.close()
print("[figure] budget_cost_curve.png")

# ============================================================================
# PHASE 16 – RANKING STABILITY / SENSITIVITY ANALYSIS
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 16 – RANKING STABILITY / SENSITIVITY ANALYSIS")
print("=" * 70)

sensitivity_rows = []
p_vec = base["calibrated_probability"].values

reference_rank = base["rank_risk_x_cost_fixed"].values

for fc in rc.FIXED_COST_GRID:
    for ss in rc.SALARY_SHARE_GRID:
        cost = rc.replacement_cost_fixed_salary(base["MonthlyIncome"], fc, ss)
        erl  = p_vec * cost.values
        rank_new = pd.Series(erl).rank(ascending=False, method="first").astype(int).values

        sp_r, _  = spearmanr(reference_rank, rank_new)
        kt_r, _  = kendalltau(reference_rank, rank_new)

        top10_overlap  = len(set(np.where(reference_rank <= 10)[0]) &
                             set(np.where(rank_new <= 10)[0]))
        top25_overlap  = len(set(np.where(reference_rank <= 25)[0]) &
                             set(np.where(rank_new <= 25)[0]))
        top50_overlap  = len(set(np.where(reference_rank <= 50)[0]) &
                             set(np.where(rank_new <= 50)[0]))
        top100_overlap = len(set(np.where(reference_rank <= 100)[0]) &
                             set(np.where(rank_new <= 100)[0]))

        sensitivity_rows.append({
            "fixed_cost":     fc,
            "salary_share":   ss,
            "spearman_r":     round(sp_r, 4),
            "kendall_tau":    round(kt_r, 4),
            "top10_overlap":  top10_overlap,
            "top25_overlap":  top25_overlap,
            "top50_overlap":  top50_overlap,
            "top100_overlap": top100_overlap,
            "note":           "researcher-assumed cost scenario",
        })

sens_df = pd.DataFrame(sensitivity_rows)
sens_df.to_csv(rc.OUT_DIR / "cost_sensitivity.csv", index=False)
sens_df.to_csv(rc.OUT_DIR / "ranking_stability.csv", index=False)
print("[saved] cost_sensitivity.csv + ranking_stability.csv")

print("\nSensitivity table (Spearman r vs reference fc=25k, ss=0.75):")
print(sens_df[["fixed_cost", "salary_share", "spearman_r",
               "top10_overlap", "top25_overlap"]].to_string(index=False))

# ── Ranking stability heatmap figure ─────────────────────────────────────
pivot = sens_df.pivot(index="fixed_cost", columns="salary_share", values="spearman_r")
fig, ax = plt.subplots(figsize=(7, 5))
sns.heatmap(
    pivot, annot=True, fmt=".3f", cmap="YlGn",
    linewidths=0.5, ax=ax, vmin=0.9, vmax=1.0
)
ax.set_title("Ranking Stability – Spearman r\n"
             "vs Reference (fc=25k, ss=0.75)\n"
             "[researcher-assumed cost parameters]",
             fontweight="bold")
ax.set_xlabel("Salary Share")
ax.set_ylabel("Fixed Cost ($)")
plt.tight_layout()
plt.savefig(rc.FIG_DIR / "ranking_stability.png")
plt.close()
print("[figure] ranking_stability.png")

# ============================================================================
# PHASE 17 – FAIRNESS AUDIT
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 17 – FAIRNESS AUDIT")
print("=" * 70)
print("NOTE: Age, Gender, MaritalStatus were EXCLUDED from model training.")
print("This audit is a POST-HOC DIAGNOSTIC, not a compliance statement.")
print("No legal claim is made.")

# Attach audit columns to base
# base is derived from raw_enc which already contains ALL raw columns,
# so Age/Gender/MaritalStatus are already present. We only need to merge
# them in if they're missing (e.g., if a future refactor strips them).
_audit_cols_needed = ["Age", "Gender", "MaritalStatus"]
_missing_audit     = [c for c in _audit_cols_needed if c not in base.columns]

if _missing_audit:
    audit_extra = raw[["EmployeeNumber"] + _missing_audit].copy()
    audit_base  = base.merge(audit_extra, on="EmployeeNumber", how="left")
else:
    audit_base = base.copy()

audit_base["AgeBand"] = rc.age_band(audit_base["Age"])


# Budget threshold for 'selected' = top 50
FAIRNESS_BUDGET = 50
audit_base["selected_top50"] = (audit_base["rank_risk_x_cost_fixed"] <= FAIRNESS_BUDGET).astype(int)

def audit_group(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    for grp, gdf in df.groupby(group_col, observed=True):
        n         = len(gdf)
        attrition_rate  = gdf["Attrition"].mean()
        pred_pos_rate   = (gdf["calibrated_probability"] >= 0.5).mean()
        mean_prob       = gdf["calibrated_probability"].mean()
        sel_rate        = gdf["selected_top50"].mean()
        actual_pos      = gdf["Attrition"]
        pred_pos        = (gdf["calibrated_probability"] >= 0.5).astype(int)
        tp  = ((pred_pos == 1) & (actual_pos == 1)).sum()
        fp  = ((pred_pos == 1) & (actual_pos == 0)).sum()
        fn  = ((pred_pos == 0) & (actual_pos == 1)).sum()
        tn  = ((pred_pos == 0) & (actual_pos == 0)).sum()
        tpr = tp / (tp + fn) if (tp + fn) > 0 else np.nan
        fpr = fp / (fp + tn) if (fp + tn) > 0 else np.nan
        rows.append({
            "group_col":         group_col,
            "group_value":       str(grp),
            "n":                 n,
            "actual_attrition_rate": round(attrition_rate, 4),
            "predicted_positive_rate": round(pred_pos_rate, 4),
            "mean_predicted_prob":     round(mean_prob, 4),
            "selection_rate_top50":    round(sel_rate, 4),
            "true_positive_rate":      round(tpr, 4) if not np.isnan(tpr) else None,
            "false_positive_rate":     round(fpr, 4) if not np.isnan(fpr) else None,
        })
    return pd.DataFrame(rows)

fairness_parts = []
for col in ["Gender", "MaritalStatus", "AgeBand"]:
    part = audit_group(audit_base, col)
    fairness_parts.append(part)
    print(f"\nFairness audit – {col}:")
    print(part.drop(columns="group_col").to_string(index=False))

fairness_df = pd.concat(fairness_parts, ignore_index=True)
fairness_df.to_csv(rc.OUT_DIR / "fairness_audit.csv", index=False)
print("\n[saved] fairness_audit.csv")

# ── Fairness audit figure ─────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax, group_col in zip(axes, ["Gender", "MaritalStatus", "AgeBand"]):
    sub = fairness_df[fairness_df["group_col"] == group_col].copy()
    x   = np.arange(len(sub))
    w   = 0.3
    ax.bar(x - w, sub["actual_attrition_rate"],      w, label="Actual Attrition Rate",  color="#F44336", alpha=0.8)
    ax.bar(x,     sub["predicted_positive_rate"],     w, label="Predicted Positive Rate",color="#2196F3", alpha=0.8)
    ax.bar(x + w, sub["selection_rate_top50"],        w, label="Selection Rate (Top 50)",color="#4CAF50", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(sub["group_value"], rotation=15, ha="right")
    ax.set_ylim(0, 0.5)
    ax.set_title(f"Fairness Audit – {group_col}", fontweight="bold")
    ax.set_ylabel("Rate")
    ax.legend(fontsize=7)

plt.suptitle("Fairness Audit – Post-Hoc Diagnostic\n"
             "(Demographics excluded from model training)",
             fontweight="bold")
plt.tight_layout()
plt.savefig(rc.FIG_DIR / "fairness_audit.png")
plt.close()
print("[figure] fairness_audit.png")

# ============================================================================
# PHASE 18 – EMPLOYEE-LEVEL EXPLANATIONS
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 18 – EMPLOYEE-LEVEL EXPLANATIONS")
print("=" * 70)
print("NOTE: Feature contributions are model associations, NOT causal explanations.")
print("Do NOT interpret as 'reasons the employee will leave'.")

TOP_N_EXPLAIN = 20
top_employees = base.sort_values("rank_risk_x_cost_fixed").head(TOP_N_EXPLAIN).copy()

# Use sign of deviation from mean as a simple directional indicator
# (Full SHAP explanations are available from Phase 1 if SHAP was installed)
feature_cols_for_exp = [
    "MonthlyIncome", "OverTime", "YearsAtCompany", "JobLevel",
    "TotalWorkingYears", "YearsSinceLastPromotion", "JobSatisfaction",
    "EnvironmentSatisfaction", "WorkLifeBalance", "NumCompaniesWorked",
]
feature_cols_for_exp = [c for c in feature_cols_for_exp if c in base.columns]
global_means = base[feature_cols_for_exp].apply(
    lambda col: col.map({"Yes": 1, "No": 0}).fillna(col)
    if col.dtype == object else col
).mean()

exp_rows = []
for _, row in top_employees.iterrows():
    top_factors = []
    for feat in feature_cols_for_exp:
        val = row.get(feat, np.nan)
        if pd.isna(val):
            continue
        # For 'OverTime' convert to numeric
        if feat == "OverTime":
            val_num  = 1 if str(val).strip().lower() == "yes" else 0
            mean_val = base["OverTime"].map({"Yes": 1, "No": 0}).mean()
        else:
            val_num  = float(val)
            mean_val = float(global_means[feat])
        direction = "above" if val_num > mean_val else "below"
        diff = abs(val_num - mean_val)
        top_factors.append((feat, direction, diff, val_num, mean_val))

    top_factors.sort(key=lambda x: x[2], reverse=True)
    top2 = top_factors[:2]
    factor_str = "; ".join(
        f"{f} = {v:.1f} ({d} dataset mean {m:.1f})"
        for f, d, _, v, m in top2
    )
    exp_rows.append({
        "EmployeeNumber":        int(row["EmployeeNumber"]),
        "actual_attrition":      int(row["Attrition"]),
        "calibrated_probability": round(row["calibrated_probability"], 4),
        "replacement_cost_$":    round(row["replacement_cost_fixed_plus_salary"], 0),
        "ERL_fixed_$":           round(row["ERL_fixed_plus_salary"], 0),
        "priority_rank":         int(row["rank_risk_x_cost_fixed"]),
        "model_associated_factors": factor_str,
        "disclaimer": (
            "Model-associated features only. "
            "This is NOT a causal explanation. "
            "Do NOT use for real employment decisions."
        ),
    })

exp_df = pd.DataFrame(exp_rows)
exp_df.to_csv(rc.OUT_DIR / "employee_explanations.csv", index=False)
print(f"[saved] employee_explanations.csv  ({len(exp_df)} employees)")
print("\nTop 10 employee explanations:")
print(exp_df.head(10)[
    ["EmployeeNumber", "actual_attrition", "calibrated_probability",
     "ERL_fixed_$", "priority_rank"]
].to_string(index=False))

# ============================================================================
# PRINT SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 2 PIPELINE COMPLETE – SUMMARY")
print("=" * 70)

print(f"\nTotal employees:       {len(base)}")
print(f"Total actual leavers:  {int(n_total_leavers)}  ({n_total_leavers/len(base):.1%})")
print(f"\nBudget experiment results:")
print(budget_df[[
    "budget",
    "risk_only_leavers_captured",
    "risk_x_cost_fixed_leavers_captured",
    "random_mean_leavers_captured"
]].to_string(index=False))

print(f"\nRanking stability (Spearman r, selected rows):")
print(sens_df[sens_df["fixed_cost"].isin([0, 25_000])][
    ["fixed_cost", "salary_share", "spearman_r", "top10_overlap", "top25_overlap"]
].to_string(index=False))

print("\nOutputs saved:")
for f in sorted(rc.OUT_DIR.glob("*")):
    print(f"  {f.name}")
print("\nFigures saved:")
for f in sorted(rc.FIG_DIR.glob("*.png")):
    print(f"  {f.name}")

print(f"\n[NEXT] Run retainiq_03_rag.py to generate the RAG-based literature "
      f"context layer and retention briefs.")
print(f"\n[DISCLAIMER] {rc.DISCLAIMER}")
