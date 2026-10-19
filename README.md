# RetainIQ: Employee Attrition Risk Prediction and Cost-Weighted Retention Prioritization

> **Research Paper Title:** A Cost-Weighted Machine Learning Framework for Employee Attrition Prediction and Retention Prioritization

---

## ⚠️ Important Disclaimers

> **RetainIQ is a benchmark-validated research prototype.**
>
> - The IBM HR Analytics dataset is **synthetic/fictional** and does not represent any real company or workforce.
> - All results are for **academic research purposes only**.
> - This system **must NOT** be used to make real employment decisions.
> - All probability and cost estimates are **model outputs under researcher-defined assumptions**, not guaranteed predictions or industry standards.
> - No **causal relationships** between features and attrition are implied.
> - The system is predictive, not causal.

---

## Project Overview

RetainIQ is not just another attrition classifier. The central research idea is:

```
Prediction
    ↓
Calibrated Attrition Probability
    ↓
Replacement-Cost Scenario
    ↓
Expected Replacement Loss (ERL)
    ↓
Limited HR Intervention Capacity
    ↓
Priority Ranking
    ↓
Evaluation Using Realized Out-of-Fold Outcomes
    ↓
Fairness Audit
    ↓
Literature-Grounded Explanation
```

**Primary Research Question:**
> *"Can calibrated employee attrition probabilities be transformed into a cost-aware and capacity-constrained retention prioritization framework that identifies a different and potentially more economically relevant intervention set than risk-only ranking?"*

---

## Research Questions

| # | Research Question |
|---|---|
| RQ1 | How effectively can machine-learning models estimate employee attrition risk under class imbalance? |
| RQ2 | Do domain-informed engineered features improve predictive discrimination and probability calibration? |
| RQ3 | Does cost-weighted prioritization select a materially different intervention set than risk-only ranking? |
| RQ4 | How sensitive are retention priorities to replacement-cost assumptions and intervention capacity? |
| RQ5 | Do the proposed prioritization strategies capture more actual leavers and realized replacement-cost exposure than a random intervention strategy at the same capacity? |

---

## Project Structure

```
RetainIQ/
├── data/
│   └── WA_Fn-UseC_-HR-Employee-Attrition.csv   ← Place dataset here
├── kb/
│   └── *.pdf                                    ← Optional: research PDFs for RAG
├── outputs/                                     ← Generated CSV / JSON artefacts
├── figures/                                     ← Generated PNG figures
├── reports/                                     ← Research report markdown files
├── retainiq_common.py                           ← Shared utilities and constants
├── retainiq_01_baseline.py                      ← Phase 1–9: data + models + calibration
├── retainiq_02_priority.py                      ← Phase 10–19: cost + rankings + evaluation
├── retainiq_03_rag.py                           ← Phase 20: optional RAG layer
├── requirements.txt
└── README.md
```

---

## Dataset

- **Name:** IBM HR Analytics Employee Attrition & Performance
- **Source:** [Kaggle](https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset)
- **Expected dimensions:** 1,470 rows × 35 columns
- **Target:** `Attrition` (Yes=1, No=0)
- **Note:** This is a **synthetic benchmark dataset** created by IBM data scientists. Results do not represent a real company.

---

## Installation

```bash
pip install -r requirements.txt
```

**Python version:** 3.9+

**Key dependencies:**
- scikit-learn ≥ 1.3
- xgboost ≥ 2.0 (falls back to HistGradientBoostingClassifier if unavailable)
- shap ≥ 0.43 (optional, skipped if unavailable)
- pypdf ≥ 4.0 (optional, for RAG PDF extraction)

---

## Execution Order

```bash
# Step 1: Data quality + models + calibration + feature ablation
python retainiq_01_baseline.py

# Step 2: Cost scenarios + ERL + rankings + budget experiments + fairness
python retainiq_02_priority.py

# Step 3: Optional RAG literature layer
python retainiq_03_rag.py
```

> **Important:** Scripts must be run in order. Each script depends on outputs from the previous one.

---

## Pipeline Architecture

### Phase 1: Data Quality & Cleaning

- Shape, dtypes, missing values, duplicates, unique counts
- Constant column detection and removal
- Identifier column exclusion (`EmployeeNumber` never used as a feature)
- Target encoding: `Yes → 1`, `No → 0`
- Outputs: `outputs/data_quality_report.csv`

### Fairness Design

The following variables are **excluded from model training**:

| Variable | Reason | Role |
|---|---|---|
| `Age` | Demographic | Post-hoc fairness audit only |
| `Gender` | Demographic | Post-hoc fairness audit only |
| `MaritalStatus` | Demographic | Post-hoc fairness audit only |

### Phase 2: Feature Engineering (Ablation A vs B)

| Feature | Formula |
|---|---|
| `YearsAtCompanyRatio` | `YearsAtCompany / TotalWorkingYears` |
| `IncomePerExperience` | `MonthlyIncome / (TotalWorkingYears + 1)` |
| `YearsSincePromotionRatio` | `YearsSinceLastPromotion / (YearsAtCompany + 1)` |
| `YearsWithManagerRatio` | `YearsWithCurrManager / (YearsAtCompany + 1)` |
| `JobLevelExperienceInteraction` | `JobLevel × TotalWorkingYears` |
| `PromotionGap` | `YearsSinceLastPromotion / (YearsAtCompany + 1)` |
| `IncomeGrowthIndicator` | `1 if MonthlyIncome > training-fold median, else 0` |

> All feature engineering statistics (e.g., median income) are computed **inside the training fold** to prevent leakage.

### Phase 3: Models

| Model | Purpose |
|---|---|
| Logistic Regression | Interpretable linear baseline |
| Random Forest | Nonlinear ensemble |
| XGBoost | Stronger nonlinear benchmark |

All models use `class_weight="balanced"`. Primary metric: **PR-AUC**.

### Phase 4: Calibration

- **Method:** Sigmoid (Platt) calibration via `CalibratedClassifierCV`
- **Fold-safe:** Calibration is fitted **inside each outer training fold** using inner 3-fold CV
- The validation employee **never influences** model or calibration fitting
- **Metrics:** Brier Score, ECE (Expected Calibration Error)

### Phase 5: Cost Scenarios (Researcher Assumptions)

| Scenario | Formula | Parameters |
|---|---|---|
| Fixed + Salary Share | `FixedCost + SalaryShare × AnnualSalary` | FC=\$25,000 / SS=0.75 |
| Seniority-scaled | `AnnualSalary × SeniorityFactor[JobLevel]` | JL1=0.60 ... JL5=1.50 |

> **These are researcher-defined hypothetical scenarios for sensitivity analysis. They are NOT empirical industry standards.**

### Phase 6: Rankings

| Ranking | Sort Key |
|---|---|
| Risk-Only | Calibrated attrition probability |
| Cost-Only | Replacement cost (Scenario 1) |
| Risk × Cost (Fixed) | ERL = P × Replacement Cost (Scenario 1) |
| Risk × Cost (Seniority) | ERL = P × Replacement Cost (Scenario 2) |

### Phase 7: Budget Experiments

Intervention capacities tested: **Top 10 / 25 / 50 / 100**

Evaluation uses **actual out-of-fold attrition outcomes** (not predicted probabilities).
Random baseline: **1,000 repetitions** per budget.

---

## Output Files

| File | Description |
|---|---|
| `data_quality_report.csv` | Per-column quality summary |
| `baseline_model_comparison.csv` | All model experiment results |
| `baseline_oof_predictions.csv` | OOF probabilities for all employees |
| `feature_ablation.csv` | Ablation A vs B comparison |
| `calibration_results.csv` | Brier + ECE: calibrated vs uncalibrated |
| `employee_priority.csv` | Per-employee cost and ERL |
| `budget_results.csv` | Budget experiment results |
| `cost_sensitivity.csv` | Ranking stability across cost grid |
| `ranking_stability.csv` | Same as above |
| `fairness_audit.csv` | Per-group fairness metrics |
| `employee_explanations.csv` | Top employees with model-associated factors |
| `retention_briefs.csv` | RAG literature context per employee |
| `leakage_checklist.md` | Data leakage verification |
| `final_model_metadata.json` | Full reproducibility metadata |
| `experiment_summary.csv` | All experiments in one table |

---

## Figures

| Figure | Description |
|---|---|
| `target_distribution.png` | Attrition class imbalance |
| `feature_ablation.png` | Baseline vs engineered feature comparison |
| `model_comparison.png` | Model PR-AUC and ROC-AUC |
| `calibration_curve.png` | Calibration quality: calibrated vs uncalibrated |
| `risk_vs_cost.png` | Risk probability vs ERL scatter |
| `budget_curve.png` | Leavers captured by strategy at each budget |
| `budget_cost_curve.png` | Realized cost exposure captured by strategy |
| `ranking_stability.png` | Heatmap of ranking stability across cost grid |
| `feature_importance.png` | Permutation feature importance |
| `fairness_audit.png` | Group-level fairness metrics |
| `shap_summary.png` | SHAP values (if tree model selected and SHAP available) |

---

## Research Contribution

> RetainIQ presents a transparent cost-weighted decision-support framework that extends employee attrition prediction beyond risk estimation by integrating calibrated attrition probabilities, scenario-based replacement costs, and capacity-constrained retention prioritization. The framework evaluates prioritization strategies using out-of-fold realized attrition outcomes and performs sensitivity and fairness analyses to quantify uncertainty and potential disparities.

**What RetainIQ does NOT claim:**
- ❌ "First employee attrition model"
- ❌ "State-of-the-art accuracy"
- ❌ "Proves why employees leave"
- ❌ "Determines which employees should be saved"
- ❌ "Suitable for real HR decisions"

---

## Limitations

1. The IBM HR dataset is **synthetic** and does not represent any real organisation.
2. The dataset is relatively **small** (1,470 employees).
3. Replacement-cost parameters are **researcher-defined hypothetical assumptions**.
4. The model is **predictive**, not causal.
5. Fairness audit is limited to the **demographic attributes available** in the dataset.
6. Results may **not generalise** to other organisations, industries, or regions.
7. Actual retention interventions and their effectiveness are **not observed** in this dataset.
8. Real replacement costs vary by **organisation, role, geography, seniority, and hiring conditions**.
9. Out-of-fold evaluation on this benchmark does **not establish real-world deployment validity**.
10. The framework does not account for **selection bias** in who receives interventions.

---

## Reproducibility

All experiments use `random_state = 42`. Full metadata is saved to `outputs/final_model_metadata.json`.

```
CV: StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
Calibration: CalibratedClassifierCV(method='sigmoid', cv=StratifiedKFold(n_splits=3))
```

---

## License

This project is for academic research only. The IBM HR dataset is publicly available on Kaggle under its original license.
