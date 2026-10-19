// backend/services/employeeService.js
// ===================================
// Employee Roster & Separation Impact Engine for HR Management.
// Loads actual IBM HR dataset and calculates replacement cost,
// replacement multiplier (FTEs needed), and market availability score.

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import axios from "axios";
import { calculateReplacementCost, calculateERL } from "./costEngine.js";
import { searchCandidates } from "./candidateRagService.js";
import { scrapeMarketBenchmarks } from "./marketScraperService.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CSV_PATH = path.join(__dirname, "../../data/WA_Fn-UseC_-HR-Employee-Attrition.csv");
const ML_URL = process.env.ML_SERVICE_URL || "http://localhost:8001";

let EMPLOYEES_CACHE = null;

/**
 * Parse CSV line handling commas inside quotes
 */
function parseCSVLine(line) {
  const values = [];
  let current = "";
  let insideQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      insideQuotes = !insideQuotes;
    } else if (char === "," && !insideQuotes) {
      values.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  values.push(current.trim());
  return values;
}

/**
 * Load and cache employee records
 */
export function getEmployees() {
  if (EMPLOYEES_CACHE) {
    return EMPLOYEES_CACHE;
  }

  if (!fs.existsSync(CSV_PATH)) {
    console.error("[employeeService] CSV not found at", CSV_PATH);
    return [];
  }

  const raw = fs.readFileSync(CSV_PATH, "utf-8");
  const lines = raw.split(/\r?\n/).filter(Boolean);
  const headers = parseCSVLine(lines[0]);

  const employees = [];
  for (let i = 1; i < lines.length; i++) {
    const row = parseCSVLine(lines[i]);
    if (row.length !== headers.length) continue;

    const record = {};
    headers.forEach((h, idx) => {
      const val = row[idx];
      record[h] = isNaN(Number(val)) ? val : Number(val);
    });

    const empId = `EMP-${String(i).padStart(4, "0")}`;
    const monthlyIncome = record.MonthlyIncome || 5000;
    const annualSalary = monthlyIncome * 12;

    employees.push({
      id: empId,
      code: `ID-${1000 + i}`,
      role: record.JobRole || "Specialist",
      department: record.Department || "R&D",
      jobLevel: record.JobLevel || 1,
      monthlyIncome,
      annualSalary,
      totalExperienceYears: record.TotalWorkingYears || 3,
      yearsAtCompany: record.YearsAtCompany || 2,
      yearsInCurrentRole: record.YearsInCurrentRole || 1,
      performanceRating: record.PerformanceRating || 3,
      jobSatisfaction: record.JobSatisfaction || 3,
      environmentSatisfaction: record.EnvironmentSatisfaction || 3,
      workLifeBalance: record.WorkLifeBalance || 3,
      overtime: record.OverTime || "No",
      rawFeatures: record,
    });
  }

  EMPLOYEES_CACHE = employees;
  console.log(`[employeeService] Loaded ${employees.length} employees from roster.`);
  return employees;
}

/**
 * Filter & search employees
 */
export function searchRoster({ query = "", department = "", role = "", limit = 50, offset = 0 }) {
  const all = getEmployees();
  let filtered = all;

  if (department) {
    filtered = filtered.filter(e => e.department.toLowerCase() === department.toLowerCase());
  }

  if (role) {
    filtered = filtered.filter(e => e.role.toLowerCase().includes(role.toLowerCase()));
  }

  if (query) {
    const q = query.toLowerCase();
    filtered = filtered.filter(e =>
      e.id.toLowerCase().includes(q) ||
      e.code.toLowerCase().includes(q) ||
      e.role.toLowerCase().includes(q) ||
      e.department.toLowerCase().includes(q)
    );
  }

  const paginated = filtered.slice(offset, offset + limit);
  return {
    total: filtered.length,
    employees: paginated,
  };
}

/**
 * Get employee by ID
 */
export function getEmployeeById(id) {
  const all = getEmployees();
  return all.find(e => e.id === id || e.code === id);
}

/**
 * Analyze Separation / Replacement of an Employee
 */
export async function analyzeSeparation(employee, customOptions = {}) {
  // 1. Predict attrition / flight probability via ML Service
  let prediction = {
    calibrated_probability: 0.25,
    probability_pct: 25,
    risk_category: "LOW",
    model_name: "LogisticRegression",
    model_version: "1.0.0",
  };
  let modelFactors = [];

  try {
    const predResp = await axios.post(`${ML_URL}/api/predict`, employee.rawFeatures, { timeout: 3500 });
    prediction = predResp.data.prediction;
    modelFactors = predResp.data.model_factors || [];
  } catch (err) {
    console.warn("[employeeService] ML service fallback:", err.message);
  }

  // 2. Fetch live market benchmarks for role
  const benchmark = await scrapeMarketBenchmarks(employee.role, employee.totalExperienceYears);

  // 3. Replacement Multiplier (RM) formulation:
  // How many new hires are required to match this employee's productivity?
  // Senior level (3+) or high tenure (5+ yrs) requires 1.5 - 2.5 FTEs to replace institutional memory
  const level = Number(employee.jobLevel) || 1;
  const tenure = Number(employee.yearsAtCompany) || 1;
  let replacementMultiplier = 1.0;
  if (level >= 4 || tenure >= 8) {
    replacementMultiplier = 2.0;
  } else if (level >= 3 || tenure >= 5) {
    replacementMultiplier = 1.5;
  } else if (level === 2 && tenure >= 3) {
    replacementMultiplier = 1.25;
  }

  // 4. Replacement Availability Score (RAS) formulation:
  // Probability of finding an equivalent replacement in the talent market (0% to 100%)
  let marketAvailabilityPct = 78;
  let vacancyDays = benchmark.expected_hiring_days || 45;

  if (employee.role.includes("Research") || employee.role.includes("Director")) {
    marketAvailabilityPct = Math.max(45, 75 - (level * 6) - Math.min(15, tenure));
    vacancyDays = Math.round(55 + (level * 8));
  } else if (employee.role.includes("Sales Executive") || employee.role.includes("Manager")) {
    marketAvailabilityPct = Math.max(55, 85 - (level * 5));
    vacancyDays = Math.round(40 + (level * 6));
  } else {
    marketAvailabilityPct = Math.max(65, 90 - (level * 4));
    vacancyDays = Math.round(30 + (level * 5));
  }

  // 5. Cost Engine computation
  const salaryPerFTE = customOptions.annualCompensation || benchmark.compensation?.median_annual || employee.annualSalary;
  const recruitmentCost = customOptions.recruitmentCost || benchmark.recruitment_cost_per_employee || Math.round(salaryPerFTE * 0.16);
  const trainingCost = customOptions.trainingCost || benchmark.training_cost || 50000;
  const onboardingCost = customOptions.onboardingCost || benchmark.onboarding_cost || 40000;
  const rampUpDays = benchmark.rampup_days || 75;
  const productivityRampUp = benchmark.productivity_during_rampup || 0.60;

  const costCalc = calculateReplacementCost({
    numberOfReplacements: replacementMultiplier,
    annualCompensation: salaryPerFTE,
    recruitmentCost,
    onboardingCost,
    trainingCost,
    vacancyDays,
    rampUpDays,
    productivityDuringRampUp: productivityRampUp,
    departingEmployeeAnnualSalary: employee.annualSalary,
  });

  const erl = calculateERL(prediction.calibrated_probability, costCalc.total_replacement_impact);

  // 6. Time-to-Productivity Gap Loss (PGC) and Knowledge Capital Loss (KCL)
  const dailyValue = employee.annualSalary / 365;
  const knowledgeLossEstimate = Math.round(dailyValue * 30 * Math.min(10, tenure) * 0.35);

  // 7. Find matching candidates from candidate database
  const candidateResults = searchCandidates({
    role: employee.role,
    minExperience: Math.max(1, employee.totalExperienceYears - 2),
    maxSalary: Math.round(salaryPerFTE * 1.2),
  });

  return {
    employee: {
      id: employee.id,
      code: employee.code,
      role: employee.role,
      department: employee.department,
      jobLevel: employee.jobLevel,
      annualSalary: employee.annualSalary,
      monthlyIncome: employee.monthlyIncome,
      tenureYears: employee.yearsAtCompany,
      totalExperienceYears: employee.totalExperienceYears,
      performanceRating: employee.performanceRating,
      overtime: employee.overtime,
      jobSatisfaction: employee.jobSatisfaction,
    },
    departure_risk: {
      probability_pct: prediction.probability_pct,
      calibrated_probability: prediction.calibrated_probability,
      risk_category: prediction.risk_category,
      model_factors: modelFactors.slice(0, 5),
    },
    replacement_feasibility: {
      replacement_multiplier: replacementMultiplier,
      multiplier_explanation:
        replacementMultiplier > 1
          ? `Because of this employee's seniority (Job Level ${level}) and ${tenure} years of company experience, hiring ${replacementMultiplier} replacement FTEs is estimated to restore equivalent operational output.`
          : `Standard 1:1 replacement is feasible based on current role scope and market availability.`,
      market_availability_pct: marketAvailabilityPct,
      market_liquidity_tier: marketAvailabilityPct >= 75 ? "High Availability" : marketAvailabilityPct >= 55 ? "Moderate Scarcity" : "Acute Scarcity",
      estimated_vacancy_days: vacancyDays,
      estimated_rampup_days: rampUpDays,
      productivity_during_rampup_pct: Math.round(productivityRampUp * 100),
    },
    financial_impact: {
      total_replacement_exposure: costCalc.total_replacement_impact,
      expected_replacement_loss: erl.expected_replacement_loss,
      breakdown: costCalc.breakdown,
      knowledge_capital_loss_estimate: knowledgeLossEstimate,
      market_benchmark_reference: benchmark.source_attribution,
    },
    candidate_matches: candidateResults.candidates.slice(0, 3),
    strategic_recommendation: {
      verdict:
        prediction.probability_pct >= 50
          ? "CRITICAL RETENTION INTERVENTION REQUIRED: High flight risk coupled with significant replacement disruption."
          : level >= 4
          ? "HIGH SUCCESSION RISK: Even with moderate departure probability, the replacement multiplier of " + replacementMultiplier + "× creates substantial vacancy friction."
          : "STABLE PROFILE: Standard replacement protocols apply if separation occurs.",
      key_actions: [
        `Conduct stay interview focusing on work condition correlates (OverTime = ${employee.overtime}, Satisfaction = ${employee.jobSatisfaction}/4).`,
        `Pre-qualify replacement pipeline in case of separation (Estimated hiring lead time: ${vacancyDays} days).`,
        `Plan knowledge transfer to reduce institutional memory loss (Tenure: ${tenure} years).`,
      ],
    },
  };
}
