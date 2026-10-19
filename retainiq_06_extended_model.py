"""
retainiq_06_extended_model.py
=============================
PHASE 23 - Productivity Index (PI)
PHASE 24 - Replacement Multiplier (RM)
PHASE 25 - Time-to-Productivity Gap Cost (PGC)
PHASE 26 - Knowledge Capital Loss (KCL)
PHASE 27 - Replacement Availability Score (RAS)
PHASE 28 - Extended Expected Replacement Loss (XERL)
PHASE 29 - Organizational Impact Score (OIS)
PHASE 30 - Department-Level Cascade Analysis
PHASE 31 - Research Gap Analysis & Paper Metrics

NEW RESEARCH CONTRIBUTIONS (fills gaps in existing literature):
---------------------------------------------------------------
1. Productivity-weighted replacement cost (vs salary-only in prior work)
2. Replacement Multiplier: formalized "how many new hires to replace one"
3. Time-to-Productivity Cost: onboarding deficit quantified from IBM features
4. Knowledge Capital Loss: tenure × performance × role complexity
5. Replacement Availability Score: talent scarcity by role rarity
6. Extended ERL integrating all five components into one unified metric
7. Organizational Impact Score: team-level cascade, not just individual cost

DISCLAIMER
----------
RetainIQ is a benchmark research prototype on the IBM HR Analytics SYNTHETIC
dataset. All metrics are researcher-defined hypothetical scenarios for research
sensitivity analysis. They must NOT be used for real employment decisions.
No causal relationships are implied.
"""
from __future__ import annotations

import sys, json, warnings
import os
os.environ["OMP_NUM_THREADS"] = "4"
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

sys.path.insert(0, str(Path(__file__).parent))
import retainiq_common as rc

print("\n" + "="*70)
print("PHASE 23-31  EXTENDED COST & ORGANIZATIONAL IMPACT MODEL")
print("="*70)
print("\nDISCLAIMER: All parameters below are RESEARCHER-DEFINED hypothetical")
print("scenarios on a SYNTHETIC benchmark. Not for real employment decisions.\n")

# ── Load base data ────────────────────────────────────────────────────────────
CSV  = rc.DATA_DIR / "WA_Fn-UseC_-HR-Employee-Attrition.csv"
OOF  = rc.OUT_DIR  / "baseline_oof_predictions.csv"
PRI  = rc.OUT_DIR  / "employee_priority.csv"

for p in [CSV, OOF]:
    if not p.exists():
        sys.exit(f"[ERROR] Missing: {p}. Run earlier phases first.")

raw = pd.read_csv(CSV)
raw["Attrition"] = raw["Attrition"].map({"Yes": 1, "No": 0})
oof = pd.read_csv(OOF)
pri = pd.read_csv(PRI) if PRI.exists() else pd.DataFrame()

df = raw.merge(oof[["EmployeeNumber","calibrated_probability"]], on="EmployeeNumber", how="left")
if not pri.empty:
    df = df.merge(pri[["EmployeeNumber","AnnualSalary",
                        "replacement_cost_fixed_plus_salary",
                        "ERL_fixed_plus_salary"]], on="EmployeeNumber", how="left")
else:
    df["AnnualSalary"] = df["MonthlyIncome"] * 12
    df["replacement_cost_fixed_plus_salary"] = 25000 + 0.75 * df["AnnualSalary"]
    df["ERL_fixed_plus_salary"] = df["calibrated_probability"] * df["replacement_cost_fixed_plus_salary"]

# ============================================================================
# PHASE 23 - PRODUCTIVITY INDEX
# ============================================================================
print("="*70)
print("PHASE 23 - PRODUCTIVITY INDEX (PI)")
print("="*70)
print("""
Research rationale: Existing attrition cost models use salary as a proxy for
employee value. This conflates compensation with productivity. A senior employee
earning the same as a junior may contribute 2-3x the organizational output. We
construct a composite Productivity Index from IBM HR features that are proxies
for individual contribution quality.

Formula (weighted composite, all components 0-1 normalized):
  PI = 0.30 * (PerformanceRating / 4)        -- rated output quality
     + 0.20 * (JobLevel / 5)                  -- organizational seniority
     + 0.20 * (JobInvolvement / 4)            -- engagement/initiative
     + 0.15 * min(YearsInCurrentRole / 10,1)  -- role mastery
     + 0.15 * (1 - min(YearsSincePromo/10,1)) -- recency of recognition

Limitation: No direct productivity measurement exists in the IBM dataset.
PI is a researcher-constructed proxy. Treat as a relative, not absolute, measure.
""")

eps = 1e-6
df["PI_performance"]  = df["PerformanceRating"] / 4.0
df["PI_level"]        = df["JobLevel"] / 5.0
df["PI_involvement"]  = df["JobInvolvement"] / 4.0
df["PI_mastery"]      = np.minimum(df["YearsInCurrentRole"] / 10.0, 1.0)
df["PI_promo"]        = 1.0 - np.minimum(df["YearsSinceLastPromotion"] / 10.0, 1.0)

df["ProductivityIndex"] = (
    0.30 * df["PI_performance"] +
    0.20 * df["PI_level"]       +
    0.20 * df["PI_involvement"] +
    0.15 * df["PI_mastery"]     +
    0.15 * df["PI_promo"]
)

print("Productivity Index (PI) distribution:")
print(df["ProductivityIndex"].describe().round(3))
print(f"High productivity (PI>=0.7): {(df['ProductivityIndex']>=0.7).sum()} employees")
print(f"Low  productivity (PI<=0.4): {(df['ProductivityIndex']<=0.4).sum()} employees")

# ============================================================================
# PHASE 24 - REPLACEMENT MULTIPLIER
# ============================================================================
print("\n" + "="*70)
print("PHASE 24 - REPLACEMENT MULTIPLIER (RM)")
print("="*70)
print("""
Research gap: Prior cost-of-turnover models (Boushey & Glynn 2012, SHRM 2017)
estimate total replacement cost as a fixed salary multiple. They do not model
how many new employees are required to collectively replace one departing
experienced employee. A junior hire cannot immediately replace a 15-year senior
engineer -- the organisation may need 1.5-2.5 FTEs to cover the same output.

Replacement Multiplier (RM) quantifies this: RM=2.0 means the organisation
needs ~2 new hires to collectively match the departing employee's contribution.

Formula (researcher-defined, based on seniority tier):
  Base RM from JobLevel:  JL1=1.0, JL2=1.25, JL3=1.5, JL4=2.0, JL5=2.5
  Tenure adjustment:      +0.1 per 5 years above 5-year threshold
  Performance adjustment: PerformanceRating=4 adds +0.3
  Capped at RM_max=3.0

Research note: These values are researcher-assumed. Empirical validation
requires longitudinal hiring and output data not available in the IBM dataset.
""")

BASE_RM = {1: 1.0, 2: 1.25, 3: 1.5, 4: 2.0, 5: 2.5}

def compute_rm(row):
    base = BASE_RM.get(int(row["JobLevel"]), 1.0)
    tenure_bonus = max(0, (row["TotalWorkingYears"] - 5) / 5) * 0.1
    perf_bonus   = 0.30 if row["PerformanceRating"] >= 4 else 0.0
    return min(3.0, base + tenure_bonus + perf_bonus)

df["ReplacementMultiplier"] = df.apply(compute_rm, axis=1)

print("Replacement Multiplier distribution:")
print(df["ReplacementMultiplier"].describe().round(3))
rm_dist = df["ReplacementMultiplier"].value_counts(bins=[0,1.1,1.4,1.75,2.25,3.1]).sort_index()
print("RM bands:\n", rm_dist)

# ============================================================================
# PHASE 25 - TIME-TO-PRODUCTIVITY GAP COST (PGC)
# ============================================================================
print("\n" + "="*70)
print("PHASE 25 - TIME-TO-PRODUCTIVITY GAP COST (PGC)")
print("="*70)
print("""
Research gap: Turnover cost models rarely quantify the duration of the
productivity deficit after a replacement is hired. A new employee operates
at reduced productivity until they reach full role proficiency. This creates
a time-valued cost that compounds with seniority.

Time-to-Productivity (TtP): Weeks until replacement reaches 80% of departing
employee's productivity. Based on JobLevel (proxy for role complexity):
  JL1: 12 weeks  JL2: 20 weeks  JL3: 32 weeks  JL4: 48 weeks  JL5: 64 weeks

Productivity Deficit Rate (PDR): Fraction of output lost during TtP.
We assume a linear ramp: average deficit = 40% during onboarding period.

PGC = (AnnualSalary * PI / 52) * TtP_weeks * PDR * RM

Interpretation: How much production value is permanently lost during the
gap between departure and full replacement productivity.
""")

TTP_WEEKS = {1: 12, 2: 20, 3: 32, 4: 48, 5: 64}
PDR = 0.40  # 40% average productivity deficit during onboarding

df["TtP_weeks"] = df["JobLevel"].map(TTP_WEEKS)
df["WeeklyProductionValue"] = (df["AnnualSalary"] * df["ProductivityIndex"]) / 52.0
df["ProductivityGapCost"]   = (df["WeeklyProductionValue"] * df["TtP_weeks"]
                                * PDR * df["ReplacementMultiplier"])

print("Time-to-Productivity Gap Cost (PGC) distribution:")
print(df["ProductivityGapCost"].describe().round(0))

# ============================================================================
# PHASE 26 - KNOWLEDGE CAPITAL LOSS (KCL)
# ============================================================================
print("\n" + "="*70)
print("PHASE 26 - KNOWLEDGE CAPITAL LOSS (KCL)")
print("="*70)
print("""
Research gap: Knowledge loss is consistently cited as a major hidden cost of
attrition (DeLong 2004, Beazley et al. 2002) but rarely quantified in
ML-based attrition cost models. Experienced employees accumulate institutional
knowledge -- client relationships, process understanding, mentorship capacity --
that cannot be transferred through documentation alone.

Knowledge Factor (KF) by years at company:
  <2 years:   0.05  (limited institutional ties)
  2-5 years:  0.15
  5-10 years: 0.30
  10-20 years:0.50
  >20 years:  0.70  (deep institutional capital)

KCL = AnnualSalary * KF * PI * JobLevel/5

Research limitation: The IBM dataset provides no direct knowledge metrics.
KF is a researcher-assumed proxy based on published HR literature estimates.
""")

def knowledge_factor(years):
    if years < 2:   return 0.05
    if years < 5:   return 0.15
    if years < 10:  return 0.30
    if years < 20:  return 0.50
    return 0.70

df["KnowledgeFactor"]      = df["YearsAtCompany"].apply(knowledge_factor)
df["KnowledgeCapitalLoss"] = (df["AnnualSalary"] * df["KnowledgeFactor"]
                               * df["ProductivityIndex"] * df["JobLevel"] / 5.0)

print("Knowledge Capital Loss (KCL) distribution:")
print(df["KnowledgeCapitalLoss"].describe().round(0))

# ============================================================================
# PHASE 27 - REPLACEMENT AVAILABILITY SCORE (RAS)
# ============================================================================
print("\n" + "="*70)
print("PHASE 27 - REPLACEMENT AVAILABILITY SCORE (RAS)")
print("="*70)
print("""
Research gap: Existing attrition cost models implicitly assume P(finding
equivalent replacement)=1.0. In practice, for specialised or senior roles,
equivalent talent is scarce. This creates a talent scarcity premium that
existing cost models miss entirely.

RAS = P(finding an equivalent-productivity replacement in the labour market)

Operationalisation (researcher-defined for IBM dataset):
  Base RAS from JobRole rarity within dataset:
    Roles with <3% representation: RAS_base=0.40  (scarce)
    Roles with 3-8%:               RAS_base=0.60  (moderate)
    Roles with >8%:                RAS_base=0.80  (common)
  
  Adjusted by JobLevel:
    JL5: -0.20  (senior -> harder to find exact equivalent)
    JL4: -0.10
    JL3: 0.00
    JL2: +0.05
    JL1: +0.10
  
  Adjusted by PerformanceRating:
    PR=4 (Excellent): -0.15 (top performers are rare)
    PR=3 (Good): 0.00
  
  Capped [0.20, 0.95]

Talent Scarcity Premium = (1 - RAS) * AnnualSalary * PI
""")

# Role rarity from data
role_pcts = (df["JobRole"].value_counts(normalize=True) * 100)

def ras_base(role):
    pct = role_pcts.get(role, 5.0)
    if pct < 3.0:  return 0.40
    if pct < 8.0:  return 0.60
    return 0.80

JL_RAS_ADJ = {1: 0.10, 2: 0.05, 3: 0.00, 4: -0.10, 5: -0.20}

def compute_ras(row):
    base = ras_base(row["JobRole"])
    jl_adj = JL_RAS_ADJ.get(int(row["JobLevel"]), 0.0)
    pr_adj = -0.15 if row["PerformanceRating"] >= 4 else 0.0
    return float(np.clip(base + jl_adj + pr_adj, 0.20, 0.95))

df["ReplacementAvailabilityScore"] = df.apply(compute_ras, axis=1)
df["TalentScarcityPremium"] = ((1 - df["ReplacementAvailabilityScore"])
                                * df["AnnualSalary"] * df["ProductivityIndex"])

print("RAS distribution:")
print(df["ReplacementAvailabilityScore"].describe().round(3))
print("\nTalent Scarcity Premium distribution:")
print(df["TalentScarcityPremium"].describe().round(0))

# ============================================================================
# PHASE 28 - EXTENDED ERL (XERL)
# ============================================================================
print("\n" + "="*70)
print("PHASE 28 - EXTENDED EXPECTED REPLACEMENT LOSS (XERL)")
print("="*70)
print("""
The Extended ERL integrates all five cost components into a unified metric
that addresses the four main gaps in prior work:

XERL = P(attrition) × [
    RecruitmentCost × RM              +  # base cost × replacement multiplier
    ProductivityGapCost (PGC)         +  # onboarding deficit × weeks
    KnowledgeCapitalLoss (KCL)        +  # institutional knowledge loss
    TalentScarcityPremium (TSP)          # cost premium for hard-to-fill roles
]

Compare with Original ERL = P(attrition) × RecruitmentCost

Research hypothesis (RQ6): XERL re-ranks a materially different Top-K set
from both Risk-Only and original ERL rankings, specifically elevating high-
tenure, high-performing, specialist-role employees over high-probability
but low-experience, common-role employees.
""")

df["XERL_components_sum"] = (
    df["replacement_cost_fixed_plus_salary"] * df["ReplacementMultiplier"] +
    df["ProductivityGapCost"] +
    df["KnowledgeCapitalLoss"] +
    df["TalentScarcityPremium"]
)
df["ExtendedERL"] = df["calibrated_probability"] * df["XERL_components_sum"]

# Ranks
df["rank_risk_only"]  = df["calibrated_probability"].rank(ascending=False, method="first").astype(int)
df["rank_erl_basic"]  = df["ERL_fixed_plus_salary"].rank(ascending=False, method="first").astype(int)
df["rank_xerl"]       = df["ExtendedERL"].rank(ascending=False, method="first").astype(int)

# Cost components breakdown
df["XERL_base_cost"] = df["replacement_cost_fixed_plus_salary"] * df["ReplacementMultiplier"]
df["XERL_pgc_share"] = df["ProductivityGapCost"]
df["XERL_kcl_share"] = df["KnowledgeCapitalLoss"]
df["XERL_tsp_share"] = df["TalentScarcityPremium"]

print("XERL distribution:")
print(df["ExtendedERL"].describe().round(0))
print("\nComponent means (for all employees):")
print(f"  Recruitment cost portion: ${df['XERL_base_cost'].mean():,.0f}")
print(f"  Productivity gap cost:    ${df['ProductivityGapCost'].mean():,.0f}")
print(f"  Knowledge capital loss:   ${df['KnowledgeCapitalLoss'].mean():,.0f}")
print(f"  Talent scarcity premium:  ${df['TalentScarcityPremium'].mean():,.0f}")
print(f"  XERL total mean:          ${df['ExtendedERL'].mean():,.0f}")
print(f"  Basic ERL total mean:     ${df['ERL_fixed_plus_salary'].mean():,.0f}")
print(f"  XERL uplift factor:       {df['ExtendedERL'].mean()/df['ERL_fixed_plus_salary'].mean():.2f}x")

# ── Ranking difference analysis ──────────────────────────────────────────────
from scipy.stats import spearmanr
r, _ = spearmanr(df["rank_erl_basic"], df["rank_xerl"])
top10_overlap = len(set(df.nsmallest(10,"rank_erl_basic")["EmployeeNumber"])
                    & set(df.nsmallest(10,"rank_xerl")["EmployeeNumber"]))
top25_overlap = len(set(df.nsmallest(25,"rank_erl_basic")["EmployeeNumber"])
                    & set(df.nsmallest(25,"rank_xerl")["EmployeeNumber"]))

print(f"\nRanking comparison (Basic ERL vs XERL):")
print(f"  Spearman r = {r:.4f}")
print(f"  Top-10 overlap: {top10_overlap}/10")
print(f"  Top-25 overlap: {top25_overlap}/25")

# ============================================================================
# PHASE 29 - ORGANIZATIONAL IMPACT SCORE (OIS)
# ============================================================================
print("\n" + "="*70)
print("PHASE 29 - ORGANIZATIONAL IMPACT SCORE (OIS)")
print("="*70)
print("""
Research gap: Individual-level attrition cost models treat each departure
independently. In practice, losing a senior employee creates cascade effects:
team productivity drops, remaining employees shoulder extra load (increasing
their own attrition risk), and knowledge transfer to multiple juniors is needed.

Organizational Impact Score (OIS) accounts for:
1. Individual XERL  
2. Team leadership premium (Manager/Director roles amplify team impact)
3. Department scarcity (smaller departments -> higher impact per leaver)
4. Cascade risk (high-tenure leavers increase manager workload)

OIS = ExtendedERL × TeamImpactMultiplier × DeptScarcityFactor

TeamImpactMultiplier:
  Manager/Director/VP/C-Level roles: 1.5-2.0x (team cascade effect)
  Other roles: 1.0x

DeptScarcityFactor = 1 + (1 - dept_relative_size)
  Smaller departments -> more impacted per leaver
""")

# Leadership roles
LEADERSHIP_ROLES = {
    "Manager": 1.5,
    "Manufacturing Director": 1.8,
    "Research Director": 1.8,
    "Healthcare Representative": 1.1,
    "Sales Executive": 1.0,
    "Human Resources": 1.2,
}

def leadership_mult(role):
    for k, v in LEADERSHIP_ROLES.items():
        if k.lower() in str(role).lower() and "director" in str(role).lower():
            return 1.8
        if k.lower() in str(role).lower() and "manager" in str(role).lower():
            return 1.5
    return 1.0

df["LeadershipMultiplier"] = df["JobRole"].apply(leadership_mult)

# Department scarcity
dept_sizes = df.groupby("Department")["EmployeeNumber"].count()
total = len(df)
dept_relative = (dept_sizes / total)
df["DeptRelativeSize"] = df["Department"].map(dept_relative)
df["DeptScarcityFactor"] = 1 + (1 - df["DeptRelativeSize"])

df["OrganizationalImpactScore"] = (df["ExtendedERL"]
                                    * df["LeadershipMultiplier"]
                                    * df["DeptScarcityFactor"])

print("Organizational Impact Score (OIS) distribution:")
print(df["OrganizationalImpactScore"].describe().round(0))

# ============================================================================
# PHASE 30 - DEPARTMENT-LEVEL CASCADE ANALYSIS
# ============================================================================
print("\n" + "="*70)
print("PHASE 30 - DEPARTMENT CASCADE ANALYSIS")
print("="*70)

dept_agg = df.groupby("Department").agg(
    total_employees   = ("EmployeeNumber","count"),
    actual_leavers    = ("Attrition","sum"),
    attrition_rate    = ("Attrition","mean"),
    mean_prob         = ("calibrated_probability","mean"),
    mean_pi           = ("ProductivityIndex","mean"),
    mean_rm           = ("ReplacementMultiplier","mean"),
    mean_ttp          = ("TtP_weeks","mean"),
    mean_ras          = ("ReplacementAvailabilityScore","mean"),
    total_erl_basic   = ("ERL_fixed_plus_salary","sum"),
    total_xerl        = ("ExtendedERL","sum"),
    total_ois         = ("OrganizationalImpactScore","sum"),
    mean_xerl         = ("ExtendedERL","mean"),
    expected_leavers  = ("calibrated_probability","sum"),
).reset_index()

dept_agg["xerl_uplift"] = dept_agg["total_xerl"] / dept_agg["total_erl_basic"].clip(lower=1)
dept_agg = dept_agg.sort_values("total_xerl", ascending=False)

print("\nDepartment-level cascade summary:")
print(dept_agg[["Department","total_employees","actual_leavers","attrition_rate",
                "mean_pi","mean_rm","mean_ras","total_erl_basic","total_xerl","xerl_uplift"]].to_string(index=False))

# ============================================================================
# PHASE 31 - RESEARCH GAP ANALYSIS & PAPER METRICS
# ============================================================================
print("\n" + "="*70)
print("PHASE 31 - RESEARCH GAP ANALYSIS")
print("="*70)

# Top-10 XERL vs Top-10 Basic ERL ranking difference
top10_xerl = df.nsmallest(10,"rank_xerl")[["EmployeeNumber","Attrition","calibrated_probability",
    "ProductivityIndex","ReplacementMultiplier","TtP_weeks","ReplacementAvailabilityScore",
    "ExtendedERL","rank_xerl","rank_erl_basic","rank_risk_only"]]
print("\nTop-10 by XERL (extended model):")
print(top10_xerl.to_string(index=False))

# Budget simulation using XERL
print("\nBudget experiment: XERL vs Basic ERL vs Risk-Only")
print("(Metric: realized leavers captured in top-K)")
for k in [10, 25, 50, 100]:
    top_risk  = set(df.nsmallest(k,"rank_risk_only")["EmployeeNumber"])
    top_erl   = set(df.nsmallest(k,"rank_erl_basic")["EmployeeNumber"])
    top_xerl  = set(df.nsmallest(k,"rank_xerl")["EmployeeNumber"])
    
    n_risk  = df[df["EmployeeNumber"].isin(top_risk)]["Attrition"].sum()
    n_erl   = df[df["EmployeeNumber"].isin(top_erl)]["Attrition"].sum()
    n_xerl  = df[df["EmployeeNumber"].isin(top_xerl)]["Attrition"].sum()
    
    xerl_cost = df[df["EmployeeNumber"].isin(top_xerl)]["ExtendedERL"].sum()
    risk_xerl_cost = df[df["EmployeeNumber"].isin(top_risk)]["ExtendedERL"].sum()
    
    print(f"  Top-{k:3d}  Risk-Only={n_risk:3.0f} leavers  "
          f"ERL-Basic={n_erl:3.0f} leavers  "
          f"XERL={n_xerl:3.0f} leavers  "
          f"XERL cost=${xerl_cost:,.0f}  Risk-XERL cost=${risk_xerl_cost:,.0f}")

# ── Save all outputs ──────────────────────────────────────────────────────────
SAVE_COLS = [
    "EmployeeNumber","Department","JobRole","JobLevel","TotalWorkingYears",
    "YearsAtCompany","YearsInCurrentRole","YearsSinceLastPromotion",
    "MonthlyIncome","AnnualSalary","PerformanceRating","JobInvolvement",
    "OverTime","Attrition","calibrated_probability",
    "ProductivityIndex","ReplacementMultiplier","TtP_weeks",
    "ReplacementAvailabilityScore","KnowledgeFactor",
    "ProductivityGapCost","KnowledgeCapitalLoss","TalentScarcityPremium",
    "XERL_base_cost","XERL_pgc_share","XERL_kcl_share","XERL_tsp_share",
    "ExtendedERL","OrganizationalImpactScore",
    "rank_risk_only","rank_erl_basic","rank_xerl",
    "LeadershipMultiplier","DeptScarcityFactor",
    "ERL_fixed_plus_salary","replacement_cost_fixed_plus_salary",
]
save_cols = [c for c in SAVE_COLS if c in df.columns]
df[save_cols].to_csv(rc.OUT_DIR / "extended_model.csv", index=False)
dept_agg.to_csv(rc.OUT_DIR / "department_cascade.csv", index=False)

# Research gap summary
gaps = {
    "gap1_productivity_weighted_erl": {
        "description": "Productivity-weighted ERL vs salary-only ERL",
        "xerl_uplift_mean": round(float(df["ExtendedERL"].mean() / df["ERL_fixed_plus_salary"].mean()), 3),
        "xerl_top10_overlap_with_basic_erl": int(top10_overlap),
    },
    "gap2_replacement_multiplier": {
        "description": "How many new hires needed to replace one leaver",
        "mean_rm": round(float(df["ReplacementMultiplier"].mean()), 3),
        "rm_gt_2_count": int((df["ReplacementMultiplier"]>=2.0).sum()),
        "rm_gt_2_pct": round(float((df["ReplacementMultiplier"]>=2.0).mean()*100), 1),
    },
    "gap3_time_to_productivity": {
        "description": "Onboarding productivity deficit cost",
        "mean_ttp_weeks": round(float(df["TtP_weeks"].mean()), 1),
        "mean_pgc": round(float(df["ProductivityGapCost"].mean()), 0),
    },
    "gap4_knowledge_capital_loss": {
        "description": "Institutional knowledge loss quantification",
        "mean_kcl": round(float(df["KnowledgeCapitalLoss"].mean()), 0),
        "high_knowledge_employees_gt10yr": int((df["YearsAtCompany"]>=10).sum()),
    },
    "gap5_replacement_availability": {
        "description": "P(finding equivalent replacement) by role/level",
        "mean_ras": round(float(df["ReplacementAvailabilityScore"].mean()), 3),
        "low_ras_lt04_count": int((df["ReplacementAvailabilityScore"]<=0.4).sum()),
    },
    "gap6_xerl_ranking_novelty": {
        "description": "XERL produces materially different rankings vs basic ERL",
        "spearman_r_xerl_vs_basic_erl": round(float(r), 4),
        "top10_overlap_xerl_vs_basic_erl": int(top10_overlap),
        "top25_overlap_xerl_vs_basic_erl": int(top25_overlap),
    },
}
with open(rc.OUT_DIR / "research_gaps.json", "w") as f:
    json.dump(gaps, f, indent=2)

print("\n[saved] extended_model.csv")
print("[saved] department_cascade.csv")
print("[saved] research_gaps.json")
print("\n" + "="*70)
print("EXTENDED MODEL COMPLETE")
print("="*70)
print(f"\nKey research findings for the paper:")
print(f"  XERL mean uplift vs basic ERL:  {df['ExtendedERL'].mean()/df['ERL_fixed_plus_salary'].mean():.2f}x")
print(f"  Mean Replacement Multiplier:    {df['ReplacementMultiplier'].mean():.2f}")
print(f"  Employees needing RM>=2.0:      {(df['ReplacementMultiplier']>=2.0).mean()*100:.1f}%")
print(f"  Mean Time-to-Productivity:      {df['TtP_weeks'].mean():.1f} weeks")
print(f"  Mean Productivity Gap Cost:     ${df['ProductivityGapCost'].mean():,.0f}")
print(f"  Mean Knowledge Capital Loss:    ${df['KnowledgeCapitalLoss'].mean():,.0f}")
print(f"  Mean Talent Scarcity Premium:   ${df['TalentScarcityPremium'].mean():,.0f}")
print(f"  XERL vs Basic ERL Spearman r:   {r:.4f}")
print(f"  Top-10 overlap (XERL vs ERL):   {top10_overlap}/10")
print(f"\n[NEXT] Run retainiq_webapp.py to generate the full web application.")
print(f"\nDISCLAIMER: All values are researcher-defined estimates on a SYNTHETIC")
print(f"benchmark. No causal claims are made. Not for real employment decisions.")
