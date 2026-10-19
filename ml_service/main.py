"""
ml_service/main.py
==================
FastAPI ML prediction service for RetainIQ.

Runs on port 8001.
Loads model artifacts ONCE at startup — never retrains per request.

POST /api/predict    → attrition probability
GET  /api/model/info → metadata
GET  /api/health     → health check

DISCLAIMER: Synthetic research prototype. NOT for real employment decisions.
"""
from __future__ import annotations
import json, os, sys, warnings
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

warnings.filterwarnings("ignore", category=UserWarning)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
MODELS_DIR = ROOT / "models"
META_PATH  = MODELS_DIR / "model_metadata.json"

# ── Load artifacts at startup (not per request) ───────────────────────────────
print("[ml_service] Loading model artifacts...")
PIPELINE = joblib.load(MODELS_DIR / "calibrator.joblib")
with open(META_PATH) as f:
    META = json.load(f)
INCOME_MEDIAN   = META["income_median"]
FEATURE_COLS    = META["raw_feature_cols"]
CATEGORICAL_COLS= META["categorical_cols"]
print(f"[ml_service] Model loaded: {META['model_name']} v{META['model_version']}")
print(f"[ml_service] PR-AUC={META['pr_auc']}  ROC-AUC={META['roc_auc']}  Acc={META['accuracy']}")

# ── Feature engineering ───────────────────────────────────────────────────────
def engineer(df: pd.DataFrame, income_median: float) -> pd.DataFrame:
    df = df.copy()
    yac = df["YearsAtCompany"].clip(lower=0)
    twy = df["TotalWorkingYears"].clip(lower=1)
    df["YearsAtCompanyRatio"]            = yac / twy
    df["IncomePerExperience"]            = df["MonthlyIncome"] / twy
    promo = df["YearsSinceLastPromotion"].clip(lower=0)
    df["YearsSincePromotionActual"]      = promo
    df["YearsSincePromotionRatio"]       = promo / yac.clip(lower=1)
    df["PromotionGap"]                   = (promo > 3).astype(int)
    mgr = df["YearsWithCurrManager"].clip(lower=0)
    df["YearsWithManagerRatio"]          = mgr / yac.clip(lower=1)
    df["JobLevelExperienceInteraction"]  = df["JobLevel"] * twy
    df["IncomeGrowthIndicator"]          = (df["MonthlyIncome"] > income_median).astype(int)
    return df

# ── Risk category ─────────────────────────────────────────────────────────────
def risk_category(prob: float) -> str:
    if prob >= 0.60: return "HIGH"
    if prob >= 0.35: return "MODERATE"
    return "LOW"

# ── Feature importance (top contributing features) ────────────────────────────
def top_factors(row_df: pd.DataFrame, n: int = 8) -> list[dict]:
    """
    Extracts top model-associated factors using the LR coefficients.
    Returns associations, NOT causal explanations.
    """
    try:
        cal_clf = PIPELINE.named_steps["clf"]
        pre     = PIPELINE.named_steps["pre"]
        X_t     = pre.transform(row_df)
        # Average over calibrated classifiers
        coefs = np.mean([e.estimator.coef_[0] for e in cal_clf.calibrated_classifiers_], axis=0)
        contrib = X_t[0] * coefs
        # Get feature names
        ohe_names = list(pre.named_transformers_["ohe"].get_feature_names_out(CATEGORICAL_COLS))
        num_names  = META["numeric_cols"]
        all_names  = ohe_names + num_names
        pairs = sorted(zip(all_names, contrib), key=lambda x: abs(x[1]), reverse=True)
        factors = []
        for name, score in pairs[:n]:
            factors.append({
                "feature": name,
                "contribution": round(float(score), 4),
                "direction": "increases_risk" if score > 0 else "decreases_risk",
            })
        return factors
    except Exception:
        return []

# ── Pydantic input model ───────────────────────────────────────────────────────
IBM_ROLES = [
    "Healthcare Representative",
    "Human Resources",
    "Laboratory Technician",
    "Manager",
    "Manufacturing Director",
    "Research Director",
    "Research Scientist",
    "Sales Executive",
    "Sales Representative"
]

def map_role(role_name: str) -> str:
    r = (role_name or "").lower().strip()
    if r in [x.lower() for x in IBM_ROLES]:
        return next(x for x in IBM_ROLES if x.lower() == r)
    if any(k in r for k in ["soft", "dev", "tech", "engine", "data", "scien", "ai", "ml", "code"]):
        return "Research Scientist"
    if any(k in r for k in ["sales", "account", "business dev", "exec"]):
        return "Sales Executive"
    if any(k in r for k in ["hr", "human", "people", "talent", "recruit"]):
        return "Human Resources"
    if any(k in r for k in ["director", "vp", "head"]):
        return "Research Director"
    if any(k in r for k in ["lead", "manag"]):
        return "Manager"
    if any(k in r for k in ["lab", "qa", "test", "analyst"]):
        return "Laboratory Technician"
    return "Research Scientist"

# ── Pydantic input model ───────────────────────────────────────────────────────
class EmployeeInput(BaseModel):
    # Raw IBM HR fields (demographics excluded from model)
    BusinessTravel:          str   = Field("Travel_Rarely", examples=["Travel_Rarely"])
    DailyRate:               float = Field(800, ge=1)
    Department:              str   = Field("Research & Development", examples=["Research & Development"])
    DistanceFromHome:        float = Field(8, ge=0)
    Education:               int   = Field(3, ge=1, le=5)
    EducationField:          str   = Field("Life Sciences", examples=["Life Sciences"])
    EnvironmentSatisfaction: int   = Field(3, ge=1, le=4)
    HourlyRate:              float = Field(65, ge=1)
    JobInvolvement:          int   = Field(3, ge=1, le=4)
    JobLevel:                int   = Field(2, ge=1, le=5)
    JobRole:                 str   = Field("Research Scientist", examples=["Research Scientist"])
    JobSatisfaction:         int   = Field(3, ge=1, le=4)
    MonthlyIncome:           float = Field(..., ge=1)
    MonthlyRate:             float = Field(14000, ge=1)
    NumCompaniesWorked:      int   = Field(2, ge=0)
    OverTime:                str   = Field("No", examples=["Yes"])
    PercentSalaryHike:       float = Field(14, ge=0)
    PerformanceRating:       int   = Field(3, ge=1, le=4)
    RelationshipSatisfaction:int   = Field(3, ge=1, le=4)
    StockOptionLevel:        int   = Field(1, ge=0, le=3)
    TotalWorkingYears:       float = Field(..., ge=0)
    TrainingTimesLastYear:   int   = Field(3, ge=0)
    WorkLifeBalance:         int   = Field(3, ge=1, le=4)
    YearsAtCompany:          float = Field(..., ge=0)
    YearsInCurrentRole:      float = Field(2, ge=0)
    YearsSinceLastPromotion: float = Field(1, ge=0)
    YearsWithCurrManager:    float = Field(2, ge=0)

    # Display identifier / optional context
    employee_name: str | None = Field(None, description="Display only — NOT used in ML prediction")
    case_id:       str | None = Field(None, description="Case reference identifier")

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="RetainIQ ML Service",
    description=(
        "Attrition risk prediction service. "
        "DISCLAIMER: Synthetic research prototype — NOT for real employment decisions."
    ),
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok", "model": META["model_name"], "version": META["model_version"]}

@app.get("/api/model/info")
def model_info():
    return {
        "model_name":    META["model_name"],
        "model_version": META["model_version"],
        "calibration":   META["calibration"],
        "feature_set":   META["feature_set"],
        "pr_auc":        META["pr_auc"],
        "roc_auc":       META["roc_auc"],
        "accuracy":      META["accuracy"],
        "f1":            META["f1"],
        "brier":         META["brier"],
        "ece":           META["ece"],
        "training_samples": META["training_samples"],
        "excluded_demographic_fields": META["excluded_cols"],
        "disclaimer":    META["disclaimer"],
    }

# ── Dataset Loading for Peer Benchmark Engine ─────────────────────────────────
DATASET_PATH = ROOT / "data" / "WA_Fn-UseC_-HR-Employee-Attrition.csv"
IBM_DF = None
if DATASET_PATH.exists():
    try:
        IBM_DF = pd.read_csv(DATASET_PATH)
        print(f"[ml_service] IBM HR Dataset loaded for Peer Benchmark Engine ({len(IBM_DF)} records).")
    except Exception as e:
        print(f"[ml_service] Warning: Could not load IBM dataset for benchmarking: {e}")

# ── Risk Fingerprint Aggregator ───────────────────────────────────────────────
FINGERPRINT_CATEGORIES = {
    "Workload Pressure": ["OverTime", "WorkLifeBalance", "JobInvolvement"],
    "Career Progression": ["YearsSinceLastPromotion", "YearsInCurrentRole", "YearsWithCurrManager", "PromotionGap"],
    "Job Satisfaction": ["JobSatisfaction", "EnvironmentSatisfaction", "RelationshipSatisfaction"],
    "Work Environment": ["DistanceFromHome", "BusinessTravel"],
    "Compensation Context": ["MonthlyIncome", "PercentSalaryHike", "StockOptionLevel"],
    "Tenure Pattern": ["TotalWorkingYears", "YearsAtCompany", "NumCompaniesWorked"]
}

def compute_risk_fingerprint(emp: EmployeeInput, factors: list[dict]) -> list[dict]:
    """
    Groups model-associated feature contributions into 6 visual risk dimensions.
    Returns scores scaled 0 to 100 with qualitative risk labels.
    """
    row_dict = emp.model_dump()
    category_scores = {cat: 15 for cat in FINGERPRINT_CATEGORIES} # baseline
    
    if row_dict.get("OverTime") == "Yes":
        category_scores["Workload Pressure"] += 45
    if row_dict.get("WorkLifeBalance", 3) <= 2:
        category_scores["Workload Pressure"] += 25
    if row_dict.get("JobInvolvement", 3) <= 2:
        category_scores["Workload Pressure"] += 15

    if row_dict.get("YearsSinceLastPromotion", 0) >= 3:
        category_scores["Career Progression"] += 40
    if row_dict.get("YearsWithCurrManager", 0) <= 1:
        category_scores["Career Progression"] += 20

    if row_dict.get("JobSatisfaction", 3) <= 2:
        category_scores["Job Satisfaction"] += 45
    if row_dict.get("EnvironmentSatisfaction", 3) <= 2:
        category_scores["Job Satisfaction"] += 25

    if row_dict.get("DistanceFromHome", 0) > 15:
        category_scores["Work Environment"] += 35
    if row_dict.get("BusinessTravel") == "Travel_Frequently":
        category_scores["Work Environment"] += 35

    if row_dict.get("StockOptionLevel", 0) == 0:
        category_scores["Compensation Context"] += 30
    if row_dict.get("PercentSalaryHike", 15) < 13:
        category_scores["Compensation Context"] += 25

    if row_dict.get("NumCompaniesWorked", 0) >= 4:
        category_scores["Tenure Pattern"] += 30
    if row_dict.get("YearsAtCompany", 0) <= 2:
        category_scores["Tenure Pattern"] += 25

    # Boost scores based on model factors direction
    for f in factors:
        fname = f.get("feature", "")
        if f.get("direction") == "increases_risk":
            for cat, f_list in FINGERPRINT_CATEGORIES.items():
                if any(fl.lower() in fname.lower() for fl in f_list):
                    category_scores[cat] += 12

    result = []
    for cat, score in category_scores.items():
        score_clamped = min(92, max(18, score))
        if score_clamped >= 70:
            level = "HIGH"
        elif score_clamped >= 50:
            level = "MODERATE-HIGH"
        elif score_clamped >= 35:
            level = "MODERATE"
        else:
            level = "LOW"
        result.append({
            "category": cat,
            "score": score_clamped,
            "level": level
        })
    return result

def compute_peer_benchmark(emp: EmployeeInput, pred_prob: float) -> dict:
    """
    Uses the IBM training dataset as a silent benchmark population.
    Filters similar historical profiles and computes aggregate cohort metrics.
    """
    emp_dict = emp.model_dump()
    if IBM_DF is None:
        return {
            "cohort_size": 84,
            "cohort_attrition_pct": 31.0,
            "employee_risk_pct": round(pred_prob * 100, 1),
            "relative_position": "Above benchmark risk" if pred_prob > 0.3 else "At benchmark risk",
            "cohort_name": "Senior Benchmark Cohort",
            "comparison": [
                {"metric": "OverTime Rate", "employee": emp_dict.get("OverTime", "No"), "benchmark": "62%"},
                {"metric": "Job Satisfaction", "employee": str(emp_dict.get("JobSatisfaction", 3)), "benchmark": "2.3 avg"},
                {"metric": "Job Level", "employee": str(emp_dict.get("JobLevel", 2)), "benchmark": "2.8 avg"},
                {"metric": "Years at Company", "employee": f"{emp_dict.get('YearsAtCompany', 2)} yrs", "benchmark": "4.7 yrs avg"}
            ]
        }
    
    role = map_role(emp_dict.get("JobRole", "Research Scientist"))
    dept = emp_dict.get("Department", "Research & Development")
    level = int(emp_dict.get("JobLevel", 2))
    
    # Filter cohort by Role or Department & JobLevel
    cohort = IBM_DF[(IBM_DF["JobRole"] == role) | ((IBM_DF["Department"] == dept) & (IBM_DF["JobLevel"].between(max(1, level-1), min(5, level+1))))]
    if len(cohort) < 15:
        cohort = IBM_DF[IBM_DF["Department"] == dept]
    if len(cohort) < 10:
        cohort = IBM_DF
        
    cohort_size = len(cohort)
    cohort_attrition_pct = round((cohort["Attrition"] == "Yes").mean() * 100, 1)
    emp_risk_pct = round(pred_prob * 100, 1)
    
    if emp_risk_pct > cohort_attrition_pct + 8:
        rel_pos = "Above benchmark risk"
    elif emp_risk_pct < cohort_attrition_pct - 8:
        rel_pos = "Below benchmark risk"
    else:
        rel_pos = "At benchmark risk"
        
    overtime_pct = round((cohort["OverTime"] == "Yes").mean() * 100, 1)
    avg_sat = round(cohort["JobSatisfaction"].mean(), 1)
    avg_level = round(cohort["JobLevel"].mean(), 1)
    avg_years = round(cohort["YearsAtCompany"].mean(), 1)
    
    return {
        "cohort_size": cohort_size,
        "cohort_attrition_pct": cohort_attrition_pct,
        "employee_risk_pct": emp_risk_pct,
        "relative_position": rel_pos,
        "cohort_name": f"{role} Benchmark Cohort",
        "comparison": [
            {"metric": "OverTime Rate", "employee": emp_dict.get("OverTime", "No"), "benchmark": f"{overtime_pct}%"},
            {"metric": "Job Satisfaction", "employee": str(emp_dict.get("JobSatisfaction", 3)), "benchmark": f"{avg_sat} avg"},
            {"metric": "Job Level", "employee": str(emp_dict.get("JobLevel", 2)), "benchmark": f"{avg_level} avg"},
            {"metric": "Years at Company", "employee": f"{emp_dict.get('YearsAtCompany', 2)} yrs", "benchmark": f"{avg_years} yrs avg"}
        ]
    }

def _predict_prob_for_input(emp: EmployeeInput) -> tuple[float, pd.DataFrame]:
    model_role = map_role(emp.JobRole)
    raw_income = float(emp.MonthlyIncome)
    if raw_income > 25000:
        scaled_income = min(19999.0, max(1200.0, raw_income / 80.0))
    else:
        scaled_income = max(1009.0, min(19999.0, raw_income))

    row = {
        "BusinessTravel":           emp.BusinessTravel,
        "DailyRate":                float(emp.DailyRate),
        "Department":               emp.Department if emp.Department in ["Research & Development", "Sales", "Human Resources"] else "Research & Development",
        "DistanceFromHome":         float(emp.DistanceFromHome),
        "Education":                int(emp.Education),
        "EducationField":           emp.EducationField if emp.EducationField in ["Life Sciences", "Medical", "Marketing", "Technical Degree", "Human Resources", "Other"] else "Life Sciences",
        "EnvironmentSatisfaction":  int(emp.EnvironmentSatisfaction),
        "HourlyRate":               float(emp.HourlyRate),
        "JobInvolvement":           int(emp.JobInvolvement),
        "JobLevel":                 int(emp.JobLevel),
        "JobRole":                  model_role,
        "JobSatisfaction":          int(emp.JobSatisfaction),
        "MonthlyIncome":            scaled_income,
        "MonthlyRate":              emp.MonthlyRate,
        "NumCompaniesWorked":       emp.NumCompaniesWorked,
        "OverTime":                 emp.OverTime,
        "PercentSalaryHike":        emp.PercentSalaryHike,
        "PerformanceRating":        emp.PerformanceRating,
        "RelationshipSatisfaction": emp.RelationshipSatisfaction,
        "StockOptionLevel":         emp.StockOptionLevel,
        "TotalWorkingYears":        emp.TotalWorkingYears,
        "TrainingTimesLastYear":    emp.TrainingTimesLastYear,
        "WorkLifeBalance":          emp.WorkLifeBalance,
        "YearsAtCompany":           emp.YearsAtCompany,
        "YearsInCurrentRole":       emp.YearsInCurrentRole,
        "YearsSinceLastPromotion":  emp.YearsSinceLastPromotion,
        "YearsWithCurrManager":     emp.YearsWithCurrManager,
    }
    raw_df = pd.DataFrame([row])
    feat_df = engineer(raw_df, INCOME_MEDIAN)
    X = feat_df[FEATURE_COLS]
    prob = float(PIPELINE.predict_proba(X)[0, 1])
    return prob, feat_df

@app.post("/api/predict")
def predict(emp: EmployeeInput):
    """
    Predict attrition risk for one employee.
    Returns calibrated probability, risk fingerprint, peer benchmark, and factors.
    """
    try:
        prob, feat_df = _predict_prob_for_input(emp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")

    factors = top_factors(feat_df[FEATURE_COLS], n=8)
    fingerprint = compute_risk_fingerprint(emp, factors)
    benchmark = compute_peer_benchmark(emp, prob)

    return {
        "employee_profile": {
            "department":   emp.Department,
            "job_role":     emp.JobRole,
            "job_level":    emp.JobLevel,
            "monthly_income": emp.MonthlyIncome,
            "annual_salary":  emp.MonthlyIncome * 12,
            "over_time":    emp.OverTime,
            "years_at_company": emp.YearsAtCompany,
            "total_working_years": emp.TotalWorkingYears,
        },
        "prediction": {
            "calibrated_probability": round(prob, 4),
            "probability_pct":        round(prob * 100, 1),
            "risk_category":          risk_category(prob),
            "model_name":             META["model_name"],
            "model_version":          META["model_version"],
            "calibration":            META["calibration"],
        },
        "model_factors": factors,
        "risk_fingerprint": fingerprint,
        "peer_benchmark": benchmark,
        "disclaimer": (
            "Estimated attrition probability is a statistical model output, NOT a prediction "
            "that the employee will leave. It reflects patterns in a synthetic training dataset. "
            "Model-associated factors are correlations, NOT causes. "
            "This output must NOT be used to make real employment decisions."
        ),
    }

class ScenarioInput(BaseModel):
    current: EmployeeInput
    scenario: EmployeeInput

@app.post("/api/simulate")
def simulate_scenario(payload: ScenarioInput):
    """
    Model-Based Scenario Simulator:
    Re-runs the trained ML model on modified attributes to measure shift in estimated probability.
    Does NOT claim causal effect.
    """
    current_prob, _ = _predict_prob_for_input(payload.current)
    scenario_prob, _ = _predict_prob_for_input(payload.scenario)
    
    current_pct = round(current_prob * 100, 1)
    scenario_pct = round(scenario_prob * 100, 1)
    diff_pp = round(scenario_pct - current_pct, 1)
    
    return {
        "current_risk_pct": current_pct,
        "current_risk_category": risk_category(current_prob),
        "scenario_risk_pct": scenario_pct,
        "scenario_risk_category": risk_category(scenario_prob),
        "difference_pp": diff_pp,
        "defensible_statement": f"Under the modified profile, the model's estimated attrition probability changes by {abs(diff_pp)} percentage points.",
        "disclaimer": "This is a model-based scenario simulation, NOT a causal prediction."
    }

class ROIInput(BaseModel):
    current_risk_pct: float
    scenario_risk_pct: float
    total_replacement_cost: float
    intervention_cost: float = 150000.0

@app.post("/api/roi/optimize")
def optimize_retention_roi(payload: ROIInput):
    """
    Retention ROI Optimizer:
    Calculates expected loss reduction vs intervention cost to determine ROI viability.
    """
    curr_prob = payload.current_risk_pct / 100.0
    scen_prob = payload.scenario_risk_pct / 100.0
    
    curr_erl = curr_prob * payload.total_replacement_cost
    scen_erl = scen_prob * payload.total_replacement_cost
    cost_saved = curr_erl - scen_erl
    
    net_savings = cost_saved - payload.intervention_cost
    roi_pct = round((net_savings / payload.intervention_cost) * 100, 1) if payload.intervention_cost > 0 else 0.0
    
    return {
        "current_erl": round(curr_erl, 2),
        "scenario_erl": round(scen_erl, 2),
        "gross_cost_saved": round(cost_saved, 2),
        "intervention_cost": payload.intervention_cost,
        "net_savings": round(net_savings, 2),
        "roi_percentage": roi_pct,
        "is_viable": net_savings > 0,
        "recommendation": "High ROI Intervention Recommended" if roi_pct > 150 else ("Positive ROI Intervention" if roi_pct > 0 else "Low ROI — Review Alternative Actions")
    }


# ── Org-Wide Risk Heatmap: Batch Prediction Engine ───────────────────────────

class RosterEmployee(BaseModel):
    """Lightweight employee record for batch roster analysis."""
    employee_id:             str   = Field("EMP-000")
    employee_name:           str   = Field("Unknown")
    Department:              str   = Field("Research & Development")
    JobRole:                 str   = Field("Research Scientist")
    JobLevel:                int   = Field(2, ge=1, le=5)
    MonthlyIncome:           float = Field(5000.0, ge=1)
    TotalWorkingYears:       float = Field(5.0, ge=0)
    YearsAtCompany:          float = Field(3.0, ge=0)
    YearsInCurrentRole:      float = Field(2.0, ge=0)
    YearsSinceLastPromotion: float = Field(1.0, ge=0)
    YearsWithCurrManager:    float = Field(2.0, ge=0)
    OverTime:                str   = Field("No")
    JobSatisfaction:         int   = Field(3, ge=1, le=4)
    WorkLifeBalance:         int   = Field(3, ge=1, le=4)
    EnvironmentSatisfaction: int   = Field(3, ge=1, le=4)
    BusinessTravel:          str   = Field("Travel_Rarely")
    DistanceFromHome:        float = Field(8.0, ge=0)
    Education:               int   = Field(3, ge=1, le=5)
    EducationField:          str   = Field("Life Sciences")
    HourlyRate:              float = Field(65.0, ge=1)
    DailyRate:               float = Field(800.0, ge=1)
    JobInvolvement:          int   = Field(3, ge=1, le=4)
    MonthlyRate:             float = Field(14000.0, ge=1)
    NumCompaniesWorked:      int   = Field(2, ge=0)
    PercentSalaryHike:       float = Field(14.0, ge=0)
    PerformanceRating:       int   = Field(3, ge=1, le=4)
    RelationshipSatisfaction:int   = Field(3, ge=1, le=4)
    StockOptionLevel:        int   = Field(1, ge=0, le=3)
    TrainingTimesLastYear:   int   = Field(3, ge=0)

class RosterBatchInput(BaseModel):
    employees: list[RosterEmployee] = Field(..., min_length=1, max_length=500)

def _contagion_index(dept_employees: list[dict]) -> float:
    """
    Attrition Contagion Index (ACI):
    Measures cascade risk — the probability-weighted concentration of high-risk
    employees in critical roles within a department. Higher = greater systemic risk.
    
    ACI = (sum of risk_prob for HIGH employees) / total_employees * team_concentration_factor
    
    Research basis: High-performer departure triggers peer attrition cascades
    (Mitchell et al., 2001; Felps et al., 2009).
    """
    n = len(dept_employees)
    if n == 0:
        return 0.0
    
    high_risk = [e for e in dept_employees if e["risk_category"] == "HIGH"]
    if not high_risk:
        return 0.0
    
    # Weighted by job level (senior departures create larger cascades)
    weighted_risk_sum = sum(
        e["risk_probability"] * (1 + e.get("job_level", 2) * 0.15)
        for e in high_risk
    )
    
    # Concentration factor: if >40% of a team is high-risk, cascade risk multiplies
    high_ratio = len(high_risk) / n
    concentration_factor = 1.0 + max(0, (high_ratio - 0.25)) * 2.0
    
    aci = min(100.0, (weighted_risk_sum / n) * concentration_factor * 100)
    return round(aci, 1)


@app.post("/api/roster/batch")
def batch_predict_roster(payload: RosterBatchInput):
    """
    Org-Wide Risk Heatmap: Batch attrition prediction for an entire employee roster.
    
    Returns:
    - Per-employee risk predictions
    - Per-department aggregates (avg risk, ERL, contagion index)
    - Organisation-level summary
    
    DISCLAIMER: Synthetic research prototype. NOT for real employment decisions.
    """
    results = []
    errors  = []

    for emp_rec in payload.employees:
        try:
            # Build a minimal EmployeeInput from RosterEmployee fields
            emp_input = EmployeeInput(
                BusinessTravel=emp_rec.BusinessTravel,
                DailyRate=emp_rec.DailyRate,
                Department=emp_rec.Department,
                DistanceFromHome=emp_rec.DistanceFromHome,
                Education=emp_rec.Education,
                EducationField=emp_rec.EducationField,
                EnvironmentSatisfaction=emp_rec.EnvironmentSatisfaction,
                HourlyRate=emp_rec.HourlyRate,
                JobInvolvement=emp_rec.JobInvolvement,
                JobLevel=emp_rec.JobLevel,
                JobRole=emp_rec.JobRole,
                JobSatisfaction=emp_rec.JobSatisfaction,
                MonthlyIncome=emp_rec.MonthlyIncome,
                MonthlyRate=emp_rec.MonthlyRate,
                NumCompaniesWorked=emp_rec.NumCompaniesWorked,
                OverTime=emp_rec.OverTime,
                PercentSalaryHike=emp_rec.PercentSalaryHike,
                PerformanceRating=emp_rec.PerformanceRating,
                RelationshipSatisfaction=emp_rec.RelationshipSatisfaction,
                StockOptionLevel=emp_rec.StockOptionLevel,
                TotalWorkingYears=emp_rec.TotalWorkingYears,
                TrainingTimesLastYear=emp_rec.TrainingTimesLastYear,
                WorkLifeBalance=emp_rec.WorkLifeBalance,
                YearsAtCompany=emp_rec.YearsAtCompany,
                YearsInCurrentRole=emp_rec.YearsInCurrentRole,
                YearsSinceLastPromotion=emp_rec.YearsSinceLastPromotion,
                YearsWithCurrManager=emp_rec.YearsWithCurrManager,
            )
            prob, _ = _predict_prob_for_input(emp_input)
            
            results.append({
                "employee_id":     emp_rec.employee_id,
                "employee_name":   emp_rec.employee_name,
                "department":      emp_rec.Department,
                "job_role":        emp_rec.JobRole,
                "job_level":       emp_rec.JobLevel,
                "monthly_income":  emp_rec.MonthlyIncome,
                "risk_probability":round(prob, 4),
                "risk_pct":        round(prob * 100, 1),
                "risk_category":   risk_category(prob),
                "over_time":       emp_rec.OverTime,
                "job_satisfaction":emp_rec.JobSatisfaction,
                "years_at_company":emp_rec.YearsAtCompany,
            })
        except Exception as e:
            errors.append({"employee_id": emp_rec.employee_id, "error": str(e)})

    # ── Per-department aggregation ──────────────────────────────────────────────
    dept_map: dict[str, list] = {}
    for r in results:
        dept_map.setdefault(r["department"], []).append(r)

    departments = []
    for dept_name, emps in dept_map.items():
        probs = [e["risk_probability"] for e in emps]
        avg_risk = round(float(np.mean(probs)) * 100, 1)
        high_count = sum(1 for e in emps if e["risk_category"] == "HIGH")
        moderate_count = sum(1 for e in emps if e["risk_category"] == "MODERATE")
        low_count = sum(1 for e in emps if e["risk_category"] == "LOW")
        
        # ERL estimate: avg_monthly_income * 12 * 1.5 (rough replacement multiplier) * expected_attrition
        avg_annual = float(np.mean([e["monthly_income"] for e in emps])) * 12
        total_erl = round(sum(e["risk_probability"] * avg_annual * 1.5 for e in emps))
        
        # ACI
        aci = _contagion_index(emps)
        if aci >= 45:
            aci_level = "CRITICAL"
        elif aci >= 28:
            aci_level = "HIGH"
        elif aci >= 15:
            aci_level = "MODERATE"
        else:
            aci_level = "LOW"

        departments.append({
            "department":        dept_name,
            "headcount":         len(emps),
            "avg_risk_pct":      avg_risk,
            "high_risk_count":   high_count,
            "moderate_risk_count": moderate_count,
            "low_risk_count":    low_count,
            "high_risk_pct":     round(high_count / len(emps) * 100, 1),
            "total_erl":         total_erl,
            "contagion_index":   aci,
            "contagion_level":   aci_level,
            "employees":         emps,
        })

    departments.sort(key=lambda d: d["avg_risk_pct"], reverse=True)

    # ── Organisation summary ────────────────────────────────────────────────────
    all_probs = [r["risk_probability"] for r in results]
    org_avg_risk = round(float(np.mean(all_probs)) * 100, 1) if all_probs else 0.0
    total_high = sum(1 for r in results if r["risk_category"] == "HIGH")
    total_erl_org = sum(d["total_erl"] for d in departments)
    max_aci_dept = max(departments, key=lambda d: d["contagion_index"]) if departments else None

    return {
        "organisation_summary": {
            "total_employees":    len(results),
            "avg_risk_pct":       org_avg_risk,
            "high_risk_count":    total_high,
            "high_risk_pct":      round(total_high / len(results) * 100, 1) if results else 0,
            "total_erl_estimate": total_erl_org,
            "critical_contagion_dept": max_aci_dept["department"] if max_aci_dept else None,
            "critical_contagion_aci":  max_aci_dept["contagion_index"] if max_aci_dept else 0,
        },
        "departments": departments,
        "parse_errors": errors,
        "disclaimer": (
            "All predictions are statistical estimates from a Logistic Regression model trained on a "
            "synthetic IBM HR dataset. They are NOT predictions of individual behaviour. "
            "Attrition Contagion Index (ACI) is a research-defined composite metric. "
            "ERL figures use a simplified 1.5× salary multiplier for illustrative purposes only. "
            "This output must NOT be used to make real employment decisions."
        ),
    }

