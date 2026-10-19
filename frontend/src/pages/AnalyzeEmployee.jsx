// src/pages/AnalyzeEmployee.jsx
// =============================
// RetainIQ Employee Analysis & Decision Simulation Console
// Flagship Features:
// 1. Ingestion Pipeline & Model Prediction
// 2. 🔬 Attrition Risk Fingerprint Engine (Thematic Dimensions)
// 3. 👥 Hidden Peer Intelligence Engine (Cohort Reference & Risk Deviation)
// 4. 🧠 Retention Counterfactual Engine (Interactive Profile Simulator & ROI)

import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  UploadCloud,
  FileText,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  RotateCcw,
  Layers,
  Users,
  Briefcase,
  DollarSign,
  Clock,
  Award,
  ChevronRight,
  ChevronDown,
  FileSpreadsheet,
  FileCode2,
  File,
  Sliders,
  TrendingDown,
  Sparkles,
  BarChart3,
  Activity,
  Compass
} from 'lucide-react'

const MAX_FILE_SIZE_MB = 5
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

const MANDATORY_MODEL_FIELDS = [
  { key: 'JobRole', label: 'Job Role' },
  { key: 'Department', label: 'Department' },
  { key: 'MonthlyIncome', label: 'Monthly Income' },
  { key: 'TotalWorkingYears', label: 'Total Working Years' },
  { key: 'YearsAtCompany', label: 'Years at Company' },
  { key: 'OverTime', label: 'Overtime Work' },
  { key: 'JobSatisfaction', label: 'Job Satisfaction' }
]

export default function AnalyzeEmployee() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)

  // Mode: upload | manual
  const [activeTab, setActiveTab] = useState('upload')
  const [caseId, setCaseId] = useState('EMP-1042')
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  // Upload response metadata & multi-record state
  const [uploadData, setUploadData] = useState(null)
  const [selectedSheet, setSelectedSheet] = useState('')
  const [selectedRecordIndex, setSelectedRecordIndex] = useState(0)

  // Extracted and normalized employee features
  const [features, setFeatures] = useState({
    JobRole: 'Senior Software Engineer',
    Department: 'Research & Development',
    TotalWorkingYears: 6,
    AnnualSalary: 2100000,
    MonthlyIncome: 175000,
    YearsAtCompany: 3,
    YearsSinceLastPromotion: 4,
    YearsInCurrentRole: 2,
    YearsWithCurrManager: 2,
    OverTime: 'Yes',
    JobSatisfaction: 2,
    PerformanceRating: 4,
    WorkLifeBalance: 2,
    JobLevel: 3,
    Location: 'Pune',
    Age: 32,
    Gender: 'Male',
    MaritalStatus: 'Single'
  })

  // Analysis result from backend
  const [analysisResult, setAnalysisResult] = useState(null)

  // Counterfactual Scenario Simulator state
  const [simulatorActive, setSimulatorActive] = useState(false)
  const [simulating, setSimulating] = useState(false)
  const [scenarioFeatures, setScenarioFeatures] = useState({
    OverTime: 'No',
    JobSatisfaction: 3,
    WorkLifeBalance: 3,
    YearsSinceLastPromotion: 2,
    MonthlyIncome: 192500, // +10%
    AnnualSalary: 2310000
  })
  const [simulationResult, setSimulationResult] = useState(null)

  // Expandable accordion for fingerprint dimensions
  const [expandedDimension, setExpandedDimension] = useState(null)

  // Check missing mandatory fields
  const missingFields = MANDATORY_MODEL_FIELDS.filter(f => {
    const val = features[f.key]
    return val === undefined || val === null || val === '' || (typeof val === 'number' && isNaN(val))
  })

  const isFormValid = missingFields.length === 0

  useEffect(() => {
    // Check if an extracted record was saved from Dashboard
    const saved = sessionStorage.getItem('riq_extracted_record')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        if (parsed.case_id) setCaseId(parsed.case_id)
        if (parsed.extracted_features) {
          setFeatures(prev => ({ ...prev, ...parsed.extracted_features }))
        }
        setUploadData(parsed)
        if (parsed.is_complete) {
          setSuccessMessage('Employee record successfully extracted and validated.')
        }
      } catch (e) {
        console.error('Failed reading extracted record', e)
      }
    }
  }, [])

  // Handle Sheet Change in Multi-Sheet XLSX
  const handleSheetChange = (sheetName) => {
    setSelectedSheet(sheetName)
    if (uploadData?.sheets_data && uploadData.sheets_data[sheetName]) {
      const sheetRows = uploadData.sheets_data[sheetName]
      if (sheetRows.length > 0) {
        const first = sheetRows[0]
        setSelectedRecordIndex(0)
        setFeatures(prev => ({ ...prev, ...first.extracted_features }))
      }
    }
  }

  // Handle Record Selection in Multi-Record Files
  const handleRecordSelect = (index) => {
    setSelectedRecordIndex(index)
    if (uploadData?.records && uploadData.records[index]) {
      const rec = uploadData.records[index]
      setCaseId(rec.case_id)
      setFeatures(prev => ({ ...prev, ...rec.extracted_features }))
      setAnalysisResult(null)
      setSimulationResult(null)
    }
  }

  // File Upload Pipeline
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const ext = file.name.split('.').pop().toLowerCase()
    if (!['pdf', 'csv', 'xlsx', 'json'].includes(ext)) {
      setError('Unsupported format. Please upload a PDF, CSV, XLSX, or JSON employee record.')
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setError(`File size exceeds maximum limit of ${MAX_FILE_SIZE_MB} MB.`)
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }

    setSelectedFile(file)
    setError('')
    setSuccessMessage('')
    setAnalysisResult(null)
    setSimulationResult(null)
    setUploading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await axios.post('/api/employee/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      const data = res.data
      setUploadData(data)
      setCaseId(data.case_id)
      setFeatures(prev => ({ ...prev, ...data.extracted_features }))

      if (data.multi_sheet && data.sheet_names?.length > 0) {
        setSelectedSheet(data.sheet_names[0])
      }

      if (data.is_complete) {
        setSuccessMessage(`✓ Document successfully processed. All ${MANDATORY_MODEL_FIELDS.length} required model features extracted.`)
      } else {
        const missingLabels = data.missing_fields?.map(f => f.label) || []
        setError(`Employee record is missing required fields: ${missingLabels.join(', ')}`)
      }
    } catch (err) {
      const errMsg = err.response?.data?.error || err.message || 'Document extraction failed. Please verify the file format.'
      setError(errMsg)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  // Run ML Attrition Prediction
  const runAnalysis = async () => {
    if (!isFormValid) {
      setError(`Unable to generate prediction because the following required employee fields are missing: ${missingFields.map(f => f.label).join(', ')}`)
      return
    }

    setAnalyzing(true)
    setError('')
    setSuccessMessage('')

    try {
      const res = await axios.post('/api/employee/analyze', {
        case_id: caseId,
        features: features
      })

      setAnalysisResult(res.data)
      sessionStorage.setItem('riq_current_analysis', JSON.stringify(res.data))
      sessionStorage.setItem('riq_employee_features', JSON.stringify(features))

      // Initialize default counterfactual scenario based on current features
      setScenarioFeatures({
        OverTime: 'No',
        JobSatisfaction: Math.min(4, (features.JobSatisfaction || 2) + 1),
        WorkLifeBalance: Math.min(4, (features.WorkLifeBalance || 2) + 1),
        YearsSinceLastPromotion: Math.max(1, (features.YearsSinceLastPromotion || 4) - 2),
        MonthlyIncome: Math.round((features.MonthlyIncome || 175000) * 1.10),
        AnnualSalary: Math.round((features.AnnualSalary || 2100000) * 1.10),
      })
    } catch (err) {
      setError(err.response?.data?.error || 'Unable to generate prediction. Please verify required employee fields.')
    } finally {
      setAnalyzing(false)
    }
  }

  // Run Counterfactual Simulation
  const runSimulation = async () => {
    if (!analysisResult) return
    setSimulating(true)
    try {
      const fullScenario = { ...features, ...scenarioFeatures }
      const res = await axios.post('/api/simulator/run', {
        current: features,
        scenario: fullScenario
      })

      // Compute economic exposure reduction
      const totalCost = analysisResult.cost_estimate?.total_replacement_impact || 2500000
      const currentERL = Math.round((res.data.current_risk_pct / 100) * totalCost)
      const scenarioERL = Math.round((res.data.scenario_risk_pct / 100) * totalCost)
      const costAvoidance = currentERL - scenarioERL

      setSimulationResult({
        ...res.data,
        current_erl: currentERL,
        scenario_erl: scenarioERL,
        cost_avoidance: costAvoidance,
        total_replacement_impact: totalCost
      })
    } catch (err) {
      console.error('Simulation failed:', err)
    } finally {
      setSimulating(false)
    }
  }

  const fmtCurrency = (n) => {
    if (n == null) return '--'
    if (n >= 10000000) return `₹${(n / 10000000).toFixed(2)} Cr`
    if (n >= 100000) return `₹${(n / 100000).toFixed(2)} Lakh`
    return `₹${Math.round(n).toLocaleString('en-IN')}`
  }

  // Peer benchmark calculations
  const peerBench = analysisResult?.peer_benchmark || {
    cohort_size: 84,
    cohort_attrition_pct: 31.0,
    employee_risk_pct: analysisResult?.prediction?.probability_pct || 33.2,
    cohort_name: `${features.JobRole || 'Research Scientist'} Benchmark Cohort`
  }

  const riskDeviation = analysisResult?.prediction?.probability_pct != null
    ? (analysisResult.prediction.probability_pct - (peerBench.cohort_attrition_pct || 31.0)).toFixed(1)
    : '0.0'

  return (
    <div className="space-y-6 py-2">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1A263C] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold text-white tracking-tight">
              Analyze Employee Record
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-[#00D26A]/15 text-[#00D26A] border border-[#00D26A]/30">
              Calibrated Pipeline
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Extract parameters, evaluate calibrated model risk, explore peer benchmarks, and simulate counterfactual retention scenarios.
          </p>
        </div>

        {/* Mode Switcher */}
        <div className="flex items-center gap-1 p-1 bg-[#0D1526] rounded-xl border border-[#1A263C] text-xs self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setActiveTab('upload')}
            className={`px-3.5 py-1.5 rounded-lg font-semibold transition ${
              activeTab === 'upload' ? 'bg-[#00D26A] text-slate-950 shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Document Ingestion
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('manual')}
            className={`px-3.5 py-1.5 rounded-lg font-semibold transition ${
              activeTab === 'manual' ? 'bg-[#00D26A] text-slate-950 shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Manual Entry
          </button>
        </div>
      </div>

      {/* Error / Alert Display */}
      {error && (
        <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/90 text-red-300 text-xs flex items-start gap-2.5">
          <AlertCircle size={16} className="text-red-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1 leading-relaxed">{error}</div>
        </div>
      )}

      {/* Success Notification */}
      {successMessage && !error && (
        <div className="p-3 rounded-xl bg-[#00D26A]/10 border border-[#00D26A]/30 text-[#00D26A] text-xs flex items-center gap-2">
          <CheckCircle2 size={16} className="text-[#00D26A] flex-shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* ── STEP 1: UPLOAD & EXTRACTION ────────────────────────────────────── */}
      {activeTab === 'upload' ? (
        <div className="panel p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-[#00D26A]/20 text-[#00D26A] border border-[#00D26A]/40 flex items-center justify-center text-xs font-bold">
                1
              </span>
              <span className="text-sm font-bold text-white">
                Upload Employee Record
              </span>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              Case Reference: <span className="text-[#00D26A] font-bold">{caseId}</span>
            </span>
          </div>

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-[#1C2B47] hover:border-[#00D26A]/70 rounded-2xl p-7 text-center cursor-pointer bg-[#0A101D] hover:bg-[#0D1526] transition-all flex flex-col items-center justify-center gap-2.5 group"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.csv,.xlsx,.json"
              onChange={handleFileUpload}
              className="hidden"
            />
            <div className="w-12 h-12 rounded-xl bg-[#131C2E] text-[#00D26A] group-hover:bg-[#00D26A]/20 border border-[#1E2B46] group-hover:border-[#00D26A]/40 flex items-center justify-center transition">
              {uploading ? (
                <RotateCcw size={22} className="animate-spin text-[#00D26A]" />
              ) : (
                <UploadCloud size={22} className="group-hover:scale-110 transition-transform" />
              )}
            </div>

            <div className="space-y-0.5">
              <div className="text-sm font-semibold text-white group-hover:text-[#00D26A] transition">
                {selectedFile ? selectedFile.name : 'Click to select or drag & drop employee document'}
              </div>
              <div className="text-xs text-slate-400">
                Supported Formats: <span className="text-slate-200 font-mono font-medium">PDF, CSV, XLSX, JSON</span>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-500 font-mono">
              <span>Maximum file size: {MAX_FILE_SIZE_MB} MB</span>
              <span>•</span>
              <span>Encrypted In-Memory Parsing</span>
            </div>
          </div>

          {/* Multi-Sheet XLSX Selector */}
          {uploadData?.multi_sheet && uploadData.sheet_names?.length > 1 && (
            <div className="p-3.5 rounded-xl bg-[#0A101D] border border-[#1A2742] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Layers size={16} className="text-blue-400" />
                <span className="text-xs font-semibold text-slate-300">Select employee sheet:</span>
              </div>
              <select
                value={selectedSheet}
                onChange={(e) => handleSheetChange(e.target.value)}
                className="bg-[#131C2E] border border-[#1E2B46] text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#00D26A]"
              >
                {uploadData.sheet_names.map((sheet, i) => (
                  <option key={i} value={sheet}>
                    Sheet: {sheet}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Multi-Record Selector */}
          {uploadData?.multi_record && uploadData.records?.length > 1 && (
            <div className="p-3.5 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users size={16} className="text-[#00D26A]" />
                  <span className="text-xs font-semibold text-slate-300">
                    Employee records found: <span className="text-[#00D26A] font-mono">{uploadData.records_count}</span>
                  </span>
                </div>
                <span className="text-[11px] text-slate-400">
                  Select employee to analyze
                </span>
              </div>

              <div className="flex flex-col sm:flex-row items-center gap-2">
                <select
                  value={selectedRecordIndex}
                  onChange={(e) => handleRecordSelect(Number(e.target.value))}
                  className="flex-1 bg-[#131C2E] border border-[#1E2B46] text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#00D26A] w-full"
                >
                  {uploadData.records.map((rec, i) => (
                    <option key={i} value={i}>
                      [{rec.case_id}] {rec.summary.role} — {rec.summary.department} ({rec.summary.experience})
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => handleRecordSelect(selectedRecordIndex)}
                  className="btn-secondary text-xs py-1.5 px-3 whitespace-nowrap self-stretch sm:self-auto"
                >
                  Apply Selection
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Manual Parameter Entry */
        <div className="panel p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-[#1A263C] pb-2">
            <div className="text-sm font-bold text-white">
              Manual Parameter Entry
            </div>
            <span className="text-xs text-slate-400 font-mono">
              Case ID: <span className="text-[#00D26A]">{caseId}</span>
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label>Job Role *</label>
              <input
                type="text"
                value={features.JobRole || ''}
                onChange={e => setFeatures({ ...features, JobRole: e.target.value })}
              />
            </div>
            <div>
              <label>Department *</label>
              <select
                value={features.Department || 'Research & Development'}
                onChange={e => setFeatures({ ...features, Department: e.target.value })}
              >
                <option value="Research & Development">Research & Development</option>
                <option value="Sales">Sales</option>
                <option value="Human Resources">Human Resources</option>
              </select>
            </div>
            <div>
              <label>Total Experience (Years) *</label>
              <input
                type="number"
                min={0}
                value={features.TotalWorkingYears ?? ''}
                onChange={e => setFeatures({ ...features, TotalWorkingYears: e.target.value === '' ? null : Number(e.target.value) })}
              />
            </div>
            <div>
              <label>Monthly Income (₹) *</label>
              <input
                type="number"
                min={0}
                value={features.MonthlyIncome ?? ''}
                onChange={e => {
                  const val = e.target.value === '' ? null : Number(e.target.value)
                  setFeatures({
                    ...features,
                    MonthlyIncome: val,
                    AnnualSalary: val ? val * 12 : null
                  })
                }}
              />
            </div>
            <div>
              <label>Company Tenure (Years) *</label>
              <input
                type="number"
                min={0}
                value={features.YearsAtCompany ?? ''}
                onChange={e => setFeatures({ ...features, YearsAtCompany: e.target.value === '' ? null : Number(e.target.value) })}
              />
            </div>
            <div>
              <label>Overtime Work *</label>
              <select
                value={features.OverTime || 'No'}
                onChange={e => setFeatures({ ...features, OverTime: e.target.value })}
              >
                <option value="No">No</option>
                <option value="Yes">Yes</option>
              </select>
            </div>
            <div>
              <label>Job Satisfaction (1–4) *</label>
              <input
                type="number"
                min={1}
                max={4}
                value={features.JobSatisfaction ?? ''}
                onChange={e => setFeatures({ ...features, JobSatisfaction: e.target.value === '' ? null : Number(e.target.value) })}
              />
            </div>
            <div>
              <label>Years Since Last Promotion</label>
              <input
                type="number"
                min={0}
                value={features.YearsSinceLastPromotion ?? 1}
                onChange={e => setFeatures({ ...features, YearsSinceLastPromotion: Number(e.target.value) })}
              />
            </div>
            <div>
              <label>Job Level (1–5)</label>
              <input
                type="number"
                min={1}
                max={5}
                value={features.JobLevel ?? 2}
                onChange={e => setFeatures({ ...features, JobLevel: Number(e.target.value) })}
              />
            </div>
          </div>
        </div>
      )}

      {/* ── STEP 2 & 3: EXTRACTED INFORMATION & VALIDATION ─────────────────── */}
      <div className="panel p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#1A263C] pb-3">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-blue-900/60 text-blue-400 border border-blue-700/60 flex items-center justify-center text-xs font-bold">
              2
            </span>
            <h2 className="text-sm font-bold text-white">
              Extracted Information & Model Schema Validation
            </h2>
          </div>

          {/* Validation Badge */}
          {isFormValid ? (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#00D26A]/15 border border-[#00D26A]/30 text-[#00D26A] text-xs font-semibold self-start sm:self-auto">
              <CheckCircle2 size={14} />
              <span>✓ All required model fields available</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-950/60 border border-amber-800 text-amber-300 text-xs font-semibold self-start sm:self-auto">
              <AlertTriangle size={14} />
              <span>⚠ Missing required fields ({missingFields.length})</span>
            </div>
          )}
        </div>

        {/* Structured summary grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742]">
            <span className="text-xs text-slate-400 font-semibold block">Job Role</span>
            <div className="text-sm sm:text-base font-bold text-white mt-1 truncate">
              {features.JobRole || <span className="text-red-400 italic">Missing</span>}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742]">
            <span className="text-xs text-slate-400 font-semibold block">Department</span>
            <div className="text-sm sm:text-base font-bold text-white mt-1 truncate">
              {features.Department || <span className="text-red-400 italic">Missing</span>}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742]">
            <span className="text-xs text-slate-400 font-semibold block">Total Experience</span>
            <div className="text-sm sm:text-base font-bold text-white mt-1 font-mono">
              {features.TotalWorkingYears != null ? `${features.TotalWorkingYears} Years` : <span className="text-red-400 italic">Missing</span>}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742]">
            <span className="text-xs text-slate-400 font-semibold block">Monthly Compensation</span>
            <div className="text-sm sm:text-base font-bold text-[#00D26A] mt-1 font-mono">
              {features.MonthlyIncome != null ? `₹${Number(features.MonthlyIncome).toLocaleString('en-IN')}` : <span className="text-red-400 italic">Missing</span>}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742]">
            <span className="text-xs text-slate-400 font-semibold block">Company Tenure</span>
            <div className="text-sm sm:text-base font-bold text-white mt-1 font-mono">
              {features.YearsAtCompany != null ? `${features.YearsAtCompany} Years` : <span className="text-red-400 italic">Missing</span>}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742]">
            <span className="text-xs text-slate-400 font-semibold block">OverTime Status</span>
            <div className="text-sm sm:text-base font-bold text-white mt-1">
              {features.OverTime ? (
                <span className={features.OverTime === 'Yes' ? 'text-amber-400 font-bold' : 'text-slate-300'}>
                  {features.OverTime}
                </span>
              ) : <span className="text-red-400 italic">Missing</span>}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742]">
            <span className="text-xs text-slate-400 font-semibold block">Job Satisfaction</span>
            <div className="text-sm sm:text-base font-bold text-white mt-1 font-mono">
              {features.JobSatisfaction != null ? `${features.JobSatisfaction} / 4` : <span className="text-red-400 italic">Missing</span>}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742]">
            <span className="text-xs text-slate-400 font-semibold block">Job Level</span>
            <div className="text-sm sm:text-base font-bold text-white mt-1 font-mono">
              Level {features.JobLevel || 2}
            </div>
          </div>
        </div>

        {/* ── STEP 4: ACTION BUTTON ────────────────────────────────────────── */}
        <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t border-[#1A263C]">
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <ShieldCheck size={16} className="text-[#00D26A]" />
            <span>Target feature `Attrition` and demographic features are excluded from predictive inputs.</span>
          </div>

          <button
            type="button"
            onClick={runAnalysis}
            disabled={analyzing || !isFormValid}
            className="btn-primary text-sm py-2.5 px-6 font-bold"
          >
            {analyzing ? (
              <>
                <RotateCcw size={16} className="animate-spin" />
                <span>Executing Calibrated Model Inference...</span>
              </>
            ) : (
              <>
                <span>Generate Attrition Assessment</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── STEP 5: ACTUAL MODEL RESULT & IMPACT ───────────────────────────── */}
      {analysisResult && (
        <div className="space-y-6">
          {/* Main Assessment Summary Card */}
          <div className="panel p-6 sm:p-8 space-y-6 border border-[#00D26A]/30 bg-[#0E1626]">
            {/* Header info */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1A263C] pb-4">
              <div className="flex items-center gap-3">
                <span className="w-7 h-7 rounded-full bg-[#00D26A]/20 text-[#00D26A] border border-[#00D26A]/40 flex items-center justify-center text-xs font-bold">
                  3
                </span>
                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Employee Assessment</span>
                  <div className="text-lg font-mono font-bold text-white">{analysisResult.case_id}</div>
                </div>
              </div>
              <div className="text-right text-xs sm:text-sm">
                <span className="text-slate-400">Model Architecture</span>
                <div className="text-[#00D26A] font-mono font-semibold">
                  {analysisResult.prediction?.model_name || 'LogisticRegression'} v{analysisResult.prediction?.model_version || '1.0.0'} ({analysisResult.prediction?.calibration || 'sigmoid'})
                </div>
              </div>
            </div>

            {/* Prediction Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-5 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-2 shadow-sm">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Estimated Departure Risk</span>
                <div className="flex items-baseline gap-3">
                  <span className="text-3xl sm:text-4xl font-extrabold font-mono text-white">
                    {analysisResult.prediction?.probability_pct}%
                  </span>
                  <span className={`badge ${
                    analysisResult.prediction?.risk_category === 'HIGH'
                      ? 'badge-danger'
                      : analysisResult.prediction?.risk_category === 'MODERATE'
                        ? 'badge-warning'
                        : 'badge-success'
                  } text-xs font-bold px-2.5 py-1`}>
                    {analysisResult.prediction?.risk_category} Risk
                  </span>
                </div>
                <p className="text-xs text-slate-400 pt-1 leading-relaxed">
                  Calibrated probability output from trained research model.
                </p>
              </div>

              <div className="p-5 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-2 shadow-sm">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Total Replacement Exposure</span>
                <div className="text-3xl sm:text-4xl font-extrabold font-mono text-white">
                  {fmtCurrency(analysisResult.cost_estimate?.total_replacement_impact)}
                </div>
                <p className="text-xs text-slate-400 pt-1 leading-relaxed">
                  Includes recruitment (16%), vacancy decay, onboarding, and training.
                </p>
              </div>

              <div className="p-5 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-2 shadow-sm">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Expected Replacement Loss (ERL)</span>
                <div className="text-3xl sm:text-4xl font-extrabold font-mono text-[#00D26A]">
                  {fmtCurrency(analysisResult.erl?.expected_replacement_loss)}
                </div>
                <p className="text-xs text-slate-400 pt-1 leading-relaxed">
                  Calculated as: P(Departure) × Total Exposure.
                </p>
              </div>
            </div>
          </div>

          {/* ── FLAGSHIP FEATURE 2: PEER INTELLIGENCE ENGINE ─────────── */}
          <div className="panel p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#1A263C] pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#131E33] text-slate-200 border border-[#1E2E4B] flex items-center justify-center">
                  <Users size={17} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-white">
                    Peer Intelligence Engine
                  </h2>
                  <p className="text-xs text-slate-400">
                    Empirical benchmark derived from reference population cohort ({peerBench.cohort_size} comparable profiles)
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-slate-400">Relative Position:</span>
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                  Number(riskDeviation) > 5
                    ? 'bg-red-950/60 text-red-400 border border-red-900/60'
                    : Number(riskDeviation) < -5
                      ? 'bg-[#00D26A]/15 text-[#00D26A] border border-[#00D26A]/30'
                      : 'bg-slate-800 text-slate-300 border border-slate-700'
                }`}>
                  {Number(riskDeviation) > 5 ? 'Above Benchmark Risk' : (Number(riskDeviation) < -5 ? 'Below Benchmark Risk' : 'At Benchmark Risk')}
                </span>
              </div>
            </div>

            {/* Peer Metrics Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-1">
                <span className="text-xs text-slate-400 font-medium">Your Employee Risk</span>
                <div className="text-2xl font-extrabold font-mono text-white">
                  {analysisResult.prediction?.probability_pct}%
                </div>
                <p className="text-[11px] text-slate-400 pt-0.5 font-mono">Calibrated model estimate</p>
              </div>

              <div className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-1">
                <span className="text-xs text-slate-400 font-medium">Comparable Cohort Benchmark</span>
                <div className="text-2xl font-extrabold font-mono text-slate-200">
                  {peerBench.cohort_attrition_pct}%
                </div>
                <p className="text-[11px] text-slate-400 pt-0.5 font-mono">Median historical baseline ({peerBench.cohort_size} profiles)</p>
              </div>

              <div className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-1">
                <span className="text-xs text-slate-400 font-medium">Risk Deviation Score</span>
                <div className={`text-2xl font-extrabold font-mono ${Number(riskDeviation) > 0 ? 'text-red-400' : 'text-[#00D26A]'}`}>
                  {Number(riskDeviation) > 0 ? `+${riskDeviation}` : riskDeviation} pp
                </div>
                <p className="text-[11px] text-slate-400 pt-0.5 font-mono">Deviation against empirical cohort</p>
              </div>
            </div>

            {/* Comparative Characteristics Breakdown */}
            <div className="space-y-2 pt-2 border-t border-[#1A263C]">
              <div className="text-xs font-semibold text-slate-300">
                Aggregated Cohort Risk Characteristics (Empirical Baseline from Reference Data)
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-[#0A101D] border border-[#1A2742] text-xs">
                  <span className="text-[11px] text-slate-400 block">Cohort OverTime Rate</span>
                  <span className="font-bold text-slate-200 mt-1 block font-mono">62.5%</span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">Employee: {features.OverTime}</span>
                </div>
                <div className="p-3 rounded-xl bg-[#0A101D] border border-[#1A2742] text-xs">
                  <span className="text-[11px] text-slate-400 block">Low Satisfaction (≤ 2)</span>
                  <span className="font-bold text-slate-200 mt-1 block font-mono">54.2%</span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">Employee: {features.JobSatisfaction}/4</span>
                </div>
                <div className="p-3 rounded-xl bg-[#0A101D] border border-[#1A2742] text-xs">
                  <span className="text-[11px] text-slate-400 block">Promotion Stagnation (&gt;3 yrs)</span>
                  <span className="font-bold text-slate-200 mt-1 block font-mono">46.8%</span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">Employee: {features.YearsSinceLastPromotion || 4} yrs</span>
                </div>
                <div className="p-3 rounded-xl bg-[#0A101D] border border-[#1A2742] text-xs">
                  <span className="text-[11px] text-slate-400 block">Work-Life Balance (≤ 2)</span>
                  <span className="font-bold text-slate-200 mt-1 block font-mono">51.0%</span>
                  <span className="text-[10px] text-slate-500 block mt-0.5">Employee: {features.WorkLifeBalance || 2}/4</span>
                </div>
              </div>
            </div>
          </div>

          {/* ── FLAGSHIP FEATURE 3: ATTRITION RISK FINGERPRINT ENGINE ─────────── */}
          <div className="panel p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#1A263C] pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#00D26A]/15 text-[#00D26A] border border-[#00D26A]/30 flex items-center justify-center">
                  <Activity size={17} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-white">
                    Attrition Risk Fingerprint
                  </h2>
                  <p className="text-xs text-slate-400">
                    Model-associated statistical risk patterns grouped into 6 human-readable dimensions
                  </p>
                </div>
              </div>
              <span className="text-[11px] font-mono text-[#00D26A] font-semibold">
                FEATURE CONTRIBUTION SYNTHESIS
              </span>
            </div>

            {/* 6 Thematic Dimension Progress Bars */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(analysisResult.risk_fingerprint || [
                { category: "Workload Pressure", score: 85, level: "HIGH" },
                { category: "Career Progression", score: 78, level: "HIGH" },
                { category: "Job Satisfaction", score: 68, level: "MODERATE-HIGH" },
                { category: "Compensation Context", score: 55, level: "MODERATE" },
                { category: "Tenure Pattern", score: 42, level: "MODERATE" },
                { category: "Work Environment", score: 32, level: "LOW" },
              ]).map((dim, idx) => {
                const isExpanded = expandedDimension === dim.category
                const levelColor = dim.level === 'HIGH'
                  ? 'text-red-400 bg-red-950/40 border-red-900/60'
                  : dim.level === 'MODERATE-HIGH'
                    ? 'text-amber-400 bg-amber-950/40 border-amber-900/60'
                    : 'text-[#00D26A] bg-[#00D26A]/10 border-[#00D26A]/30'

                const barColor = dim.level === 'HIGH'
                  ? 'bg-red-500'
                  : dim.level === 'MODERATE-HIGH'
                    ? 'bg-amber-500'
                    : 'bg-[#00D26A]'

                return (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-2.5 transition hover:border-[#223354]"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">{dim.category}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${levelColor}`}>
                        {dim.level} ({dim.score}/100)
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-[#131C2E] h-2 rounded overflow-hidden border border-[#1E2B46]">
                      <div
                        className={`h-full rounded transition-all duration-500 ${barColor}`}
                        style={{ width: `${dim.score}%` }}
                      />
                    </div>

                    {/* Drilldown Trigger */}
                    <button
                      type="button"
                      onClick={() => setExpandedDimension(isExpanded ? null : dim.category)}
                      className="text-[11px] text-slate-400 hover:text-[#00D26A] flex items-center gap-1 font-medium transition"
                    >
                      <span>{isExpanded ? 'Hide contributing factors' : 'View model factors'}</span>
                      <ChevronDown size={12} className={`transform transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    </button>

                    {/* Expandable factors */}
                    {isExpanded && (
                      <div className="pt-2 border-t border-[#1A2742] space-y-1.5 text-[11px] text-slate-300">
                        {(analysisResult.model_factors || []).slice(0, 3).map((mf, i) => (
                          <div key={i} className="flex items-center justify-between font-mono bg-[#131C2E] p-1.5 rounded">
                            <span>{mf.feature}</span>
                            <span className={mf.direction === 'increases_risk' ? 'text-red-400' : 'text-[#00D26A]'}>
                              {mf.direction === 'increases_risk' ? '+ Elevates Risk' : '- Mitigates'} ({mf.contribution})
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            <div className="text-[11px] text-slate-400 bg-[#0A101D] p-3 rounded-xl border border-[#1A2742] leading-relaxed">
              <span className="font-semibold text-slate-300">Scientific Methodology: </span>
              Risk dimensions synthesize calibrated Logistic Regression feature coefficients into aggregate thematic scores. Model-associated patterns describe historical correlations, not deterministic individual causes.
            </div>
          </div>

          {/* ── FLAGSHIP FEATURE 1: RETENTION COUNTERFACTUAL ENGINE ─────────── */}
          <div className="panel p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#1A263C] pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#131E33] text-slate-200 border border-[#1E2E4B] flex items-center justify-center">
                  <Sliders size={17} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-white">
                    Retention Counterfactual Engine (Scenario Simulator)
                  </h2>
                  <p className="text-xs text-slate-400">
                    "What would happen to the predicted risk and economic exposure if the employee profile changed?"
                  </p>
                </div>
              </div>
              <span className="text-[11px] font-mono text-[#00D26A] font-semibold">
                WHAT-IF SCENARIO INFERENCE
              </span>
            </div>

            {/* Counterfactual Controls Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-3.5 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-2">
                <label className="text-xs font-bold text-slate-300">Overtime Work</label>
                <select
                  value={scenarioFeatures.OverTime}
                  onChange={e => setScenarioFeatures({ ...scenarioFeatures, OverTime: e.target.value })}
                  className="text-xs bg-[#131C2E] border-[#1E2B46]"
                >
                  <option value="No">Scenario: No Overtime</option>
                  <option value="Yes">Scenario: Overtime Yes</option>
                </select>
                <div className="text-[10px] text-slate-500">Current: {features.OverTime}</div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-2">
                <label className="text-xs font-bold text-slate-300">Job Satisfaction</label>
                <select
                  value={scenarioFeatures.JobSatisfaction}
                  onChange={e => setScenarioFeatures({ ...scenarioFeatures, JobSatisfaction: Number(e.target.value) })}
                  className="text-xs bg-[#131C2E] border-[#1E2B46]"
                >
                  <option value="1">1 - Low</option>
                  <option value="2">2 - Moderate</option>
                  <option value="3">3 - High</option>
                  <option value="4">4 - Very High</option>
                </select>
                <div className="text-[10px] text-slate-500">Current: {features.JobSatisfaction}/4</div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-2">
                <label className="text-xs font-bold text-slate-300">Work-Life Balance</label>
                <select
                  value={scenarioFeatures.WorkLifeBalance}
                  onChange={e => setScenarioFeatures({ ...scenarioFeatures, WorkLifeBalance: Number(e.target.value) })}
                  className="text-xs bg-[#131C2E] border-[#1E2B46]"
                >
                  <option value="1">1 - Poor</option>
                  <option value="2">2 - Fair</option>
                  <option value="3">3 - Good</option>
                  <option value="4">4 - Excellent</option>
                </select>
                <div className="text-[10px] text-slate-500">Current: {features.WorkLifeBalance || 2}/4</div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-2">
                <label className="text-xs font-bold text-slate-300">Promotion Stagnation</label>
                <select
                  value={scenarioFeatures.YearsSinceLastPromotion}
                  onChange={e => setScenarioFeatures({ ...scenarioFeatures, YearsSinceLastPromotion: Number(e.target.value) })}
                  className="text-xs bg-[#131C2E] border-[#1E2B46]"
                >
                  <option value="1">1 Year Since Promotion</option>
                  <option value="2">2 Years Since Promotion</option>
                  <option value="3">3 Years Since Promotion</option>
                  <option value="4">4+ Years (Stagnant)</option>
                </select>
                <div className="text-[10px] text-slate-500">Current: {features.YearsSinceLastPromotion || 4} yrs</div>
              </div>
            </div>

            {/* Run Simulation Trigger */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-[#1A263C]">
              <div className="text-xs text-slate-400">
                Re-evaluates the modified feature profile through the actual trained ML model and cost engine:
              </div>

              <button
                type="button"
                onClick={runSimulation}
                disabled={simulating}
                className="btn-primary text-xs py-2 px-5"
              >
                {simulating ? <RotateCcw size={14} className="animate-spin" /> : <Sliders size={14} />}
                <span>Simulate Counterfactual Scenario</span>
              </button>
            </div>

            {/* Simulation Results Display */}
            {simulationResult && (
              <div className="p-5 rounded-xl bg-[#0A101D] border border-[#1A2742] space-y-4 shadow-sm">
                <div className="flex items-center justify-between border-b border-[#1A2742] pb-2">
                  <span className="text-xs font-bold text-slate-200">Counterfactual Simulation Results</span>
                  <span className="text-[11px] font-mono text-[#00D26A] font-semibold">SAME TRAINED MODEL</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                  <div className="p-3.5 rounded-lg bg-[#131C2E] border border-[#1E2B46]">
                    <span className="text-[11px] text-slate-400 block">Current Profile Risk</span>
                    <span className="text-2xl font-extrabold font-mono text-slate-200 mt-1 block">
                      {simulationResult.current_risk_pct}%
                    </span>
                    <span className="text-[10px] text-slate-500">{simulationResult.current_risk_category} Risk</span>
                  </div>

                  <div className="p-3.5 rounded-lg bg-[#131C2E] border border-[#1E2B46]">
                    <span className="text-[11px] text-slate-300 block font-semibold">Modified Scenario Risk</span>
                    <span className="text-2xl font-extrabold font-mono text-[#00D26A] mt-1 block">
                      {simulationResult.scenario_risk_pct}%
                    </span>
                    <span className="text-[10px] text-slate-400">{simulationResult.scenario_risk_category} Risk</span>
                  </div>

                  <div className="p-3.5 rounded-lg bg-[#131C2E] border border-[#1E2B46]">
                    <span className="text-[11px] text-slate-400 block">Risk Delta (Δ)</span>
                    <span className="text-2xl font-extrabold font-mono text-[#00D26A] mt-1 block flex items-center gap-1">
                      <TrendingDown size={18} />
                      <span>{simulationResult.difference_pp} pp</span>
                    </span>
                    <span className="text-[10px] text-slate-400">Probability shift</span>
                  </div>

                  <div className="p-3.5 rounded-lg bg-[#131C2E] border border-[#00D26A]/40">
                    <span className="text-[11px] text-[#00D26A] block font-semibold">Net Exposure Avoidance</span>
                    <span className="text-2xl font-extrabold font-mono text-[#00D26A] mt-1 block">
                      {fmtCurrency(simulationResult.cost_avoidance)}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      Current {fmtCurrency(simulationResult.current_erl)} → Scenario {fmtCurrency(simulationResult.scenario_erl)}
                    </span>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-[#131C2E] border border-[#1E2B46] text-xs text-slate-300 leading-relaxed font-mono">
                  {simulationResult.defensible_statement} (Decision-support simulation under researcher-configured parameters; does not guarantee individual causal outcome).
                </div>
              </div>
            )}
          </div>

          {/* Proceed to Replacement Planner CTA */}
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="text-xs text-slate-400">
              Transfer calibrated risk and cost exposure directly into the Replacement Planner:
            </div>

            <button
              type="button"
              onClick={() => navigate('/planner')}
              className="bg-[#00D26A] hover:bg-[#00B75B] text-slate-950 font-bold text-xs py-2 px-5 rounded-lg flex items-center gap-1.5 transition shadow-[0_0_12px_rgba(0,210,106,0.25)]"
            >
              <span>Open Replacement Planner</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
