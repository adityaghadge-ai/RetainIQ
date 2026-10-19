# 01 – Problem Statement

## Research Context

Employee attrition – the voluntary or involuntary departure of employees – imposes
significant costs on organisations, including recruitment, training, knowledge loss,
and productivity reduction. Predictive analytics has been applied to estimate which
employees are at risk of leaving; however, most existing work frames the problem
primarily as a binary classification task optimised for discriminative accuracy.

## The Gap This Research Addresses

Knowing that an employee has a **high predicted probability of attrition** does not
directly answer the operational question that HR decision-makers face:

> **"Given that HR can realistically intervene with only a limited number of employees,
> which employees should be prioritised — and does accounting for economic exposure
> change that selection?"**

This requires moving beyond a single risk probability into a **cost-aware,
capacity-constrained prioritisation framework**.

## RetainIQ's Research Position

RetainIQ targets the following integrated gap:

A transparent framework that moves from **calibrated individual attrition probability**
to **economically informed retention prioritisation**, explicitly considering:

1. Uncertainty in replacement-cost assumptions
2. Limited HR intervention capacity
3. Ranking differences between risk-only and cost-aware strategies
4. Evaluation using realised out-of-fold outcomes (not model-generated exposure)
5. Fairness auditing when demographic attributes are excluded from model training
6. Literature-grounded explanations without claiming predictive associations are causal

**The research contribution is therefore the DECISION FRAMEWORK, not a new classifier.**

## What RetainIQ Must Not Claim

- This system is NOT a production-ready HR decision tool.
- The IBM dataset is synthetic; results do not represent a real organisation.
- The model is predictive, not causal.
- No employment decisions should be made automatically based on this system.
