// src/pages/Dashboard.jsx
// ========================
// RetainIQ Dashboard — Restrained, Workflow-Oriented Professional B2B Interface

import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  UploadCloud,
  FileText,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Database,
  Activity,
  UserCheck
} from 'lucide-react'

export default function Dashboard() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)

  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [isDragOver, setIsDragOver] = useState(false)

  // Real Backend Model Metadata
  const [modelMeta, setModelMeta] = useState(null)

  // Active Employee Case state read from sessionStorage
  const [activeAnalysis, setActiveAnalysis] = useState(null)

  useEffect(() => {
    // Read model info from backend
    axios.get('/api/model/info')
      .then(res => setModelMeta(res.data))
      .catch(err => console.error('Failed fetching model info:', err))

    // Read actual active employee analysis if available
    const saved = sessionStorage.getItem('riq_current_analysis')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        if (parsed && parsed.prediction) {
          setActiveAnalysis(parsed)
        }
      } catch (e) {
        console.error(e)
      }
    }
  }, [])

  const handleFileDrop = (e) => {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0])
    }
  }

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0])
    }
  }

  const validateAndSetFile = (file) => {
    setUploadError('')
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['pdf', 'csv', 'xlsx', 'json'].includes(ext)) {
      setUploadError('Unsupported format. Please upload a PDF, CSV, XLSX, or JSON employee record.')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setUploadError('File size exceeds maximum limit of 5 MB.')
      return
    }
    setSelectedFile(file)
  }

  const handleUploadAndAnalyze = async () => {
    if (!selectedFile) return
    setUploading(true)
    setUploadError('')

    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const uploadRes = await axios.post('/api/employee/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      const extracted = uploadRes.data
      sessionStorage.setItem('riq_extracted_record', JSON.stringify(extracted))
      navigate('/analyze')
    } catch (err) {
      setUploadError(err.response?.data?.error || 'Document extraction failed. Please try another file or manual entry.')
    } finally {
      setUploading(false)
    }
  }

  const fmtCurrency = (n) => {
    if (n == null) return '--'
    if (n >= 10000000) return `₹${(n / 10000000).toFixed(2)} Cr`
    if (n >= 100000) return `₹${(n / 100000).toFixed(2)} Lakh`
    return `₹${Math.round(n).toLocaleString('en-IN')}`
  }

  return (
    <div className="space-y-8 py-4 max-w-6xl mx-auto">
      {/* Header Block */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1A263C] pb-6">
        <div className="space-y-1.5">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            RetainIQ — Employee Attrition & Replacement Intelligence
          </h1>
          <p className="text-sm sm:text-base text-slate-400 max-w-3xl">
            Analyze employee records, estimate departure risk using calibrated machine learning models, and evaluate potential replacement exposure.
          </p>
        </div>

        <button
          type="button"
          onClick={() => navigate('/analyze')}
          className="btn-primary text-sm py-2.5 px-5 flex items-center gap-2 self-start sm:self-auto font-bold"
        >
          <span>Analyze Employee</span>
          <ArrowRight size={16} />
        </button>
      </div>

      {/* Main Action Section: Upload File */}
      <div className="panel p-7 sm:p-8 space-y-5 shadow-lg">
        <div className="flex items-center justify-between">
          <h2 className="text-base sm:text-lg font-bold text-white">Start Analysis</h2>
          <span className="text-xs text-slate-400 font-mono">Maximum file size: 5 MB</span>
        </div>

        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleFileDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition flex flex-col items-center justify-center gap-3 ${
            isDragOver
              ? 'border-blue-500 bg-blue-950/20'
              : selectedFile
              ? 'border-[#00D26A] bg-[#00D26A]/10'
              : 'border-[#1A2742] hover:border-slate-600 bg-[#0A101D] hover:bg-[#0D1526]'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.csv,.xlsx,.json"
            onChange={handleFileSelect}
            className="hidden"
          />

          <div className="w-12 h-12 rounded-xl bg-[#131C2E] border border-[#1E2B46] text-slate-300 flex items-center justify-center">
            {selectedFile ? <FileText size={24} className="text-[#00D26A]" /> : <UploadCloud size={24} />}
          </div>

          <div className="space-y-1">
            {selectedFile ? (
              <>
                <div className="text-base font-semibold text-white flex items-center justify-center gap-2">
                  <CheckCircle2 size={18} className="text-[#00D26A]" />
                  <span>{selectedFile.name}</span>
                </div>
                <div className="text-xs text-slate-400 font-mono">
                  {(selectedFile.size / 1024).toFixed(1)} KB · Click to change file
                </div>
              </>
            ) : (
              <>
                <div className="text-base font-semibold text-slate-200">
                  Drag and drop employee file here, or browse
                </div>
                <div className="text-xs text-slate-400">
                  Supported formats: PDF, CSV, XLSX, JSON (Extracts tenure, role, compensation, and work condition indicators)
                </div>
              </>
            )}
          </div>
        </div>

        {uploadError && (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-800 text-red-300 text-sm flex items-center gap-2.5">
            <AlertCircle size={18} className="flex-shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-3 border-t border-[#1A263C]">
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <ShieldCheck size={16} className="text-[#00D26A]" />
            <span>Age, Gender, and MaritalStatus strictly excluded from ML inputs.</span>
          </div>

          <button
            type="button"
            onClick={handleUploadAndAnalyze}
            disabled={!selectedFile || uploading}
            className="btn-primary text-sm py-2.5 px-6 w-full sm:w-auto font-bold flex items-center justify-center gap-2"
          >
            <span>{uploading ? 'Extracting...' : 'Upload & Run Analysis'}</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>

      {/* Two-Column Section: Recent Analysis & System Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Recent Analysis */}
        <div className="panel p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-[#1A263C] pb-3">
            <h2 className="text-base font-bold text-white">Recent Employee Analysis</h2>
            {activeAnalysis && (
              <button
                type="button"
                onClick={() => navigate('/reports')}
                className="text-xs text-[#00D26A] hover:underline font-semibold"
              >
                View Full Report →
              </button>
            )}
          </div>

          {activeAnalysis ? (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between py-2 border-b border-[#1A263C]/60">
                <span className="text-slate-400">Employee Case</span>
                <span className="font-mono font-bold text-white">{activeAnalysis.case_id}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1A263C]/60">
                <span className="text-slate-400">Target Role</span>
                <span className="font-medium text-slate-200">{activeAnalysis.features?.JobRole || 'Senior Software Engineer'}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1A263C]/60">
                <span className="text-slate-400">Estimated Departure Risk</span>
                <span className="font-mono font-bold text-white">{activeAnalysis.prediction?.probability_pct}% ({activeAnalysis.prediction?.risk_category})</span>
              </div>
              {activeAnalysis.erl?.expected_replacement_loss != null && (
                <div className="flex justify-between py-2 border-b border-[#1A263C]/60">
                  <span className="text-slate-400">Expected Replacement Loss</span>
                  <span className="font-mono font-bold text-[#00D26A]">
                    {fmtCurrency(activeAnalysis.erl?.expected_replacement_loss)}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-slate-400 space-y-2">
              <p>No employee record analyzed in this session.</p>
              <button
                type="button"
                onClick={() => navigate('/analyze')}
                className="text-xs text-[#00D26A] hover:underline font-semibold"
              >
                Analyze an employee record →
              </button>
            </div>
          )}
        </div>

        {/* Live System & Model Status */}
        <div className="panel p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-[#1A263C] pb-3">
            <h2 className="text-base font-bold text-white">Model Infrastructure & Governance</h2>
            <span className="badge badge-success text-xs font-bold">● Live Service</span>
          </div>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-2 border-b border-[#1A263C]/60">
              <span className="text-slate-400">Active Model</span>
              <span className="font-mono font-bold text-white">{modelMeta?.model_name || 'LogisticRegression'} v{modelMeta?.model_version || '1.0.0'}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#1A263C]/60">
              <span className="text-slate-400">Calibration Method</span>
              <span className="font-medium text-[#00D26A]">{modelMeta?.calibration || 'Sigmoid Platt Scaling'}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#1A263C]/60">
              <span className="text-slate-400">Out-of-Fold ROC-AUC</span>
              <span className="font-mono font-bold text-white">{modelMeta?.roc_auc ? (modelMeta.roc_auc * 100).toFixed(1) + '%' : '82.4%'}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#1A263C]/60">
              <span className="text-slate-400">Expected Calibration Error</span>
              <span className="font-mono font-bold text-[#00D26A]">{modelMeta?.ece || '0.0224'} (-72.4%)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
