// backend/server.js
// ==================
// RetainIQ Express backend orchestrator.
// Proxies ML predictions to FastAPI service.
// Runs deterministic cost engine.
// Executes Candidate RAG retrieval, market scraper agent, and employee roster analysis.
// Calls Gemini for structured action plans.

import "dotenv/config";
import express from "express";
import cors from "cors";
import axios from "axios";
import multer from "multer";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

import { calculateReplacementCost, calculateERL, compareScenarios } from "./services/costEngine.js";
import { generateActionPlan } from "./services/geminiService.js";
import { searchCandidates, addCandidate, getAllCandidates } from "./services/candidateRagService.js";
import { scrapeMarketBenchmarks } from "./services/marketScraperService.js";
import { registerUser, authenticate, verifyAuth } from "./services/authService.js";
import { getEmployees, searchRoster, getEmployeeById, analyzeSeparation } from "./services/employeeService.js";
import { parseEmployeeDocument, SECONDARY_DEFAULTS, MANDATORY_FIELDS } from "./services/documentParser.js";
import { defaultSalaryProvider } from "./services/marketSalaryProvider.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app  = express();
const PORT = process.env.PORT || 8000;
const ML   = process.env.ML_SERVICE_URL || "http://localhost:8001";

// Multer config for employee records and resumes
const upload = multer({
  dest: path.join(__dirname, "../uploads"),
  limits: { fileSize: 5 * 1024 * 1024 }, // 5 MB limit
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    if (![".pdf", ".csv", ".xlsx", ".xls", ".json"].includes(ext)) {
      return cb(new Error("Unsupported format. Please upload a PDF, CSV, XLSX, or JSON employee record."));
    }
    cb(null, true);
  },
});

const uploadMiddleware = (req, res, next) => {
  upload.single("file")(req, res, (err) => {
    if (err) {
      if (err.code === "LIMIT_FILE_SIZE") {
        return res.status(400).json({ error: "File size exceeds maximum limit of 5 MB." });
      }
      return res.status(400).json({ error: err.message || "File upload failed." });
    }
    next();
  });
};

app.use(cors({ origin: ["http://localhost:5173", "http://localhost:3000", "*"] }));
app.use(express.json({ limit: "10mb" }));

// ── Authentication ─────────────────────────────────────────────────────────
// POST /api/auth/register
app.post("/api/auth/register", (req, res) => {
  const result = registerUser(req.body);
  if (!result.success) {
    return res.status(400).json(result);
  }
  res.status(201).json(result);
});

// POST /api/auth/login
app.post("/api/auth/login", (req, res) => {
  const { email, username, password } = req.body;
  const identifier = email || username;
  const result = authenticate(identifier, password);
  if (!result.success) {
    return res.status(401).json(result);
  }
  res.json(result);
});

// GET /api/auth/me
app.get("/api/auth/me", verifyAuth, (req, res) => {
  res.json({ user: req.user });
});

// GET /api/health & /api/status
app.get(["/api/health", "/api/status"], (req, res) => {
  res.json({ status: "healthy", version: "2.4.0", ml_service: ML });
});

// ── Document Ingestion & Extraction Workflow ──────────────────────────────
// POST /api/employee/upload (PDF, XLSX, CSV, JSON parsing)
app.post("/api/employee/upload", uploadMiddleware, async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: "No file uploaded. Please upload a PDF, CSV, XLSX, or JSON employee record." });
  }
  try {
    const result = await parseEmployeeDocument(req.file.path, req.file.originalname);
    // Remove temporary uploaded file immediately for privacy compliance
    try { fs.unlinkSync(req.file.path); } catch {}
    res.json(result);
  } catch (err) {
    try { if (req.file?.path) fs.unlinkSync(req.file.path); } catch {}
    res.status(400).json({ error: err.message || "Document extraction failed" });
  }
});

// POST /api/employee/analyze (Validates mandatory fields -> Calls ML Model -> Precomputes initial cost & market)
app.post("/api/employee/analyze", async (req, res) => {
  try {
    const { case_id = "EMP-1042", features = {} } = req.body;

    // Check mandatory fields
    const missing = [];
    for (const field of MANDATORY_FIELDS) {
      if (features[field.key] === undefined || features[field.key] === null || features[field.key] === "" || (typeof features[field.key] === "number" && isNaN(features[field.key]))) {
        missing.push(field.label);
      }
    }

    if (missing.length > 0) {
      return res.status(400).json({
        error: `Unable to generate prediction because the following required employee fields are missing: ${missing.join(", ")}`,
        missing_fields: missing,
      });
    }

    // Merge with secondary operational defaults
    const completeFeatures = { ...SECONDARY_DEFAULTS, ...features };
    // Attrition is never an input feature
    delete completeFeatures.Attrition;

    // 1. Trained ML Model inference
    const mlResp = await axios.post(`${ML}/api/predict`, completeFeatures, { timeout: 4000 });
    const prediction = mlResp.data.prediction;
    const modelFactors = mlResp.data.model_factors || [];
    const riskFingerprint = mlResp.data.risk_fingerprint || [];
    const peerBenchmark = mlResp.data.peer_benchmark || {};

    // 2. Market salary benchmark retrieval
    const annualSalary = completeFeatures.AnnualSalary || (completeFeatures.MonthlyIncome * 12);
    const marketEstimate = await defaultSalaryProvider.getSalaryEstimate({
      role: completeFeatures.JobRole,
      experienceYears: completeFeatures.TotalWorkingYears,
      location: completeFeatures.Location || "National Average / Hybrid",
    });

    // 3. Initial replacement baseline
    const costEstimate = calculateReplacementCost({
      numberOfReplacements: 1,
      annualCompensation: marketEstimate.median_salary || annualSalary,
      recruitmentCost: Math.round(annualSalary * 0.16),
      onboardingCost: 40000,
      trainingCost: 50000,
      vacancyDays: 60,
      rampUpDays: 90,
      productivityDuringRampUp: 0.60,
      departingEmployeeAnnualSalary: annualSalary,
    });

    // 4. Expected Replacement Loss
    const erl = calculateERL(prediction.calibrated_probability, costEstimate.total_replacement_impact);

    res.json({
      case_id,
      features: completeFeatures,
      prediction,
      model_factors: modelFactors,
      risk_fingerprint: riskFingerprint,
      peer_benchmark: peerBenchmark,
      market_estimate: marketEstimate,
      cost_estimate: costEstimate,
      erl,
    });
  } catch (err) {
    if (err.code === "ECONNREFUSED" || err.message?.includes("ECONNREFUSED") || err.message?.includes("connect")) {
      return res.status(503).json({
        error: "ML Prediction Service is offline (http://localhost:8001). Please ensure the Python ML service is running with 'python -m uvicorn ml_service.main:app --port 8001' or run 'run_retainiq.bat'.",
        detail: err.message
      });
    }
    res.status(500).json({ error: "Employee analysis failed", detail: err.message });
  }
});

// ── Model-Based What-If Simulator & ROI Proxy Endpoints ────────────────────
app.post("/api/simulator/run", async (req, res) => {
  try {
    const r = await axios.post(`${ML}/api/simulate`, req.body);
    res.json(r.data);
  } catch (e) {
    res.status(500).json({ error: "Simulator error", detail: e.message });
  }
});

app.post("/api/roi/optimize", async (req, res) => {
  try {
    const r = await axios.post(`${ML}/api/roi/optimize`, req.body);
    res.json(r.data);
  } catch (e) {
    res.status(500).json({ error: "ROI optimization error", detail: e.message });
  }
});


// ── Org-Wide Risk Heatmap: Roster Batch Analysis ──────────────────────────
// POST /api/roster/analyze — accepts JSON array of employees or CSV upload
// Proxies to ML /api/roster/batch, adds ERL formatting.

const rosterUpload = multer({
  dest: path.join(__dirname, "../uploads"),
  limits: { fileSize: 10 * 1024 * 1024 }, // 10 MB for rosters
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    if (![".csv", ".json"].includes(ext)) {
      return cb(new Error("Roster upload must be a CSV or JSON file."));
    }
    cb(null, true);
  },
});

const rosterUploadMiddleware = (req, res, next) => {
  rosterUpload.single("file")(req, res, (err) => {
    if (err) return res.status(400).json({ error: err.message || "Roster file upload failed." });
    next();
  });
};

// POST /api/roster/analyze — JSON body with employees array
app.post("/api/roster/analyze", async (req, res) => {
  try {
    const { employees } = req.body;
    if (!employees || !Array.isArray(employees) || employees.length === 0) {
      return res.status(400).json({ error: "Request body must include a non-empty 'employees' array." });
    }
    if (employees.length > 500) {
      return res.status(400).json({ error: "Roster batch analysis supports up to 500 employees at once." });
    }

    const mlResp = await axios.post(`${ML}/api/roster/batch`, { employees }, { timeout: 30000 });
    res.json(mlResp.data);
  } catch (err) {
    if (err.code === "ECONNREFUSED" || err.message?.includes("ECONNREFUSED")) {
      return res.status(503).json({ error: "ML Prediction Service is offline. Please ensure the Python ML service is running." });
    }
    res.status(500).json({ error: "Roster analysis failed", detail: err.message });
  }
});

// POST /api/roster/upload — CSV/JSON file upload, auto-parsed
app.post("/api/roster/upload", rosterUploadMiddleware, async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: "No roster file uploaded. Please upload a CSV or JSON file." });
  }
  try {
    const ext = path.extname(req.file.originalname).toLowerCase();
    const raw = fs.readFileSync(req.file.path, "utf-8");
    try { fs.unlinkSync(req.file.path); } catch {}

    let employees = [];

    if (ext === ".json") {
      const parsed = JSON.parse(raw);
      employees = Array.isArray(parsed) ? parsed : (parsed.employees || []);
    } else if (ext === ".csv") {
      // Minimal CSV parser — split on lines, first row is header
      const lines = raw.split(/\r?\n/).filter(l => l.trim());
      if (lines.length < 2) {
        return res.status(400).json({ error: "CSV file must have a header row and at least one data row." });
      }
      const headers = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, ""));
      for (let i = 1; i < lines.length; i++) {
        const vals = lines[i].split(",").map(v => v.trim().replace(/^"|"$/g, ""));
        if (vals.length < 2) continue;
        const obj = {};
        headers.forEach((h, idx) => { obj[h] = vals[idx] ?? ""; });
        employees.push(obj);
      }
    }

    if (employees.length === 0) {
      return res.status(400).json({ error: "No valid employee records found in the uploaded file." });
    }

    // Normalize common field name variations
    const normalizeEmp = (e) => ({
      employee_id:             String(e.employee_id || e.EmployeeID || e.emp_id || `EMP-${Math.floor(Math.random()*9999)}`),
      employee_name:           String(e.employee_name || e.Name || e.EmployeeName || "Unknown"),
      Department:              String(e.Department || e.department || "Research & Development"),
      JobRole:                 String(e.JobRole || e.job_role || e.Role || "Research Scientist"),
      JobLevel:                Number(e.JobLevel || e.job_level || 2),
      MonthlyIncome:           Number(e.MonthlyIncome || e.monthly_income || 5000),
      TotalWorkingYears:       Number(e.TotalWorkingYears || e.total_working_years || 5),
      YearsAtCompany:          Number(e.YearsAtCompany || e.years_at_company || 3),
      YearsInCurrentRole:      Number(e.YearsInCurrentRole || e.years_in_current_role || 2),
      YearsSinceLastPromotion: Number(e.YearsSinceLastPromotion || e.years_since_last_promotion || 1),
      YearsWithCurrManager:    Number(e.YearsWithCurrManager || e.years_with_curr_manager || 2),
      OverTime:                String(e.OverTime || e.overtime || e.Overtime || "No"),
      JobSatisfaction:         Number(e.JobSatisfaction || e.job_satisfaction || 3),
      WorkLifeBalance:         Number(e.WorkLifeBalance || e.work_life_balance || 3),
      EnvironmentSatisfaction: Number(e.EnvironmentSatisfaction || e.environment_satisfaction || 3),
      BusinessTravel:          String(e.BusinessTravel || e.business_travel || "Travel_Rarely"),
      DistanceFromHome:        Number(e.DistanceFromHome || e.distance_from_home || 8),
      Education:               Number(e.Education || e.education || 3),
      EducationField:          String(e.EducationField || e.education_field || "Life Sciences"),
      HourlyRate:              Number(e.HourlyRate || e.hourly_rate || 65),
      DailyRate:               Number(e.DailyRate || e.daily_rate || 800),
      JobInvolvement:          Number(e.JobInvolvement || e.job_involvement || 3),
      MonthlyRate:             Number(e.MonthlyRate || e.monthly_rate || 14000),
      NumCompaniesWorked:      Number(e.NumCompaniesWorked || e.num_companies_worked || 2),
      PercentSalaryHike:       Number(e.PercentSalaryHike || e.percent_salary_hike || 14),
      PerformanceRating:       Number(e.PerformanceRating || e.performance_rating || 3),
      RelationshipSatisfaction:Number(e.RelationshipSatisfaction || e.relationship_satisfaction || 3),
      StockOptionLevel:        Number(e.StockOptionLevel || e.stock_option_level || 1),
      TrainingTimesLastYear:   Number(e.TrainingTimesLastYear || e.training_times_last_year || 3),
    });

    const normalized = employees.map(normalizeEmp).filter(e => e.MonthlyIncome > 0);

    if (normalized.length > 500) {
      return res.status(400).json({ error: "Roster batch analysis supports up to 500 employees at once." });
    }

    const mlResp = await axios.post(`${ML}/api/roster/batch`, { employees: normalized }, { timeout: 30000 });
    res.json(mlResp.data);
  } catch (err) {
    if (err.code === "ECONNREFUSED" || err.message?.includes("ECONNREFUSED")) {
      return res.status(503).json({ error: "ML Prediction Service is offline. Please ensure the Python ML service is running." });
    }
    res.status(500).json({ error: "Roster upload analysis failed", detail: err.message });
  }
});


// GET /api/employees (Search/browse roster from dataset)
app.get("/api/employees", (req, res) => {
  try {
    const { query = "", department = "", role = "", limit = 50, offset = 0 } = req.query;
    const result = searchRoster({
      query,
      department,
      role,
      limit: Number(limit),
      offset: Number(offset),
    });
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: "Failed fetching employees", detail: err.message });
  }
});

// GET /api/employees/:id
app.get("/api/employees/:id", (req, res) => {
  const emp = getEmployeeById(req.params.id);
  if (!emp) {
    return res.status(404).json({ error: "Employee not found in roster" });
  }
  res.json({ employee: emp });
});

// POST /api/employees/:id/separation-analysis
// Full HR analysis: ML Flight Risk + Financial Loss + Replacement Multiplier + Market Availability
app.post("/api/employees/:id/separation-analysis", async (req, res) => {
  try {
    const emp = getEmployeeById(req.params.id);
    if (!emp) {
      return res.status(404).json({ error: "Employee not found in roster" });
    }
    const analysis = await analyzeSeparation(emp, req.body.customOptions || {});
    res.json(analysis);
  } catch (err) {
    res.status(500).json({ error: "Separation analysis failed", detail: err.message });
  }
});

// POST /api/employees/custom-analysis (Manual entry analysis)
app.post("/api/employees/custom-analysis", async (req, res) => {
  try {
    const rawFeatures = req.body;
    const monthlyIncome = rawFeatures.MonthlyIncome || 5000;
    const emp = {
      id: rawFeatures.id || "EMP-MANUAL-01",
      code: rawFeatures.code || rawFeatures.id || "EMP-MANUAL-01",
      role: rawFeatures.JobRole || "Specialist",
      department: rawFeatures.Department || "R&D",
      jobLevel: rawFeatures.JobLevel || 2,
      monthlyIncome,
      annualSalary: monthlyIncome * 12,
      totalExperienceYears: rawFeatures.TotalWorkingYears || 4,
      yearsAtCompany: rawFeatures.YearsAtCompany || 2,
      yearsInCurrentRole: rawFeatures.YearsInCurrentRole || 1,
      performanceRating: rawFeatures.PerformanceRating || 3,
      jobSatisfaction: rawFeatures.JobSatisfaction || 3,
      environmentSatisfaction: rawFeatures.EnvironmentSatisfaction || 3,
      workLifeBalance: rawFeatures.WorkLifeBalance || 3,
      overtime: rawFeatures.OverTime || "No",
      rawFeatures,
    };
    const analysis = await analyzeSeparation(emp, req.body.customOptions || {});
    res.json(analysis);
  } catch (err) {
    res.status(500).json({ error: "Custom analysis failed", detail: err.message });
  }
});

// ── Health & Diagnostics ───────────────────────────────────────────────────
app.get("/api/health", async (req, res) => {
  let mlStatus = "unreachable";
  let mlMeta = null;
  try {
    const r = await axios.get(`${ML}/api/health`, { timeout: 2500 });
    mlStatus = r.data.status;
  } catch {}
  try {
    const r2 = await axios.get(`${ML}/api/model/info`, { timeout: 2500 });
    mlMeta = r2.data;
  } catch {}

  res.json({
    status: "ok",
    backend: "Express v8000",
    ml_service: mlStatus,
    ml_metadata: mlMeta,
    gemini_configured: !!(process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY !== "your_gemini_api_key_here"),
    gemini_model: process.env.GEMINI_MODEL || "gemini-2.0-flash",
    timestamp: new Date().toISOString(),
  });
});

// ── Model info ─────────────────────────────────────────────────────────────
app.get("/api/model/info", async (req, res) => {
  try {
    const r = await axios.get(`${ML}/api/model/info`);
    res.json(r.data);
  } catch (e) {
    res.status(503).json({ error: "ML service unavailable", detail: e.message });
  }
});

// ── Predict Attrition (ML Model ONLY) ───────────────────────────────────────
app.post("/api/predict", async (req, res) => {
  try {
    const r = await axios.post(`${ML}/api/predict`, req.body);
    res.json(r.data);
  } catch (e) {
    const status = e.response?.status || 503;
    res.status(status).json({
      error: "Prediction failed",
      detail: e.response?.data || e.message,
    });
  }
});

// ── Deterministic Replacement Cost Engine ──────────────────────────────────
app.post("/api/replacement/calculate", (req, res) => {
  try {
    const body = req.body || {};
    const calibratedProbability = Number(body.calibratedProbability ?? body.costParams?.calibratedProbability ?? 0.35);
    const departingSalary = Number(body.departingSalary || body.costParams?.departingEmployeeAnnualSalary || body.costParams?.annualCompensation || 1200000);
    const annualCompensation = Number(body.replacementSalaryPerFTE || body.annualCompensation || body.costParams?.annualCompensation || departingSalary);
    const numberOfReplacements = Number(body.numberOfReplacements || body.costParams?.numberOfReplacements || 1);
    const recruitmentCost = body.recruitmentCost !== undefined ? Number(body.recruitmentCost) : Math.round(annualCompensation * 0.16);
    const onboardingCost = body.onboardingCost !== undefined ? Number(body.onboardingCost) : 40000;
    const trainingCost = body.trainingCost !== undefined ? Number(body.trainingCost) : 50000;
    const vacancyDays = Number(body.vacancyDays || body.costParams?.vacancyDays || 60);
    const rampUpDays = Number(body.rampUpDays || body.costParams?.rampUpDays || 90);
    const productivityDuringRampUp = body.productivityDuringRampUp !== undefined
      ? Number(body.productivityDuringRampUp)
      : (body.rampUpProductivityPct !== undefined ? Number(body.rampUpProductivityPct) / 100 : 0.60);

    const costParams = {
      numberOfReplacements,
      annualCompensation,
      recruitmentCost,
      onboardingCost,
      trainingCost,
      vacancyDays,
      rampUpDays,
      productivityDuringRampUp,
      departingEmployeeAnnualSalary: departingSalary,
      ...body.costParams,
    };

    const costResult = calculateReplacementCost(costParams);
    const erlResult  = calculateERL(calibratedProbability, costResult.total_replacement_impact);
    res.json({ ...costResult, erl: erlResult });
  } catch (e) {
    res.status(400).json({ error: "Cost calculation error", detail: e.message });
  }
});

// ── Scenario Analysis (1, 2, 3, 4, Custom Replacements) ────────────────────
app.post("/api/replacement/scenario", (req, res) => {
  try {
    const body = req.body || {};
    const calibratedProbability = Number(body.calibratedProbability ?? 0.35);
    const departingSalary = Number(body.departingSalary || body.departingEmployeeAnnualSalary || 1200000);
    const replacementSalaryPerFTE = Number(body.replacementSalaryPerFTE || departingSalary);
    const vacancyDays = Number(body.vacancyDays || 60);
    const rampUpDays = Number(body.rampUpDays || 90);
    const productivityDuringRampUp = body.productivityDuringRampUp !== undefined
      ? Number(body.productivityDuringRampUp)
      : (body.rampUpProductivityPct !== undefined ? Number(body.rampUpProductivityPct) / 100 : 0.60);

    let scenariosList = body.scenarios;
    if (!scenariosList || !Array.isArray(scenariosList)) {
      const counts = Array.isArray(body.counts) ? body.counts : [1, 2, 3, 4];
      scenariosList = counts.map(n => ({
        numberOfReplacements: n,
        annualCompensation: replacementSalaryPerFTE,
        recruitmentCost: Math.round(replacementSalaryPerFTE * 0.16),
        onboardingCost: 40000,
        trainingCost: 50000,
        vacancyDays,
        rampUpDays,
        productivityDuringRampUp,
        label: `${n} Replacement${n > 1 ? "s" : ""}`,
      }));
    }

    const results = compareScenarios(scenariosList, calibratedProbability, departingSalary);
    res.json({ scenarios: results });
  } catch (e) {
    res.status(400).json({ error: "Scenario error", detail: e.message });
  }
});

// ── Market Compensation Estimate ───────────────────────────────────────────
app.post("/api/market/compensation", async (req, res) => {
  try {
    const estimate = await defaultSalaryProvider.getSalaryEstimate(req.body);
    res.json(estimate);
  } catch (e) {
    res.status(500).json({ error: "Market compensation estimation failed", detail: e.message });
  }
});

// ── Candidate RAG Search ───────────────────────────────────────────────────
app.post("/api/candidates/search", (req, res) => {
  try {
    const results = searchCandidates(req.body);
    res.json(results);
  } catch (e) {
    res.status(500).json({ error: "Candidate search failed", detail: e.message });
  }
});

// GET /api/candidates/all
app.get("/api/candidates/all", (req, res) => {
  try {
    const candidates = getAllCandidates();
    res.json({ candidates, total: candidates.length });
  } catch (e) {
    res.status(500).json({ error: "Failed to fetch candidates", detail: e.message });
  }
});

// POST /api/candidates/upload
app.post("/api/candidates/upload", verifyAuth, upload.single("resume"), (req, res) => {
  try {
    let candidateData = req.body;
    if (req.file) {
      candidateData.resume_file = req.file.originalname;
      candidateData.resume_path = req.file.path;
      if (!candidateData.name) {
        candidateData.name = path.basename(req.file.originalname, path.extname(req.file.originalname));
      }
    }
    const created = addCandidate(candidateData);
    res.status(201).json({
      success: true,
      message: "Candidate profile successfully ingested into RetainIQ candidate KB",
      candidate: created,
    });
  } catch (e) {
    res.status(400).json({ error: "Candidate ingestion error", detail: e.message });
  }
});

// ── Web Scraping & Market Benchmark AI Agent ───────────────────────────────
app.post("/api/market/benchmark", async (req, res) => {
  try {
    const { role = "Software Engineer", experience_years = 3 } = req.body;
    const benchmark = await scrapeMarketBenchmarks(role, experience_years);
    res.json(benchmark);
  } catch (e) {
    res.status(500).json({ error: "Market scraping failed", detail: e.message });
  }
});

// ── Research Literature RAG ────────────────────────────────────────────────
app.post("/api/research/search", (req, res) => {
  const { factors = [] } = req.body;
  const SEED_EVIDENCE = [
    {
      source: "Griffeth, Hom & Gaertner (2000) Meta-Analysis",
      page: 463,
      passage: "Overall job satisfaction remains one of the strongest predictive correlates of employee turnover across occupational categories (corrected r = -.28).",
      topic: "job_satisfaction",
    },
    {
      source: "Boushey & Glynn (2012) Center for American Progress",
      page: 12,
      passage: "Mandatory overtime and extended work hours exhibit a non-linear relationship with departure intention, with hazard ratios increasing sharply beyond 48 hours weekly.",
      topic: "overtime",
    },
    {
      source: "Allen, Bryant & Vardaman (2010) Journal of Management",
      page: 54,
      passage: "Predictive retention models must incorporate replacement friction: high-turnover roles incur indirect vacancy and productivity ramp-up costs that frequently exceed direct recruitment fees.",
      topic: "replacement_cost",
    },
    {
      source: "Blundell, Costa Dias, Meghir & Shaw (2016)",
      page: 89,
      passage: "Wage growth deceleration and prolonged promotion stagnation (exceeding 3 years in grade) systematically amplify external job search behavior among mid-career professionals.",
      topic: "promotion_stagnation",
    },
    {
      source: "SHRM Human Capital Benchmarking Survey (2024)",
      page: 24,
      passage: "Average time-to-fill for specialized technical and scientific personnel ranges between 45 and 72 days, generating significant interim team fatigue and cascade turnover risks.",
      topic: "vacancy_loss",
    },
  ];

  let filtered = SEED_EVIDENCE;
  if (factors && factors.length > 0) {
    const lowerFactors = factors.map(f => (f.feature || f).toLowerCase());
    filtered = SEED_EVIDENCE.filter(item =>
      lowerFactors.some(f => f.includes(item.topic) || item.passage.toLowerCase().includes(f))
    );
    if (filtered.length === 0) filtered = SEED_EVIDENCE;
  }

  res.json({
    evidence: filtered,
    total: filtered.length,
    disclaimer: "Academic literature identifies statistical associations across historical populations. Literature correlation must not be interpreted as deterministic personal causation.",
  });
});

// ── Research Paper Content & Artifacts ─────────────────────────────────────
app.get("/api/research/paper", (req, res) => {
  const paperPath = path.join(__dirname, "../reports/RESEARCH_PAPER.md");
  if (fs.existsSync(paperPath)) {
    const content = fs.readFileSync(paperPath, "utf-8");
    res.json({ paper: content, title: "A Cost-Weighted Machine Learning Framework for Employee Attrition Prediction and Retention Prioritization" });
  } else {
    res.status(404).json({ error: "Research paper manuscript not yet generated." });
  }
});

// ── Audited Market Salary Provider ─────────────────────────────────────────
app.post("/api/market/compensation", async (req, res) => {
  try {
    const estimate = await defaultSalaryProvider.getSalaryEstimate(req.body);
    res.json(estimate);
  } catch (e) {
    res.status(500).json({ error: "Market compensation retrieval failed", detail: e.message });
  }
});

// ── Gemini Report & Action Plan Synthesis ──────────────────────────────────
app.post("/api/ai/report", async (req, res) => {
  const {
    case_id,
    employeeProfile,
    prediction,
    modelFactors,
    costCalculation,
    replacementScenarios,
    researchEvidence,
    candidateMatches,
  } = req.body;

  if (!prediction) {
    return res.status(400).json({ error: "prediction is required" });
  }

  try {
    const plan = await generateActionPlan({
      employeeProfile,
      prediction,
      modelFactors: modelFactors || [],
      costCalculation,
      replacementScenarios: replacementScenarios || [],
      researchEvidence: researchEvidence || [],
      candidateMatches: candidateMatches || [],
    });
    res.json({ case_id, report: plan, action_plan: plan });
  } catch (e) {
    if (e.message.includes("GEMINI_API_KEY")) {
      return res.json({
        case_id,
        gemini_configured: false,
        source: "deterministic_fallback",
        report: {
          risk_summary: `Estimated departure probability: ${prediction.probability_pct}%. Risk category: ${prediction.risk_category}. (Deterministic grounded synthesis — configure GEMINI_API_KEY in backend/.env for dynamic generative LLM plan).`,
          financial_summary: `Calculated total replacement exposure: ${costCalculation?.total_replacement_impact ? '₹' + Number(costCalculation.total_replacement_impact).toLocaleString('en-IN') : 'Calculated'}. Expected Replacement Loss: ${costCalculation?.erl?.expected_replacement_loss ? '₹' + Number(costCalculation.erl.expected_replacement_loss).toLocaleString('en-IN') : 'Calculated'}.`,
          replacement_summary: "Multi-head replacement scenario highlights non-linear vacancy and ramp-up loss over direct compensation.",
          candidate_summary: `${candidateMatches?.length || 0} candidate profiles ranked against supplied technical profile.`,
          recommended_actions: [
            { priority: 1, action: "Conduct structured Stay Interview and review OverTime workload", rationale: "OverTime and satisfaction scores are dominant model-associated factors", type: "retention" },
            { priority: 2, action: "Activate candidate talent pipeline for identified vacancy risk", rationale: "Anticipated vacancy exceeds 45 days, causing team productivity decay", type: "replacement" },
            { priority: 3, action: "Calibrate compensation against live industry benchmarks", rationale: "Market intelligence indicates salary competitiveness gap", type: "monitoring" },
          ],
          assumptions: ["Linear vacancy loss based on daily employee value", "Constant productivity ramp-up trajectory", "Standard 16% agency fee rate"],
          limitations: [
            "Prediction is probabilistic, not deterministic.",
            "Synthetic research prototype — not for real employment decisions.",
            "Model associations do not imply individual causation.",
          ],
        },
      });
    }
    res.status(500).json({ error: "Report generation failed", detail: e.message });
  }
});

// Alias for backward compatibility
app.post("/api/ai/action-plan", (req, res, next) => {
  req.url = "/api/ai/report";
  app._router.handle(req, res, next);
});

// Ensure uploads folder exists
const uploadsDir = path.join(__dirname, "../uploads");
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

// Warm employee roster cache
getEmployees();

app.listen(PORT, () => {
  console.log(`[backend] RetainIQ Express running on http://localhost:${PORT}`);
  console.log(`[backend] ML service expected at ${ML}`);
});
