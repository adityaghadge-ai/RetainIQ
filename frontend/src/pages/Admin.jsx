// src/pages/Admin.jsx
import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  ShieldCheck,
  LogIn,
  LogOut,
  Upload,
  Activity,
  Cpu,
  Database,
  CheckCircle2,
  AlertTriangle,
  Server,
  Lock
} from 'lucide-react'

export default function Admin() {
  const [token, setToken] = useState(localStorage.getItem('riq_admin_token') || '')
  const [user, setUser] = useState(null)
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [health, setHealth] = useState(null)

  // Candidate creation form
  const [candName, setCandName] = useState('')
  const [candRole, setCandRole] = useState('Software Engineer')
  const [candExp, setCandExp] = useState(4)
  const [candSkills, setCandSkills] = useState('Python, FastAPI, Docker, SQL')
  const [candEdu, setCandEdu] = useState('B.Tech Computer Science')
  const [candSalary, setCandSalary] = useState(1500000)
  const [candNotice, setCandNotice] = useState(30)
  const [candProjects, setCandProjects] = useState('Engineered resilient distributed microservices')
  const [uploadMsg, setUploadMsg] = useState('')
  const [uploadLoading, setUploadLoading] = useState(false)

  useEffect(() => {
    fetchHealth()
    if (token) {
      verifyToken()
    }
  }, [token])

  const fetchHealth = async () => {
    try {
      const res = await axios.get('/api/health')
      setHealth(res.data)
    } catch (err) {
      console.error(err)
    }
  }

  const verifyToken = async () => {
    try {
      const res = await axios.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setUser(res.data.user)
    } catch {
      handleLogout()
    }
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoginError('')
    try {
      const res = await axios.post('/api/auth/login', { username, password })
      if (res.data.success) {
        setToken(res.data.token)
        setUser(res.data.user)
        localStorage.setItem('riq_admin_token', res.data.token)
      }
    } catch (err) {
      setLoginError(err.response?.data?.error || 'Authentication failed. Please verify credentials.')
    }
  }

  const handleLogout = () => {
    setToken('')
    setUser(null)
    localStorage.removeItem('riq_admin_token')
  }

  const handleAddCandidate = async (e) => {
    e.preventDefault()
    setUploadLoading(true)
    setUploadMsg('')
    try {
      const res = await axios.post(
        '/api/candidates/upload',
        {
          name: candName,
          role: candRole,
          experience_years: Number(candExp),
          skills: candSkills.split(',').map(s => s.trim()),
          education: candEdu,
          salary_expectation: Number(candSalary),
          notice_period_days: Number(candNotice),
          projects: candProjects,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      )
      setUploadMsg(`Profile ingested: ${res.data.candidate.name} (${res.data.candidate.id})`)
      setCandName('')
    } catch (err) {
      setUploadMsg(`Error: ${err.response?.data?.error || err.message}`)
    } finally {
      setUploadLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <ShieldCheck size={20} className="text-blue-500" />
            System Administration & Security Console
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Cryptographic access control, talent knowledge base ingestion, and microservice telemetry
          </p>
        </div>
        {user && (
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-slate-400">Authenticated: {user.username}</span>
            <button
              onClick={handleLogout}
              className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
            >
              <LogOut size={13} /> Sign Out
            </button>
          </div>
        )}
      </div>

      {/* Telemetry Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="panel p-4 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="uppercase text-[10px] font-semibold">Orchestrator Backend</span>
            <Server size={14} className="text-emerald-400" />
          </div>
          <div className="text-base font-bold font-mono text-slate-100">Port 8000: Online</div>
          <div className="text-[11px] text-slate-400">Node.js Express / JWT Middleware</div>
        </div>

        <div className="panel p-4 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="uppercase text-[10px] font-semibold">ML Microservice</span>
            <Cpu size={14} className="text-blue-400" />
          </div>
          <div className="text-base font-bold font-mono text-slate-100">
            {health?.ml_service === 'ok' ? 'Port 8001: Calibrated' : 'Standby'}
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            {health?.ml_metadata ? `${health.ml_metadata.model_name} (PR-AUC: ${health.ml_metadata.pr_auc})` : 'FastAPI / CalibratedClassifierCV'}
          </div>
        </div>

        <div className="panel p-4 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="uppercase text-[10px] font-semibold">AI Synthesis Layer</span>
            <Database size={14} className="text-purple-400" />
          </div>
          <div className="text-base font-bold font-mono text-slate-100">
            {health?.gemini_configured ? 'Gemini 2.0 Flash' : 'Deterministic Fallback'}
          </div>
          <div className="text-[11px] text-slate-400 font-mono">{health?.gemini_model || 'gemini-2.0-flash'}</div>
        </div>
      </div>

      {!user ? (
        /* Sign In Panel */
        <div className="panel p-8 max-w-md mx-auto space-y-4 my-8">
          <div className="text-center space-y-1">
            <div className="w-10 h-10 rounded bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-blue-400">
              <Lock size={18} />
            </div>
            <h2 className="text-sm font-semibold text-slate-100">Administrator Access Required</h2>
            <p className="text-xs text-slate-400">Enter administrative credentials to ingest talent profiles into the RAG vector base</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-3 pt-2">
            <div>
              <label>Administrator Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
              />
            </div>
            <div>
              <label>Security Password</label>
              <input
                type="password"
                value={password}
                placeholder="Enter password (e.g. RetainIQ@2026)"
                onChange={e => setPassword(e.target.value)}
                required
              />
            </div>

            {loginError && (
              <div className="text-xs p-2 rounded bg-rose-950/60 border border-rose-800 text-rose-300 flex items-center gap-2">
                <AlertTriangle size={13} /> {loginError}
              </div>
            )}

            <button
              type="submit"
              className="w-full btn-primary text-xs py-2.5 font-medium flex items-center justify-center gap-1.5"
            >
              <LogIn size={14} /> Authenticate Admin Session
            </button>

            <div className="text-[11px] text-slate-500 text-center font-mono pt-2">
              Default Capstone Credentials: <code>admin</code> / <code>RetainIQ@2026</code>
            </div>
          </form>
        </div>
      ) : (
        /* Authenticated Ingestion Console */
        <div className="panel p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Upload size={16} className="text-blue-400" />
              <h2 className="text-sm font-semibold text-slate-100">
                Candidate Profile Ingestion into Knowledge Base
              </h2>
            </div>
            <span className="text-[10px] font-mono text-emerald-400">JWT AUTHENTICATED</span>
          </div>
          <p className="text-xs text-slate-400">
            Ingest structured candidate profiles directly into the persistent candidate knowledge base. Profiles become immediately available to RAG similarity searches.
          </p>

          <form onSubmit={handleAddCandidate} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label>Candidate Full Name</label>
              <input
                type="text"
                value={candName}
                onChange={e => setCandName(e.target.value)}
                placeholder="e.g. Diya Sengupta"
                required
              />
            </div>
            <div>
              <label>Specialization / Target Role</label>
              <input
                type="text"
                value={candRole}
                onChange={e => setCandRole(e.target.value)}
                placeholder="e.g. Research Scientist"
                required
              />
            </div>
            <div>
              <label>Relevant Experience (Years)</label>
              <input
                type="number"
                min={0}
                max={40}
                value={candExp}
                onChange={e => setCandExp(e.target.value)}
                required
              />
            </div>
            <div>
              <label>Salary Expectation (₹/year)</label>
              <input
                type="number"
                step={50000}
                value={candSalary}
                onChange={e => setCandSalary(e.target.value)}
                required
              />
            </div>
            <div className="sm:col-span-2">
              <label>Technical Skills (comma-separated)</label>
              <input
                type="text"
                value={candSkills}
                onChange={e => setCandSkills(e.target.value)}
                placeholder="Python, Scikit-Learn, PyTorch, SQL, Statistics"
                required
              />
            </div>
            <div>
              <label>Education Degree</label>
              <input
                type="text"
                value={candEdu}
                onChange={e => setCandEdu(e.target.value)}
              />
            </div>
            <div>
              <label>Notice Period (Days)</label>
              <input
                type="number"
                value={candNotice}
                min={0}
                max={180}
                onChange={e => setCandNotice(e.target.value)}
              />
            </div>
            <div className="sm:col-span-2">
              <label>Key Project Experience</label>
              <textarea
                value={candProjects}
                rows={2}
                onChange={e => setCandProjects(e.target.value)}
              />
            </div>

            <div className="sm:col-span-2 flex items-center justify-between pt-2">
              <button
                type="submit"
                disabled={uploadLoading}
                className="btn-primary text-xs py-2 px-4 flex items-center gap-1.5"
              >
                <Upload size={14} /> {uploadLoading ? 'Ingesting...' : 'Ingest Profile into KB'}
              </button>
              {uploadMsg && (
                <span
                  className={`text-xs font-mono ${
                    uploadMsg.startsWith('Profile ingested') ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {uploadMsg}
                </span>
              )}
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
