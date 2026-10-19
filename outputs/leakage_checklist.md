# RetainIQ - Data Leakage Checklist
Generated automatically. Review each item carefully.

| Item | Status |
|------|--------|
| EmployeeNumber not used as feature | PASS |
| Attrition not used as feature | PASS |
| Age/Gender/MaritalStatus excluded from model | PASS |
| No preprocessing fit on full dataset | PASS |
| No SMOTE/ADASYN before CV | PASS |
| No target-derived feature | PASS |
| No future information | PASS |
| Calibration inside outer training fold only | PASS |
| OOF predictions used for evaluation | PASS |
| Cost calculation occurs after probability | PASS |
| Final full-data model NOT used for unbiased evaluation | PASS |
