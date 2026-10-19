// src/pages/Candidates.jsx
import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  Users,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Briefcase,
  MapPin,
  Clock,
  Layers,
  ChevronRight
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function Candidates() {
  const navigate = useNavigate()
  const [role, setRole] = useState('')
  const [skills, setSkills] = useState('')
  const [minExp, setMinExp] = useState(3)
  const [maxSalary, setMaxSalary] = useState(2500000)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedCandidate, setSelectedCandidate] = useState(null)

  useEffect(() => {
    const stored = localStorage.getItem('riq_prediction')
    if (stored) {
      try {
        const p = JSON.parse(stored)
        if (p.employee_profile?.job_role) {
          setRole(p.employee_profile.job_role)
        }
      } catch {}
    }
    const sel = localStorage.getItem('riq_selected_candidate')
    if (sel) {
      try { setSelectedCandidate(JSON.parse(sel)) } catch {}
    }
    loadCandidates()
  }, [])

  const loadCandidates = async () => {
    setLoading(true)
    try {
      const res = await axios.get('/api/candidates/all')
      setResults(res.data.candidates || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (e) => {
    e?.preventDefault()
    setLoading(true)
    try {
      const skillArray = skills
        .split(',')
        .map(s => s.trim())
        .filter(Boolean)

      const res = await axios.post('/api/candidates/search', {
        role,
        skills: skillArray,
        minExperience: Number(minExp),
        maxSalary: Number(maxSalary),
      })
      setResults(res.data.candidates || [])
    } catch (err) {
      console.error('Candidate search failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectCandidate = (cand) => {
    setSelectedCandidate(cand)
    localStorage.setItem('riq_selected_candidate', JSON.stringify(cand))
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100">
            Talent Pool Sourcing & Candidate RAG Matching
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Multi-criteria explainable alignment against replacement profile specifications
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/results')}
            className="btn-primary text-xs py-2 px-3.5 flex items-center gap-1.5"
          >
            Review Action Memo <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Query Specifications Filter Bar */}
      <form onSubmit={handleSearch} className="panel p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-blue-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-200">
              Replacement Role Criteria
            </span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">WEIGHTED MULTI-CRITERIA SCORING</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div>
            <label>Target Role</label>
            <input
              type="text"
              value={role}
              onChange={e => setRole(e.target.value)}
              placeholder="e.g. Research Scientist"
            />
          </div>
          <div>
            <label>Required Competencies</label>
            <input
              type="text"
              value={skills}
              onChange={e => setSkills(e.target.value)}
              placeholder="Python, ML, SQL, FastAPI"
            />
          </div>
          <div>
            <label>Min Experience (Years)</label>
            <input
              type="number"
              min={0}
              max={30}
              value={minExp}
              onChange={e => setMinExp(e.target.value)}
            />
          </div>
          <div>
            <label>Salary Ceiling (₹/year)</label>
            <input
              type="number"
              step={100000}
              value={maxSalary}
              onChange={e => setMaxSalary(e.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-1">
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5"
            >
              <Search size={13} /> {loading ? 'Evaluating Pipeline...' : 'Search & Rank Candidates'}
            </button>
            <button
              type="button"
              onClick={loadCandidates}
              className="btn-secondary text-xs py-1.5 px-3"
            >
              Reset Filters
            </button>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {results.length} Profiles Evaluated
          </span>
        </div>
      </form>

      {/* Candidate Cards Grid */}
      <div className="space-y-3">
        {results.map((c) => {
          const isSelected = selectedCandidate?.id === c.id
          const score = c.match_score != null ? Math.round(c.match_score * 100) : 80
          return (
            <div
              key={c.id}
              onClick={() => handleSelectCandidate(c)}
              className={`panel p-4 transition-colors cursor-pointer ${
                isSelected
                  ? 'border-blue-500/80 bg-blue-950/20'
                  : 'hover:border-slate-700'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="font-semibold text-sm text-slate-100">{c.name}</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                      {c.id}
                    </span>
                    {isSelected && (
                      <span className="badge-low text-[10px] flex items-center gap-1">
                        <CheckCircle2 size={11} /> Selected for Replacement Pipeline
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap">
                    <span className="flex items-center gap-1">
                      <Briefcase size={12} className="text-slate-500" /> {c.role} ({c.experience_years} yrs exp)
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock size={12} className="text-slate-500" /> Notice: {c.notice_period_days} days
                    </span>
                    <span className="flex items-center gap-1">
                      <MapPin size={12} className="text-slate-500" /> {c.location}
                    </span>
                  </div>

                  {/* Skills tags */}
                  <div className="flex gap-1.5 flex-wrap pt-1">
                    {(c.skills || []).map((s) => {
                      const isMatch = (c.matching_skills || []).includes(s.toLowerCase())
                      return (
                        <span
                          key={s}
                          className={`text-[11px] px-2 py-0.5 rounded border ${
                            isMatch
                              ? 'bg-blue-950/40 border-blue-800/60 text-blue-300'
                              : 'bg-slate-900 border-slate-800 text-slate-400'
                          }`}
                        >
                          {s}
                        </span>
                      )
                    })}
                  </div>

                  {c.projects && (
                    <div className="text-xs text-slate-400 pt-1">
                      <span className="text-slate-300 font-medium">Experience Highlight:</span> {c.projects}
                    </div>
                  )}
                </div>

                {/* Score Column */}
                <div className="sm:text-right flex sm:flex-col items-center sm:items-end justify-between gap-1 flex-shrink-0">
                  <div className="text-[10px] uppercase font-semibold text-slate-400">Match Index</div>
                  <div
                    className={`text-2xl font-extrabold font-mono ${
                      score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-amber-400' : 'text-slate-300'
                    }`}
                  >
                    {score}%
                  </div>
                  <div className="text-xs font-mono text-slate-400">
                    ₹{(c.salary_expectation / 100000).toFixed(1)}L Expected
                  </div>

                  {c.score_breakdown && (
                    <div className="hidden sm:block text-[10px] font-mono text-slate-500 space-y-0.5 mt-2">
                      <div>Skill: {c.score_breakdown.skill_score}%</div>
                      <div>Role: {c.score_breakdown.role_score}%</div>
                      <div>Exp: {c.score_breakdown.experience_score}%</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="disclaimer-box text-[11px]">
        <strong>RAG Matching Protocol:</strong> Match percentages reflect algorithmic alignment against explicit input parameters. Candidate scoring is decision-support data and does not constitute a guaranteed hiring recommendation.
      </div>
    </div>
  )
}
