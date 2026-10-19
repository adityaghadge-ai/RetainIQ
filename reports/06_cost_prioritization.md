# 06 – Cost Prioritisation

## Overview

After calibrated probabilities are generated, the framework translates them into
economically-informed retention priorities.

## Why Probability Alone Is Insufficient

If HR ranks employees purely by predicted attrition probability, a high-risk
low-salary employee may receive priority over a moderate-risk high-cost employee.
The economic exposure in the second case may be larger.

## Expected Replacement Loss (ERL)

For each employee i:

```
ERL_i = P(attrition)_i × ReplacementCost_i
```

The ERL integrates both the **likelihood** of leaving and the **economic impact**
if they do leave.

## Cost Scenarios (Researcher Assumptions)

> **All cost parameters are researcher-defined hypothetical assumptions for
> research sensitivity analysis. They are NOT empirical industry standards.**

### Scenario 1: Fixed Cost + Salary Share

```
AnnualSalary = MonthlyIncome × 12
ReplacementCost_1 = FixedCost + SalaryShare × AnnualSalary
Default: FixedCost = $25,000 / SalaryShare = 0.75
```

This scenario can change rankings because the fixed cost component gives
relatively greater weight to lower-salary employees than a pure salary multiplier would.

### Scenario 2: Seniority-Scaled

```
ReplacementCost_2 = AnnualSalary × SeniorityFactor[JobLevel]
Factors: JL1=0.60, JL2=0.75, JL3=1.00, JL4=1.25, JL5=1.50
```

This scenario specifically reweights by job level, reflecting the observation
in literature that senior roles have disproportionately higher replacement costs.

## Why Constant Multipliers Cannot Change Rankings

If `Cost = k × Salary` for any constant k, then:
`ERL = P × k × Salary`

Changing k scales all ERLs equally and **does not change the rank ordering**.
RetainIQ uses non-constant cost structures so that different employees can
actually change positions across scenarios.

## Four Core Rankings

| Ranking | Sort Key |
|---|---|
| A: Risk-Only | Calibrated probability |
| B: Cost-Only | Replacement cost (Scenario 1) |
| C: Risk × Cost (Fixed) | ERL – Scenario 1 |
| D: Risk × Cost (Seniority) | ERL – Scenario 2 |
