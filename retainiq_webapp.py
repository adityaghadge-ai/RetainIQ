"""
retainiq_webapp.py
==================
Generates retainiq_app.html -- the full interactive research web application.

Run:
    python retainiq_webapp.py
Then open: RetainIQ/retainiq_app.html in any browser.

DISCLAIMER: RetainIQ is a benchmark research prototype on the IBM HR Analytics
SYNTHETIC dataset. NOT for real employment decisions.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import retainiq_common as rc

# ── Load all data ─────────────────────────────────────────────────────────────
def load(name):
    p = rc.OUT_DIR / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

ext_df   = load("extended_model.csv")
dept_df  = load("department_cascade.csv")
budget_df= load("budget_results.csv")
fair_df  = load("fairness_audit.csv")
cal_df   = load("calibration_results.csv")
model_df = load("baseline_model_comparison.csv")
gaps_path= rc.OUT_DIR / "research_gaps.json"
gaps     = json.loads(gaps_path.read_text()) if gaps_path.exists() else {}

if ext_df.empty:
    sys.exit("[ERROR] Run retainiq_06_extended_model.py first.")

# ── Serialise to JSON ─────────────────────────────────────────────────────────
def safe_json(df, cols=None):
    d = df[cols].copy() if cols else df.copy()
    return json.loads(d.fillna("").to_json(orient="records"))

emp_cols = ["EmployeeNumber","Department","JobRole","JobLevel","TotalWorkingYears",
            "YearsAtCompany","YearsInCurrentRole","YearsSinceLastPromotion",
            "MonthlyIncome","AnnualSalary","PerformanceRating","JobInvolvement",
            "OverTime","Attrition","calibrated_probability",
            "ProductivityIndex","ReplacementMultiplier","TtP_weeks",
            "ReplacementAvailabilityScore","KnowledgeFactor",
            "ProductivityGapCost","KnowledgeCapitalLoss","TalentScarcityPremium",
            "XERL_base_cost","ExtendedERL","OrganizationalImpactScore",
            "rank_risk_only","rank_erl_basic","rank_xerl",
            "ERL_fixed_plus_salary","replacement_cost_fixed_plus_salary"]
emp_cols = [c for c in emp_cols if c in ext_df.columns]

eng_models = model_df[model_df["feature_set"]=="engineered"] if not model_df.empty else pd.DataFrame()

DATA = {
    "employees": safe_json(ext_df, emp_cols),
    "departments": safe_json(dept_df),
    "budget": safe_json(budget_df),
    "fairness": safe_json(fair_df),
    "calibration": safe_json(cal_df),
    "models": safe_json(eng_models, ["model","roc_auc","pr_auc","precision","recall","f1","accuracy","brier","ece"]) if not eng_models.empty else [],
    "gaps": gaps,
    "summary": {
        "total_employees": int(len(ext_df)),
        "total_leavers": int(ext_df["Attrition"].sum()),
        "attrition_rate": round(float(ext_df["Attrition"].mean())*100, 1),
        "mean_pi": round(float(ext_df["ProductivityIndex"].mean()), 3),
        "mean_rm": round(float(ext_df["ReplacementMultiplier"].mean()), 2),
        "mean_ttp": round(float(ext_df["TtP_weeks"].mean()), 1),
        "mean_ras": round(float(ext_df["ReplacementAvailabilityScore"].mean()), 3),
        "mean_pgc": round(float(ext_df["ProductivityGapCost"].mean()), 0),
        "mean_kcl": round(float(ext_df["KnowledgeCapitalLoss"].mean()), 0),
        "mean_xerl": round(float(ext_df["ExtendedERL"].mean()), 0),
        "mean_basic_erl": round(float(ext_df["ERL_fixed_plus_salary"].mean()), 0),
        "xerl_uplift": round(float(ext_df["ExtendedERL"].mean() / ext_df["ERL_fixed_plus_salary"].mean()), 2),
        "accuracy": 0.8748, "roc_auc": 0.8236, "pr_auc": 0.5983, "f1": 0.4065,
        "total_xerl_at_risk": round(float((ext_df["calibrated_probability"] * ext_df["ExtendedERL"]).sum()), 0),
        "rm_gt2_pct": round(float((ext_df["ReplacementMultiplier"]>=2.0).mean()*100), 1),
    }
}
DATA_JSON = json.dumps(DATA, default=str)

# ─────────────────────────── HTML PARTS ──────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
:root {
  --bg: #060b18; --bg2: #0d1526; --bg3: #141f35; --bg4: #1c2a45;
  --border: rgba(100,180,255,.12);
  --a1: #60a5fa; --a2: #34d399; --a3: #fbbf24; --a4: #f87171;
  --a5: #a78bfa; --a6: #38bdf8; --a7: #fb923c;
  --text: #e2e8f0; --text2: #94a3b8; --text3: #64748b;
  --glass: rgba(255,255,255,.04); --glassborder: rgba(255,255,255,.07);
  --radius: 16px; --radius-sm: 10px;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text);
  min-height: 100vh; overflow-x: hidden; }
body::before { content: '';
  background: radial-gradient(ellipse 80% 60% at 10% 10%, rgba(96,165,250,.07) 0%, transparent 60%),
              radial-gradient(ellipse 60% 60% at 90% 80%, rgba(52,211,153,.05) 0%, transparent 60%),
              radial-gradient(ellipse 50% 50% at 50% 50%, rgba(167,139,250,.04) 0%, transparent 70%);
  position: fixed; inset: 0; pointer-events: none; z-index: 0; }
.wrapper { position: relative; z-index: 1; display: flex; min-height: 100vh; }

/* SIDEBAR */
.sidebar {
  width: 240px; flex-shrink: 0;
  background: var(--bg2); border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  position: fixed; top: 0; left: 0; height: 100vh;
  z-index: 200; overflow-y: auto; }
.sidebar-logo { padding: 1.5rem 1.25rem; border-bottom: 1px solid var(--glassborder); }
.logo-mark { display: flex; align-items: center; gap: .75rem; }
.logo-icon { width: 38px; height: 38px; border-radius: 12px;
  background: linear-gradient(135deg, #60a5fa, #34d399);
  display: flex; align-items: center; justify-content: center;
  font-weight: 900; font-size: .85rem; color: #060b18; letter-spacing: -.5px; }
.logo-text { font-size: 1.15rem; font-weight: 800; letter-spacing: -.5px; }
.logo-text span { color: #34d399; }
.logo-sub { font-size: .65rem; color: var(--text3); margin-top: .2rem; text-transform: uppercase; letter-spacing: .8px; }
.nav-section { padding: .75rem .75rem .25rem; font-size: .65rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 1px; color: var(--text3); }
.nav-item { display: flex; align-items: center; gap: .7rem;
  padding: .65rem 1rem; margin: .1rem .5rem; border-radius: 10px;
  cursor: pointer; font-size: .82rem; font-weight: 500; color: var(--text2);
  transition: all .2s; border: none; background: none; width: calc(100% - 1rem); text-align: left; }
.nav-item:hover { background: var(--glassborder); color: var(--text); }
.nav-item.active { background: rgba(96,165,250,.12); color: var(--a1);
  border-left: 2px solid var(--a1); margin-left: calc(.5rem - 2px); }
.nav-icon { font-size: .9rem; width: 20px; text-align: center; }
.sidebar-footer { margin-top: auto; padding: 1rem; }
.disclaimer-chip { background: rgba(251,191,36,.08); border: 1px solid rgba(251,191,36,.2);
  border-radius: 8px; padding: .5rem .75rem; font-size: .68rem; color: #fbbf24; line-height: 1.4; }

/* MAIN */
.main { margin-left: 240px; flex: 1; padding: 2rem; min-height: 100vh; }
.page { display: none; animation: fadeUp .3s ease; }
.page.active { display: block; }
@keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:none; } }

/* PAGE HEADER */
.page-header { margin-bottom: 2rem; }
.page-title { font-size: 1.6rem; font-weight: 800; letter-spacing: -.5px; }
.page-title span { background: linear-gradient(135deg, var(--a1), var(--a2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.page-sub { font-size: .85rem; color: var(--text2); margin-top: .35rem; }

/* STAT CARDS */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(175px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
.kpi { background: var(--glass); border: 1px solid var(--glassborder); border-radius: var(--radius);
  padding: 1.25rem 1.5rem; position: relative; overflow: hidden; transition: transform .2s, border-color .2s; }
.kpi:hover { transform: translateY(-3px); border-color: rgba(96,165,250,.25); }
.kpi::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: var(--kgrad); }
.kpi-label { font-size: .68rem; font-weight: 700; color: var(--text2); text-transform: uppercase; letter-spacing: .8px; margin-bottom: .5rem; }
.kpi-value { font-size: 1.9rem; font-weight: 900; letter-spacing: -.5px; line-height: 1; }
.kpi-sub { font-size: .72rem; color: var(--text2); margin-top: .3rem; }

/* CARDS / GRIDS */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 1.25rem; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.25rem; margin-bottom: 1.25rem; }
.grid-4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1rem; margin-bottom: 1.25rem; }
@media(max-width:1100px) { .grid-3,.grid-4 { grid-template-columns:1fr 1fr; } }
@media(max-width:750px) { .grid-2,.grid-3,.grid-4 { grid-template-columns:1fr; } }
.card { background: var(--glass); border: 1px solid var(--glassborder); border-radius: var(--radius); padding: 1.5rem; }
.card + .card { margin-top: 0; }
.card-title { font-size: .9rem; font-weight: 700; margin-bottom: 1rem; display: flex; align-items: center; gap: .5rem; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--a1); box-shadow: 0 0 8px var(--a1); flex-shrink: 0; }
.dot2 { --a1: #34d399; } .dot3 { --a1: #fbbf24; } .dot4 { --a1: #f87171; } .dot5 { --a1: #a78bfa; }
.chart-h { position: relative; height: 260px; }
.chart-h-tall { position: relative; height: 320px; }
.chart-h-sm { position: relative; height: 200px; }

/* TABLES */
.tbl-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .8rem; }
th { background: rgba(96,165,250,.08); color: var(--a1); font-weight: 700; font-size: .68rem;
  text-transform: uppercase; letter-spacing: .6px; padding: .7rem 1rem; text-align: left;
  border-bottom: 1px solid var(--glassborder); white-space: nowrap; }
td { padding: .6rem 1rem; border-bottom: 1px solid rgba(255,255,255,.03); white-space: nowrap; }
tr:hover td { background: rgba(255,255,255,.025); }
tr:last-child td { border-bottom: none; }

/* BADGES */
.badge { display: inline-flex; align-items: center; gap: .3rem; font-size: .66rem; font-weight: 700;
  padding: .18rem .6rem; border-radius: 99px; text-transform: uppercase; letter-spacing: .4px; }
.b-high { background: rgba(248,113,113,.15); color: #f87171; border: 1px solid rgba(248,113,113,.25); }
.b-mod  { background: rgba(251,191,36,.15);  color: #fbbf24; border: 1px solid rgba(251,191,36,.25); }
.b-low  { background: rgba(52,211,153,.15);  color: #34d399; border: 1px solid rgba(52,211,153,.25); }
.b-blue { background: rgba(96,165,250,.15);  color: #60a5fa; border: 1px solid rgba(96,165,250,.25); }
.b-purple{background:rgba(167,139,250,.15); color: #a78bfa; border:1px solid rgba(167,139,250,.25); }

/* FORM CONTROLS */
.control-row { display: flex; gap: .75rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.ctrl { background: var(--bg3); border: 1px solid var(--glassborder); border-radius: var(--radius-sm);
  padding: .55rem 1rem; color: var(--text); font-family: 'Inter',sans-serif; font-size: .82rem;
  outline: none; transition: border-color .2s; flex: 1; min-width: 170px; }
.ctrl:focus { border-color: var(--a1); }
.ctrl option { background: #1c2a45; }
.btn { background: linear-gradient(135deg, #60a5fa, #34d399); color: #060b18; border: none;
  border-radius: var(--radius-sm); padding: .55rem 1.25rem; font-family: 'Inter',sans-serif;
  font-size: .82rem; font-weight: 700; cursor: pointer; transition: opacity .2s; }
.btn:hover { opacity: .85; }

/* EMPLOYEE CARD */
#emp-profile { display: none; margin-bottom: 1.5rem;
  background: linear-gradient(135deg, rgba(96,165,250,.08), rgba(52,211,153,.06));
  border: 1px solid rgba(96,165,250,.2); border-radius: var(--radius); padding: 1.75rem;
  animation: fadeUp .3s ease; }
.ep-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem; }
.ep-name { font-size: 1.2rem; font-weight: 800; }
.ep-role { font-size: .82rem; color: var(--text2); margin-top: .25rem; }
.ep-kpis { display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: .75rem; margin-bottom: 1.25rem; }
.ep-kpi { background: rgba(255,255,255,.04); border-radius: 10px; padding: .85rem 1rem; }
.ep-kpi .lbl { font-size: .62rem; text-transform: uppercase; letter-spacing: .7px; color: var(--text2); margin-bottom: .3rem; }
.ep-kpi .val { font-size: 1.05rem; font-weight: 700; }
.cost-breakdown { display: grid; grid-template-columns: repeat(4,1fr); gap: .75rem; }
.cost-item { background: rgba(255,255,255,.03); border-radius: 10px; padding: .85rem; text-align: center; }
.cost-item .ci-lbl { font-size: .65rem; color: var(--text2); text-transform: uppercase; margin-bottom: .3rem; }
.cost-item .ci-val { font-size: .95rem; font-weight: 700; }

/* METRIC BARS */
.mbar { margin-bottom: .85rem; }
.mbar-header { display: flex; justify-content: space-between; margin-bottom: .3rem; }
.mbar-lbl { font-size: .75rem; color: var(--text2); }
.mbar-val { font-size: .75rem; font-weight: 700; }
.mbar-track { height: 6px; background: rgba(255,255,255,.07); border-radius: 99px; overflow: hidden; }
.mbar-fill { height: 100%; border-radius: 99px; }

/* DISCLAIMER */
.disc { background: rgba(251,191,36,.06); border: 1px solid rgba(251,191,36,.18);
  border-radius: 10px; padding: .75rem 1rem; font-size: .73rem; color: #fbbf24; line-height: 1.5; margin-bottom: 1.5rem; }

/* RESEARCH GAPS */
.gap-card { background: var(--glass); border: 1px solid var(--glassborder); border-radius: var(--radius); padding: 1.5rem; margin-bottom: 1rem; }
.gap-title { font-size: .9rem; font-weight: 700; margin-bottom: .5rem; display: flex; align-items: center; gap: .6rem; }
.gap-num { width: 26px; height: 26px; border-radius: 8px; background: rgba(96,165,250,.15);
  color: #60a5fa; font-size: .75rem; font-weight: 800; display: flex; align-items: center; justify-content: center; }
.gap-desc { font-size: .8rem; color: var(--text2); line-height: 1.6; margin-bottom: .75rem; }
.gap-finding { background: rgba(52,211,153,.08); border-left: 3px solid #34d399; border-radius: 0 8px 8px 0;
  padding: .6rem 1rem; font-size: .78rem; color: #34d399; font-weight: 600; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(96,165,250,.25); border-radius: 99px; }
"""

BODY = """
<aside class="sidebar">
  <div class="sidebar-logo">
    <div class="logo-mark">
      <div class="logo-icon">RIQ</div>
      <div>
        <div class="logo-text">Retain<span>IQ</span></div>
        <div class="logo-sub">Research Platform</div>
      </div>
    </div>
  </div>
  <div style="padding:.5rem 0;">
    <div class="nav-section">Analytics</div>
    <button class="nav-item active" onclick="nav('overview',this)"><span class="nav-icon">&#9672;</span> Overview</button>
    <button class="nav-item" onclick="nav('employees',this)"><span class="nav-icon">&#9671;</span> Employee Analyzer</button>
    <button class="nav-item" onclick="nav('replacement',this)"><span class="nav-icon">&#9670;</span> Replacement Modeler</button>
    <button class="nav-item" onclick="nav('orgimpact',this)"><span class="nav-icon">&#9673;</span> Org. Impact</button>
    <button class="nav-item" onclick="nav('budget',this)"><span class="nav-icon">&#9678;</span> Budget Experiment</button>
    <div class="nav-section">Research</div>
    <button class="nav-item" onclick="nav('models',this)"><span class="nav-icon">&#9674;</span> Model Performance</button>
    <button class="nav-item" onclick="nav('fairness',this)"><span class="nav-icon">&#9679;</span> Fairness Audit</button>
    <button class="nav-item" onclick="nav('gaps',this)"><span class="nav-icon">&#9675;</span> Research Gaps</button>
  </div>
  <div class="sidebar-footer">
    <div class="disclaimer-chip">RESEARCH PROTOTYPE<br>IBM Synthetic Dataset Only<br>NOT for real HR decisions</div>
  </div>
</aside>

<main class="main">

<!-- =========================================================== OVERVIEW -->
<div id="page-overview" class="page active">
  <div class="page-header">
    <div class="page-title"><span>RetainIQ</span> — Organizational Attrition Intelligence</div>
    <div class="page-sub">Extended cost model with Productivity Index, Replacement Multiplier, Knowledge Capital Loss &amp; Talent Scarcity Analysis</div>
  </div>
  <div class="disc"><strong>DISCLAIMER:</strong> All metrics are researcher-defined estimates on the IBM HR Analytics <em>synthetic</em> dataset (1,470 employees). Results are for academic research only. Must NOT be used for real employment decisions.</div>
  <div class="kpi-grid" id="ov-kpis"></div>
  <div class="grid-2">
    <div class="card"><div class="card-title"><div class="dot"></div>Attrition Rate by Department</div><div class="chart-h"><canvas id="ch-dept-att"></canvas></div></div>
    <div class="card"><div class="card-title"><div class="dot dot2"></div>XERL Cost Breakdown (Mean Components)</div><div class="chart-h"><canvas id="ch-xerl-breakdown"></canvas></div></div>
  </div>
  <div class="grid-3">
    <div class="card"><div class="card-title"><div class="dot dot3"></div>Replacement Multiplier Distribution</div><div class="chart-h"><canvas id="ch-rm-dist"></canvas></div></div>
    <div class="card"><div class="card-title"><div class="dot dot4"></div>Productivity Index vs Attrition Risk</div><div class="chart-h"><canvas id="ch-pi-prob"></canvas></div></div>
    <div class="card"><div class="card-title"><div class="dot dot5"></div>XERL vs Basic ERL (Top 50)</div><div class="chart-h"><canvas id="ch-erl-compare"></canvas></div></div>
  </div>
</div>

<!-- =========================================================== EMPLOYEES -->
<div id="page-employees" class="page">
  <div class="page-header">
    <div class="page-title">Employee <span>Risk Analyzer</span></div>
    <div class="page-sub">Search any employee to see full attrition risk, productivity profile, replacement cost, and organizational impact</div>
  </div>
  <div id="emp-profile">
    <div class="ep-header">
      <div>
        <div class="ep-name" id="ep-name">Employee</div>
        <div class="ep-role" id="ep-role"></div>
      </div>
      <div id="ep-risk" class="badge"></div>
    </div>
    <div class="ep-kpis">
      <div class="ep-kpi"><div class="lbl">P(Attrition)</div><div class="val" id="ep-prob"></div></div>
      <div class="ep-kpi"><div class="lbl">Risk Rank</div><div class="val" id="ep-rrank"></div></div>
      <div class="ep-kpi"><div class="lbl">XERL Rank</div><div class="val" id="ep-xrank"></div></div>
      <div class="ep-kpi"><div class="lbl">Productivity Index</div><div class="val" id="ep-pi"></div></div>
      <div class="ep-kpi"><div class="lbl">Replacement Multiplier</div><div class="val" id="ep-rm"></div></div>
      <div class="ep-kpi"><div class="lbl">Time to Productivity</div><div class="val" id="ep-ttp"></div></div>
      <div class="ep-kpi"><div class="lbl">Replacement Availability</div><div class="val" id="ep-ras"></div></div>
      <div class="ep-kpi"><div class="lbl">Annual Salary</div><div class="val" id="ep-sal"></div></div>
      <div class="ep-kpi"><div class="lbl">Actual Outcome</div><div class="val" id="ep-actual"></div></div>
    </div>
    <div class="card-title" style="margin:.75rem 0 .5rem"><div class="dot dot3"></div>Extended Cost Breakdown (XERL Components)</div>
    <div class="cost-breakdown" id="ep-costs"></div>
    <div style="margin-top:1rem;font-size:.7rem;color:var(--text3);border-top:1px solid var(--glassborder);padding-top:.75rem">
      All costs are researcher-assumed hypothetical estimates. Model associations are NOT causal. Not for real employment decisions.
    </div>
  </div>
  <div class="control-row">
    <input type="number" class="ctrl" id="emp-id" placeholder="Search by Employee ID..."/>
    <select class="ctrl" id="emp-dept"><option value="">All Departments</option><option>Sales</option><option>Research &amp; Development</option><option>Human Resources</option></select>
    <select class="ctrl" id="emp-risk"><option value="">All Risk Levels</option><option value="HIGH">High Risk</option><option value="MODERATE">Moderate Risk</option><option value="LOW">Low Risk</option></select>
    <select class="ctrl" id="emp-sort"><option value="xerl">Sort: XERL (Extended Priority)</option><option value="erl">Sort: Basic ERL</option><option value="risk">Sort: Attrition Risk</option><option value="ois">Sort: Org. Impact</option></select>
  </div>
  <div class="card">
    <div class="card-title"><div class="dot"></div>Employee Priority List — Click row to inspect</div>
    <div class="tbl-wrap"><table id="emp-table"></table></div>
    <div style="margin-top:.75rem;font-size:.7rem;color:var(--text3)">Showing top 60. LEFT=actual leaver (OOF label). RAS=Replacement Availability. RM=Replacement Multiplier.</div>
  </div>
</div>

<!-- =========================================================== REPLACEMENT -->
<div id="page-replacement" class="page">
  <div class="page-header">
    <div class="page-title">Replacement <span>Modeler</span></div>
    <div class="page-sub">How many new hires are needed to replace one departing employee? What is the probability of finding equivalent talent?</div>
  </div>
  <div class="disc">Replacement Multiplier (RM) and Availability Score (RAS) are researcher-defined estimates. Empirical validation requires longitudinal hiring data not available in the IBM dataset.</div>
  <div class="grid-4" id="rep-kpis"></div>
  <div class="grid-2">
    <div class="card"><div class="card-title"><div class="dot"></div>Replacement Multiplier by Job Level</div><div class="chart-h"><canvas id="ch-rm-jl"></canvas></div></div>
    <div class="card"><div class="card-title"><div class="dot dot2"></div>Replacement Availability Score by Role</div><div class="chart-h-tall"><canvas id="ch-ras-role"></canvas></div></div>
  </div>
  <div class="grid-2">
    <div class="card"><div class="card-title"><div class="dot dot3"></div>Time-to-Productivity (weeks) by Job Level</div><div class="chart-h-sm"><canvas id="ch-ttp-jl"></canvas></div></div>
    <div class="card"><div class="card-title"><div class="dot dot4"></div>Knowledge Capital Loss by Tenure Group</div><div class="chart-h-sm"><canvas id="ch-kcl-tenure"></canvas></div></div>
  </div>
  <div class="card">
    <div class="card-title"><div class="dot dot5"></div>High-Risk Replacement Analysis — Top 20 by XERL</div>
    <div class="tbl-wrap"><table id="rep-table"></table></div>
  </div>
</div>

<!-- =========================================================== ORG IMPACT -->
<div id="page-orgimpact" class="page">
  <div class="page-header">
    <div class="page-title">Organizational <span>Impact Analysis</span></div>
    <div class="page-sub">Department-level cascade effects, productivity-weighted total exposure, and company-wide attrition cost under extended model</div>
  </div>
  <div class="grid-3" id="org-kpis"></div>
  <div class="grid-2">
    <div class="card"><div class="card-title"><div class="dot"></div>Total XERL Exposure by Department</div><div class="chart-h"><canvas id="ch-dept-xerl"></canvas></div></div>
    <div class="card"><div class="card-title"><div class="dot dot2"></div>XERL Uplift vs Basic ERL by Department</div><div class="chart-h"><canvas id="ch-dept-uplift"></canvas></div></div>
  </div>
  <div class="card" style="margin-bottom:1.25rem">
    <div class="card-title"><div class="dot dot3"></div>Department Cascade Summary Table</div>
    <div class="tbl-wrap"><table id="dept-table"></table></div>
  </div>
  <div class="card">
    <div class="card-title"><div class="dot dot4"></div>XERL Component Analysis by Department</div>
    <div class="chart-h"><canvas id="ch-dept-components"></canvas></div>
  </div>
</div>

<!-- =========================================================== BUDGET -->
<div id="page-budget" class="page">
  <div class="page-header">
    <div class="page-title">Budget <span>Experiment</span></div>
    <div class="page-sub">Capacity-constrained intervention simulation: which strategy captures the most leavers and cost exposure at each budget?</div>
  </div>
  <div class="disc">Evaluation uses <strong>realized out-of-fold outcomes</strong> (ground-truth attrition labels), not model predictions. Costs are researcher-assumed parameters.</div>
  <div class="grid-2">
    <div class="card"><div class="card-title"><div class="dot"></div>Leavers Captured by Strategy</div><div class="chart-h-tall"><canvas id="ch-bud-leavers"></canvas></div></div>
    <div class="card"><div class="card-title"><div class="dot dot2"></div>Cost Exposure Captured ($k)</div><div class="chart-h-tall"><canvas id="ch-bud-cost"></canvas></div></div>
  </div>
  <div class="card">
    <div class="card-title"><div class="dot dot3"></div>Full Budget Results Table</div>
    <div class="tbl-wrap"><table id="bud-table"></table></div>
  </div>
</div>

<!-- =========================================================== MODELS -->
<div id="page-models" class="page">
  <div class="page-header">
    <div class="page-title">Model <span>Performance</span></div>
    <div class="page-sub">OOF evaluation of all 3 models on engineered feature set with fold-safe sigmoid calibration</div>
  </div>
  <div class="kpi-grid" id="mdl-kpis"></div>
  <div class="grid-2">
    <div class="card"><div class="card-title"><div class="dot"></div>Accuracy / ROC-AUC / PR-AUC</div><div class="chart-h"><canvas id="ch-mdl-bar"></canvas></div></div>
    <div class="card"><div class="card-title"><div class="dot dot2"></div>Calibration Impact (Brier + ECE)</div><div class="chart-h"><canvas id="ch-cal"></canvas></div></div>
  </div>
  <div class="card">
    <div class="card-title"><div class="dot dot3"></div>All Model Results (OOF, Calibrated, Engineered Features)</div>
    <div class="tbl-wrap"><table id="mdl-table"></table></div>
  </div>
  <div style="margin-top:1.25rem" class="card">
    <div class="card-title"><div class="dot dot4"></div>Why Not Just Use Accuracy?</div>
    <div style="font-size:.82rem;line-height:1.7;color:var(--text2)">
      <p>With 16.1% minority class (attrition=1), a model that <em>always predicts Stayed</em> would achieve <strong style="color:#f87171">83.9% accuracy</strong>. This is why accuracy alone is misleading for imbalanced classification.</p>
      <p style="margin-top:.75rem"><strong style="color:#34d399">PR-AUC (0.5983)</strong> is the primary metric: it measures the trade-off between precision and recall on the minority class specifically, independent of the majority class size.</p>
      <p style="margin-top:.75rem"><strong style="color:#60a5fa">Logistic Regression wins</strong> on this 1,470-row dataset — consistent with literature: on small structured HR data, regularised linear models often outperform high-capacity ensembles (RF, XGBoost).</p>
    </div>
  </div>
</div>

<!-- =========================================================== FAIRNESS -->
<div id="page-fairness" class="page">
  <div class="page-header">
    <div class="page-title">Fairness <span>Audit</span></div>
    <div class="page-sub">Post-hoc diagnostic: Age, Gender, MaritalStatus were EXCLUDED from model training</div>
  </div>
  <div class="disc">This is a post-hoc diagnostic analysis only. No legal compliance is claimed. Disparities reflect dataset characteristics, not model-induced bias. The IBM dataset is synthetic.</div>
  <div class="grid-3">
    <div class="card"><div class="card-title"><div class="dot"></div>By Gender</div><div class="chart-h"><canvas id="ch-f-gender"></canvas></div></div>
    <div class="card"><div class="card-title"><div class="dot dot2"></div>By Marital Status</div><div class="chart-h"><canvas id="ch-f-marital"></canvas></div></div>
    <div class="card"><div class="card-title"><div class="dot dot3"></div>By Age Band</div><div class="chart-h"><canvas id="ch-f-age"></canvas></div></div>
  </div>
  <div class="card">
    <div class="card-title"><div class="dot dot4"></div>Key Fairness Finding</div>
    <div style="font-size:.82rem;line-height:1.7;color:var(--text2)">
      <p><strong style="color:#f87171">Age &lt;30</strong> employees have the highest actual attrition (27.9%) but the <em>lowest</em> Top-50 XERL selection rate — because younger employees have lower salaries, so cost-weighted ranking systematically deprioritises them despite high risk.</p>
      <p style="margin-top:.75rem"><strong style="color:#fbbf24">Conversely</strong>, Age 50+ employees have moderate attrition (13.3%) but the highest selection rate (6.94%) due to salary-inflated ERL. This is the central fairness tension in cost-weighted HR prioritisation frameworks.</p>
      <p style="margin-top:.75rem;color:#34d399">Research implication: any cost-weighted retention framework must explicitly acknowledge and report this age-salary interaction to avoid inadvertent age-based selection patterns.</p>
    </div>
  </div>
  <div class="card" style="margin-top:1.25rem">
    <div class="card-title"><div class="dot dot5"></div>Fairness Audit Table</div>
    <div class="tbl-wrap"><table id="fair-table"></table></div>
  </div>
</div>

<!-- =========================================================== RESEARCH GAPS -->
<div id="page-gaps" class="page">
  <div class="page-header">
    <div class="page-title">Research <span>Gap Analysis</span></div>
    <div class="page-sub">Six novel contributions that fill gaps in prior attrition cost literature — for research paper publication</div>
  </div>
  <div id="gap-cards"></div>
  <div class="card" style="margin-top:1.25rem">
    <div class="card-title"><div class="dot"></div>Research Questions Addressed</div>
    <table id="rq-table">
      <thead><tr><th>#</th><th>Research Question</th><th>Method</th><th>Key Finding</th></tr></thead>
      <tbody>
        <tr><td style="font-weight:700;color:var(--a1)">RQ1</td><td>How effectively can ML models estimate attrition risk under class imbalance?</td><td>OOF evaluation, 3 classifiers, 5-fold CV</td><td style="color:#34d399">LR PR-AUC=0.598, ROC-AUC=0.824, Accuracy=87.5%</td></tr>
        <tr><td style="font-weight:700;color:var(--a1)">RQ2</td><td>Do engineered features improve discrimination and calibration?</td><td>Ablation A vs B on all 3 models</td><td style="color:#34d399">LR: +0.008 PR-AUC, -0.0006 Brier (model-specific)</td></tr>
        <tr><td style="font-weight:700;color:var(--a1)">RQ3</td><td>Does cost-weighted prioritisation select a different intervention set?</td><td>Budget simulation, 4 strategies</td><td style="color:#34d399">Top-10: XERL vs Risk-Only overlap=2/10 (material difference)</td></tr>
        <tr><td style="font-weight:700;color:var(--a1)">RQ4</td><td>How sensitive are rankings to cost assumptions?</td><td>16-scenario sensitivity grid</td><td style="color:#34d399">Spearman r>=0.97 overall; Top-25 shifts 36% under extreme fixed-cost</td></tr>
        <tr><td style="font-weight:700;color:var(--a1)">RQ5</td><td>Do strategies beat random baseline?</td><td>1,000-repetition random baseline</td><td style="color:#34d399">All strategies: 4.4-6.3x lift over random</td></tr>
        <tr><td style="font-weight:700;color:var(--a1)">RQ6</td><td>Does XERL produce materially different rankings from basic ERL?</td><td>Spearman rank correlation, top-K overlap</td><td style="color:#34d399">Top-10 overlap=5/10; Spearman r=0.913</td></tr>
        <tr><td style="font-weight:700;color:var(--a1)">RQ7</td><td>Does the replacement multiplier alter total cost exposure materially?</td><td>XERL uplift analysis</td><td style="color:#34d399">XERL=2.08x basic ERL on average; 13.3% employees need RM>=2.0</td></tr>
      </tbody>
    </table>
  </div>
</div>

</main>
"""

JS = r"""
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter',sans-serif";
const D = window.__DATA__;
const S = D.summary;

function nav(id, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.getElementById('page-'+id).classList.add('active');
  btn.classList.add('active');
}

const COLORS = ['#60a5fa','#34d399','#fbbf24','#f87171','#a78bfa','#38bdf8','#fb923c','#e879f9'];
const risk_label = p => p >= 0.60 ? 'HIGH' : (p >= 0.35 ? 'MODERATE' : 'LOW');
const risk_class = r => r==='HIGH'?'b-high':(r==='MODERATE'?'b-mod':'b-low');
const fmt = n => isNaN(+n)||n===''?'--':Math.round(+n).toLocaleString();
const fmtD = (n,d=3) => isNaN(+n)||n===''?'--':(+n).toFixed(d);

// ─── OVERVIEW ────────────────────────────────────────────────────────────────
function buildOverview() {
  const kpis = [
    {l:'Employees',v:S.total_employees.toLocaleString(),s:'IBM HR (Synthetic)',g:'linear-gradient(135deg,#60a5fa,#a78bfa)'},
    {l:'Actual Leavers',v:S.total_leavers.toLocaleString(),s:S.attrition_rate+'% attrition rate',g:'linear-gradient(135deg,#f87171,#fbbf24)'},
    {l:'Accuracy',v:(S.accuracy*100).toFixed(1)+'%',s:'OOF Logistic Regression',g:'linear-gradient(135deg,#34d399,#60a5fa)'},
    {l:'PR-AUC (primary)',v:S.pr_auc.toFixed(4),s:'Minority-class discrimination',g:'linear-gradient(135deg,#a78bfa,#60a5fa)'},
    {l:'Mean Repl. Multiplier',v:S.mean_rm+'x',s:'Avg. FTEs needed per leaver',g:'linear-gradient(135deg,#fbbf24,#fb923c)'},
    {l:'Mean Repl. Availability',v:(S.mean_ras*100).toFixed(0)+'%',s:'P(finding equivalent talent)',g:'linear-gradient(135deg,#34d399,#a78bfa)'},
    {l:'Mean XERL',v:'$'+Math.round(S.mean_xerl).toLocaleString(),s:'Extended replacement loss',g:'linear-gradient(135deg,#f87171,#a78bfa)'},
    {l:'XERL Uplift vs ERL',v:S.xerl_uplift+'x',s:'Extended vs basic cost model',g:'linear-gradient(135deg,#38bdf8,#34d399)'},
  ];
  document.getElementById('ov-kpis').innerHTML = kpis.map(k=>`
    <div class="kpi" style="--kgrad:${k.g}">
      <div class="kpi-label">${k.l}</div>
      <div class="kpi-value">${k.v}</div>
      <div class="kpi-sub">${k.s}</div>
    </div>`).join('');

  // Dept attrition
  const depts = D.departments;
  new Chart(document.getElementById('ch-dept-att'), {
    type:'bar',
    data:{labels:depts.map(d=>d.Department),
      datasets:[
        {label:'Attrition Rate',data:depts.map(d=>+(+d.attrition_rate*100).toFixed(1)),backgroundColor:['#f87171aa','#60a5faaa','#fbbf24aa'],borderColor:['#f87171','#60a5fa','#fbbf24'],borderWidth:2},
      ]},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{y:{min:0,max:30,grid:{color:'rgba(255,255,255,.05)'},ticks:{callback:v=>v+'%'}},x:{grid:{display:false}}},
      plugins:{legend:{display:false}}}
  });

  // XERL breakdown donut
  new Chart(document.getElementById('ch-xerl-breakdown'), {
    type:'doughnut',
    data:{labels:['Recruitment x RM','Productivity Gap','Knowledge Loss','Talent Scarcity'],
      datasets:[{data:[S.mean_rm,S.mean_pgc,S.mean_kcl,S.mean_xerl-S.mean_pgc-S.mean_kcl-(S.mean_rm*S.mean_basic_erl)].map(Math.abs),
        backgroundColor:['#60a5faaa','#34d399aa','#a78bfaaa','#fbbf24aa'],
        borderColor:['#60a5fa','#34d399','#a78bfa','#fbbf24'],borderWidth:2}]},
    options:{responsive:true,maintainAspectRatio:false,cutout:'60%',
      plugins:{legend:{position:'bottom',labels:{font:{size:10}}}}}
  });

  // RM distribution histogram
  const emps = D.employees;
  const rmBands = ['1.0-1.1','1.1-1.4','1.4-1.75','1.75-2.25','2.25-3.0'];
  const rmCounts = [
    emps.filter(e=>+e.ReplacementMultiplier<=1.1).length,
    emps.filter(e=>+e.ReplacementMultiplier>1.1&&+e.ReplacementMultiplier<=1.4).length,
    emps.filter(e=>+e.ReplacementMultiplier>1.4&&+e.ReplacementMultiplier<=1.75).length,
    emps.filter(e=>+e.ReplacementMultiplier>1.75&&+e.ReplacementMultiplier<=2.25).length,
    emps.filter(e=>+e.ReplacementMultiplier>2.25).length,
  ];
  new Chart(document.getElementById('ch-rm-dist'), {
    type:'bar',
    data:{labels:rmBands,datasets:[{label:'Employees',data:rmCounts,
      backgroundColor:['#34d399aa','#60a5faaa','#fbbf24aa','#fb923caa','#f87171aa'],
      borderColor:['#34d399','#60a5fa','#fbbf24','#fb923c','#f87171'],borderWidth:2}]},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{y:{grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},
      plugins:{legend:{display:false}}}
  });

  // PI vs Prob scatter
  const scatter_data = emps.filter((_,i)=>i%5===0).map(e=>({
    x:+(+e.ProductivityIndex).toFixed(3), y:+(+e.calibrated_probability).toFixed(3),
    att:e.Attrition
  }));
  new Chart(document.getElementById('ch-pi-prob'), {
    type:'scatter',
    data:{datasets:[
      {label:'Stayed',data:scatter_data.filter(d=>!d.att).map(d=>({x:d.x,y:d.y})),
        backgroundColor:'#60a5fa44',borderColor:'#60a5fa',pointRadius:3},
      {label:'Left',data:scatter_data.filter(d=>d.att).map(d=>({x:d.x,y:d.y})),
        backgroundColor:'#f8717144',borderColor:'#f87171',pointRadius:3},
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{x:{title:{display:true,text:'Productivity Index'},grid:{color:'rgba(255,255,255,.05)'}},
              y:{title:{display:true,text:'P(Attrition)'},grid:{color:'rgba(255,255,255,.05)'}}},
      plugins:{legend:{position:'bottom'}}}
  });

  // Top 50 XERL vs ERL
  const top50 = [...emps].sort((a,b)=>+a.rank_xerl-+b.rank_xerl).slice(0,50);
  new Chart(document.getElementById('ch-erl-compare'), {
    type:'bar',
    data:{labels:top50.map(e=>'#'+e.EmployeeNumber),
      datasets:[
        {label:'Basic ERL',data:top50.map(e=>+(+e.ERL_fixed_plus_salary/1000).toFixed(1)),backgroundColor:'#60a5fa44',borderColor:'#60a5fa',borderWidth:1},
        {label:'XERL',data:top50.map(e=>+(+e.ExtendedERL/1000).toFixed(1)),backgroundColor:'#f8717144',borderColor:'#f87171',borderWidth:1},
      ]},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{y:{title:{display:true,text:'$k'},grid:{color:'rgba(255,255,255,.05)'}},x:{display:false}},
      plugins:{legend:{position:'bottom'}}}
  });
}

// ─── EMPLOYEES ────────────────────────────────────────────────────────────────
function renderEmpTable(emps) {
  const t = document.getElementById('emp-table');
  if(!emps.length){t.innerHTML='<tbody><tr><td colspan="11" style="text-align:center;padding:2rem;color:var(--text3)">No results.</td></tr></tbody>';return;}
  t.innerHTML=`<thead><tr><th>XERL Rank</th><th>Risk Rank</th><th>Emp#</th><th>Outcome</th>
    <th>P(Att)</th><th>Prod. Index</th><th>Repl. Mult.</th><th>TtP(wks)</th>
    <th>RAS</th><th>XERL($k)</th><th>Dept/Role</th></tr></thead>
  <tbody>${emps.slice(0,60).map(r=>`<tr onclick="showEmp(${r.EmployeeNumber})" style="cursor:pointer">
    <td style="font-weight:700;color:var(--a1)">#${r.rank_xerl||'--'}</td>
    <td style="color:var(--text2)">#${r.rank_risk_only||'--'}</td>
    <td style="font-weight:600">${r.EmployeeNumber}</td>
    <td class="${+r.Attrition===1?'':''}"><span style="color:${+r.Attrition===1?'#f87171':'#34d399'};font-weight:600">${+r.Attrition===1?'LEFT':'STAY'}</span></td>
    <td>${(+r.calibrated_probability).toFixed(3)}</td>
    <td>${(+r.ProductivityIndex).toFixed(3)}</td>
    <td><span class="badge ${+r.ReplacementMultiplier>=2?'b-high':(+r.ReplacementMultiplier>=1.4?'b-mod':'b-low')}">${(+r.ReplacementMultiplier).toFixed(2)}x</span></td>
    <td>${r.TtP_weeks} wks</td>
    <td style="color:${+r.ReplacementAvailabilityScore<0.5?'#f87171':+r.ReplacementAvailabilityScore<0.7?'#fbbf24':'#34d399'}">${(+r.ReplacementAvailabilityScore*100).toFixed(0)}%</td>
    <td style="font-weight:600">$${(+r.ExtendedERL/1000).toFixed(1)}k</td>
    <td style="font-size:.75rem;color:var(--text2)">${(r.Department||'').replace('Research & Development','R&D')} / ${r.JobRole||''}</td>
  </tr>`).join('')}</tbody>`;
}

function showEmp(id) {
  const e = D.employees.find(r=>+r.EmployeeNumber===+id);
  if(!e) return;
  const card = document.getElementById('emp-profile');
  card.style.display = 'block';
  document.getElementById('ep-name').textContent = 'Employee #'+e.EmployeeNumber;
  document.getElementById('ep-role').textContent = (e.JobRole||'')+' · '+(e.Department||'')+' · Level '+(e.JobLevel||'');
  const rb = document.getElementById('ep-risk');
  const rl = risk_label(+e.calibrated_probability);
  rb.textContent = rl; rb.className = 'badge '+risk_class(rl);
  document.getElementById('ep-prob').textContent = (+e.calibrated_probability).toFixed(3);
  document.getElementById('ep-rrank').textContent = '#'+(e.rank_risk_only||'--')+' / 1,470';
  document.getElementById('ep-xrank').textContent = '#'+(e.rank_xerl||'--')+' / 1,470';
  document.getElementById('ep-pi').textContent = (+e.ProductivityIndex).toFixed(3);
  document.getElementById('ep-rm').textContent = (+e.ReplacementMultiplier).toFixed(2)+'x FTEs';
  document.getElementById('ep-ttp').textContent = e.TtP_weeks+' weeks';
  document.getElementById('ep-ras').textContent = (+e.ReplacementAvailabilityScore*100).toFixed(0)+'%';
  document.getElementById('ep-sal').textContent = '$'+(+e.AnnualSalary||+e.MonthlyIncome*12).toLocaleString();
  const act = document.getElementById('ep-actual');
  act.textContent = +e.Attrition===1?'Left (Leaver)':'Stayed';
  act.style.color = +e.Attrition===1?'#f87171':'#34d399';
  document.getElementById('ep-costs').innerHTML = [
    {l:'Recruitment Cost x RM',v:'$'+Math.round(+e.XERL_base_cost||0).toLocaleString(),c:'#60a5fa'},
    {l:'Productivity Gap Cost',v:'$'+Math.round(+e.ProductivityGapCost||0).toLocaleString(),c:'#34d399'},
    {l:'Knowledge Capital Loss',v:'$'+Math.round(+e.KnowledgeCapitalLoss||0).toLocaleString(),c:'#a78bfa'},
    {l:'Talent Scarcity Premium',v:'$'+Math.round(+e.TalentScarcityPremium||0).toLocaleString(),c:'#fbbf24'},
  ].concat([{l:'TOTAL XERL',v:'$'+Math.round(+e.ExtendedERL||0).toLocaleString(),c:'#f87171'}])
  .map(c=>`<div class="cost-item"><div class="ci-lbl">${c.l}</div><div class="ci-val" style="color:${c.c}">${c.v}</div></div>`).join('');
  card.scrollIntoView({behavior:'smooth',block:'start'});
}

function filterEmps() {
  const idv = +document.getElementById('emp-id').value||0;
  if(idv){showEmp(idv);return;}
  const dept = document.getElementById('emp-dept').value;
  const risk = document.getElementById('emp-risk').value;
  const sort = document.getElementById('emp-sort').value;
  let emps = [...D.employees];
  if(dept) emps = emps.filter(e=>e.Department===dept);
  if(risk) emps = emps.filter(e=>risk_label(+e.calibrated_probability)===risk);
  const sk = sort==='xerl'?'rank_xerl':sort==='erl'?'rank_erl_basic':sort==='ois'?'OrganizationalImpactScore':'rank_risk_only';
  if(sort==='ois') emps.sort((a,b)=>+b[sk]-+a[sk]);
  else emps.sort((a,b)=>(+a[sk]||9999)-(+b[sk]||9999));
  renderEmpTable(emps);
}

function buildEmployees() {
  ['emp-id','emp-dept','emp-risk','emp-sort'].forEach(id=>{
    document.getElementById(id).addEventListener('input',filterEmps);
    document.getElementById(id).addEventListener('change',filterEmps);
  });
  renderEmpTable([...D.employees].sort((a,b)=>(+a.rank_xerl||9999)-(+b.rank_xerl||9999)));
}

// ─── REPLACEMENT ─────────────────────────────────────────────────────────────
function buildReplacement() {
  const emps = D.employees;
  const kpis=[
    {l:'Mean Repl. Multiplier',v:S.mean_rm+'x',s:'Average FTEs per leaver',g:'linear-gradient(135deg,#fbbf24,#fb923c)'},
    {l:'Need RM >= 2.0',v:S.rm_gt2_pct+'%',s:'Senior/expert employees',g:'linear-gradient(135deg,#f87171,#a78bfa)'},
    {l:'Mean Time-to-Prod.',v:S.mean_ttp+' weeks',s:'To 80% proficiency',g:'linear-gradient(135deg,#60a5fa,#38bdf8)'},
    {l:'Mean Productivity Gap',v:'$'+Math.round(S.mean_pgc).toLocaleString(),s:'Onboarding output deficit',g:'linear-gradient(135deg,#34d399,#60a5fa)'},
  ];
  document.getElementById('rep-kpis').innerHTML = kpis.map(k=>`
    <div class="kpi" style="--kgrad:${k.g}"><div class="kpi-label">${k.l}</div><div class="kpi-value">${k.v}</div><div class="kpi-sub">${k.s}</div></div>`).join('');

  // RM by job level
  const jls=[1,2,3,4,5];
  const rmByJl = jls.map(jl=>{ const e=emps.filter(r=>+r.JobLevel===jl); return e.length?+(e.reduce((s,r)=>s+(+r.ReplacementMultiplier||0),0)/e.length).toFixed(2):0; });
  new Chart(document.getElementById('ch-rm-jl'),{
    type:'bar',
    data:{labels:jls.map(j=>'Job Level '+j),datasets:[{label:'Mean RM',data:rmByJl,
      backgroundColor:COLORS.map(c=>c+'88'),borderColor:COLORS,borderWidth:2}]},
    options:{responsive:true,maintainAspectRatio:false,scales:{y:{min:0,max:3.5,grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},plugins:{legend:{display:false}}}
  });

  // RAS by role
  const roles=[...new Set(emps.map(e=>e.JobRole))].filter(Boolean);
  const rasRole = roles.map(r=>{ const e=emps.filter(x=>x.JobRole===r); return e.length?+(e.reduce((s,x)=>s+(+x.ReplacementAvailabilityScore||0),0)/e.length*100).toFixed(0):0; });
  const sortIdx = rasRole.map((_,i)=>i).sort((a,b)=>rasRole[a]-rasRole[b]);
  new Chart(document.getElementById('ch-ras-role'),{
    type:'bar',
    data:{labels:sortIdx.map(i=>roles[i]),
      datasets:[{label:'Mean RAS (%)',data:sortIdx.map(i=>rasRole[i]),
        backgroundColor:sortIdx.map(i=>rasRole[i]<50?'#f8717188':'#34d39988'),
        borderColor:sortIdx.map(i=>rasRole[i]<50?'#f87171':'#34d399'),borderWidth:2}]},
    options:{responsive:true,maintainAspectRatio:false,indexAxis:'y',
      scales:{x:{min:0,max:100,grid:{color:'rgba(255,255,255,.05)'},ticks:{callback:v=>v+'%'}},y:{grid:{display:false}}},
      plugins:{legend:{display:false}}}
  });

  // TtP by JL
  const ttpByJl = jls.map(jl=>{ const e=emps.filter(r=>+r.JobLevel===jl); return e.length?+(e[0].TtP_weeks):0; });
  new Chart(document.getElementById('ch-ttp-jl'),{
    type:'bar',
    data:{labels:jls.map(j=>'JL '+j),datasets:[{label:'Time-to-Productivity (weeks)',data:ttpByJl,backgroundColor:'#60a5fa88',borderColor:'#60a5fa',borderWidth:2}]},
    options:{responsive:true,maintainAspectRatio:false,scales:{y:{grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},plugins:{legend:{display:false}}}
  });

  // KCL by tenure
  const tenureBands=['<2yr','2-5yr','5-10yr','10-20yr','>20yr'];
  const kclBand = [
    emps.filter(e=>+e.YearsAtCompany<2).reduce((s,e)=>s+(+e.KnowledgeCapitalLoss||0),0)/Math.max(1,emps.filter(e=>+e.YearsAtCompany<2).length),
    emps.filter(e=>+e.YearsAtCompany>=2&&+e.YearsAtCompany<5).reduce((s,e)=>s+(+e.KnowledgeCapitalLoss||0),0)/Math.max(1,emps.filter(e=>+e.YearsAtCompany>=2&&+e.YearsAtCompany<5).length),
    emps.filter(e=>+e.YearsAtCompany>=5&&+e.YearsAtCompany<10).reduce((s,e)=>s+(+e.KnowledgeCapitalLoss||0),0)/Math.max(1,emps.filter(e=>+e.YearsAtCompany>=5&&+e.YearsAtCompany<10).length),
    emps.filter(e=>+e.YearsAtCompany>=10&&+e.YearsAtCompany<20).reduce((s,e)=>s+(+e.KnowledgeCapitalLoss||0),0)/Math.max(1,emps.filter(e=>+e.YearsAtCompany>=10&&+e.YearsAtCompany<20).length),
    emps.filter(e=>+e.YearsAtCompany>=20).reduce((s,e)=>s+(+e.KnowledgeCapitalLoss||0),0)/Math.max(1,emps.filter(e=>+e.YearsAtCompany>=20).length),
  ].map(v=>Math.round(v/1000));
  new Chart(document.getElementById('ch-kcl-tenure'),{
    type:'bar',
    data:{labels:tenureBands,datasets:[{label:'Mean KCL ($k)',data:kclBand,backgroundColor:'#a78bfa88',borderColor:'#a78bfa',borderWidth:2}]},
    options:{responsive:true,maintainAspectRatio:false,scales:{y:{grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},plugins:{legend:{display:false}}}
  });

  // Replacement table
  const top20 = [...emps].sort((a,b)=>(+a.rank_xerl||9999)-(+b.rank_xerl||9999)).slice(0,20);
  document.getElementById('rep-table').innerHTML=`<thead><tr>
    <th>XERL Rank</th><th>Emp#</th><th>Outcome</th><th>P(Att)</th>
    <th>Prod. Index</th><th>RM (FTEs needed)</th><th>TtP (weeks)</th><th>RAS (%)</th>
    <th>Knowledge Loss</th><th>Prod. Gap Cost</th><th>XERL ($)</th></tr></thead>
  <tbody>${top20.map(r=>`<tr onclick="document.querySelector('[onclick*=employees]') && nav('employees', document.querySelector('[onclick*=employees]')); showEmp(${r.EmployeeNumber})" style="cursor:pointer">
    <td style="font-weight:700;color:var(--a1)">#${r.rank_xerl}</td>
    <td style="font-weight:600">${r.EmployeeNumber}</td>
    <td style="color:${+r.Attrition===1?'#f87171':'#34d399'};font-weight:600">${+r.Attrition===1?'LEFT':'STAY'}</td>
    <td>${(+r.calibrated_probability).toFixed(3)}</td>
    <td>${(+r.ProductivityIndex).toFixed(3)}</td>
    <td><span class="badge ${+r.ReplacementMultiplier>=2?'b-high':(+r.ReplacementMultiplier>=1.5?'b-mod':'b-low')}">${(+r.ReplacementMultiplier).toFixed(2)}x</span></td>
    <td>${r.TtP_weeks}</td>
    <td style="color:${+r.ReplacementAvailabilityScore<0.5?'#f87171':+r.ReplacementAvailabilityScore<0.7?'#fbbf24':'#34d399'}">${(+r.ReplacementAvailabilityScore*100).toFixed(0)}%</td>
    <td>$${Math.round(+r.KnowledgeCapitalLoss||0).toLocaleString()}</td>
    <td>$${Math.round(+r.ProductivityGapCost||0).toLocaleString()}</td>
    <td style="font-weight:700;color:var(--a4)">$${Math.round(+r.ExtendedERL||0).toLocaleString()}</td>
  </tr>`).join('')}</tbody>`;
}

// ─── ORG IMPACT ───────────────────────────────────────────────────────────────
function buildOrgImpact() {
  const depts = D.departments;
  const emps = D.employees;
  const ok=[
    {l:'Total XERL Exposure',v:'$'+Math.round(emps.reduce((s,e)=>s+(+e.ExtendedERL||0),0)/1e6).toLocaleString()+'M',s:'Sum of all employee XERL',g:'linear-gradient(135deg,#f87171,#a78bfa)'},
    {l:'Expected Annual Loss',v:'$'+Math.round(emps.reduce((s,e)=>s+(+e.calibrated_probability||0)*(+e.ExtendedERL||0),0)/1e6).toFixed(1)+'M',s:'P(att) x XERL summed',g:'linear-gradient(135deg,#fbbf24,#fb923c)'},
    {l:'Highest OIS Dept',v:'Sales',s:'Highest cascade risk',g:'linear-gradient(135deg,#60a5fa,#38bdf8)'},
  ];
  document.getElementById('org-kpis').innerHTML = ok.map(k=>`
    <div class="kpi" style="--kgrad:${k.g}"><div class="kpi-label">${k.l}</div><div class="kpi-value">${k.v}</div><div class="kpi-sub">${k.s}</div></div>`).join('');

  new Chart(document.getElementById('ch-dept-xerl'),{
    type:'bar',
    data:{labels:depts.map(d=>d.Department.replace('Research & Development','R&D')),
      datasets:[
        {label:'Basic ERL ($M)',data:depts.map(d=>+(d.total_erl_basic/1e6).toFixed(2)),backgroundColor:'#60a5fa55',borderColor:'#60a5fa',borderWidth:2},
        {label:'XERL ($M)',data:depts.map(d=>+(d.total_xerl/1e6).toFixed(2)),backgroundColor:'#f8717155',borderColor:'#f87171',borderWidth:2},
      ]},
    options:{responsive:true,maintainAspectRatio:false,scales:{y:{grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},plugins:{legend:{position:'bottom'}}}
  });

  new Chart(document.getElementById('ch-dept-uplift'),{
    type:'bar',
    data:{labels:depts.map(d=>d.Department.replace('Research & Development','R&D')),
      datasets:[{label:'XERL/ERL Uplift',data:depts.map(d=>+(+d.xerl_uplift).toFixed(2)),
        backgroundColor:['#34d39988','#60a5fa88','#fbbf2488'],borderColor:['#34d399','#60a5fa','#fbbf24'],borderWidth:2}]},
    options:{responsive:true,maintainAspectRatio:false,scales:{y:{min:0,max:4,grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},plugins:{legend:{display:false}}}
  });

  document.getElementById('dept-table').innerHTML=`<thead><tr>
    <th>Department</th><th>Employees</th><th>Actual Leavers</th><th>Att. Rate</th>
    <th>Mean PI</th><th>Mean RM</th><th>Mean RAS</th><th>Mean TtP(wks)</th>
    <th>Basic ERL Total</th><th>XERL Total</th><th>XERL Uplift</th></tr></thead>
  <tbody>${depts.map(r=>`<tr>
    <td style="font-weight:700;color:var(--a1)">${r.Department}</td>
    <td>${r.total_employees}</td>
    <td style="color:#f87171;font-weight:600">${r.actual_leavers}</td>
    <td>${(+r.attrition_rate*100).toFixed(1)}%</td>
    <td>${(+r.mean_pi).toFixed(3)}</td>
    <td><span class="badge ${+r.mean_rm>=1.6?'b-high':+r.mean_rm>=1.4?'b-mod':'b-low'}">${(+r.mean_rm).toFixed(2)}x</span></td>
    <td>${(+r.mean_ras*100).toFixed(0)}%</td>
    <td>${(+r.mean_ttp).toFixed(0)} wks</td>
    <td>$${Math.round(+r.total_erl_basic).toLocaleString()}</td>
    <td style="font-weight:700;color:#f87171">$${Math.round(+r.total_xerl).toLocaleString()}</td>
    <td style="color:#fbbf24;font-weight:700">${(+r.xerl_uplift).toFixed(2)}x</td>
  </tr>`).join('')}</tbody>`;

  // Component chart by dept
  new Chart(document.getElementById('ch-dept-components'),{
    type:'bar',
    data:{labels:depts.map(d=>d.Department.replace('Research & Development','R&D')),
      datasets:[
        {label:'Recruitment x RM',data:depts.map(d=>Math.round(D.employees.filter(e=>e.Department===d.Department).reduce((s,e)=>s+(+e.XERL_base_cost||0),0)/1e3)),backgroundColor:'#60a5fa88',borderColor:'#60a5fa',borderWidth:2,stack:'a'},
        {label:'Productivity Gap',data:depts.map(d=>Math.round(D.employees.filter(e=>e.Department===d.Department).reduce((s,e)=>s+(+e.ProductivityGapCost||0),0)/1e3)),backgroundColor:'#34d39988',borderColor:'#34d399',borderWidth:2,stack:'a'},
        {label:'Knowledge Loss',data:depts.map(d=>Math.round(D.employees.filter(e=>e.Department===d.Department).reduce((s,e)=>s+(+e.KnowledgeCapitalLoss||0),0)/1e3)),backgroundColor:'#a78bfa88',borderColor:'#a78bfa',borderWidth:2,stack:'a'},
        {label:'Talent Scarcity',data:depts.map(d=>Math.round(D.employees.filter(e=>e.Department===d.Department).reduce((s,e)=>s+(+e.TalentScarcityPremium||0),0)/1e3)),backgroundColor:'#fbbf2488',borderColor:'#fbbf24',borderWidth:2,stack:'a'},
      ]},
    options:{responsive:true,maintainAspectRatio:false,scales:{y:{stacked:true,grid:{color:'rgba(255,255,255,.05)'},ticks:{callback:v=>v+'k'}},x:{grid:{display:false}}},plugins:{legend:{position:'bottom'}}}
  });
}

// ─── BUDGET ───────────────────────────────────────────────────────────────────
function buildBudget(){
  const b=D.budget; const budgets=b.map(r=>r.budget);
  const strats=[
    {key:'risk_only',label:'Risk-Only',color:'#60a5fa'},
    {key:'cost_only',label:'Cost-Only',color:'#fbbf24'},
    {key:'risk_x_cost_fixed',label:'Risk x Cost (Fixed)',color:'#34d399'},
    {key:'risk_x_cost_seniority',label:'Risk x Cost (Seniority)',color:'#a78bfa'},
    {key:'random',label:'Random Baseline',color:'#64748b'},
  ];
  new Chart(document.getElementById('ch-bud-leavers'),{
    type:'line',
    data:{labels:budgets,datasets:strats.map(s=>({label:s.label,
      data:b.map(r=>s.key==='random'?r.random_mean_leavers_captured:r[s.key+'_leavers_captured']),
      borderColor:s.color,backgroundColor:s.color+'22',borderWidth:s.key==='random'?1.5:2.5,
      borderDash:s.key==='random'?[4,4]:[],tension:.3,pointRadius:5,fill:false}))},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{x:{title:{display:true,text:'Intervention Budget'},grid:{color:'rgba(255,255,255,.05)'}},y:{title:{display:true,text:'Actual Leavers Captured'},grid:{color:'rgba(255,255,255,.05)'}}},
      plugins:{legend:{position:'bottom'}}}
  });
  new Chart(document.getElementById('ch-bud-cost'),{
    type:'line',
    data:{labels:budgets,datasets:strats.map(s=>({label:s.label,
      data:b.map(r=>s.key==='random'?(r.random_mean_cost_captured||0)/1e3:(r[s.key+'_cost_captured']||0)/1e3),
      borderColor:s.color,backgroundColor:s.color+'22',borderWidth:s.key==='random'?1.5:2.5,
      borderDash:s.key==='random'?[4,4]:[],tension:.3,pointRadius:5,fill:false}))},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{x:{title:{display:true,text:'Intervention Budget'},grid:{color:'rgba(255,255,255,.05)'}},y:{title:{display:true,text:'Cost Exposure ($k)'},grid:{color:'rgba(255,255,255,.05)'}}},
      plugins:{legend:{position:'bottom'}}}
  });
  document.getElementById('bud-table').innerHTML=`<thead><tr>
    <th>Budget</th><th>Risk-Only Leavers</th><th>RxC Fixed</th><th>Cost-Only</th><th>Random</th>
    <th>Risk-Only Cost</th><th>RxC Fixed Cost</th></tr></thead>
  <tbody>${b.map(r=>`<tr>
    <td style="font-weight:700;color:var(--a1)">Top ${r.budget}</td>
    <td style="color:#60a5fa;font-weight:600">${r.risk_only_leavers_captured} (${r.risk_only_pct_leavers_captured}%)</td>
    <td style="color:#34d399;font-weight:600">${r.risk_x_cost_fixed_leavers_captured} (${r.risk_x_cost_fixed_pct_leavers_captured}%)</td>
    <td>${r.cost_only_leavers_captured}</td>
    <td style="color:var(--text3)">${(+r.random_mean_leavers_captured).toFixed(1)}</td>
    <td>$${Math.round(r.risk_only_cost_captured||0).toLocaleString()}</td>
    <td style="color:#34d399">$${Math.round(r.risk_x_cost_fixed_cost_captured||0).toLocaleString()}</td>
  </tr>`).join('')}</tbody>`;
}

// ─── MODELS ───────────────────────────────────────────────────────────────────
function buildModels(){
  const mk=[
    {l:'Accuracy',v:(S.accuracy*100).toFixed(1)+'%',s:'OOF LR (Engineered)',g:'linear-gradient(135deg,#34d399,#60a5fa)'},
    {l:'ROC-AUC',v:S.roc_auc.toFixed(4),s:'Discrimination quality',g:'linear-gradient(135deg,#60a5fa,#a78bfa)'},
    {l:'PR-AUC (Primary)',v:S.pr_auc.toFixed(4),s:'Minority-class metric',g:'linear-gradient(135deg,#a78bfa,#60a5fa)'},
    {l:'F1 Score',v:S.f1.toFixed(4),s:'Precision-recall balance',g:'linear-gradient(135deg,#fbbf24,#fb923c)'},
    {l:'Brier Score',v:'0.0988',s:'Probability quality',g:'linear-gradient(135deg,#38bdf8,#60a5fa)'},
    {l:'ECE (calibrated)',v:'0.0224',s:'-72% from uncalibrated',g:'linear-gradient(135deg,#34d399,#a78bfa)'},
  ];
  document.getElementById('mdl-kpis').innerHTML = mk.map(k=>`
    <div class="kpi" style="--kgrad:${k.g}"><div class="kpi-label">${k.l}</div><div class="kpi-value">${k.v}</div><div class="kpi-sub">${k.s}</div></div>`).join('');

  const mdl = D.models;
  new Chart(document.getElementById('ch-mdl-bar'),{
    type:'bar',
    data:{labels:mdl.map(m=>m.model.replace('LogisticRegression','LR').replace('RandomForest','RF')),
      datasets:[
        {label:'Accuracy%',data:mdl.map(m=>(+m.accuracy*100).toFixed(1)),backgroundColor:'#60a5fa55',borderColor:'#60a5fa',borderWidth:2},
        {label:'ROC-AUC x100',data:mdl.map(m=>(+m.roc_auc*100).toFixed(1)),backgroundColor:'#34d39955',borderColor:'#34d399',borderWidth:2},
        {label:'PR-AUC x100',data:mdl.map(m=>(+m.pr_auc*100).toFixed(1)),backgroundColor:'#a78bfa55',borderColor:'#a78bfa',borderWidth:2},
      ]},
    options:{responsive:true,maintainAspectRatio:false,scales:{y:{min:40,max:100,grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},plugins:{legend:{position:'bottom'}}}
  });

  const cal=D.calibration;
  new Chart(document.getElementById('ch-cal'),{
    type:'bar',
    data:{labels:cal.map(r=>r.model),datasets:[
      {label:'Brier',data:cal.map(r=>+r.brier),backgroundColor:['#f8717155','#34d39955'],borderColor:['#f87171','#34d399'],borderWidth:2},
      {label:'ECE',data:cal.map(r=>+r.ece),backgroundColor:['#fbbf2455','#60a5fa55'],borderColor:['#fbbf24','#60a5fa'],borderWidth:2},
    ]},
    options:{responsive:true,maintainAspectRatio:false,scales:{y:{min:0,max:0.14,grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},plugins:{legend:{position:'bottom'}}}
  });

  document.getElementById('mdl-table').innerHTML=`<thead><tr>
    <th>Model</th><th>Accuracy</th><th>ROC-AUC</th><th>PR-AUC</th><th>Precision</th><th>Recall</th><th>F1</th><th>Brier</th><th>ECE</th></tr></thead>
  <tbody>${mdl.map((r,i)=>`<tr ${i===0?'style="background:rgba(96,165,250,.06)"':''}>
    <td style="font-weight:700;color:${i===0?'var(--a1)':'var(--text)'}">${r.model.replace('LogisticRegression','Logistic Regression')}</td>
    <td style="color:#34d399;font-weight:700">${(+r.accuracy*100).toFixed(2)}%</td>
    <td>${(+r.roc_auc).toFixed(4)}</td><td>${(+r.pr_auc).toFixed(4)}</td>
    <td>${(+r.precision).toFixed(4)}</td><td>${(+r.recall).toFixed(4)}</td>
    <td>${(+r.f1).toFixed(4)}</td><td>${(+r.brier).toFixed(4)}</td><td>${(+r.ece).toFixed(4)}</td>
  </tr>`).join('')}</tbody>`;
}

// ─── FAIRNESS ─────────────────────────────────────────────────────────────────
function buildFairness(){
  [{col:'Gender',id:'ch-f-gender'},{col:'MaritalStatus',id:'ch-f-marital'},{col:'AgeBand',id:'ch-f-age'}].forEach(g=>{
    const rows=D.fairness.filter(r=>r.group_col===g.col);
    new Chart(document.getElementById(g.id),{type:'bar',
      data:{labels:rows.map(r=>r.group_value),datasets:[
        {label:'Actual Attrition',data:rows.map(r=>+r.actual_attrition_rate),backgroundColor:'#f8717155',borderColor:'#f87171',borderWidth:2},
        {label:'Mean Pred. Prob',data:rows.map(r=>+r.mean_predicted_prob),backgroundColor:'#60a5fa55',borderColor:'#60a5fa',borderWidth:2},
        {label:'Selection Rate',data:rows.map(r=>+r.selection_rate_top50),backgroundColor:'#34d39955',borderColor:'#34d399',borderWidth:2},
      ]},
      options:{responsive:true,maintainAspectRatio:false,
        scales:{y:{min:0,max:0.4,grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},
        plugins:{legend:{position:'bottom',labels:{font:{size:10}}}}}
    });
  });
  document.getElementById('fair-table').innerHTML=`<thead><tr>
    <th>Group</th><th>Value</th><th>N</th><th>Actual Att.</th>
    <th>Mean Pred.</th><th>TPR</th><th>FPR</th><th>Selection (Top50)</th></tr></thead>
  <tbody>${D.fairness.map(r=>`<tr>
    <td style="font-weight:700;color:var(--a1)">${r.group_col}</td>
    <td>${r.group_value}</td><td>${r.n}</td>
    <td>${(+r.actual_attrition_rate*100).toFixed(1)}%</td>
    <td>${(+r.mean_predicted_prob).toFixed(3)}</td>
    <td>${(+(r.true_positive_rate||0)*100).toFixed(1)}%</td>
    <td>${(+(r.false_positive_rate||0)*100).toFixed(1)}%</td>
    <td>${(+r.selection_rate_top50*100).toFixed(1)}%</td>
  </tr>`).join('')}</tbody>`;
}

// ─── RESEARCH GAPS ────────────────────────────────────────────────────────────
function buildGaps(){
  const gaps = [
    {n:1,title:'Productivity-Weighted Cost Model',
     desc:'Prior attrition cost models (Boushey & Glynn 2012, SHRM 2017) use salary as a proxy for employee value, implicitly treating compensation as equivalent to productivity. We introduce a Productivity Index (PI) composed of PerformanceRating, JobLevel, JobInvolvement, role mastery, and recency of recognition -- replacing the salary-only assumption with a researcher-constructed composite.',
     finding:'XERL mean = 2.08x basic ERL. The uplift confirms that salary-only models systematically underestimate replacement cost for high-PI employees.'},
    {n:2,title:'Replacement Multiplier (RM): Formalising "How Many New Hires?"',
     desc:'Existing literature acknowledges that senior employees are harder to replace but does not formally model how many new hires (FTEs) are needed to collectively match one departing employee\'s output. We introduce RM as a seniority-tiered parameter: JL1=1.0x, JL2=1.25x, JL3=1.5x, JL4=2.0x, JL5=2.5x, adjusted for tenure and performance rating.',
     finding:'Mean RM=1.49x. 13.3% of employees have RM>=2.0 (need 2+ replacements). These are disproportionately concentrated in Research & Development.'},
    {n:3,title:'Time-to-Productivity Gap Cost (PGC)',
     desc:'New employees operate at reduced productivity during onboarding. Prior cost models approximate this as a fixed overhead. We model it explicitly: TtP = weeks to 80% proficiency (by JobLevel: 12-64 weeks), with a 40% average productivity deficit during that window. PGC = (AnnualSalary x PI / 52) x TtP x PDR x RM.',
     finding:'Mean PGC=$29,417. This is the largest single hidden cost for senior employees (JL5: TtP=64 weeks x high salary x high PI).'},
    {n:4,title:'Knowledge Capital Loss (KCL): Quantifying Institutional Memory',
     desc:'DeLong (2004) and Beazley et al. (2002) identify knowledge loss as a major hidden cost but provide no quantification framework for ML pipelines. We introduce KCL = AnnualSalary x KnowledgeFactor(YearsAtCompany) x PI x JobLevel/5, where KF ranges from 0.05 (<2yr) to 0.70 (>20yr).',
     finding:'Mean KCL=$11,992. Employees with >20 years at company carry up to $140,752 in knowledge capital loss -- invisible to salary-only models.'},
    {n:5,title:'Replacement Availability Score (RAS): Talent Scarcity Modelling',
     desc:'No prior ML-based attrition cost model accounts for the probability of finding an equivalent replacement. We operationalise RAS as a function of role rarity (within-dataset frequency), JobLevel (senior=scarcer), and PerformanceRating (excellent performers are rare). Talent Scarcity Premium = (1-RAS) x AnnualSalary x PI.',
     finding:'Mean RAS=77.2%. Roles with RAS<50% (Research Director, Manager) carry $16,775+ average scarcity premium. This shifts XERL rankings materially for specialist roles.'},
    {n:6,title:'Extended ERL Re-Ranks Materially vs Basic ERL',
     desc:'XERL integrates all five components: XERL = P(att) x [Cost x RM + PGC + KCL + TSP]. We test RQ6: does XERL select a materially different Top-K intervention set from basic ERL? Evaluated using Spearman rank correlation and top-K overlap analysis.',
     finding:'Spearman r=0.9131 (correlated but not identical). Top-10 overlap=5/10 (50% different). XERL elevates high-tenure, high-performance, specialist employees that basic ERL systematically undervalues.'},
  ];
  document.getElementById('gap-cards').innerHTML = gaps.map(g=>`
    <div class="gap-card">
      <div class="gap-title"><div class="gap-num">${g.n}</div>${g.title}</div>
      <div class="gap-desc">${g.desc}</div>
      <div class="gap-finding">Research Finding: ${g.finding}</div>
    </div>`).join('');
}

// ─── INIT ─────────────────────────────────────────────────────────────────────
buildOverview();
buildEmployees();
buildReplacement();
buildOrgImpact();
buildBudget();
buildModels();
buildFairness();
buildGaps();
"""

# Assemble
HTML = ("<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'/>"
        "<meta name='viewport' content='width=device-width,initial-scale=1.0'/>"
        "<title>RetainIQ - Organizational Attrition Intelligence Platform</title>"
        "<meta name='description' content='RetainIQ: Extended Cost-Weighted ML Framework for Employee Attrition with Replacement Multiplier, Knowledge Loss, and Productivity Analysis'/>"
        "<script src='https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'></script>"
        "<style>" + CSS + "</style></head><body>"
        "<div class='wrapper'>"
        + BODY +
        "</div>"
        "<script>window.__DATA__ = " + DATA_JSON + ";\n" + JS + "</script>"
        "</body></html>")

out = rc.ROOT / "retainiq_app.html"
out.write_text(HTML, encoding="utf-8")
print("[saved] retainiq_app.html ->", out)
print("Open: file:///"+str(out).replace("\\","/"))
