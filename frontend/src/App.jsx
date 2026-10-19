// src/App.jsx
// ===========
// RetainIQ Application Shell — B2B HR Intelligence Platform

import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  UserCheck,
  Calculator,
  FileCheck,
  FileText,
  Menu,
  X,
  ChevronRight,
  AlertTriangle,
  RotateCcw,
  LogOut,
  Network
} from 'lucide-react'
import React, { useState } from 'react'

import Auth from './pages/Auth'
import Dashboard from './pages/Dashboard'
import AnalyzeEmployee from './pages/AnalyzeEmployee'
import ReplacementPlanner from './pages/ReplacementPlanner'
import Reports from './pages/Reports'
import Research from './pages/Research'
import OrgRiskMap from './pages/OrgRiskMap'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error, info) {
    console.error('[RetainIQ Error Boundary]', error, info)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="panel p-6 text-center max-w-md mx-auto my-16 space-y-3">
          <div className="w-10 h-10 rounded-full bg-red-950/40 border border-red-800 text-red-400 flex items-center justify-center mx-auto">
            <AlertTriangle size={18} />
          </div>
          <h2 className="text-base font-semibold text-slate-100">Component Warning</h2>
          <p className="text-xs text-slate-400 font-mono">
            {this.state.error?.message || 'A UI component encountered an unexpected error.'}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false })
              window.location.reload()
            }}
            className="btn-primary text-xs py-1.5 px-3 mx-auto"
          >
            <RotateCcw size={14} /> Reload View
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

// Primary Navigation
const PRIMARY_NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/analyze',   icon: UserCheck,       label: 'Analyze Employee' },
  { to: '/org-risk',  icon: Network,         label: 'Org Risk Heatmap', badge: 'NEW' },
  { to: '/planner',   icon: Calculator,      label: 'Replacement Planner' },
  { to: '/reports',   icon: FileCheck,       label: 'Reports' },
]

const SECONDARY_NAV = [
  { to: '/research',  icon: FileText,        label: 'Research & Validation' },
]

function HeaderBar({ sidebarOpen, setSidebarOpen, onLogout }) {
  const location = useLocation()
  const allItems = [...PRIMARY_NAV, ...SECONDARY_NAV]
  const currentNav = allItems.find(n => n.to === location.pathname) || { label: 'Overview' }

  return (
    <header className="h-14 border-b border-[#1A263C] bg-[#0A101D] px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-[#152033] transition"
          aria-label="Toggle navigation menu"
        >
          {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
        </button>

        <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
          <span>RetainIQ</span>
          <ChevronRight size={13} className="text-slate-600" />
          <span className="text-slate-100 font-semibold">{currentNav.label}</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* System Ready Badge */}
        <div className="bg-[#0D1526] border border-[#1A2742] px-3 py-1.5 rounded-full flex items-center gap-2 text-xs text-slate-200 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-[#00D26A] shadow-[0_0_8px_#00D26A]" />
          <span className="font-medium text-[11px] text-slate-200">System Ready</span>
        </div>

        {/* Sign Out Button */}
        <button
          onClick={onLogout}
          title="Sign Out"
          className="px-3 py-1.5 text-xs font-medium rounded-lg border border-[#1A263C] bg-[#0D1526] text-slate-300 hover:text-slate-100 hover:bg-[#152033] transition flex items-center gap-1.5 shadow-sm"
        >
          <LogOut size={13} className="text-slate-400" />
          <span>Sign Out</span>
        </button>
      </div>
    </header>
  )
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [authUser, setAuthUser] = useState(() => {
    const token = localStorage.getItem('riq_admin_token')
    const userStr = localStorage.getItem('riq_auth_user')
    try {
      return token && userStr ? JSON.parse(userStr) : null
    } catch {
      return null
    }
  })

  const handleLogout = () => {
    localStorage.removeItem('riq_admin_token')
    localStorage.removeItem('riq_auth_user')
    sessionStorage.clear()
    setAuthUser(null)
  }

  if (!authUser) {
    return <Auth onAuthSuccess={(user) => setAuthUser(user)} />
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen flex bg-[#0A101D] text-slate-100 font-sans">
        {/* Sidebar */}
        <aside
          className={`${
            sidebarOpen ? 'w-60' : 'w-16'
          } flex-shrink-0 transition-all duration-150 border-r border-[#1A263C] bg-[#0A101D] flex flex-col fixed top-0 left-0 h-screen z-50`}
        >
          {/* Brand header */}
          <div className="h-16 px-4 border-b border-[#1A263C] flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#00D26A] text-slate-950 font-extrabold text-sm flex items-center justify-center shadow-[0_0_12px_rgba(0,210,106,0.3)]">
              R
            </div>
            {sidebarOpen && (
              <div className="flex flex-col">
                <span className="font-bold text-base tracking-tight text-white leading-tight">RetainIQ</span>
                <span className="text-[11px] font-medium text-[#00D26A]">Platform v2.4</span>
              </div>
            )}
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 py-4 px-3 space-y-1.5 overflow-y-auto">
            {PRIMARY_NAV.map(({ to, icon: Icon, label, badge }) => (
              <NavLink
                key={to}
                to={to}
                title={!sidebarOpen ? label : undefined}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-[#00D26A] text-slate-950 font-bold shadow-[0_0_16px_rgba(0,210,106,0.25)]'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#131C2E]'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon size={18} className={`flex-shrink-0 ${isActive ? 'text-slate-950' : 'text-slate-400'}`} />
                    {sidebarOpen && <span className="truncate flex-1">{label}</span>}
                    {sidebarOpen && badge && (
                      <span style={{
                        fontSize: '9px', fontWeight: 800, padding: '2px 5px', borderRadius: '4px',
                        background: isActive ? 'rgba(0,0,0,0.2)' : 'rgba(239,68,68,0.2)',
                        color: isActive ? '#06130C' : '#f87171',
                        border: `1px solid ${isActive ? 'rgba(0,0,0,0.15)' : 'rgba(239,68,68,0.35)'}`,
                        letterSpacing: '0.04em',
                        flexShrink: 0,
                      }}>{badge}</span>
                    )}
                  </>
                )}
              </NavLink>
            ))}

            <div className="pt-6 pb-2 px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              {sidebarOpen && 'Documentation'}
            </div>

            {SECONDARY_NAV.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                title={!sidebarOpen ? label : undefined}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-[#00D26A] text-slate-950 font-bold shadow-[0_0_16px_rgba(0,210,106,0.25)]'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#131C2E]'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon size={18} className={`flex-shrink-0 ${isActive ? 'text-slate-950' : 'text-slate-400'}`} />
                    {sidebarOpen && <span className="truncate">{label}</span>}
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </aside>

        {/* Content Area */}
        <div className={`flex-1 flex flex-col transition-all duration-150 ${sidebarOpen ? 'ml-60' : 'ml-16'}`}>
          <HeaderBar
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
            onLogout={handleLogout}
          />
          <main className="p-6 flex-1 max-w-6xl w-full mx-auto space-y-6">
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/analyze"   element={<AnalyzeEmployee />} />
                <Route path="/org-risk"  element={<OrgRiskMap />} />
                <Route path="/planner"   element={<ReplacementPlanner />} />
                <Route path="/reports"   element={<Reports />} />
                <Route path="/research"  element={<Research />} />
                <Route path="*"          element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </ErrorBoundary>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
