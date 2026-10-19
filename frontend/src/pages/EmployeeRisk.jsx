// src/pages/EmployeeRisk.jsx
// ==========================
// Employee Separation & Replacement Impact Console for HR Managers.
// Select any actual employee from the roster or enter custom parameters.
// Computes:
// 1. Total Financial Loss to Company
// 2. Chances of Finding a Replacement (Market Availability Score)
// 3. Replacement Multiplier (Do we need 1, 2, or 3 FTEs to match their productivity?)
// 4. Calibrated Attrition Probability from ML Model
// 5. Pre-matched Replacement Candidates from Talent Pool

import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  Users,
  Search,
  Filter,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  TrendingDown,
  Layers,
  ArrowRight,
  Briefcase,
  Clock,
  ShieldAlert,
  ChevronRight,
  UserX,
  FileCheck
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function EmployeeRisk() {
  const navigate = useNavigate()
  const [employees, setEmployees] = useState([])
  const [selectedEmp, setSelectedEmp] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedDept, setSelectedDept] = useState('')
  const [selectedRole, setSelectedRole] = useState('')
  const [loadingList, setLoadingList] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [activeMode, setActiveMode] = useState('roster') // 'roster' | 'custom'

  // Custom manual entry fields
  const [customId, setCustomId] = useState('EMP-TARGET-01')
  const [customRole, setCustomRole] = useState('Research Scientist')
  const [customDept, setCustomDept] = useState('Research & Development')
  const [customLevel, setCustomLevel] = useState(3)
  const [customSalary, setCustomSalary] = useState(1500000)
  const [customTenure, setCustomTenure] = useState(6)
  const [customExp, setCustomExp] = useState(8)
  const [customOvertime, setCustomOvertime] = useState('No')
  const [customSatisfaction, setCustomSatisfaction] = useState(3)

  useEffect(() => {
    fetchRoster()
  }, [selectedDept, selectedRole])

  const fetchRoster = async () => {
    setLoadingList(true)
    try {
      const res = await axios.get('/api/employees', {
        params: {
          query: searchQuery,
          department: selectedDept,
          role: selectedRole,
          limit: 30,
        },
      })
      const list = res.data.employees || []
      setEmployees(list)
      if (list.length > 0 && !selectedEmp && activeMode === 'roster') {
        setSelectedEmp(list[0])
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoadingList(false)
    }
  }

  const handleSelectEmployee = (emp) => {
    setSelectedEmp(emp)
    setAnalysisResult(null)
  }

  const handleRunAnalysis = async () => {
    setAnalyzing(true)
    try {
      let res
      if (activeMode === 'roster') {
        if (!selectedEmp) return
        res = await axios.post(`/api/employees/${selectedEmp.id}/separation-analysis`, {})
      } else {
        const monthly = Math.round(customSalary / 12)
        res = await axios.post('/api/employees/custom-analysis', {
          id: customId || 'EMP-MANUAL-01',
          code: customId || 'EMP-MANUAL-01',
          JobRole: customRole,
          Department: customDept,
          JobLevel: Number(customLevel),
          MonthlyIncome: monthly,
          TotalWorkingYears: Number(customExp),
          YearsAtCompany: Number(customTenure),
          YearsInCurrentRole: Math.max(1, Math.round(customTenure / 2)),
          OverTime: customOvertime,
          JobSatisfaction: Number(customSatisfaction),
          EnvironmentSatisfaction: 3,
          WorkLifeBalance: 3,
          PerformanceRating: 3,
          BusinessTravel: 'Travel_Rarely',
          DailyRate: 800,
          HourlyRate: 65,
          MonthlyRate: 14000,
          NumCompaniesWorked: 2,
          PercentSalaryHike: 14,
          RelationshipSatisfaction: 3,
          StockOptionLevel: 1,
          TrainingTimesLastYear: 3,
          YearsSinceLastPromotion: 1,
          YearsWithCurrManager: Math.max(1, Math.round(customTenure / 2)),
          DistanceFromHome: 8,
          Education: 3,
          EducationField: 'Life Sciences',
        })
      }

      setAnalysisResult(res.data)
      localStorage.setItem('riq_last_analysis', JSON.stringify(res.data))
      // Save prediction for downstream modules
      localStorage.setItem(
        'riq_prediction',
        JSON.stringify({
          employee_profile: {
            job_role: res.data.employee.role,
            department: res.data.employee.department,
            annual_salary: res.data.employee.annualSalary,
          },
          prediction: res.data.departure_risk,
          model_factors: res.data.departure_risk?.model_factors || [],
        })
      )
    } catch (err) {
      console.error('Analysis failed:', err)
    } finally {
      setAnalyzing(false)
    }
  }

  const fmt = (n) => (n != null ? `₹${Math.round(n).toLocaleString('en-IN')}` : '--')

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <UserX size={20} className="text-rose-400" />
            Employee Separation & Replacement Impact Console
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Evaluate the financial loss to the company, replacement multiplier, and talent market availability when an employee departs
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="flex items-center gap-1.5 p-1 rounded-md bg-slate-900 border border-slate-800 text-xs">
          <button
            type="button"
            onClick={() => {
              setActiveMode('roster')
              setAnalysisResult(null)
            }}
            className={`px-3 py-1 rounded font-medium transition ${
              activeMode === 'roster' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Select from Company Roster
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveMode('custom')
              setAnalysisResult(null)
            }}
            className={`px-3 py-1 rounded font-medium transition ${
              activeMode === 'custom' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Custom / Manual Entry
          </button>
        </div>
      </div>

      {/* Mode A: Company Roster Browser */}
      {activeMode === 'roster' && (
        <div className="space-y-4">
          <div className="panel p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Search size={14} className="text-blue-400" /> Select Employee for Replacement Analysis
              </span>
              <span className="text-[11px] font-mono text-slate-400">1,470 Company Records</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label>Search by ID or Designation</label>
                <input
                  type="text"
                  placeholder="e.g. EMP-0010 or Research..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && fetchRoster()}
                />
              </div>
              <div>
                <label>Department Filter</label>
                <select
                  value={selectedDept}
                  onChange={e => setSelectedDept(e.target.value)}
                >
                  <option value="">All Departments</option>
                  <option value="Research & Development">Research & Development</option>
                  <option value="Sales">Sales</option>
                  <option value="Human Resources">Human Resources</option>
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  onClick={fetchRoster}
                  disabled={loadingList}
                  className="w-full btn-secondary text-xs py-2 h-[35px]"
                >
                  {loadingList ? 'Refreshing Roster...' : 'Apply Filters'}
                </button>
              </div>
            </div>

            {/* Employee Quick Selector Table */}
            <div className="overflow-x-auto max-h-56 overflow-y-auto border border-slate-800/80 rounded bg-slate-950/60 mt-2">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-900 border-b border-slate-800 text-left">
                  <tr>
                    <th className="py-2 px-3 text-slate-400 font-semibold">Select</th>
                    <th className="py-2 px-3 text-slate-400 font-semibold">Employee ID</th>
                    <th className="py-2 px-3 text-slate-400 font-semibold">Role & Job Level</th>
                    <th className="py-2 px-3 text-slate-400 font-semibold">Department</th>
                    <th className="py-2 px-3 text-slate-400 font-semibold text-right">Annual Salary</th>
                    <th className="py-2 px-3 text-slate-400 font-semibold text-right">Tenure</th>
                    <th className="py-2 px-3 text-slate-400 font-semibold text-right">Performance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 font-mono">
                  {employees.map(emp => {
                    const isSelected = selectedEmp?.id === emp.id
                    return (
                      <tr
                        key={emp.id}
                        onClick={() => handleSelectEmployee(emp)}
                        className={`cursor-pointer transition-colors ${
                          isSelected ? 'bg-blue-950/50 text-blue-200' : 'hover:bg-slate-800/40 text-slate-300'
                        }`}
                      >
                        <td className="py-2 px-3">
                          <input
                            type="radio"
                            name="selectedEmployee"
                            checked={isSelected}
                            onChange={() => handleSelectEmployee(emp)}
                            className="cursor-pointer accent-blue-500 w-3.5 h-3.5"
                          />
                        </td>
                        <td className="py-2 px-3 font-semibold text-slate-100">{emp.id}</td>
                        <td className="py-2 px-3 font-sans text-slate-200">
                          {emp.role} <span className="text-[10px] text-slate-500">(Level {emp.jobLevel})</span>
                        </td>
                        <td className="py-2 px-3 font-sans text-slate-400">{emp.department}</td>
                        <td className="py-2 px-3 text-right text-slate-200">{fmt(emp.annualSalary)}</td>
                        <td className="py-2 px-3 text-right text-slate-400">{emp.yearsAtCompany} yrs</td>
                        <td className="py-2 px-3 text-right text-emerald-400">{emp.performanceRating}/4</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {selectedEmp && (
              <div className="p-3 rounded bg-blue-950/20 border border-blue-900/40 flex items-center justify-between flex-wrap gap-3">
                <div className="text-xs">
                  <span className="font-semibold text-slate-200">Selected Profile:</span>{' '}
                  <span className="text-blue-300 font-medium">
                    {selectedEmp.id} · {selectedEmp.role} (Level {selectedEmp.jobLevel}, {selectedEmp.department})
                  </span>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Salary: {fmt(selectedEmp.annualSalary)} · Company Tenure: {selectedEmp.yearsAtCompany} years · OverTime: {selectedEmp.overtime}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleRunAnalysis}
                  disabled={analyzing}
                  className="btn-primary text-xs py-2 px-4 flex items-center gap-1.5"
                >
                  {analyzing ? 'Computing Company Loss & Feasibility...' : 'Analyze Impact of Separation'}
                  <ArrowRight size={14} />
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Mode B: Manual Parameter Input */}
      {activeMode === 'custom' && (
        <div className="panel p-5 space-y-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-300 border-b border-slate-800 pb-2">
            Manual Employee Specifications for Separation Modeling
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label>Employee Identifier / Code</label>
              <input
                type="text"
                value={customId}
                onChange={e => setCustomId(e.target.value)}
                placeholder="e.g. EMP-1042 or EMP-TARGET-01"
              />
            </div>
            <div>
              <label>Job Role</label>
              <select value={customRole} onChange={e => setCustomRole(e.target.value)}>
                <option value="Research Scientist">Research Scientist</option>
                <option value="Software Engineer">Software Engineer</option>
                <option value="Sales Executive">Sales Executive</option>
                <option value="Laboratory Technician">Laboratory Technician</option>
                <option value="Healthcare Representative">Healthcare Representative</option>
                <option value="Manufacturing Director">Manufacturing Director</option>
                <option value="Human Resources">Human Resources</option>
              </select>
            </div>
            <div>
              <label>Department</label>
              <select value={customDept} onChange={e => setCustomDept(e.target.value)}>
                <option value="Research & Development">Research & Development</option>
                <option value="Sales">Sales</option>
                <option value="Human Resources">Human Resources</option>
              </select>
            </div>
            <div>
              <label>Seniority Level (Grade 1–5)</label>
              <input
                type="number"
                min={1}
                max={5}
                value={customLevel}
                onChange={e => setCustomLevel(e.target.value)}
              />
            </div>
            <div>
              <label>Annual Compensation (₹)</label>
              <input
                type="number"
                step={50000}
                value={customSalary}
                onChange={e => setCustomSalary(e.target.value)}
              />
            </div>
            <div>
              <label>Company Tenure (Years)</label>
              <input
                type="number"
                min={0}
                max={30}
                value={customTenure}
                onChange={e => setCustomTenure(e.target.value)}
              />
            </div>
            <div>
              <label>Total Experience (Years)</label>
              <input
                type="number"
                min={0}
                max={40}
                value={customExp}
                onChange={e => setCustomExp(e.target.value)}
              />
            </div>
            <div>
              <label>Works Overtime</label>
              <select value={customOvertime} onChange={e => setCustomOvertime(e.target.value)}>
                <option value="No">No</option>
                <option value="Yes">Yes</option>
              </select>
            </div>
            <div>
              <label>Job Satisfaction (1–4)</label>
              <input
                type="number"
                min={1}
                max={4}
                value={customSatisfaction}
                onChange={e => setCustomSatisfaction(e.target.value)}
              />
            </div>
            <div className="flex items-end">
              <button
                type="button"
                onClick={handleRunAnalysis}
                disabled={analyzing}
                className="w-full btn-primary text-xs py-2 h-[35px]"
              >
                {analyzing ? 'Computing Loss & Multipliers...' : 'Analyze Separation Impact'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SEPARATION & REPLACEMENT IMPACT RESULTS (The Core HR Decision Dashboard) */}
      {/* ========================================================================= */}
      {analysisResult && (
        <div className="space-y-6 animate-fadeIn">
          {/* Executive KPI Summary */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total Company Loss */}
            <div className="panel p-4 border-rose-900/60 bg-rose-950/20">
              <div className="flex items-center justify-between text-xs text-rose-300 mb-1">
                <span className="font-semibold uppercase tracking-wider text-[10px]">Total Loss to Company</span>
                <DollarSign size={14} className="text-rose-400" />
              </div>
              <div className="text-2xl font-bold font-mono text-rose-400">
                {fmt(analysisResult.financial_impact?.total_replacement_exposure)}
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                Vacancy loss + ramp-up delay + recruitment
              </div>
            </div>

            {/* Chances of Getting New Employee */}
            <div className="panel p-4 border-sky-900/60 bg-sky-950/20">
              <div className="flex items-center justify-between text-xs text-sky-300 mb-1">
                <span className="font-semibold uppercase tracking-wider text-[10px]">Chances of Replacement</span>
                <Briefcase size={14} className="text-sky-400" />
              </div>
              <div className="text-2xl font-bold font-mono text-sky-400">
                {analysisResult.replacement_feasibility?.market_availability_pct}% Chance
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                {analysisResult.replacement_feasibility?.market_liquidity_tier} · ~{analysisResult.replacement_feasibility?.estimated_vacancy_days}d hire lead time
              </div>
            </div>

            {/* Replacement Multiplier */}
            <div className="panel p-4 border-amber-900/60 bg-amber-950/20">
              <div className="flex items-center justify-between text-xs text-amber-300 mb-1">
                <span className="font-semibold uppercase tracking-wider text-[10px]">Replacement Multiplier</span>
                <Users size={14} className="text-amber-400" />
              </div>
              <div className="text-2xl font-bold font-mono text-amber-400">
                {analysisResult.replacement_feasibility?.replacement_multiplier}× FTEs Needed
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                {analysisResult.replacement_feasibility?.replacement_multiplier > 1
                  ? 'Requires 2 personnel to match experience output'
                  : 'Standard 1:1 replacement feasible'}
              </div>
            </div>

            {/* Attrition Risk */}
            <div className="panel p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span className="font-semibold uppercase tracking-wider text-[10px]">Flight / Attrition Risk</span>
                <span
                  className={
                    analysisResult.departure_risk?.risk_category === 'HIGH'
                      ? 'badge-high'
                      : analysisResult.departure_risk?.risk_category === 'MODERATE'
                      ? 'badge-mod'
                      : 'badge-low'
                  }
                >
                  {analysisResult.departure_risk?.risk_category}
                </span>
              </div>
              <div className="text-2xl font-bold font-mono text-slate-100">
                {analysisResult.departure_risk?.probability_pct}%
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                Calibrated departure probability
              </div>
            </div>
          </div>

          {/* Deep-Dive Grid: Financial Itemization & Replacement Feasibility */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Financial Loss Breakdown */}
            <div className="panel p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-slate-100">
                  Itemized Financial Loss if Separated
                </h3>
                <span className="text-[10px] font-mono text-slate-400">DETERMINISTIC FORMULAS</span>
              </div>

              <div className="space-y-2 text-xs">
                {Object.entries(analysisResult.financial_impact?.breakdown || {}).map(([k, v]) => (
                  <div key={k} className="flex justify-between py-1.5 border-b border-slate-800/50">
                    <span className="text-slate-300 capitalize">{k.replace(/_/g, ' ')}</span>
                    <span className="font-mono font-medium text-slate-100">{fmt(v)}</span>
                  </div>
                ))}
                <div className="flex justify-between py-1.5 border-b border-slate-800/50">
                  <span className="text-slate-300">Knowledge Capital Loss (Institutional Memory)</span>
                  <span className="font-mono font-medium text-amber-400">
                    {fmt(analysisResult.financial_impact?.knowledge_capital_loss_estimate)}
                  </span>
                </div>
                <div className="flex justify-between pt-2 text-sm font-bold text-rose-400">
                  <span>Total Financial Impact to Company</span>
                  <span className="font-mono">{fmt(analysisResult.financial_impact?.total_replacement_exposure)}</span>
                </div>
                <div className="flex justify-between text-xs text-amber-300 font-mono">
                  <span>Expected Replacement Loss (P × Loss)</span>
                  <span>{fmt(analysisResult.financial_impact?.expected_replacement_loss)}</span>
                </div>
              </div>

              <div className="text-[10px] text-slate-500 pt-1">
                Reference Benchmark: {analysisResult.financial_impact?.market_benchmark_reference}
              </div>
            </div>

            {/* Replacement Feasibility & Ramp-up Deficit */}
            <div className="panel p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-slate-100">
                  Can We Replace Them? Talent Market Feasibility
                </h3>
                <span className="text-[10px] font-mono text-sky-400">AVAILABILITY METRIC</span>
              </div>

              <div className="p-3.5 rounded bg-slate-900 border border-slate-800 space-y-2 text-xs">
                <div className="font-semibold text-slate-200">
                  Replacement Multiplier: {analysisResult.replacement_feasibility?.replacement_multiplier} FTEs
                </div>
                <p className="text-slate-400 leading-relaxed">
                  {analysisResult.replacement_feasibility?.multiplier_explanation}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded bg-slate-900 border border-slate-800">
                  <div className="text-[10px] uppercase font-semibold text-slate-400">Chances of Sourcing Replacement</div>
                  <div className="text-lg font-bold font-mono text-sky-400 mt-1">
                    {analysisResult.replacement_feasibility?.market_availability_pct}%
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    {analysisResult.replacement_feasibility?.market_liquidity_tier}
                  </div>
                </div>

                <div className="p-3 rounded bg-slate-900 border border-slate-800">
                  <div className="text-[10px] uppercase font-semibold text-slate-400">Vacancy Delay</div>
                  <div className="text-lg font-bold font-mono text-slate-200 mt-1">
                    ~{analysisResult.replacement_feasibility?.estimated_vacancy_days} Days
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Time to hire in current market</div>
                </div>

                <div className="p-3 rounded bg-slate-900 border border-slate-800">
                  <div className="text-[10px] uppercase font-semibold text-slate-400">Ramp-Up Duration</div>
                  <div className="text-lg font-bold font-mono text-slate-200 mt-1">
                    {analysisResult.replacement_feasibility?.estimated_rampup_days} Days
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Time to full productive output</div>
                </div>

                <div className="p-3 rounded bg-slate-900 border border-slate-800">
                  <div className="text-[10px] uppercase font-semibold text-slate-400">Ramp-Up Productivity</div>
                  <div className="text-lg font-bold font-mono text-emerald-400 mt-1">
                    {analysisResult.replacement_feasibility?.productivity_during_rampup_pct}%
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Initial onboarding efficiency</div>
                </div>
              </div>
            </div>
          </div>

          {/* Replacement Candidates Sourced from Talent Pool */}
          <div className="panel p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Users size={16} className="text-blue-400" />
                <h3 className="text-sm font-semibold text-slate-100">
                  Pre-Matched Candidates in Talent Pool for this Role
                </h3>
              </div>
              <button
                type="button"
                onClick={() => navigate('/candidates')}
                className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1"
              >
                Browse Full Talent Database <ChevronRight size={12} />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {(analysisResult.candidate_matches || []).map((cand) => (
                <div key={cand.id} className="p-3.5 rounded bg-slate-900 border border-slate-800 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-200">{cand.name}</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/80 text-emerald-400 font-bold">
                      {Math.round(cand.match_score * 100)}% Match
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    {cand.role} · {cand.experience_years} yrs exp · Notice: {cand.notice_period_days}d
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono">
                    Expected: ₹{(cand.salary_expectation / 100000).toFixed(1)}L/yr
                  </div>
                  <div className="flex gap-1 flex-wrap pt-1">
                    {(cand.skills || []).slice(0, 3).map((s) => (
                      <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Strategic HR Decision Verdict & Next Steps */}
          <div className="panel p-5 space-y-3 bg-[#0d1628] border-blue-900/60">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-400">
              <FileCheck size={16} /> HR Strategic Action Summary
            </div>
            <div className="text-sm font-semibold text-slate-100">
              {analysisResult.strategic_recommendation?.verdict}
            </div>
            <ul className="space-y-1.5 text-xs text-slate-300 pt-1">
              {(analysisResult.strategic_recommendation?.key_actions || []).map((act, i) => (
                <li key={i} className="flex items-start gap-2">
                  <CheckCircle2 size={13} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span>{act}</span>
                </li>
              ))}
            </ul>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <span className="text-xs text-slate-400">
                Proceed to formal scenario simulation or action plan memo:
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => navigate('/replacement')}
                  className="btn-secondary text-xs py-1.5 px-3"
                >
                  Scenario Calculator
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/results')}
                  className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5"
                >
                  Generate Decision Memo <ArrowRight size={13} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
