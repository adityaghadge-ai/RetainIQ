// src/pages/Research.jsx
// =====================
// Verified Empirical Research Telemetry (Clean Enterprise Theme & Large Typography)

import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  BookOpen,
  Download,
  Copy,
  Check,
  Award,
  ShieldCheck,
  Layers,
  Activity
} from 'lucide-react'

// Verified 5-Fold Stratified Out-of-Fold (OOF) Metrics from outputs/baseline_model_comparison.csv
const VERIFIED_OOF_METRICS = [
  { label: 'PR-AUC (Primary Metric)',  value: '0.5983', desc: 'Precision-Recall AUC on minority attrition class' },
  { label: 'ROC-AUC (Discrimination)', value: '0.8236', desc: 'Global ranking separation quality across 5 folds' },
  { label: 'Classification Accuracy', value: '87.48%', desc: '5-fold out-of-fold stratified cross-validation' },
  { label: 'F1 Score (Balanced)',      value: '0.4065', desc: 'Harmonic mean of precision (0.863) & recall (0.266)' },
  { label: 'Brier Score (Distortion)', value: '0.0988', desc: 'Mean squared probability error across all folds' },
  { label: 'ECE (Expected Calib Err)', value: '0.0224', desc: 'Sigmoid Platt scaling calibration quality (-72.4%)' },
]

// Real model comparison across 6 experiments from baseline_model_comparison.csv
const MODEL_COMPARISON = [
  { exp: 'Exp 4 (Selected)', model: 'LogisticRegression', feat: 'Engineered Ratios', pr_auc: '0.5983', roc_auc: '0.8236', acc: '87.48%', ece: '0.0224' },
  { exp: 'Exp 1',            model: 'LogisticRegression', feat: 'Raw Baseline',      pr_auc: '0.5899', roc_auc: '0.8243', acc: '87.01%', ece: '0.0264' },
  { exp: 'Exp 6',            model: 'XGBoost',            feat: 'Engineered Ratios', pr_auc: '0.5440', roc_auc: '0.8047', acc: '86.80%', ece: '0.0376' },
  { exp: 'Exp 3',            model: 'XGBoost',            feat: 'Raw Baseline',      pr_auc: '0.5397', roc_auc: '0.8055', acc: '86.53%', ece: '0.0281' },
  { exp: 'Exp 2',            model: 'RandomForest',       feat: 'Raw Baseline',      pr_auc: '0.5343', roc_auc: '0.8089', acc: '85.92%', ece: '0.0171' },
  { exp: 'Exp 5',            model: 'RandomForest',       feat: 'Engineered Ratios', pr_auc: '0.4785', roc_auc: '0.7903', acc: '84.90%', ece: '0.0279' },
]

export default function Research() {
  const [paper, setPaper] = useState('')
  const [showPaper, setShowPaper] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    axios.get('/api/research/paper')
      .then(res => setPaper(res.data.paper))
      .catch(err => console.error(err))
  }, [])

  const handleDownload = () => {
    const blob = new Blob([paper], { type: 'text/markdown;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'RetainIQ_Academic_Research_Paper.md'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(paper)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-8 py-4 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1A263C] pb-6">
        <div className="space-y-1.5">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Research & Empirical Validation
          </h1>
          <p className="text-sm sm:text-base text-slate-400">
            Verified 5-fold cross-validation benchmarks, probability calibration, and complete academic publication manuscript.
          </p>
        </div>

        {paper && (
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowPaper(!showPaper)}
              className="btn-secondary text-sm py-2 px-4 flex items-center gap-2"
            >
              <BookOpen size={16} />
              <span>{showPaper ? 'Hide Manuscript' : 'View Manuscript'}</span>
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="btn-primary text-sm py-2 px-4 flex items-center gap-2 font-bold"
            >
              <Download size={16} />
              <span>Download .md</span>
            </button>
          </div>
        )}
      </div>

      {/* Verified Metrics Grid */}
      <div className="space-y-4">
        <h2 className="text-base sm:text-lg font-bold text-white">
          Verified 5-Fold Stratified Cross-Validation (Out-of-Fold)
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {VERIFIED_OOF_METRICS.map((m, i) => (
            <div key={i} className="panel p-5 space-y-2 shadow-sm">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">{m.label}</span>
              <div className="text-3xl font-extrabold font-mono text-[#00D26A]">
                {m.value}
              </div>
              <p className="text-xs text-slate-400 leading-relaxed pt-1">
                {m.desc}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Model Benchmark Comparison Table */}
      <div className="space-y-4">
        <h2 className="text-base sm:text-lg font-bold text-white">
          Benchmark Model Comparison (6 Empirical Experiments)
        </h2>

        <div className="overflow-x-auto border border-[#1A263C] rounded-xl">
          <table className="w-full text-sm">
            <thead className="bg-[#0A101D] border-b border-[#1A263C] text-left text-slate-400">
              <tr>
                <th className="py-3.5 px-5 font-semibold">Experiment</th>
                <th className="py-3.5 px-5 font-semibold">Model Architecture</th>
                <th className="py-3.5 px-5 font-semibold">Feature Set</th>
                <th className="py-3.5 px-5 text-right font-semibold">PR-AUC</th>
                <th className="py-3.5 px-5 text-right font-semibold">ROC-AUC</th>
                <th className="py-3.5 px-5 text-right font-semibold">Accuracy</th>
                <th className="py-3.5 px-5 text-right font-semibold">ECE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1A263C]/80 font-mono text-slate-300">
              {MODEL_COMPARISON.map((row, idx) => (
                <tr key={idx} className={row.exp.includes('Selected') ? 'bg-[#00D26A]/10 font-bold' : 'hover:bg-[#131C2E]/40'}>
                  <td className="py-3.5 px-5 font-sans">
                    <span className={row.exp.includes('Selected') ? 'text-[#00D26A]' : 'text-slate-200'}>
                      {row.exp}
                    </span>
                  </td>
                  <td className="py-3.5 px-5 font-sans font-medium text-white">{row.model}</td>
                  <td className="py-3.5 px-5 font-sans text-xs text-slate-400">{row.feat}</td>
                  <td className="py-3.5 px-5 text-right text-[#00D26A] font-bold">{row.pr_auc}</td>
                  <td className="py-3.5 px-5 text-right text-white">{row.roc_auc}</td>
                  <td className="py-3.5 px-5 text-right text-slate-200">{row.acc}</td>
                  <td className="py-3.5 px-5 text-right text-[#00D26A]">{row.ece}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manuscript Viewer */}
      {showPaper && paper && (
        <div className="panel p-6 sm:p-8 space-y-4">
          <div className="flex items-center justify-between border-b border-[#1A263C] pb-3">
            <h2 className="text-base sm:text-lg font-bold text-white">
              Manuscript Preview
            </h2>
            <button
              type="button"
              onClick={handleCopy}
              className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
            >
              {copied ? <Check size={14} className="text-[#00D26A]" /> : <Copy size={14} />}
              <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
            </button>
          </div>
          <pre className="p-5 rounded-xl bg-[#0A101D] border border-[#1A2742] text-xs sm:text-sm font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap max-h-[500px] overflow-y-auto leading-relaxed">
            {paper}
          </pre>
        </div>
      )}
    </div>
  )
}
