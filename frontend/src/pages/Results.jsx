// src/pages/Results.jsx
import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Layers,
  ShieldAlert,
  ArrowRight,
  BookOpen,
  Printer
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const ProvenanceTag = ({ label }) => (
  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
    PROVENANCE: {label}
  </span>
)

export default function Results() {
  const navigate = useNavigate()
  const [prediction, setPrediction] = useState(null)
  const [plan, setPlan] = useState(null)
  const [cost, setCost] = useState(null)
  const [candidates, setCandidates] = useState([])
  const [evidence, setEvidence] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const stored = localStorage.getItem('riq_prediction')
    if (stored) {
      setPrediction(JSON.parse(stored))
    }
    const storedCost = localStorage.getItem('riq_cost_calculation')
    if (storedCost) {
      setCost(JSON.parse(storedCost))
    }
  }, [])

  const generateActionPlan = async () => {
    if (!prediction) return
    setLoading(true)
    setError('')
    try {
      // 1. Ensure cost calculation exists
      let currentCost = cost
      if (!currentCost) {
        const costRes = await axios.post('/api/replacement/calculate', {
          costParams: {
            numberOfReplacements: 1,
            annualCompensation: prediction.employee_profile?.annual_salary || 1600000,
            recruitmentCost: 100000,
            onboardingCost: 45000,
            trainingCost: 50000,
            vacancyDays: 60,
            rampUpDays: 90,
            productivityDuringRampUp: 0.60,
            departingEmployeeAnnualSalary: prediction.employee_profile?.annual_salary || 1600000,
          },
          calibratedProbability: prediction.prediction.calibrated_probability,
        })
        currentCost = costRes.data
        setCost(currentCost)
      }

      // 2. Fetch candidates
      const candRes = await axios.post('/api/candidates/search', {
        role: prediction.employee_profile?.job_role,
        minExperience: 2,
        skills: ['Python', 'Analysis'],
      })
      const cands = candRes.data.candidates || []
      setCandidates(cands)

      // 3. Fetch academic evidence
      const evidRes = await axios.post('/api/research/search', {
        factors: prediction.model_factors?.map(f => f.feature),
      })
      const evids = evidRes.data.evidence || []
      setEvidence(evids)

      // 4. Request Gemini Action Plan
      const planRes = await axios.post('/api/ai/action-plan', {
        employeeProfile: prediction.employee_profile,
        prediction: prediction.prediction,
        modelFactors: prediction.model_factors,
        costCalculation: currentCost,
        replacementScenarios: [],
        researchEvidence: evids,
        candidateMatches: cands,
      })
      setPlan(planRes.data.action_plan)
    } catch (e) {
      setError(e.response?.data?.error || e.message)
    } finally {
      setLoading(false)
    }
  }

  if (!prediction) {
    return (
      <div className="panel p-12 text-center max-w-lg mx-auto space-y-4 my-12">
        <AlertTriangle size={32} className="mx-auto text-amber-400" />
        <h2 className="text-base font-semibold text-slate-100">No Assessment Profile Found</h2>
        <p className="text-xs text-slate-400">
          Complete an employee risk evaluation before generating the decision support memo.
        </p>
        <button
          onClick={() => navigate('/employee-risk')}
          className="btn-primary text-xs py-2 px-4"
        >
          Go to Risk Assessment
        </button>
      </div>
    )
  }

  const fmt = n => (n != null ? `₹${Math.round(n).toLocaleString('en-IN')}` : '--')

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100">
            Executive Retention & Replacement Briefing Memo
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Unified synthesis of calibrated predictive inference, deterministic costs, and RAG candidate evidence
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!plan && (
            <button
              onClick={generateActionPlan}
              disabled={loading}
              className="btn-primary text-xs py-2 px-3.5"
            >
              {loading ? 'Synthesizing Memo...' : 'Generate Decision Memo'}
            </button>
          )}
          <button
            onClick={() => window.print()}
            className="btn-secondary text-xs py-2 px-3 flex items-center gap-1.5"
          >
            <Printer size={14} /> Print Briefing
          </button>
        </div>
      </div>

      {/* Memo Container */}
      <div className="panel p-6 space-y-6 bg-[#0c1222]">
        {/* Memo Metadata Block */}
        <div className="border-b border-slate-800 pb-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div>
            <div className="text-[10px] text-slate-500 uppercase">Case Evaluation</div>
            <div className="font-semibold text-slate-200 mt-0.5">
              {prediction.employee_profile?.job_role || 'Specialist'}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-slate-500 uppercase">Department</div>
            <div className="font-semibold text-slate-200 mt-0.5">
              {prediction.employee_profile?.department || 'R&D'}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-slate-500 uppercase">Attrition Probability</div>
            <div className="font-semibold text-rose-400 mt-0.5">
              {prediction.prediction?.probability_pct}% (P = {prediction.prediction?.calibrated_probability?.toFixed(3)})
            </div>
          </div>
          <div>
            <div className="text-[10px] text-slate-500 uppercase">Risk Tier</div>
            <div className="mt-0.5">
              <span
                className={
                  prediction.prediction?.risk_category === 'HIGH'
                    ? 'badge-high'
                    : prediction.prediction?.risk_category === 'MODERATE'
                    ? 'badge-mod'
                    : 'badge-low'
                }
              >
                {prediction.prediction?.risk_category}
              </span>
            </div>
          </div>
        </div>

        {/* Section 1: Attrition Risk Analysis */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              1. Probabilistic Attrition Inference
            </h2>
            <ProvenanceTag label="CALIBRATED LOGISTIC REGRESSION" />
          </div>
          <div className="p-3.5 rounded bg-slate-900 border border-slate-800 text-xs text-slate-300 leading-relaxed">
            The employee exhibits a calibrated attrition probability of{' '}
            <strong className="text-slate-100">{prediction.prediction?.probability_pct}%</strong> (
            {prediction.prediction?.risk_category} Risk Category).
            <div className="mt-2 text-[11px] text-slate-400">
              Key model-associated correlates:{' '}
              {(prediction.model_factors || [])
                .slice(0, 4)
                .map(f => `${f.feature} (${f.direction.replace('_', ' ')})`)
                .join(', ')}.
            </div>
          </div>
        </div>

        {/* Section 2: Financial Exposure */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              2. Financial Exposure & Expected Replacement Loss
            </h2>
            <ProvenanceTag label="DETERMINISTIC FORMULATION" />
          </div>
          <div className="p-3.5 rounded bg-slate-900 border border-slate-800 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <div className="text-[11px] text-slate-400">Total Replacement Exposure (1 FTE):</div>
              <div className="text-2xl font-bold font-mono text-rose-400 mt-1">
                {cost?.total_replacement_impact ? fmt(cost.total_replacement_impact) : 'Calculated in Planner'}
              </div>
              <div className="text-[10px] text-slate-500 mt-1">
                Direct recruitment + onboarding + vacancy + ramp-up losses
              </div>
            </div>
            <div>
              <div className="text-[11px] text-slate-400">Expected Replacement Loss (ERL):</div>
              <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
                {cost?.erl?.expected_replacement_loss ? fmt(cost.erl.expected_replacement_loss) : 'P(Exit) × Exposure'}
              </div>
              <div className="text-[10px] text-slate-500 mt-1">
                Mathematical expectation under baseline tenure assumptions
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Recommended Actions (AI or Deterministic Synthesis) */}
        {plan && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                3. Prioritized Human Capital Action Items
              </h2>
              <ProvenanceTag label="GEMINI 2.0 FLASH / DETERMINISTIC SYNTHESIS" />
            </div>

            <div className="space-y-2">
              {(plan.recommended_actions || []).map((act, i) => (
                <div key={i} className="p-3 rounded bg-slate-900 border border-slate-800 text-xs flex items-start gap-3">
                  <span className="w-5 h-5 rounded bg-blue-950 border border-blue-800 text-blue-300 font-mono font-bold flex items-center justify-center flex-shrink-0 text-[11px]">
                    {act.priority || i + 1}
                  </span>
                  <div>
                    <div className="font-semibold text-slate-200">{act.action}</div>
                    <div className="text-slate-400 text-[11px] mt-0.5">{act.rationale}</div>
                  </div>
                  <span className="ml-auto text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    {act.type}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 4: Sourced Candidate Pipeline */}
        {candidates.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                4. Talent Pipeline RAG Sourcing
              </h2>
              <ProvenanceTag label="CANDIDATE KNOWLEDGE BASE" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {candidates.slice(0, 2).map((c) => (
                <div key={c.id} className="p-3 rounded bg-slate-900 border border-slate-800 text-xs">
                  <div className="flex justify-between items-baseline font-semibold text-slate-200">
                    <span>{c.name} ({c.id})</span>
                    <span className="text-emerald-400 font-mono">{Math.round((c.match_score || 0.8) * 100)}% Match</span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    {c.role} · {c.experience_years} yrs exp · Notice: {c.notice_period_days} days
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 5: Academic Research Grounding */}
        {evidence.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                5. Literature Grounding & Evidence
              </h2>
              <ProvenanceTag label="RETRIEVAL AUGMENTED GENERATION (RAG)" />
            </div>
            <div className="space-y-2 text-xs">
              {evidence.slice(0, 2).map((ev, i) => (
                <div key={i} className="p-3 rounded bg-slate-900/60 border border-slate-800 text-slate-300">
                  <span className="font-semibold text-blue-400">{ev.source}:</span> "{ev.passage}"
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Compliance Footer */}
        <div className="pt-4 border-t border-slate-800 text-[11px] text-slate-500 space-y-1">
          <div>
            <strong>Operational Boundaries:</strong> This briefing memo is intended strictly for administrative workforce planning. Statistical correlations must not be interpreted as deterministic personal intent.
          </div>
          <div>
            <strong>Audit Confirmation:</strong> Demographics excluded from predictive inputs. All financial calculations derived from researcher-defined assumptions.
          </div>
        </div>
      </div>
    </div>
  )
}
