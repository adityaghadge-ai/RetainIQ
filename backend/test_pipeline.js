// backend/test_pipeline.js
// Automated test suite for RetainIQ Document Ingestion & Extraction Pipeline

import fs from "fs";
import path from "path";
import * as xlsx from "xlsx";
import { parseEmployeeDocument } from "./services/documentParser.js";

const TEST_DIR = path.join(process.cwd(), "test_data_temp");
if (!fs.existsSync(TEST_DIR)) {
  fs.mkdirSync(TEST_DIR, { recursive: true });
}

console.log("==================================================");
console.log("RETAINIQ PIPELINE AUTOMATED TEST SUITE");
console.log("==================================================");

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`[PASS] ${message}`);
    passed++;
  } else {
    console.error(`[FAIL] ${message}`);
    failed++;
  }
}

async function runTests() {
  // ── TEST 1: Valid JSON ──────────────────────────────────────────────────
  const validJsonPath = path.join(TEST_DIR, "valid_emp.json");
  const validJsonContent = {
    JobRole: "Senior Software Engineer",
    Department: "Research & Development",
    TotalWorkingYears: 6,
    MonthlyIncome: 175000,
    AnnualSalary: 2100000,
    YearsAtCompany: 3,
    YearsSinceLastPromotion: 2,
    YearsInCurrentRole: 2,
    YearsWithCurrManager: 2,
    OverTime: "Yes",
    JobSatisfaction: 2,
    PerformanceRating: 4,
    WorkLifeBalance: 2,
    JobLevel: 3,
    Location: "Pune",
    Age: 32,
    Gender: "Male",
    MaritalStatus: "Single"
  };
  fs.writeFileSync(validJsonPath, JSON.stringify(validJsonContent, null, 2));

  try {
    const res = await parseEmployeeDocument(validJsonPath, "valid_emp.json");
    assert(res.is_complete === true, "Test 1: Valid JSON parsed successfully with complete features");
    assert(res.extracted_features.JobRole === "Senior Software Engineer", "Test 1: Correct JobRole extracted");
    assert(res.extracted_features.MonthlyIncome === 175000, "Test 1: Correct MonthlyIncome extracted");
  } catch (e) {
    assert(false, `Test 1: Valid JSON failed: ${e.message}`);
  }

  // ── TEST 2: Valid CSV ───────────────────────────────────────────────────
  const validCsvPath = path.join(TEST_DIR, "valid_emp.csv");
  const validCsvContent = "JobRole,Department,TotalWorkingYears,MonthlyIncome,YearsAtCompany,OverTime,JobSatisfaction\nResearch Scientist,Research & Development,5,85000,3,No,3\n";
  fs.writeFileSync(validCsvPath, validCsvContent);

  try {
    const res = await parseEmployeeDocument(validCsvPath, "valid_emp.csv");
    assert(res.is_complete === true, "Test 2: Valid CSV parsed successfully");
    assert(res.extracted_features.JobRole === "Research Scientist", "Test 2: CSV JobRole matches");
    assert(res.extracted_features.OverTime === "No", "Test 2: CSV OverTime matches");
  } catch (e) {
    assert(false, `Test 2: Valid CSV failed: ${e.message}`);
  }

  // ── TEST 3: Valid XLSX ──────────────────────────────────────────────────
  const validXlsxPath = path.join(TEST_DIR, "valid_emp.xlsx");
  const wb = xlsx.utils.book_new();
  const ws = xlsx.utils.json_to_sheet([
    {
      JobRole: "Sales Executive",
      Department: "Sales",
      TotalWorkingYears: 8,
      MonthlyIncome: 95000,
      YearsAtCompany: 4,
      OverTime: "Yes",
      JobSatisfaction: 3
    }
  ]);
  xlsx.utils.book_append_sheet(wb, ws, "EmployeeData");
  xlsx.writeFile(wb, validXlsxPath);

  try {
    const res = await parseEmployeeDocument(validXlsxPath, "valid_emp.xlsx");
    assert(res.is_complete === true, "Test 3: Valid XLSX parsed successfully");
    assert(res.extracted_features.JobRole === "Sales Executive", "Test 3: XLSX JobRole matches");
    assert(res.extracted_features.MonthlyIncome === 95000, "Test 3: XLSX MonthlyIncome matches");
  } catch (e) {
    assert(false, `Test 3: Valid XLSX failed: ${e.message}`);
  }

  // ── TEST 4: Valid PDF ───────────────────────────────────────────────────
  const validPdfPath = path.join(TEST_DIR, "valid_emp.pdf");
  const pdfStream = `%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length 280>>stream
BT /F1 12 Tf 50 720 Td (Employee Record: EMP-1042) Tj
0 -20 Td (Job Role: Senior Software Engineer) Tj
0 -20 Td (Department: Research & Development) Tj
0 -20 Td (Monthly Income: 175000) Tj
0 -20 Td (Total Experience: 6 years) Tj
0 -20 Td (Company Tenure: 3 years) Tj
0 -20 Td (OverTime: Yes) Tj
0 -20 Td (Job Satisfaction: 2) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000222 00000 n 
0000000293 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
625
%%EOF`;
  fs.writeFileSync(validPdfPath, Buffer.from(pdfStream));

  try {
    const res = await parseEmployeeDocument(validPdfPath, "valid_emp.pdf");
    assert(res.is_complete === true, "Test 4: Valid PDF parsed successfully with complete features");
    assert(res.extracted_features.JobRole === "Senior Software Engineer", "Test 4: PDF JobRole matches");
    assert(res.extracted_features.TotalWorkingYears === 6, "Test 4: PDF TotalWorkingYears matches");
  } catch (e) {
    assert(false, `Test 4: Valid PDF failed: ${e.message}`);
  }

  // ── TEST 5: Unsupported TXT Format ──────────────────────────────────────
  const txtPath = path.join(TEST_DIR, "unsupported.txt");
  fs.writeFileSync(txtPath, "JobRole: Developer");

  try {
    await parseEmployeeDocument(txtPath, "unsupported.txt");
    assert(false, "Test 5: Unsupported TXT should have thrown an error");
  } catch (e) {
    assert(e.message === "Unsupported format. Please upload a PDF, CSV, XLSX, or JSON employee record.", "Test 5: Correct unsupported format error message returned");
  }

  // ── TEST 6: Invalid JSON Format ─────────────────────────────────────────
  const badJsonPath = path.join(TEST_DIR, "bad.json");
  fs.writeFileSync(badJsonPath, "{ JobRole: invalid json without quotes, }");

  try {
    await parseEmployeeDocument(badJsonPath, "bad.json");
    assert(false, "Test 6: Invalid JSON should have thrown an error");
  } catch (e) {
    assert(e.message === "Invalid JSON format. Please upload a valid employee record.", "Test 6: Correct invalid JSON error message returned");
  }

  // ── TEST 7: CSV Missing Required Fields ──────────────────────────────────
  const missingCsvPath = path.join(TEST_DIR, "missing.csv");
  fs.writeFileSync(missingCsvPath, "JobRole,Department\nSoftware Engineer,Engineering\n");

  try {
    const res = await parseEmployeeDocument(missingCsvPath, "missing.csv");
    assert(res.is_complete === false, "Test 7: Incomplete CSV flagged is_complete=false");
    assert(res.missing_fields.length > 0, "Test 7: Missing fields identified correctly");
  } catch (e) {
    assert(false, `Test 7: Missing CSV unexpected error: ${e.message}`);
  }

  // ── TEST 8: XLSX Missing Required Fields ─────────────────────────────────
  const missingXlsxPath = path.join(TEST_DIR, "missing.xlsx");
  const wb2 = xlsx.utils.book_new();
  const ws2 = xlsx.utils.json_to_sheet([{ JobRole: "Manager", Department: "Sales" }]);
  xlsx.utils.book_append_sheet(wb2, ws2, "Sheet1");
  xlsx.writeFile(wb2, missingXlsxPath);

  try {
    const res = await parseEmployeeDocument(missingXlsxPath, "missing.xlsx");
    assert(res.is_complete === false, "Test 8: Incomplete XLSX flagged is_complete=false");
    assert(res.missing_fields.some(f => f.key === "MonthlyIncome"), "Test 8: MonthlyIncome identified as missing");
  } catch (e) {
    assert(false, `Test 8: Missing XLSX unexpected error: ${e.message}`);
  }

  // ── TEST 9: PDF Extraction Failure / Incomplete ─────────────────────────
  const emptyPdfPath = path.join(TEST_DIR, "empty.pdf");
  const emptyPdfStream = `%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length 40>>stream
BT /F1 12 Tf 50 720 Td (Random non-HR document text) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000222 00000 n 
0000000293 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
385
%%EOF`;
  fs.writeFileSync(emptyPdfPath, Buffer.from(emptyPdfStream));

  try {
    await parseEmployeeDocument(emptyPdfPath, "empty.pdf");
    assert(false, "Test 9: Non-HR PDF should fail extraction");
  } catch (e) {
    assert(e.message === "Could not extract employee information from this PDF.", "Test 9: Correct PDF failure error message returned");
  }

  // ── TEST 10: Multi-record CSV ───────────────────────────────────────────
  const multiCsvPath = path.join(TEST_DIR, "multi.csv");
  const multiCsvContent = "JobRole,Department,TotalWorkingYears,MonthlyIncome,YearsAtCompany,OverTime,JobSatisfaction\nResearch Scientist,Research & Development,5,85000,3,No,3\nSenior Software Engineer,Research & Development,8,185000,4,Yes,2\n";
  fs.writeFileSync(multiCsvPath, multiCsvContent);

  try {
    const res = await parseEmployeeDocument(multiCsvPath, "multi.csv");
    assert(res.multi_record === true, "Test 10: Multi-record CSV detected");
    assert(res.records_count === 2, "Test 10: 2 records extracted");
    assert(res.records.length === 2, "Test 10: All records available in records array");
  } catch (e) {
    assert(false, `Test 10: Multi-record CSV failed: ${e.message}`);
  }

  // Cleanup temp files
  try {
    fs.rmSync(TEST_DIR, { recursive: true, force: true });
  } catch {}

  console.log("==================================================");
  console.log(`TEST SUMMARY: ${passed} PASSED, ${failed} FAILED`);
  console.log("==================================================");
}

runTests();
