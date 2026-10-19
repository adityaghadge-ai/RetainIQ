// src/pages/OrgRiskMap.jsx
// =========================
// RetainIQ — Org-Wide Attrition Risk Heatmap & Contagion Index
// Extraordinary Feature: Real-time batch ML prediction across an entire organisation.
// Novel metric: Attrition Contagion Index (ACI) — cascade risk measurement.

import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import {
  AlertTriangle,
  Upload,
  Users,
  Activity,
  DollarSign,
  Zap,
  ChevronDown,
  ChevronRight,
  BarChart3,
  Flame,
  Shield,
  RefreshCw,
  FileSpreadsheet,
  Info,
  X,
  ArrowUpRight,
  TrendingUp,
} from 'lucide-react'

// ── Helpers ──────────────────────────────────────────────────────────────────
const fmt = (n) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)
const fmtCr = (n) => {
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(1)}Cr`
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(1)}L`
  return `₹${fmt(n)}`
}

const RISK_COLOR = {
  HIGH:     { bg: 'rgba(239,68,68,0.15)',   border: '#ef4444', text: '#f87171',  dot: '#ef4444'  },
  MODERATE: { bg: 'rgba(245,158,11,0.12)',  border: '#f59e0b', text: '#fbbf24',  dot: '#f59e0b'  },
  LOW:      { bg: 'rgba(0,210,106,0.10)',   border: '#00D26A', text: '#00D26A',  dot: '#00D26A'  },
}

const ACI_COLOR = {
  CRITICAL: { bg: 'rgba(239,68,68,0.18)',   text: '#f87171',  label: 'Critical Contagion' },
  HIGH:     { bg: 'rgba(245,158,11,0.15)',  text: '#fbbf24',  label: 'High Contagion'     },
  MODERATE: { bg: 'rgba(99,102,241,0.15)',  text: '#a5b4fc',  label: 'Moderate Contagion' },
  LOW:      { bg: 'rgba(0,210,106,0.10)',   text: '#00D26A',  label: 'Low Contagion'      },
}

// ── Demo roster generator ─────────────────────────────────────────────────────
// Generates a realistic synthetic roster with variance across departments.
function generateDemoRoster() {
  const departments = ['Research & Development', 'Sales', 'Human Resources']
  const roles = {
    'Research & Development': ['Research Scientist', 'Laboratory Technician', 'Research Director', 'Manager'],
    'Sales': ['Sales Executive', 'Sales Representative', 'Manager'],
    'Human Resources': ['Human Resources', 'Manager'],
  }
  const travelOptions = ['Non-Travel', 'Travel_Rarely', 'Travel_Frequently']
  const edFields = ['Life Sciences', 'Medical', 'Marketing', 'Technical Degree', 'Human Resources', 'Other']

  const employees = []
  let counter = 1001

  departments.forEach((dept) => {
    const n = dept === 'Research & Development' ? 18 : dept === 'Sales' ? 12 : 5
    for (let i = 0; i < n; i++) {
      const role = roles[dept][Math.floor(Math.random() * roles[dept].length)]
      const jobLevel = role.includes('Director') ? 4 : role.includes('Manager') ? 3 : role.includes('Senior') ? 3 : Math.floor(Math.random() * 3) + 1
      const yearsAtCo = Math.floor(Math.random() * 15) + 1
      const totalYears = yearsAtCo + Math.floor(Math.random() * 8)
      const overtime = Math.random() < (dept === 'Sales' ? 0.6 : dept === 'Research & Development' ? 0.35 : 0.25) ? 'Yes' : 'No'
      const jobSat = Math.floor(Math.random() * 4) + 1
      const wlb = Math.floor(Math.random() * 4) + 1
      const income = Math.round((40000 + jobLevel * 25000 + Math.random() * 30000) / 1000) * 1000

      employees.push({
        employee_id:             `EMP-${counter++}`,
        employee_name:           `Employee ${counter - 1001}`,
        Department:              dept,
        JobRole:                 role,
        JobLevel:                jobLevel,
        MonthlyIncome:           income,
        TotalWorkingYears:       totalYears,
        YearsAtCompany:          yearsAtCo,
        YearsInCurrentRole:      Math.floor(Math.random() * yearsAtCo) + 1,
        YearsSinceLastPromotion: Math.floor(Math.random() * 8),
        YearsWithCurrManager:    Math.floor(Math.random() * yearsAtCo) + 1,
        OverTime:                overtime,
        JobSatisfaction:         jobSat,
        WorkLifeBalance:         wlb,
        EnvironmentSatisfaction: Math.floor(Math.random() * 4) + 1,
        BusinessTravel:          travelOptions[Math.floor(Math.random() * 3)],
        DistanceFromHome:        Math.floor(Math.random() * 30),
        Education:               Math.floor(Math.random() * 4) + 1,
        EducationField:          edFields[Math.floor(Math.random() * edFields.length)],
        HourlyRate:              Math.floor(Math.random() * 60) + 30,
        DailyRate:               Math.floor(Math.random() * 800) + 200,
        JobInvolvement:          Math.floor(Math.random() * 4) + 1,
        MonthlyRate:             Math.floor(Math.random() * 10000) + 4000,
        NumCompaniesWorked:      Math.floor(Math.random() * 8),
        PercentSalaryHike:       Math.floor(Math.random() * 15) + 10,
        PerformanceRating:       Math.random() < 0.15 ? 4 : 3,
        RelationshipSatisfaction:Math.floor(Math.random() * 4) + 1,
        StockOptionLevel:        Math.floor(Math.random() * 4),
        TrainingTimesLastYear:   Math.floor(Math.random() * 6),
      })
    }
  })

  return employees
}

// ── SVG Heatmap ───────────────────────────────────────────────────────────────
function DepartmentHeatmap({ departments, selectedDept, onSelectDept }) {
  const maxRisk = Math.max(...departments.map(d => d.avg_risk_pct), 1)

  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(auto-fill, minmax(280px, 1fr))`, gap: '14px' }}>
      {departments.map((dept) => {
        const riskLevel = dept.avg_risk_pct >= 40 ? 'HIGH' : dept.avg_risk_pct >= 25 ? 'MODERATE' : 'LOW'
        const col = RISK_COLOR[riskLevel]
        const aciCol = ACI_COLOR[dept.contagion_level || 'LOW']
        const isSelected = selectedDept === dept.department
        const fillWidth = `${(dept.avg_risk_pct / maxRisk) * 100}%`

        return (
          <button
            key={dept.department}
            onClick={() => onSelectDept(isSelected ? null : dept.department)}
            style={{
              background: isSelected ? col.bg : '#0E1626',
              border: `1px solid ${isSelected ? col.border : '#1A263C'}`,
              borderRadius: '14px',
              padding: '20px',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'all 0.2s ease',
              outline: 'none',
              boxShadow: isSelected ? `0 0 20px ${col.border}30` : 'none',
            }}
          >
            {/* Department name */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
                {dept.department}
              </span>
              <span style={{
                fontSize: '11px', fontWeight: 700, padding: '3px 8px', borderRadius: '6px',
                background: col.bg, color: col.text, border: `1px solid ${col.border}40`,
              }}>
                {riskLevel}
              </span>
            </div>

            {/* Risk bar */}
            <div style={{ marginBottom: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', color: '#64748b' }}>Avg. Attrition Risk</span>
                <span style={{ fontSize: '14px', fontWeight: 800, color: col.text }}>{dept.avg_risk_pct}%</span>
              </div>
              <div style={{ height: '6px', background: '#131E33', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', width: fillWidth, background: col.border,
                  borderRadius: '3px', transition: 'width 0.8s ease',
                  boxShadow: `0 0 8px ${col.border}60`,
                }} />
              </div>
            </div>

            {/* Stats row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
              <div style={{ background: '#0A101D', borderRadius: '8px', padding: '10px' }}>
                <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '3px' }}>Headcount</div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#f8fafc' }}>{dept.headcount}</div>
              </div>
              <div style={{ background: '#0A101D', borderRadius: '8px', padding: '10px' }}>
                <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '3px' }}>High Risk</div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#f87171' }}>{dept.high_risk_count}</div>
              </div>
            </div>

            {/* ERL */}
            <div style={{ background: '#0A101D', borderRadius: '8px', padding: '10px', marginBottom: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', color: '#64748b' }}>Est. ERL Exposure</span>
                <span style={{ fontSize: '13px', fontWeight: 800, color: '#fbbf24' }}>{fmtCr(dept.total_erl)}</span>
              </div>
            </div>

            {/* Contagion Index */}
            <div style={{
              background: aciCol.bg, borderRadius: '8px', padding: '10px',
              border: `1px solid ${aciCol.text}30`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Contagion Index</div>
                  <div style={{ fontSize: '11px', color: aciCol.text, fontWeight: 600, marginTop: '1px' }}>{aciCol.label}</div>
                </div>
                <div style={{ fontSize: '22px', fontWeight: 900, color: aciCol.text }}>{dept.contagion_index}</div>
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}

// ── Employee scatter plot (pure SVG) ──────────────────────────────────────────
function EmployeeScatter({ employees }) {
  const [hovered, setHovered] = useState(null)
  const svgW = 580, svgH = 260, padL = 40, padB = 30, padT = 16, padR = 20

  if (!employees || employees.length === 0) return null

  const maxIncome = Math.max(...employees.map(e => e.monthly_income), 1)
  const maxYears  = Math.max(...employees.map(e => e.years_at_company), 1)

  const toX = (v) => padL + (v / maxYears) * (svgW - padL - padR)
  const toY = (v) => padT + (1 - v / maxIncome) * (svgH - padT - padB)

  return (
    <div style={{ position: 'relative' }}>
      <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px' }}>
        Risk by Years at Company vs. Monthly Income — each dot is one employee
      </div>
      <svg width="100%" viewBox={`0 0 ${svgW} ${svgH}`} style={{ overflow: 'visible' }}>
        {/* Grid lines */}
        {[0.25, 0.5, 0.75, 1].map(t => (
          <line key={t} x1={padL} x2={svgW - padR} y1={padT + (1-t)*(svgH-padT-padB)} y2={padT + (1-t)*(svgH-padT-padB)}
            stroke="#1A263C" strokeWidth={1} />
        ))}
        {/* Axis labels */}
        <text x={padL - 6} y={padT + (svgH - padT - padB)/2} fill="#475569" fontSize="10" textAnchor="end" dominantBaseline="middle" transform={`rotate(-90 ${padL-6} ${padT+(svgH-padT-padB)/2})`}>Income</text>
        <text x={(svgW + padL - padR)/2} y={svgH - 4} fill="#475569" fontSize="10" textAnchor="middle">Years at Company</text>

        {/* Dots */}
        {employees.map((emp, idx) => {
          const col = RISK_COLOR[emp.risk_category] || RISK_COLOR.LOW
          const cx = toX(emp.years_at_company)
          const cy = toY(emp.monthly_income)
          const r = emp.risk_category === 'HIGH' ? 7 : emp.risk_category === 'MODERATE' ? 5.5 : 4.5
          return (
            <g key={idx}>
              {emp.risk_category === 'HIGH' && (
                <circle cx={cx} cy={cy} r={r + 5} fill={col.dot} opacity={0.12} />
              )}
              <circle
                cx={cx} cy={cy} r={r}
                fill={col.dot}
                fillOpacity={0.85}
                stroke={col.border}
                strokeWidth={1}
                style={{ cursor: 'pointer', transition: 'r 0.15s' }}
                onMouseEnter={() => setHovered({ emp, cx, cy })}
                onMouseLeave={() => setHovered(null)}
              />
            </g>
          )
        })}

        {/* Tooltip */}
        {hovered && (() => {
          const { emp, cx, cy } = hovered
          const col = RISK_COLOR[emp.risk_category]
          const tw = 160, th = 72
          const tx = Math.min(cx + 10, svgW - tw - padR)
          const ty = Math.max(cy - th - 8, padT)
          return (
            <g>
              <rect x={tx} y={ty} width={tw} height={th} rx={7} fill="#0E1626" stroke={col.border} strokeWidth={1} />
              <text x={tx+10} y={ty+16} fill="#f8fafc" fontSize="11" fontWeight="700">{emp.employee_id}</text>
              <text x={tx+10} y={ty+30} fill="#94a3b8" fontSize="10">{emp.job_role}</text>
              <text x={tx+10} y={ty+44} fill={col.text} fontSize="11" fontWeight="700">{emp.risk_pct}% risk</text>
              <text x={tx+10} y={ty+58} fill="#64748b" fontSize="9">OT: {emp.over_time} · Sat: {emp.job_satisfaction}/4</text>
            </g>
          )
        })()}
      </svg>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '16px', marginTop: '4px' }}>
        {['HIGH', 'MODERATE', 'LOW'].map(cat => {
          const col = RISK_COLOR[cat]
          return (
            <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: col.dot }} />
              <span style={{ fontSize: '11px', color: '#64748b' }}>{cat}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function OrgRiskMap() {
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState('')
  const [result, setResult] = useState(null)
  const [selectedDept, setSelectedDept] = useState(null)
  const [sortBy, setSortBy] = useState('risk') // risk | aci | erl | headcount
  const [showInfo, setShowInfo] = useState(false)
  const fileRef = useRef(null)

  // Run on IBM demo roster automatically
  const runDemo = useCallback(async () => {
    setLoading(true)
    setError('')
    setResult(null)
    setSelectedDept(null)

    const employees = generateDemoRoster()
    try {
      const resp = await axios.post('/api/roster/analyze', { employees })
      setResult(resp.data)
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Analysis failed. Is the ML service running?')
    } finally {
      setLoading(false)
    }
  }, [])

  // Upload CSV/JSON
  const handleFileUpload = async (file) => {
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['csv', 'json'].includes(ext)) {
      setError('Roster upload must be a .csv or .json file.')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)
    setSelectedDept(null)

    const form = new FormData()
    form.append('file', file)
    try {
      const resp = await axios.post('/api/roster/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(resp.data)
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Upload failed.')
    } finally {
      setLoading(false)
    }
  }

  // Sort departments
  const sortedDepts = result?.departments
    ? [...result.departments].sort((a, b) => {
        if (sortBy === 'risk')      return b.avg_risk_pct - a.avg_risk_pct
        if (sortBy === 'aci')       return b.contagion_index - a.contagion_index
        if (sortBy === 'erl')       return b.total_erl - a.total_erl
        if (sortBy === 'headcount') return b.headcount - a.headcount
        return 0
      })
    : []

  const activeDept = result?.departments?.find(d => d.department === selectedDept)

  const org = result?.organisation_summary

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', paddingBottom: '60px' }}>

      {/* ── Page Header ── */}
      <div style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <div style={{
                width: 36, height: 36, borderRadius: '10px',
                background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.35)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Activity size={18} color="#f87171" />
              </div>
              <h1 style={{ fontSize: '22px', fontWeight: 800, color: '#f8fafc', margin: 0 }}>
                Org-Wide Risk Heatmap
              </h1>
              <span style={{
                fontSize: '10px', fontWeight: 700, padding: '3px 8px', borderRadius: '5px',
                background: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)',
                textTransform: 'uppercase', letterSpacing: '0.08em',
              }}>
                Flagship Feature
              </span>
            </div>
            <p style={{ fontSize: '14px', color: '#64748b', margin: 0, maxWidth: '560px', lineHeight: 1.6 }}>
              Batch-predict attrition risk across your entire organisation. Visualise department-level exposure, 
              identify cascade risk clusters, and quantify total ERL in one view.
            </p>
          </div>

          <button
            onClick={() => setShowInfo(!showInfo)}
            style={{
              background: '#0E1626', border: '1px solid #1A263C', borderRadius: '8px',
              padding: '8px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
              color: '#64748b', fontSize: '12px', fontWeight: 600, transition: 'all 0.15s',
            }}
          >
            <Info size={13} />
            ACI Explained
          </button>
        </div>
      </div>

      {/* ── ACI Info Panel ── */}
      {showInfo && (
        <div style={{
          background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.25)',
          borderRadius: '12px', padding: '20px', marginBottom: '24px', position: 'relative',
        }}>
          <button onClick={() => setShowInfo(false)} style={{
            position: 'absolute', top: 14, right: 14, background: 'none', border: 'none',
            cursor: 'pointer', color: '#64748b', padding: '2px',
          }}>
            <X size={14} />
          </button>
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#a5b4fc', marginBottom: '10px' }}>
            Attrition Contagion Index (ACI) — Research Methodology
          </div>
          <div style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.7, maxWidth: '700px' }}>
            The ACI is a novel composite metric quantifying <em>cascade attrition risk</em> within a department.
            It is calculated as the probability-weighted concentration of HIGH-risk employees, adjusted by:
            <br /><br />
            <code style={{ fontFamily: 'monospace', fontSize: '12px', color: '#c4b5fd' }}>
              ACI = (Σ P(attrition) × JobLevel_weight) / n × concentration_factor × 100
            </code>
            <br /><br />
            The concentration factor amplifies when &gt;40% of a team is high-risk, reflecting peer attrition
            contagion effects documented in Mitchell et al. (2001) and Felps et al. (2009).
            ACI ≥ 45 = Critical; ACI ≥ 28 = High; ACI ≥ 15 = Moderate; else Low.
          </div>
        </div>
      )}

      {/* ── Action Bar ── */}
      {!result && !loading && (
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '28px',
        }}>
          {/* Demo Mode */}
          <button
            onClick={runDemo}
            style={{
              background: '#0E1626', border: '1px solid #1A263C', borderRadius: '14px',
              padding: '28px 24px', cursor: 'pointer', textAlign: 'left', transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#00D26A'; e.currentTarget.style.background = 'rgba(0,210,106,0.05)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#1A263C'; e.currentTarget.style.background = '#0E1626' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <div style={{
                width: 36, height: 36, borderRadius: '9px',
                background: 'rgba(0,210,106,0.12)', border: '1px solid rgba(0,210,106,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Zap size={18} color="#00D26A" />
              </div>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>Run Demo Analysis</div>
                <div style={{ fontSize: '12px', color: '#64748b' }}>35 synthetic employees, 3 departments</div>
              </div>
            </div>
            <div style={{ fontSize: '12px', color: '#64748b', lineHeight: 1.6 }}>
              Instantly generate and analyse a realistic IBM-characteristic roster. 
              No upload required — see the full feature in action.
            </div>
            <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '6px', color: '#00D26A', fontSize: '13px', fontWeight: 700 }}>
              Run Now <ChevronRight size={14} />
            </div>
          </button>

          {/* Upload Roster */}
          <button
            onClick={() => fileRef.current?.click()}
            style={{
              background: '#0E1626', border: '1px solid #1A263C', borderRadius: '14px',
              padding: '28px 24px', cursor: 'pointer', textAlign: 'left', transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#6366f1'; e.currentTarget.style.background = 'rgba(99,102,241,0.05)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#1A263C'; e.currentTarget.style.background = '#0E1626' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <div style={{
                width: 36, height: 36, borderRadius: '9px',
                background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Upload size={18} color="#818cf8" />
              </div>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>Upload Roster File</div>
                <div style={{ fontSize: '12px', color: '#64748b' }}>CSV or JSON · up to 500 employees</div>
              </div>
            </div>
            <div style={{ fontSize: '12px', color: '#64748b', lineHeight: 1.6 }}>
              Upload your own employee roster in CSV format. Required columns:
              Department, JobRole, MonthlyIncome, YearsAtCompany, OverTime, JobSatisfaction.
            </div>
            <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '6px', color: '#818cf8', fontSize: '13px', fontWeight: 700 }}>
              Choose File <ChevronRight size={14} />
            </div>
          </button>
          <input
            ref={fileRef} type="file" accept=".csv,.json" style={{ display: 'none' }}
            onChange={e => { if (e.target.files?.[0]) handleFileUpload(e.target.files[0]) }}
          />
        </div>
      )}

      {/* ── Loading ── */}
      {loading && (
        <div style={{
          background: '#0E1626', border: '1px solid #1A263C', borderRadius: '14px',
          padding: '48px', textAlign: 'center', marginBottom: '24px',
        }}>
          <div style={{
            width: 48, height: 48, borderRadius: '50%', margin: '0 auto 16px',
            border: '3px solid #1A263C', borderTopColor: '#00D26A',
            animation: 'spin 0.9s linear infinite',
          }} />
          <div style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc', marginBottom: '6px' }}>
            Running batch ML predictions…
          </div>
          <div style={{ fontSize: '13px', color: '#64748b' }}>
            Calibrated Logistic Regression model running on each employee record
          </div>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* ── Error ── */}
      {error && (
        <div style={{
          background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: '12px', padding: '16px 20px', marginBottom: '24px',
          display: 'flex', alignItems: 'flex-start', gap: '12px',
        }}>
          <AlertTriangle size={16} color="#f87171" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#f87171', marginBottom: '4px' }}>Analysis Failed</div>
            <div style={{ fontSize: '13px', color: '#94a3b8' }}>{error}</div>
          </div>
          <button onClick={() => setError('')} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', padding: '2px' }}>
            <X size={14} />
          </button>
        </div>
      )}

      {/* ── Results ── */}
      {result && (
        <>
          {/* Reset bar */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '18px', gap: '10px' }}>
            <button
              onClick={() => { setResult(null); setSelectedDept(null); setError('') }}
              style={{
                background: '#0E1626', border: '1px solid #1A263C', borderRadius: '8px',
                padding: '8px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                color: '#64748b', fontSize: '12px', fontWeight: 600, transition: 'all 0.15s',
              }}
            >
              <RefreshCw size={12} /> New Analysis
            </button>
            <button
              onClick={runDemo}
              style={{
                background: '#0E1626', border: '1px solid #1A263C', borderRadius: '8px',
                padding: '8px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                color: '#64748b', fontSize: '12px', fontWeight: 600, transition: 'all 0.15s',
              }}
            >
              <Zap size={12} /> Re-run Demo
            </button>
          </div>

          {/* ── Org Summary Cards ── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '28px' }}>
            {[
              {
                label: 'Total Employees',
                value: org.total_employees,
                sub: 'Analysed',
                icon: <Users size={16} color="#818cf8" />,
                bg: 'rgba(99,102,241,0.1)', border: '#6366f140',
              },
              {
                label: 'Avg Attrition Risk',
                value: `${org.avg_risk_pct}%`,
                sub: 'Organisation-wide',
                icon: <Activity size={16} color="#f59e0b" />,
                bg: 'rgba(245,158,11,0.1)', border: '#f59e0b40',
              },
              {
                label: 'High-Risk Employees',
                value: `${org.high_risk_count} (${org.high_risk_pct}%)`,
                sub: 'Require immediate attention',
                icon: <Flame size={16} color="#f87171" />,
                bg: 'rgba(239,68,68,0.1)', border: '#ef444440',
              },
              {
                label: 'Total ERL Estimate',
                value: fmtCr(org.total_erl_estimate),
                sub: 'Expected Replacement Loss',
                icon: <DollarSign size={16} color="#34d399" />,
                bg: 'rgba(52,211,153,0.1)', border: '#34d39940',
              },
            ].map(card => (
              <div key={card.label} style={{
                background: card.bg, border: `1px solid ${card.border}`,
                borderRadius: '12px', padding: '18px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                  {card.icon}
                  <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>{card.label}</span>
                </div>
                <div style={{ fontSize: '20px', fontWeight: 900, color: '#f8fafc', marginBottom: '3px' }}>
                  {card.value}
                </div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>{card.sub}</div>
              </div>
            ))}
          </div>

          {/* ── Critical Contagion Alert ── */}
          {org.critical_contagion_dept && org.critical_contagion_aci >= 28 && (
            <div style={{
              background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.28)',
              borderRadius: '12px', padding: '16px 20px', marginBottom: '24px',
              display: 'flex', alignItems: 'center', gap: '14px',
            }}>
              <div style={{
                width: 36, height: 36, borderRadius: '9px', flexShrink: 0,
                background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.35)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Flame size={18} color="#f87171" />
              </div>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#f87171', marginBottom: '3px' }}>
                  Cascade Attrition Risk Detected — {org.critical_contagion_dept}
                </div>
                <div style={{ fontSize: '13px', color: '#94a3b8' }}>
                  Attrition Contagion Index of <strong style={{ color: '#f87171' }}>{org.critical_contagion_aci}</strong> indicates 
                  a concentration of high-risk employees in critical roles. Departure cascades are statistically elevated.
                  Targeted retention intervention is recommended.
                </div>
              </div>
            </div>
          )}

          {/* ── Sort Controls ── */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Sort by:</span>
            {[
              { key: 'risk', label: 'Avg Risk' },
              { key: 'aci', label: 'Contagion Index' },
              { key: 'erl', label: 'ERL Exposure' },
              { key: 'headcount', label: 'Headcount' },
            ].map(s => (
              <button
                key={s.key}
                onClick={() => setSortBy(s.key)}
                style={{
                  padding: '5px 12px', borderRadius: '7px', cursor: 'pointer', fontSize: '12px', fontWeight: 600,
                  background: sortBy === s.key ? '#00D26A' : '#0E1626',
                  color: sortBy === s.key ? '#06130C' : '#64748b',
                  border: `1px solid ${sortBy === s.key ? '#00D26A' : '#1A263C'}`,
                  transition: 'all 0.15s',
                }}
              >
                {s.label}
              </button>
            ))}
          </div>

          {/* ── Department Heatmap Grid ── */}
          <DepartmentHeatmap
            departments={sortedDepts}
            selectedDept={selectedDept}
            onSelectDept={setSelectedDept}
          />

          {/* ── Expanded Department Detail ── */}
          {activeDept && (
            <div style={{
              background: '#0E1626', border: '1px solid #1A263C', borderRadius: '14px',
              padding: '28px', marginTop: '20px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
                <div>
                  <h2 style={{ fontSize: '17px', fontWeight: 800, color: '#f8fafc', margin: '0 0 4px' }}>
                    {activeDept.department} — Employee Detail
                  </h2>
                  <div style={{ fontSize: '13px', color: '#64748b' }}>
                    {activeDept.headcount} employees · hover over dots to inspect individuals
                  </div>
                </div>
                <button
                  onClick={() => setSelectedDept(null)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', padding: '4px' }}
                >
                  <X size={16} />
                </button>
              </div>

              {/* Scatter plot */}
              <EmployeeScatter employees={activeDept.employees} />

              {/* Employee table */}
              <div style={{ marginTop: '24px', overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                  <thead>
                    <tr>
                      {['Employee ID', 'Role', 'Level', 'Risk %', 'Category', 'OT', 'Job Sat.', 'Yrs at Co.'].map(h => (
                        <th key={h} style={{
                          textAlign: 'left', padding: '8px 12px', borderBottom: '1px solid #1A263C',
                          fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em',
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[...activeDept.employees]
                      .sort((a, b) => b.risk_pct - a.risk_pct)
                      .map((emp, idx) => {
                        const col = RISK_COLOR[emp.risk_category]
                        return (
                          <tr key={idx} style={{ borderBottom: '1px solid #111827' }}>
                            <td style={{ padding: '10px 12px', color: '#94a3b8', fontFamily: 'monospace', fontSize: '12px' }}>{emp.employee_id}</td>
                            <td style={{ padding: '10px 12px', color: '#f8fafc', fontWeight: 600 }}>{emp.job_role}</td>
                            <td style={{ padding: '10px 12px', color: '#94a3b8' }}>L{emp.job_level}</td>
                            <td style={{ padding: '10px 12px', fontWeight: 800, color: col.text }}>{emp.risk_pct}%</td>
                            <td style={{ padding: '10px 12px' }}>
                              <span style={{
                                fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '5px',
                                background: col.bg, color: col.text, border: `1px solid ${col.border}40`,
                              }}>{emp.risk_category}</span>
                            </td>
                            <td style={{ padding: '10px 12px', color: emp.over_time === 'Yes' ? '#fbbf24' : '#64748b', fontWeight: emp.over_time === 'Yes' ? 700 : 400 }}>
                              {emp.over_time}
                            </td>
                            <td style={{ padding: '10px 12px', color: emp.job_satisfaction <= 2 ? '#f87171' : '#94a3b8' }}>
                              {emp.job_satisfaction}/4
                            </td>
                            <td style={{ padding: '10px 12px', color: '#94a3b8' }}>{emp.years_at_company}y</td>
                          </tr>
                        )
                      })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── Disclaimer ── */}
          <div style={{
            marginTop: '28px', background: '#0B111E', border: '1px solid #182338',
            borderRadius: '10px', padding: '14px 18px',
          }}>
            <div style={{ fontSize: '11px', color: '#475569', lineHeight: 1.65 }}>
              <strong style={{ color: '#64748b' }}>Research Disclaimer:</strong> {result.disclaimer}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
