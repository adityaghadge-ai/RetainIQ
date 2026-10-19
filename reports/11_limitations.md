# 11 – Limitations

1. **Synthetic dataset:** The IBM HR Analytics dataset is fictional. Results do not
   represent any real organisation's workforce dynamics.

2. **Small dataset:** With only 1,470 employees, statistical conclusions must be
   interpreted cautiously. The minority class (attrition=1) contains approximately
   237 employees.

3. **Hypothetical cost parameters:** All replacement-cost scenarios are
   researcher-defined assumptions. Real replacement costs vary widely by
   organisation, role, geography, seniority, and market conditions.

4. **Predictive, not causal:** The model identifies features associated with
   attrition predictions on this dataset. It does NOT establish causal mechanisms
   or guarantee that any intervention will reduce attrition.

5. **Fairness audit limitations:** The audit is restricted to Age, Gender, and
   MaritalStatus – the only demographic attributes available. Many other sources
   of potential bias cannot be assessed.

6. **No generalisation guarantee:** Results on this benchmark do not establish
   that the framework will perform similarly on data from real organisations.

7. **No intervention outcomes observed:** The dataset does not record which
   employees received retention interventions or whether those interventions
   were effective.

8. **Out-of-fold evaluation boundary:** OOF evaluation on this small synthetic
   dataset does NOT validate the framework for real deployment.

9. **RAG context only:** Literature passages retrieved by the RAG system are
   provided for contextual background. They do NOT constitute evidence that
   the identified factors caused this specific employee's attrition.

10. **Selection bias:** In a real deployment, the act of selecting employees for
    intervention could itself influence outcomes in ways this framework cannot model.
