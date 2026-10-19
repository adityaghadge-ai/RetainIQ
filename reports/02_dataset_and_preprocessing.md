# 02 – Dataset and Preprocessing

## Dataset

- **Name:** IBM HR Analytics Employee Attrition & Performance
- **Type:** Synthetic benchmark dataset (created by IBM data scientists)
- **Source:** Kaggle – https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset
- **Expected dimensions:** 1,470 rows × 35 columns
- **Target:** `Attrition` (Yes/No → 1/0)
- **Positive class rate:** approximately 16%

**Important:** This dataset is synthetic and fictional. Results must NOT be presented
as representative of any real organisation.

## Data Quality Checks Performed

- Shape verification
- Missing value audit per column
- Duplicate row detection
- Unique-value counts (identify constants and identifiers)
- Target distribution
- Impossible or suspicious value detection

## Columns Removed

| Column | Reason |
|---|---|
| `EmployeeNumber` | Identifier – no predictive signal; retained for tracking only |
| `EmployeeCount` | Constant (=1 for all rows) |
| `Over18` | Constant ("Y" for all rows) |
| `StandardHours` | Constant (=80 for all rows) |

## Excluded from Model Training (Demographic Audit Variables)

| Column | Usage |
|---|---|
| `Age` | Post-hoc fairness audit only |
| `Gender` | Post-hoc fairness audit only |
| `MaritalStatus` | Post-hoc fairness audit only |

These variables are retained in a separate audit frame and never passed to the model.

## Target Encoding

```
Attrition: Yes → 1  (positive class = employee left)
           No  → 0  (negative class = employee stayed)
```

## Preprocessing Pipeline (Inside CV)

All transformations are applied **inside each cross-validation fold** to prevent leakage.

| Feature type | Imputation | Scaling |
|---|---|---|
| Numeric | Median imputation | StandardScaler (LR only) |
| Categorical | Most-frequent imputation | OneHotEncoder(handle_unknown="ignore") |

## Class Imbalance

The minority class (Attrition=1) is approximately 16%. Primary evaluation uses:
- PR-AUC (primary)
- Recall, F1
- ROC-AUC (secondary)

**Accuracy is NOT the primary metric** due to class imbalance.
