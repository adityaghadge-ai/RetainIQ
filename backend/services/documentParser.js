// backend/services/documentParser.js
// ===================================
// Robust Document Extraction & Normalization Service for RetainIQ.
// Supports: PDF, CSV, XLSX, JSON employee records.
//
// Complies strictly with RetainIQ enterprise requirements:
// - Never hallucinates or fabricates missing required values.
// - Accurately normalizes data into internal employee schema.
// - Excludes target/demographics from predictive model input.
// - Supports single-row and multi-row datasets (with record selection).
// - Supports multi-sheet Excel workbooks (with sheet selection).

import fs from "fs";
import path from "path";
import * as xlsx from "xlsx";
import { PDFParse } from "pdf-parse";

// Official supported extensions
export const SUPPORTED_EXTENSIONS = [".pdf", ".csv", ".xlsx", ".xls", ".json"];

// Primary fields required by the ML model & deterministic cost engine
export const MANDATORY_FIELDS = [
  { key: "JobRole", aliases: ["job_role", "role", "designation", "position", "title"], label: "Job Role" },
  { key: "Department", aliases: ["department", "dept", "division", "business_unit"], label: "Department" },
  { key: "MonthlyIncome", aliases: ["monthly_income", "monthly_salary", "salary_per_month", "income", "annualsalary", "annualctc", "salary", "ctc"], label: "Monthly Income (or Annual Salary)" },
  { key: "TotalWorkingYears", aliases: ["total_working_years", "total_experience", "experience_years", "expyears", "experience", "totalexperienceyears"], label: "Total Working Years" },
  { key: "YearsAtCompany", aliases: ["years_at_company", "tenure", "tenure_years", "company_tenure", "companytenure"], label: "Years at Company" },
  { key: "OverTime", aliases: ["overtime", "over_time", "works_overtime", "ot"], label: "Overtime (Yes / No)" },
  { key: "JobSatisfaction", aliases: ["job_satisfaction", "satisfaction_level", "job_sat", "jobsatisfactionscore"], label: "Job Satisfaction (1–4)" },
];

// Secondary features with standard operational defaults if omitted from résumé / record
export const SECONDARY_DEFAULTS = {
  BusinessTravel: "Travel_Rarely",
  DailyRate: 800,
  DistanceFromHome: 8,
  Education: 3,
  EducationField: "Life Sciences",
  EnvironmentSatisfaction: 3,
  HourlyRate: 65,
  JobInvolvement: 3,
  JobLevel: 2,
  MonthlyRate: 14000,
  NumCompaniesWorked: 2,
  PercentSalaryHike: 14,
  PerformanceRating: 3,
  RelationshipSatisfaction: 3,
  StockOptionLevel: 1,
  TrainingTimesLastYear: 3,
  WorkLifeBalance: 3,
  YearsInCurrentRole: 2,
  YearsSinceLastPromotion: 1,
  YearsWithCurrManager: 2,
};

// Demographic & administrative fields retained for auditing/display, excluded from predictive model features
export const EXCLUDED_FROM_MODEL_INPUTS = [
  "Age",
  "Attrition",
  "EmployeeCount",
  "EmployeeNumber",
  "Gender",
  "MaritalStatus",
  "Over18",
  "StandardHours",
];

/**
 * Generate privacy-preserving Case Reference ID (e.g. EMP-1042)
 */
export function generateCaseId(prefix = "EMP") {
  const num = Math.floor(1000 + Math.random() * 9000);
  return `${prefix}-${num}`;
}

/**
 * Parse an employee document from disk buffer.
 */
export async function parseEmployeeDocument(filePath, originalFilename = "") {
  const filename = originalFilename || filePath;
  const ext = path.extname(filename).toLowerCase();

  if (!SUPPORTED_EXTENSIONS.includes(ext)) {
    throw new Error("Unsupported format. Please upload a PDF, CSV, XLSX, or JSON employee record.");
  }

  let structuredRecords = [];
  let multiSheet = false;
  let sheetNames = [];
  let sheetsData = {};

  if (ext === ".json") {
    structuredRecords = parseJsonFile(filePath);
  } else if (ext === ".csv") {
    structuredRecords = parseCsvFile(filePath);
  } else if (ext === ".xlsx" || ext === ".xls") {
    const xlsxResult = parseXlsxFile(filePath);
    if (xlsxResult.multi_sheet) {
      multiSheet = true;
      sheetNames = xlsxResult.sheet_names;
      sheetsData = xlsxResult.sheets_data;
      structuredRecords = xlsxResult.selected_sheet_records || [];
    } else {
      structuredRecords = xlsxResult.records || [];
    }
  } else if (ext === ".pdf") {
    structuredRecords = await parsePdfFile(filePath);
  }

  if (!structuredRecords || structuredRecords.length === 0) {
    if (ext === ".pdf") {
      throw new Error("Could not extract employee information from this PDF.");
    } else {
      throw new Error("Employee record is missing required fields: Job Role, Department, Monthly Income, Total Working Years, Years at Company, Overtime, Job Satisfaction");
    }
  }

  // Normalize all extracted records
  const normalizedRecords = structuredRecords.map((rawRec, idx) => {
    const normalized = normalizeExtractedFields(rawRec);
    const missing = getMissingMandatoryFields(normalized);
    const caseId = normalized.EmployeeNumber
      ? `EMP-${normalized.EmployeeNumber}`
      : normalized.CaseId || generateCaseId("EMP");

    return {
      index: idx,
      case_id: caseId,
      extracted_features: normalized,
      missing_fields: missing,
      is_complete: missing.length === 0,
      summary: {
        role: normalized.JobRole || "Unspecified Role",
        department: normalized.Department || "Unspecified Dept",
        experience: normalized.TotalWorkingYears != null ? `${normalized.TotalWorkingYears} yrs` : "--",
        tenure: normalized.YearsAtCompany != null ? `${normalized.YearsAtCompany} yrs` : "--",
        salary: normalized.AnnualSalary ? `₹${Number(normalized.AnnualSalary).toLocaleString('en-IN')}/yr` : (normalized.MonthlyIncome ? `₹${Number(normalized.MonthlyIncome).toLocaleString('en-IN')}/mo` : "--"),
        overtime: normalized.OverTime || "--",
        satisfaction: normalized.JobSatisfaction != null ? `${normalized.JobSatisfaction}/4` : "--",
      }
    };
  });

  // Default to first record
  const defaultSelected = normalizedRecords[0];

  return {
    source_filename: path.basename(filename),
    file_type: ext.replace(".", "").toUpperCase(),
    multi_sheet: multiSheet,
    sheet_names: sheetNames,
    sheets_data: sheetsData,
    records_count: normalizedRecords.length,
    multi_record: normalizedRecords.length > 1,
    records: normalizedRecords,
    // Active selected record properties
    case_id: defaultSelected.case_id,
    extracted_features: defaultSelected.extracted_features,
    missing_fields: defaultSelected.missing_fields,
    is_complete: defaultSelected.is_complete,
  };
}

/**
 * JSON File Parser
 */
function parseJsonFile(filePath) {
  let parsed;
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    parsed = JSON.parse(raw);
  } catch {
    throw new Error("Invalid JSON format. Please upload a valid employee record.");
  }

  if (Array.isArray(parsed)) {
    return parsed.filter(item => item && typeof item === "object");
  }

  if (parsed && typeof parsed === "object") {
    // Check for standard wrapper keys
    if (Array.isArray(parsed.employees)) return parsed.employees;
    if (Array.isArray(parsed.records)) return parsed.records;
    if (Array.isArray(parsed.data)) return parsed.data;

    if (parsed.employee && typeof parsed.employee === "object") return [parsed.employee];
    if (parsed.record && typeof parsed.record === "object") return [parsed.record];
    if (parsed.data && typeof parsed.data === "object" && !Array.isArray(parsed.data)) return [parsed.data];

    return [parsed];
  }

  throw new Error("Invalid JSON format. Please upload a valid employee record.");
}

/**
 * CSV File Parser
 */
function parseCsvFile(filePath) {
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    const workbook = xlsx.read(raw, { type: "string", raw: true });
    const firstSheetName = workbook.SheetNames[0];
    if (!firstSheetName) return [];
    const sheet = workbook.Sheets[firstSheetName];
    const rows = xlsx.utils.sheet_to_json(sheet, { defval: null });
    return rows;
  } catch (err) {
    if (err.message && err.message.includes("missing required fields")) throw err;
    throw new Error("Invalid CSV format. Please upload a valid employee record.");
  }
}

/**
 * XLSX File Parser
 */
function parseXlsxFile(filePath) {
  try {
    const buffer = fs.readFileSync(filePath);
    const workbook = xlsx.read(buffer, { type: "buffer" });
    const sheetNames = workbook.SheetNames || [];

    if (sheetNames.length === 0) return { records: [] };

    if (sheetNames.length > 1) {
      const sheetsData = {};
      for (const name of sheetNames) {
        const sheet = workbook.Sheets[name];
        const rows = xlsx.utils.sheet_to_json(sheet, { defval: null });
        sheetsData[name] = rows.map((r, i) => {
          const norm = normalizeExtractedFields(r);
          return {
            index: i,
            extracted_features: norm,
            missing_fields: getMissingMandatoryFields(norm),
          };
        });
      }

      const firstSheet = workbook.Sheets[sheetNames[0]];
      const firstRows = xlsx.utils.sheet_to_json(firstSheet, { defval: null });

      return {
        multi_sheet: true,
        sheet_names: sheetNames,
        sheets_data: sheetsData,
        selected_sheet_records: firstRows,
      };
    }

    const sheet = workbook.Sheets[sheetNames[0]];
    const rows = xlsx.utils.sheet_to_json(sheet, { defval: null });
    return { multi_sheet: false, records: rows };
  } catch (err) {
    throw new Error("Invalid XLSX file. Please upload a valid employee record.");
  }
}

/**
 * PDF File Parser
 */
async function parsePdfFile(filePath) {
  let text = "";
  try {
    const dataBuffer = fs.readFileSync(filePath);
    const parser = new PDFParse({ data: dataBuffer });
    const res = await parser.getText();
    text = res?.text || "";
  } catch {
    throw new Error("Could not extract employee information from this PDF.");
  }

  if (!text || text.trim().length < 10) {
    throw new Error("Could not extract employee information from this PDF.");
  }

  const structured = parseTextToStructured(text);
  const normalized = normalizeExtractedFields(structured);

  // Check if at least some core fields were found
  const foundCount = MANDATORY_FIELDS.filter(f => normalized[f.key] !== undefined && normalized[f.key] !== null).length;
  if (foundCount === 0) {
    throw new Error("Could not extract employee information from this PDF.");
  }

  return [normalized];
}

/**
 * Parse unstructured text lines & regex patterns into structured fields
 */
function parseTextToStructured(text) {
  const result = {};
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);

  // 1. Line-by-line key: value extraction
  for (const line of lines) {
    const match = line.match(/^([^:\-—•]+)[:\-—]\s*(.+)$/);
    if (match) {
      const rawKey = match[1].trim();
      const rawVal = match[2].trim();
      result[rawKey] = rawVal;
    }
  }

  // 2. Pattern-based heuristic fallbacks for common HR format templates
  if (!result.JobRole && !result.Role && !result.Designation) {
    const roleMatch = text.match(/(?:Role|Job\s*Role|Designation|Position|Title)\s*[:\-\s]\s*([A-Za-z0-9\s&/]+)/i);
    if (roleMatch) result.JobRole = roleMatch[1].trim().split("\n")[0];
  }

  if (!result.Department && !result.Dept) {
    const deptMatch = text.match(/(?:Department|Dept|Division|Business\s*Unit)\s*[:\-\s]\s*([A-Za-z0-9\s&/]+)/i);
    if (deptMatch) result.Department = deptMatch[1].trim().split("\n")[0];
  }

  if (!result.MonthlyIncome && !result.Salary && !result.AnnualSalary && !result.CTC) {
    const salaryMatch = text.match(/(?:Monthly\s*Salary|Monthly\s*Income|Salary|Compensation|CTC|Annual\s*Package)\s*[:\-\s]*([₹$€£]?\s*[\d,]+(?:\.\d+)?)/i);
    if (salaryMatch) result.MonthlyIncome = salaryMatch[1].trim();
  }

  if (!result.TotalWorkingYears && !result.Experience) {
    const expMatch = text.match(/(?:Total\s*Experience|Total\s*Working\s*Years|Experience|Exp)\s*[:\-\s]*(\d+(?:\.\d+)?)\s*(?:years|yrs)?/i);
    if (expMatch) result.TotalWorkingYears = expMatch[1].trim();
  }

  if (!result.YearsAtCompany && !result.Tenure) {
    const tenureMatch = text.match(/(?:Years\s*at\s*Company|Company\s*Tenure|Tenure)\s*[:\-\s]*(\d+(?:\.\d+)?)\s*(?:years|yrs)?/i);
    if (tenureMatch) result.YearsAtCompany = tenureMatch[1].trim();
  }

  if (!result.OverTime) {
    const otMatch = text.match(/(?:OverTime|Over\s*Time|Works\s*Overtime)\s*[:\-\s]*(Yes|No|True|False)/i);
    if (otMatch) result.OverTime = otMatch[1].trim();
  }

  if (!result.JobSatisfaction) {
    const satMatch = text.match(/(?:Job\s*Satisfaction|Satisfaction\s*Score|Satisfaction)\s*[:\-\s]*(\d)/i);
    if (satMatch) result.JobSatisfaction = satMatch[1].trim();
  }

  return result;
}

/**
 * Check missing mandatory fields
 */
function getMissingMandatoryFields(record) {
  const missing = [];
  for (const field of MANDATORY_FIELDS) {
    const val = record[field.key];
    if (val === undefined || val === null || val === "" || (typeof val === "number" && isNaN(val))) {
      missing.push({ key: field.key, label: field.label });
    }
  }
  return missing;
}

function cleanStr(val) {
  if (val === undefined || val === null) return undefined;
  const s = String(val).replace(/^["'\s]+|["',\s]+$/g, "").trim();
  return s.length > 0 ? s : undefined;
}

function parseNumber(val) {
  if (val === undefined || val === null || val === "") return undefined;
  if (typeof val === "number") return isNaN(val) ? undefined : val;
  const cleaned = String(val).replace(/[^0-9.-]/g, "");
  if (!cleaned) return undefined;
  const num = parseFloat(cleaned);
  return isNaN(num) ? undefined : num;
}

function findValue(map, candidates) {
  for (const c of candidates) {
    const clean = c.replace(/[^a-z0-9]/g, "");
    if (map[clean] !== undefined && map[clean] !== null && map[clean] !== "") {
      return map[clean];
    }
  }
  return undefined;
}

/**
 * Standardize & normalize extracted fields into internal schema.
 * Note: Never generates placeholder 0s or random values for missing data.
 */
export function normalizeExtractedFields(input) {
  if (!input || typeof input !== "object") return {};
  const out = {};
  const lowerInput = {};

  // Build lowercase alphanumeric lookup map
  for (const [k, v] of Object.entries(input)) {
    if (v !== undefined && v !== null && v !== "") {
      const cleanKey = k.toLowerCase().replace(/[^a-z0-9]/g, "");
      lowerInput[cleanKey] = v;
    }
  }

  // 1. Role
  const roleVal = findValue(lowerInput, ["jobrole", "role", "designation", "position", "title"]);
  if (roleVal !== undefined) out.JobRole = cleanStr(roleVal);

  // 2. Department
  const deptVal = findValue(lowerInput, ["department", "dept", "division", "businessunit"]);
  if (deptVal !== undefined) out.Department = cleanStr(deptVal);

  // 3. Compensation
  const annualVal = findValue(lowerInput, ["annualsalary", "annualctc", "ctc", "package", "annualcompensation", "annualincome"]);
  const monthlyVal = findValue(lowerInput, ["monthlyincome", "monthlysalary", "income", "salary", "monthlycompensation"]);

  if (monthlyVal !== undefined) {
    const parsed = parseNumber(monthlyVal);
    if (parsed !== undefined) {
      out.MonthlyIncome = parsed;
      out.AnnualSalary = parsed * 12;
    }
  } else if (annualVal !== undefined) {
    const parsed = parseNumber(annualVal);
    if (parsed !== undefined) {
      out.AnnualSalary = parsed;
      out.MonthlyIncome = Math.round(parsed / 12);
    }
  }

  // 4. Experience & Tenure
  const twy = findValue(lowerInput, ["totalworkingyears", "totalexperience", "experienceyears", "expyears", "experience", "totalexperienceyears"]);
  if (twy !== undefined) {
    const p = parseNumber(twy);
    if (p !== undefined) out.TotalWorkingYears = p;
  }

  const yac = findValue(lowerInput, ["yearsatcompany", "tenure", "tenureyears", "companytenure", "tenureatcompany"]);
  if (yac !== undefined) {
    const p = parseNumber(yac);
    if (p !== undefined) out.YearsAtCompany = p;
  }

  const yir = findValue(lowerInput, ["yearsincurrentrole", "yearsrole", "roletenure", "yearsinrole"]);
  if (yir !== undefined) {
    const p = parseNumber(yir);
    if (p !== undefined) out.YearsInCurrentRole = p;
  }

  const ysp = findValue(lowerInput, ["yearssincelastpromotion", "yearssincepromotion", "promotionevery", "lastpromotionyears"]);
  if (ysp !== undefined) {
    const p = parseNumber(ysp);
    if (p !== undefined) out.YearsSinceLastPromotion = p;
  }

  const ywm = findValue(lowerInput, ["yearswithcurrmanager", "yearswithmanager", "managertenure", "tenurewithmanager"]);
  if (ywm !== undefined) {
    const p = parseNumber(ywm);
    if (p !== undefined) out.YearsWithCurrManager = p;
  }

  // 5. Work conditions
  const ot = findValue(lowerInput, ["overtime", "over_time", "worksovertime", "ot"]);
  if (ot !== undefined) {
    const str = String(ot).toLowerCase().trim();
    out.OverTime = (str === "yes" || str === "y" || str === "1" || str === "true" || str.includes("yes")) ? "Yes" : "No";
  }

  const js = findValue(lowerInput, ["jobsatisfaction", "satisfactionlevel", "jobsat", "jobsatisfactionscore"]);
  if (js !== undefined) {
    const p = parseNumber(js);
    if (p !== undefined) out.JobSatisfaction = Math.min(4, Math.max(1, Math.round(p)));
  }

  const jl = findValue(lowerInput, ["joblevel", "senioritylevel", "grade", "level"]);
  if (jl !== undefined) {
    const p = parseNumber(jl);
    if (p !== undefined) out.JobLevel = Math.min(5, Math.max(1, Math.round(p)));
  }

  const perf = findValue(lowerInput, ["performancerating", "performance", "rating"]);
  if (perf !== undefined) {
    const p = parseNumber(perf);
    if (p !== undefined) out.PerformanceRating = Math.min(4, Math.max(1, Math.round(p)));
  }

  const env = findValue(lowerInput, ["environmentsatisfaction", "envsat", "environmentsat"]);
  if (env !== undefined) {
    const p = parseNumber(env);
    if (p !== undefined) out.EnvironmentSatisfaction = Math.min(4, Math.max(1, Math.round(p)));
  }

  const wlb = findValue(lowerInput, ["worklifebalance", "wlb", "worklife"]);
  if (wlb !== undefined) {
    const p = parseNumber(wlb);
    if (p !== undefined) out.WorkLifeBalance = Math.min(4, Math.max(1, Math.round(p)));
  }

  const ed = findValue(lowerInput, ["education", "educationlevel", "degreelevel"]);
  if (ed !== undefined) {
    const p = parseNumber(ed);
    if (p !== undefined) out.Education = Math.min(5, Math.max(1, Math.round(p)));
  }

  const edField = findValue(lowerInput, ["educationfield", "degree", "major", "fieldofstudy"]);
  if (edField !== undefined) out.EducationField = cleanStr(edField);

  // Demographics & Identifiers (auditing / record-keeping only, not predictive inputs)
  const age = findValue(lowerInput, ["age"]);
  if (age !== undefined) {
    const p = parseNumber(age);
    if (p !== undefined) out.Age = p;
  }

  const gender = findValue(lowerInput, ["gender", "sex"]);
  if (gender !== undefined) out.Gender = cleanStr(gender);

  const marital = findValue(lowerInput, ["maritalstatus", "marital"]);
  if (marital !== undefined) out.MaritalStatus = cleanStr(marital);

  const empNum = findValue(lowerInput, ["employeenumber", "employeeid", "empid", "id", "casenumber"]);
  if (empNum !== undefined) out.EmployeeNumber = cleanStr(empNum);

  const location = findValue(lowerInput, ["location", "city", "office", "worklocation"]);
  if (location !== undefined) out.Location = cleanStr(location);

  // Return clean merged object with normalized fields overriding raw values
  return { ...input, ...out };
}
