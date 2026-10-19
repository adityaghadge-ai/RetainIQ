// backend/services/costEngine.js
// ================================
// Deterministic replacement cost calculations.
// Gemini does NOT calculate these values.
// All are clearly labelled as researcher-defined estimates.

/**
 * Calculate full replacement cost for N employees.
 * All inputs are user-supplied; all outputs are estimates.
 */
export function calculateReplacementCost(params) {
  const {
    numberOfReplacements = 1,
    annualCompensation = 0,      // per replacement employee
    recruitmentCost = 0,         // per employee (agency fee etc.)
    onboardingCost = 0,          // per employee
    trainingCost = 0,            // per employee
    vacancyDays = 60,            // days position is unfilled
    rampUpDays = 90,             // days to reach full productivity
    productivityDuringRampUp = 0.60, // fraction (0-1)
    otherCosts = 0,              // total other costs
    // Departing employee info (for vacancy cost calc)
    departingEmployeeAnnualSalary = annualCompensation,
  } = params;

  const n = numberOfReplacements;
  const dailyValue = departingEmployeeAnnualSalary / 365;

  // Direct costs
  const compensationTotal  = n * annualCompensation;
  const recruitmentTotal   = n * recruitmentCost;
  const onboardingTotal    = n * onboardingCost;
  const trainingTotal      = n * trainingCost;

  // Vacancy / productivity loss
  const vacancyLoss = dailyValue * vacancyDays;          // whole position empty
  const rampUpLoss  = dailyValue * rampUpDays * (1 - productivityDuringRampUp) * n;

  const totalReplacementImpact = (
    compensationTotal +
    recruitmentTotal  +
    onboardingTotal   +
    trainingTotal     +
    vacancyLoss       +
    rampUpLoss        +
    otherCosts
  );

  return {
    inputs: params,
    breakdown: {
      compensation_total:   Math.round(compensationTotal),
      recruitment_total:    Math.round(recruitmentTotal),
      onboarding_total:     Math.round(onboardingTotal),
      training_total:       Math.round(trainingTotal),
      vacancy_loss:         Math.round(vacancyLoss),
      ramp_up_loss:         Math.round(rampUpLoss),
      other_costs:          Math.round(otherCosts),
    },
    total_replacement_impact: Math.round(totalReplacementImpact),
    disclaimer: "All values are researcher-defined estimates under user-supplied assumptions. Not industry-standard figures.",
  };
}

/**
 * Calculate Expected Replacement Loss.
 * ERL = calibrated_probability × total_replacement_impact
 */
export function calculateERL(calibratedProbability, totalReplacementImpact) {
  const erl = calibratedProbability * totalReplacementImpact;
  return {
    calibrated_probability: calibratedProbability,
    total_replacement_impact: totalReplacementImpact,
    expected_replacement_loss: Math.round(erl),
    explanation: (
      "Expected Replacement Loss = P(attrition) × Estimated Replacement Impact. " +
      "This is an expected-value estimate under user-defined cost assumptions. " +
      "It is NOT a guaranteed financial loss. It is a decision-support metric."
    ),
  };
}

/**
 * Compare multiple replacement scenarios.
 */
export function compareScenarios(scenarios, calibratedProbability, departingEmployeeAnnualSalary) {
  return scenarios.map(scenario => {
    const result = calculateReplacementCost({
      ...scenario,
      departingEmployeeAnnualSalary,
    });
    const erl = calculateERL(calibratedProbability, result.total_replacement_impact);
    return {
      scenario_label: scenario.label || `${scenario.numberOfReplacements} replacement(s)`,
      ...result,
      expected_replacement_loss: erl.expected_replacement_loss,
    };
  });
}
