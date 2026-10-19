// src/pages/Auth.jsx
// ====================
// Minimal Dark Authentication Gateway

import { useState } from 'react'
import axios from 'axios'
import {
  Lock,
  Mail,
  User,
  Building,
  ShieldCheck,
  ArrowRight,
  AlertCircle
} from 'lucide-react'

export default function Auth({ onAuthSuccess }) {
  const [isSignup, setIsSignup] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [organization, setOrganization] = useState('Global Enterprise Corp')
  const [role, setRole] = useState('HR_DIRECTOR')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e?.preventDefault()
    setError('')
    setLoading(true)

    const endpoint = isSignup ? '/api/auth/register' : '/api/auth/login'
    const payload = isSignup
      ? { email, password, name, organization, role }
      : { email, password }

    try {
      const res = await axios.post(endpoint, payload)
      if (res.data.success) {
        localStorage.setItem('riq_admin_token', res.data.token)
        localStorage.setItem('riq_auth_user', JSON.stringify(res.data.user))
        onAuthSuccess(res.data.user)
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Authentication failed. Please verify credentials.')
    } finally {
      setLoading(false)
    }
  }

  const handleDemoLogin = async () => {
    setError('')
    setLoading(true)
    try {
      const res = await axios.post('/api/auth/login', {
        email: 'hr@enterprise.com',
        password: 'RetainIQ@2026',
      })
      if (res.data.success) {
        localStorage.setItem('riq_admin_token', res.data.token)
        localStorage.setItem('riq_auth_user', JSON.stringify(res.data.user))
        onAuthSuccess(res.data.user)
      }
    } catch (err) {
      setError('Demo login failed: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 flex flex-col justify-center items-center p-4">
      {/* Platform Branding */}
      <div className="mb-6 text-center space-y-1">
        <div className="inline-flex items-center justify-center w-8 h-8 rounded bg-blue-600 text-white font-bold text-sm mb-1">
          R
        </div>
        <h1 className="text-xl font-bold tracking-tight text-zinc-100">
          RetainIQ
        </h1>
        <p className="text-xs text-zinc-400">
          Employee Attrition & Replacement Intelligence
        </p>
      </div>

      {/* Main Authentication Card */}
      <div className="w-full max-w-sm panel p-6 space-y-4 bg-[#121215] border border-zinc-800">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100">
            {isSignup ? 'Create Account' : 'Sign In'}
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            {isSignup ? 'Set up credentials to access decision models' : 'Enter your credentials to access the platform'}
          </p>
        </div>

        {/* 1-Click Demo Login */}
        <button
          type="button"
          onClick={handleDemoLogin}
          disabled={loading}
          className="w-full py-2 px-3 rounded border border-blue-900/60 bg-blue-950/30 hover:bg-blue-900/40 text-blue-400 text-xs font-medium flex items-center justify-center gap-2 transition"
        >
          <ShieldCheck size={14} />
          <span>Quick 1-Click HR Login (Demo)</span>
        </button>

        <div className="relative flex py-1 items-center">
          <div className="flex-grow border-t border-zinc-800"></div>
          <span className="flex-shrink mx-2 text-[11px] text-zinc-500">or sign in with email</span>
          <div className="flex-grow border-t border-zinc-800"></div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {isSignup && (
            <>
              <div>
                <label>Full Name</label>
                <div className="relative">
                  <User size={14} className="absolute left-2.5 top-2.5 text-zinc-500" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="HR Administrator"
                    className="pl-8"
                  />
                </div>
              </div>

              <div>
                <label>Organization</label>
                <div className="relative">
                  <Building size={14} className="absolute left-2.5 top-2.5 text-zinc-500" />
                  <input
                    type="text"
                    required
                    value={organization}
                    onChange={e => setOrganization(e.target.value)}
                    placeholder="Company name"
                    className="pl-8"
                  />
                </div>
              </div>
            </>
          )}

          <div>
            <label>Work Email</label>
            <div className="relative">
              <Mail size={14} className="absolute left-2.5 top-2.5 text-zinc-500" />
              <input
                type="text"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="pl-8"
              />
            </div>
          </div>

          <div>
            <label>Password</label>
            <div className="relative">
              <Lock size={14} className="absolute left-2.5 top-2.5 text-zinc-500" />
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="pl-8"
              />
            </div>
          </div>

          {error && (
            <div className="p-2.5 rounded bg-red-950/40 border border-red-800 text-red-300 text-xs flex items-center gap-2">
              <AlertCircle size={14} className="flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full btn-primary text-xs py-2 font-medium flex items-center justify-center gap-1.5"
          >
            <span>{loading ? 'Authenticating...' : isSignup ? 'Create Account' : 'Sign In'}</span>
            <ArrowRight size={13} />
          </button>
        </form>

        <div className="pt-2 border-t border-zinc-800 flex items-center justify-between text-xs text-zinc-400">
          <span>{isSignup ? 'Have an account?' : 'Need an account?'}</span>
          <button
            type="button"
            onClick={() => {
              setIsSignup(!isSignup)
              setError('')
            }}
            className="text-blue-400 hover:text-blue-300 font-medium"
          >
            {isSignup ? 'Sign In' : 'Register'}
          </button>
        </div>
      </div>
    </div>
  )
}
