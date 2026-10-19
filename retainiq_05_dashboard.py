"""
retainiq_05_dashboard.py
========================
Generates dashboard.html — self-contained HTML UI for RetainIQ results.
All CSV data is embedded as JSON. Open dashboard.html in any browser.

Run:
    python retainiq_05_dashboard.py

DISCLAIMER: RetainIQ is a research prototype on the IBM HR Analytics
SYNTHETIC dataset. NOT for real employment decisions.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import retainiq_common as rc
import pandas as pd
import numpy as np

# ─────────────────────────── Load data ───────────────────────────────────────
def load(name):
    p = rc.OUT_DIR / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

model_df    = load("baseline_model_comparison.csv")
budget_df   = load("budget_results.csv")
fairness_df = load("fairness_audit.csv")
priority_df = load("employee_priority.csv")
ablation_df = load("feature_ablation.csv")
cal_df      = load("calibration_results.csv")
oof_df      = load("baseline_oof_predictions.csv")
raw_df      = pd.read_csv(rc.DATA_DIR / "WA_Fn-UseC_-HR-Employee-Attrition.csv")
raw_df["Attrition"] = raw_df["Attrition"].map({"Yes": 1, "No": 0})

# ─────────────────────────── Build master employee frame ─────────────────────
master = raw_df.copy()
if not oof_df.empty:
    master = master.merge(oof_df[["EmployeeNumber","calibrated_probability"]],
                          on="EmployeeNumber", how="left")
if not priority_df.empty:
    master = master.merge(
        priority_df[["EmployeeNumber","AnnualSalary",
                     "replacement_cost_fixed_plus_salary",
                     "ERL_fixed_plus_salary","ERL_seniority_scaled"]],
        on="EmployeeNumber", how="left")

def risk_label(p):
    if pd.isna(p): return "UNKNOWN"
    return "HIGH" if p >= 0.60 else ("MODERATE" if p >= 0.35 else "LOW")

if "calibrated_probability" in master.columns:
    master["risk_category"] = master["calibrated_probability"].apply(risk_label)
    master["rank_erl"]  = master["ERL_fixed_plus_salary"].rank(ascending=False, method="first").astype("Int64")
    master["rank_risk"] = master["calibrated_probability"].rank(ascending=False, method="first").astype("Int64")

# ─────────────────────────── Serialise ───────────────────────────────────────
def to_json(df, cols=None):
    if df is None or df.empty: return "[]"
    d = df[cols].copy() if cols else df.copy()
    return d.fillna("").to_json(orient="records")

eng = model_df[model_df["feature_set"]=="engineered"] if not model_df.empty else pd.DataFrame()
emp_cols = ["EmployeeNumber","Attrition","calibrated_probability",
            "MonthlyIncome","AnnualSalary","JobLevel","Department",
            "JobRole","OverTime","YearsAtCompany","TotalWorkingYears",
            "ERL_fixed_plus_salary","rank_erl","rank_risk","risk_category"]

data = {
    "models":   json.loads(to_json(eng,
                    ["model","roc_auc","pr_auc","precision","recall","f1","accuracy","brier","ece"])),
    "ablation": json.loads(to_json(ablation_df,
                    ["model","feature_set","roc_auc","pr_auc","f1","accuracy","brier","ece"])),
    "budget":   json.loads(to_json(budget_df)),
    "fairness": json.loads(to_json(fairness_df)),
    "calibration": json.loads(to_json(cal_df)),
    "employees": json.loads(to_json(master, [c for c in emp_cols if c in master.columns])),
    "summary": {
        "total_employees": int(len(raw_df)),
        "total_leavers":   int(raw_df["Attrition"].sum()),
        "attrition_rate":  round(raw_df["Attrition"].mean()*100, 1),
        "final_model":     "Logistic Regression",
        "pr_auc":  0.5983, "roc_auc":  0.8236,
        "accuracy": 0.8748, "f1": 0.4065,
        "precision":0.8630, "recall": 0.2658,
        "brier":   0.0988, "ece": 0.0224,
    }
}
DATA_JSON = json.dumps(data, default=str)

# ─────────────────────────── HTML ────────────────────────────────────────────
# JavaScript uses ${} template literals and {} object literals.
# We write the HTML as a regular (non-f-string) string, then inject the JSON.
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
:root{--bg:#0a0e1a;--bg2:#111827;--bg3:#1a2236;--border:rgba(99,179,237,.15);
--accent1:#63b3ed;--accent2:#68d391;--accent3:#f6ad55;--accent4:#fc8181;
--accent5:#b794f4;--text:#e2e8f0;--text2:#94a3b8;--glass:rgba(255,255,255,.04);
--glassborder:rgba(255,255,255,.08);}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;}
body::before{content:'';position:fixed;top:-50%;left:-50%;width:200%;height:200%;
background:radial-gradient(ellipse at 20% 20%,rgba(99,179,237,.06) 0%,transparent 50%),
radial-gradient(ellipse at 80% 80%,rgba(104,211,145,.05) 0%,transparent 50%),
radial-gradient(ellipse at 50% 50%,rgba(183,148,244,.04) 0%,transparent 60%);
z-index:0;pointer-events:none;}
.wrapper{position:relative;z-index:1;}
header{background:linear-gradient(135deg,rgba(99,179,237,.12),rgba(104,211,145,.08));
border-bottom:1px solid var(--border);padding:0 2rem;backdrop-filter:blur(20px);
position:sticky;top:0;z-index:100;}
.header-inner{max-width:1400px;margin:0 auto;display:flex;align-items:center;
justify-content:space-between;height:64px;}
.logo{display:flex;align-items:center;gap:.75rem;}
.logo-icon{width:36px;height:36px;border-radius:10px;
background:linear-gradient(135deg,#63b3ed,#68d391);
display:flex;align-items:center;justify-content:center;
font-weight:800;font-size:.85rem;color:#0a0e1a;}
.logo-text{font-size:1.2rem;font-weight:700;letter-spacing:-.5px;}
.logo-text span{color:#68d391;}
.badge{background:rgba(252,129,129,.15);color:#fc8181;
border:1px solid rgba(252,129,129,.3);border-radius:99px;
font-size:.65rem;font-weight:600;padding:.2rem .7rem;letter-spacing:.5px;text-transform:uppercase;}
nav{max-width:1400px;margin:0 auto;display:flex;gap:.25rem;padding:0;
border-bottom:1px solid var(--glassborder);background:var(--bg);}
nav button{background:none;border:none;cursor:pointer;color:var(--text2);
font-family:'Inter',sans-serif;font-size:.85rem;font-weight:500;
padding:.9rem 1.25rem;border-bottom:2px solid transparent;transition:all .2s;}
nav button:hover{color:var(--text);}
nav button.active{color:var(--accent1);border-bottom-color:var(--accent1);}
main{max-width:1400px;margin:0 auto;padding:2rem;}
.tab-panel{display:none;animation:fadeIn .3s ease;}
.tab-panel.active{display:block;}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1rem;margin-bottom:2rem;}
.stat-card{background:var(--glass);border:1px solid var(--glassborder);border-radius:16px;
padding:1.25rem 1.5rem;position:relative;overflow:hidden;transition:transform .2s,border-color .2s;}
.stat-card:hover{transform:translateY(-2px);border-color:rgba(99,179,237,.3);}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--grad);}
.stat-label{font-size:.7rem;font-weight:600;color:var(--text2);text-transform:uppercase;
letter-spacing:.8px;margin-bottom:.5rem;}
.stat-value{font-size:1.8rem;font-weight:800;line-height:1;}
.stat-sub{font-size:.72rem;color:var(--text2);margin-top:.3rem;}
.section-title{font-size:1.05rem;font-weight:700;margin-bottom:1rem;display:flex;align-items:center;gap:.5rem;}
.dot{width:8px;height:8px;border-radius:50%;background:var(--accent1);box-shadow:0 0 8px var(--accent1);}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:1.5rem;}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.5rem;margin-bottom:1.5rem;}
@media(max-width:900px){.grid-2,.grid-3{grid-template-columns:1fr;}}
.card{background:var(--glass);border:1px solid var(--glassborder);border-radius:16px;padding:1.5rem;margin-bottom:0;}
.chart-wrap{position:relative;height:260px;}
.chart-wrap-tall{position:relative;height:320px;}
.table-wrap{overflow-x:auto;border-radius:12px;}
table{width:100%;border-collapse:collapse;font-size:.82rem;}
th{background:rgba(99,179,237,.08);color:var(--accent1);font-weight:600;font-size:.72rem;
text-transform:uppercase;letter-spacing:.6px;padding:.75rem 1rem;text-align:left;
border-bottom:1px solid var(--glassborder);}
td{padding:.65rem 1rem;border-bottom:1px solid rgba(255,255,255,.04);color:var(--text);}
tr:hover td{background:rgba(255,255,255,.03);}
tr:last-child td{border-bottom:none;}
.risk-badge{display:inline-block;font-size:.68rem;font-weight:700;
padding:.2rem .6rem;border-radius:99px;text-transform:uppercase;letter-spacing:.5px;}
.risk-HIGH{background:rgba(252,129,129,.15);color:#fc8181;border:1px solid rgba(252,129,129,.3);}
.risk-MODERATE{background:rgba(246,173,85,.15);color:#f6ad55;border:1px solid rgba(246,173,85,.3);}
.risk-LOW{background:rgba(104,211,145,.15);color:#68d391;border:1px solid rgba(104,211,145,.3);}
.att-yes{color:#fc8181;font-weight:600;}
.att-no{color:#68d391;}
.search-bar{display:flex;gap:.75rem;margin-bottom:1.5rem;flex-wrap:wrap;}
.search-bar input,.search-bar select{background:var(--glass);border:1px solid var(--glassborder);
border-radius:10px;padding:.6rem 1rem;color:var(--text);font-family:'Inter',sans-serif;
font-size:.85rem;outline:none;transition:border-color .2s;flex:1;min-width:180px;}
.search-bar input:focus,.search-bar select:focus{border-color:var(--accent1);}
.search-bar select option{background:#1a2236;}
#emp-card{background:linear-gradient(135deg,rgba(99,179,237,.08),rgba(104,211,145,.05));
border:1px solid rgba(99,179,237,.2);border-radius:16px;padding:1.5rem;
margin-bottom:1.5rem;display:none;animation:fadeIn .3s ease;}
.emp-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem;}
.emp-name{font-size:1.1rem;font-weight:700;}
.emp-sub{font-size:.8rem;color:var(--text2);margin-top:.2rem;}
.emp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-top:1rem;}
.emp-item .lbl{font-size:.68rem;color:var(--text2);text-transform:uppercase;letter-spacing:.6px;margin-bottom:.2rem;}
.emp-item .val{font-size:1rem;font-weight:600;}
.metric-row{margin-bottom:.75rem;}
.metric-row .m-header{display:flex;justify-content:space-between;margin-bottom:.3rem;}
.metric-row .m-label{font-size:.78rem;color:var(--text2);}
.metric-row .m-value{font-size:.78rem;font-weight:700;color:var(--text);}
.bar-track{height:6px;background:rgba(255,255,255,.08);border-radius:99px;overflow:hidden;}
.bar-fill{height:100%;border-radius:99px;}
.disclaimer{background:rgba(246,173,85,.07);border:1px solid rgba(246,173,85,.2);
border-radius:10px;padding:.75rem 1rem;font-size:.75rem;color:#f6ad55;
margin-bottom:1.5rem;line-height:1.5;}
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:rgba(99,179,237,.3);border-radius:99px;}
"""

JS = r"""
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter',sans-serif";

function switchTab(id,btn){
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab-'+id).classList.add('active');
  btn.classList.add('active');
}

const D = window.__DATA__;
const s = D.summary;

// ── Overview ──────────────────────────────────────────────────────────────────
function buildOverview(){
  const cards=[
    {label:'Employees', value:s.total_employees.toLocaleString(), sub:'IBM HR Benchmark (Synthetic)', grad:'linear-gradient(90deg,#63b3ed,#b794f4)'},
    {label:'Actual Leavers', value:s.total_leavers.toLocaleString(), sub:s.attrition_rate+'% attrition rate', grad:'linear-gradient(90deg,#fc8181,#f6ad55)'},
    {label:'Accuracy', value:(s.accuracy*100).toFixed(1)+'%', sub:'OOF · Logistic Regression', grad:'linear-gradient(90deg,#68d391,#63b3ed)'},
    {label:'ROC-AUC', value:s.roc_auc.toFixed(4), sub:'Discrimination quality', grad:'linear-gradient(90deg,#b794f4,#63b3ed)'},
    {label:'PR-AUC', value:s.pr_auc.toFixed(4), sub:'Primary metric (class imbalance)', grad:'linear-gradient(90deg,#f6ad55,#fc8181)'},
    {label:'F1 Score', value:s.f1.toFixed(4), sub:'Minority-class balance', grad:'linear-gradient(90deg,#68d391,#b794f4)'},
    {label:'Brier Score', value:s.brier.toFixed(4), sub:'Probability quality', grad:'linear-gradient(90deg,#76e4f7,#63b3ed)'},
    {label:'ECE (Post-cal.)', value:s.ece.toFixed(4), sub:'Calibration error (-72% after cal.)', grad:'linear-gradient(90deg,#68d391,#f6ad55)'},
  ];
  document.getElementById('stats-grid').innerHTML=cards.map(c=>`
    <div class="stat-card" style="--grad:${c.grad}">
      <div class="stat-label">${c.label}</div>
      <div class="stat-value">${c.value}</div>
      <div class="stat-sub">${c.sub}</div>
    </div>`).join('');

  new Chart(document.getElementById('ch-target'),{
    type:'doughnut',
    data:{labels:['Stayed','Left (Attrition)'],
      datasets:[{data:[s.total_employees-s.total_leavers, s.total_leavers],
        backgroundColor:['#68d391','#fc8181'],borderColor:'#0a0e1a',borderWidth:3}]},
    options:{plugins:{legend:{position:'bottom'},tooltip:{callbacks:{
      label:c=>` ${c.label}: ${c.parsed} (${(c.parsed/s.total_employees*100).toFixed(1)}%)`
    }}},cutout:'65%'}
  });

  const eng=D.models;
  new Chart(document.getElementById('ch-accuracy'),{
    type:'bar',
    data:{labels:eng.map(m=>m.model.replace('LogisticRegression','LR').replace('RandomForest','RF')),
      datasets:[
        {label:'Accuracy %',data:eng.map(m=>(+m.accuracy*100).toFixed(2)),backgroundColor:'#63b3ed55',borderColor:'#63b3ed',borderWidth:2},
        {label:'ROC-AUC x100',data:eng.map(m=>(+m.roc_auc*100).toFixed(2)),backgroundColor:'#68d39155',borderColor:'#68d391',borderWidth:2},
        {label:'PR-AUC x100',data:eng.map(m=>(+m.pr_auc*100).toFixed(2)),backgroundColor:'#b794f455',borderColor:'#b794f4',borderWidth:2},
      ]},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{y:{min:40,max:100,grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},
      plugins:{legend:{position:'bottom'}}}
  });

  const metrics=[
    {label:'Accuracy',value:s.accuracy,color:'#63b3ed'},
    {label:'ROC-AUC',value:s.roc_auc,color:'#68d391'},
    {label:'PR-AUC (primary)',value:s.pr_auc,color:'#b794f4'},
    {label:'F1 Score',value:s.f1,color:'#f6ad55'},
    {label:'Recall',value:s.recall,color:'#fc8181'},
    {label:'Precision',value:s.precision,color:'#76e4f7'},
  ];
  document.getElementById('metric-bars').innerHTML=metrics.map(m=>`
    <div class="metric-row">
      <div class="m-header"><span class="m-label">${m.label}</span><span class="m-value">${m.value.toFixed(4)}</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:${(m.value*100).toFixed(1)}%;background:${m.color}"></div></div>
    </div>`).join('');

  const abl=D.ablation;
  const mods=[...new Set(abl.map(r=>r.model))];
  new Chart(document.getElementById('ch-ablation'),{
    type:'bar',
    data:{labels:mods.map(m=>m.replace('LogisticRegression','LR').replace('RandomForest','RF')),
      datasets:[
        {label:'Baseline',data:mods.map(m=>{const r=abl.find(a=>a.model===m&&a.feature_set==='baseline');return r?+r.pr_auc:0;}),backgroundColor:'#63b3ed55',borderColor:'#63b3ed',borderWidth:2},
        {label:'Engineered',data:mods.map(m=>{const r=abl.find(a=>a.model===m&&a.feature_set==='engineered');return r?+r.pr_auc:0;}),backgroundColor:'#68d39155',borderColor:'#68d391',borderWidth:2},
      ]},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{y:{min:0.3,max:0.7,grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},
      plugins:{legend:{position:'bottom'}}}
  });
}

// ── Models ────────────────────────────────────────────────────────────────────
function buildModels(){
  const cols=['model','accuracy','roc_auc','pr_auc','precision','recall','f1','brier','ece'];
  const labels=['Model','Accuracy','ROC-AUC','PR-AUC','Precision','Recall','F1','Brier','ECE'];
  document.getElementById('model-table').innerHTML=`<thead><tr>${labels.map(l=>`<th>${l}</th>`).join('')}</tr></thead>
  <tbody>${D.models.map((r,i)=>`<tr ${i===0?'style="background:rgba(99,179,237,.06)"':''}>
    ${cols.map(c=>{
      const v=r[c];
      if(c==='model') return `<td style="font-weight:600;color:${i===0?'#63b3ed':'var(--text)'}">${v.replace('LogisticRegression','Logistic Regression')}</td>`;
      if(c==='accuracy') return `<td style="color:#68d391;font-weight:700">${(+v*100).toFixed(2)}%</td>`;
      return `<td>${(+v).toFixed(4)}</td>`;
    }).join('')}
  </tr>`).join('')}</tbody>`;

  const mods=D.models.map(m=>m.model.replace('LogisticRegression','LR').replace('RandomForest','RF'));
  new Chart(document.getElementById('ch-models-bar'),{
    type:'bar',data:{labels:mods,datasets:[
      {label:'PR-AUC',data:D.models.map(m=>+m.pr_auc),backgroundColor:'#b794f455',borderColor:'#b794f4',borderWidth:2},
      {label:'ROC-AUC',data:D.models.map(m=>+m.roc_auc),backgroundColor:'#63b3ed55',borderColor:'#63b3ed',borderWidth:2},
    ]},
    options:{responsive:true,maintainAspectRatio:false,scales:{y:{min:0,max:1,grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},plugins:{legend:{position:'bottom'}}}
  });
  new Chart(document.getElementById('ch-brier'),{
    type:'bar',data:{labels:mods,datasets:[
      {label:'Brier Score (lower=better)',data:D.models.map(m=>+m.brier),backgroundColor:'#f6ad5555',borderColor:'#f6ad55',borderWidth:2},
      {label:'ECE (lower=better)',data:D.models.map(m=>+m.ece),backgroundColor:'#fc818155',borderColor:'#fc8181',borderWidth:2},
    ]},
    options:{responsive:true,maintainAspectRatio:false,scales:{y:{min:0,max:0.15,grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},plugins:{legend:{position:'bottom'}}}
  });

  const ac=['model','feature_set','roc_auc','pr_auc','f1','accuracy','brier','ece'];
  const al=['Model','Feature Set','ROC-AUC','PR-AUC','F1','Accuracy','Brier','ECE'];
  document.getElementById('ablation-table').innerHTML=`<thead><tr>${al.map(l=>`<th>${l}</th>`).join('')}</tr></thead>
  <tbody>${D.ablation.map(r=>`<tr>${ac.map(c=>{
    const v=r[c];
    if(c==='model') return `<td style="font-weight:600">${v.replace('LogisticRegression','LR').replace('RandomForest','RF')}</td>`;
    if(c==='feature_set') return `<td><span style="background:${v==='engineered'?'rgba(104,211,145,.15)':'rgba(99,179,237,.1)'};color:${v==='engineered'?'#68d391':'#63b3ed'};padding:.15rem .5rem;border-radius:5px;font-size:.72rem">${v}</span></td>`;
    if(c==='accuracy') return `<td style="font-weight:600">${(+v*100).toFixed(2)}%</td>`;
    return `<td>${(+v).toFixed(4)}</td>`;
  }).join('')}</tr>`).join('')}</tbody>`;
}

// ── Budget ────────────────────────────────────────────────────────────────────
function buildBudget(){
  const b=D.budget;
  const budgets=b.map(r=>r.budget);
  const strats=[
    {key:'risk_only',label:'Risk-Only',color:'#63b3ed'},
    {key:'cost_only',label:'Cost-Only',color:'#f6ad55'},
    {key:'risk_x_cost_fixed',label:'Risk x Cost (Fixed)',color:'#68d391'},
    {key:'risk_x_cost_seniority',label:'Risk x Cost (Seniority)',color:'#b794f4'},
    {key:'random',label:'Random Baseline',color:'#94a3b8'},
  ];
  new Chart(document.getElementById('ch-budget-leavers'),{
    type:'line',
    data:{labels:budgets,datasets:strats.map(s=>({
      label:s.label,
      data:b.map(r=>s.key==='random'?r.random_mean_leavers_captured:r[s.key+'_leavers_captured']),
      borderColor:s.color,backgroundColor:s.color+'22',
      borderWidth:s.key==='random'?1.5:2.5,
      borderDash:s.key==='random'?[4,4]:[],
      tension:.3,pointRadius:5,fill:false,
    }))},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{x:{title:{display:true,text:'Intervention Budget (employees)'},grid:{color:'rgba(255,255,255,.05)'}},
              y:{title:{display:true,text:'Actual Leavers Captured'},grid:{color:'rgba(255,255,255,.05)'}}},
      plugins:{legend:{position:'bottom'}}}
  });
  new Chart(document.getElementById('ch-budget-cost'),{
    type:'line',
    data:{labels:budgets,datasets:strats.map(s=>({
      label:s.label,
      data:b.map(r=>s.key==='random'?(r.random_mean_cost_captured||0)/1000:(r[s.key+'_cost_captured']||0)/1000),
      borderColor:s.color,backgroundColor:s.color+'22',
      borderWidth:s.key==='random'?1.5:2.5,borderDash:s.key==='random'?[4,4]:[],
      tension:.3,pointRadius:5,fill:false,
    }))},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{x:{title:{display:true,text:'Intervention Budget'},grid:{color:'rgba(255,255,255,.05)'}},
              y:{title:{display:true,text:'Cost Exposure Captured ($k)'},grid:{color:'rgba(255,255,255,.05)'}}},
      plugins:{legend:{position:'bottom'}}}
  });
  document.getElementById('budget-table').innerHTML=`<thead><tr>
    <th>Budget</th><th>Risk-Only Leavers</th><th>RxC Fixed Leavers</th>
    <th>Cost-Only Leavers</th><th>Random Baseline</th>
    <th>Risk-Only Cost ($)</th><th>RxC Fixed Cost ($)</th></tr></thead>
  <tbody>${b.map(r=>`<tr>
    <td style="font-weight:700;color:var(--accent1)">Top ${r.budget}</td>
    <td style="color:#63b3ed;font-weight:600">${r.risk_only_leavers_captured} (${r.risk_only_pct_leavers_captured}%)</td>
    <td style="color:#68d391;font-weight:600">${r.risk_x_cost_fixed_leavers_captured} (${r.risk_x_cost_fixed_pct_leavers_captured}%)</td>
    <td>${r.cost_only_leavers_captured}</td>
    <td style="color:#94a3b8">${(+r.random_mean_leavers_captured).toFixed(1)}</td>
    <td>$${Math.round(r.risk_only_cost_captured||0).toLocaleString()}</td>
    <td style="color:#68d391">$${Math.round(r.risk_x_cost_fixed_cost_captured||0).toLocaleString()}</td>
  </tr>`).join('')}</tbody>`;
}

// ── Employees ─────────────────────────────────────────────────────────────────
function renderEmpTable(emps){
  const t=document.getElementById('emp-table');
  if(!emps.length){t.innerHTML='<tbody><tr><td colspan="9" style="text-align:center;padding:2rem;color:var(--text2)">No results.</td></tr></tbody>';return;}
  t.innerHTML=`<thead><tr><th>ERL Rank</th><th>Risk Rank</th><th>Emp #</th><th>Outcome</th>
    <th>P(Att)</th><th>Annual Salary</th><th>ERL ($)</th><th>Risk</th><th>Dept / Role</th></tr></thead>
  <tbody>${emps.slice(0,60).map(r=>`<tr onclick="showEmp(${r.EmployeeNumber})" style="cursor:pointer">
    <td style="font-weight:700;color:var(--accent1)">#${r.rank_erl||'—'}</td>
    <td style="color:var(--text2)">#${r.rank_risk||'—'}</td>
    <td style="font-weight:600">${r.EmployeeNumber}</td>
    <td class="${r.Attrition==1?'att-yes':'att-no'}">${r.Attrition==1?'LEFT':'STAY'}</td>
    <td>${(+r.calibrated_probability).toFixed(3)}</td>
    <td>$${Math.round(+(r.AnnualSalary||r.MonthlyIncome*12)||0).toLocaleString()}</td>
    <td style="font-weight:600">$${Math.round(+(r.ERL_fixed_plus_salary||0)).toLocaleString()}</td>
    <td><span class="risk-badge risk-${r.risk_category}">${r.risk_category}</span></td>
    <td style="font-size:.78rem;color:var(--text2)">${(r.Department||'').replace('Research & Development','R&D')} / ${r.JobRole||''}</td>
  </tr>`).join('')}</tbody>`;
}

function showEmp(id){
  const e=D.employees.find(r=>+r.EmployeeNumber===+id);
  if(!e) return;
  const card=document.getElementById('emp-card');
  card.style.display='block';
  document.getElementById('ec-name').textContent='Employee #'+e.EmployeeNumber;
  document.getElementById('ec-role').textContent=(e.JobRole||'')+'  ·  '+(e.Department||'')+'  ·  Level '+(e.JobLevel||'');
  const rb=document.getElementById('ec-risk');
  rb.textContent=e.risk_category; rb.className='risk-badge risk-'+e.risk_category;
  document.getElementById('ec-prob').textContent=(+e.calibrated_probability).toFixed(3);
  document.getElementById('ec-rrank').textContent='#'+(e.rank_risk||'—')+' of 1,470';
  document.getElementById('ec-erank').textContent='#'+(e.rank_erl||'—')+' of 1,470';
  document.getElementById('ec-income').textContent='$'+Math.round(+e.MonthlyIncome||0).toLocaleString()+' / mo';
  document.getElementById('ec-salary').textContent='$'+Math.round(+(e.AnnualSalary||+e.MonthlyIncome*12)||0).toLocaleString();
  document.getElementById('ec-erl').textContent='$'+Math.round(+(e.ERL_fixed_plus_salary||0)).toLocaleString();
  document.getElementById('ec-level').textContent=e.JobLevel||'—';
  document.getElementById('ec-years').textContent=e.YearsAtCompany||'—';
  document.getElementById('ec-ot').textContent=e.OverTime||'—';
  const act=document.getElementById('ec-actual');
  act.textContent=e.Attrition==1?'Left (Leaver)':'Stayed';
  act.className=e.Attrition==1?'val att-yes':'val att-no';
  card.scrollIntoView({behavior:'smooth',block:'start'});
}

function filterEmp(){
  const idv=+document.getElementById('emp-id-input').value||0;
  if(idv){showEmp(idv);return;}
  const dept=document.getElementById('emp-dept').value;
  const risk=document.getElementById('emp-risk').value;
  const sort=document.getElementById('emp-sort').value;
  let emps=[...D.employees];
  if(dept) emps=emps.filter(e=>e.Department===dept);
  if(risk) emps=emps.filter(e=>e.risk_category===risk);
  emps.sort((a,b)=>sort==='erl'?(+a.rank_erl||9999)-(+b.rank_erl||9999):(+a.rank_risk||9999)-(+b.rank_risk||9999));
  renderEmpTable(emps);
}

function buildEmployees(){
  ['emp-id-input','emp-dept','emp-risk','emp-sort'].forEach(id=>{
    document.getElementById(id).addEventListener('input',filterEmp);
    document.getElementById(id).addEventListener('change',filterEmp);
  });
  renderEmpTable([...D.employees].sort((a,b)=>(+a.rank_erl||9999)-(+b.rank_erl||9999)));
}

// ── Fairness ──────────────────────────────────────────────────────────────────
function buildFairness(){
  [{col:'Gender',id:'ch-fair-gender'},{col:'MaritalStatus',id:'ch-fair-marital'},{col:'AgeBand',id:'ch-fair-age'}].forEach(g=>{
    const rows=D.fairness.filter(r=>r.group_col===g.col);
    new Chart(document.getElementById(g.id),{
      type:'bar',
      data:{labels:rows.map(r=>r.group_value),datasets:[
        {label:'Actual Attrition Rate',data:rows.map(r=>+r.actual_attrition_rate),backgroundColor:'#fc818155',borderColor:'#fc8181',borderWidth:2},
        {label:'Mean Pred. Prob',data:rows.map(r=>+r.mean_predicted_prob),backgroundColor:'#63b3ed55',borderColor:'#63b3ed',borderWidth:2},
        {label:'Selection Rate (Top50)',data:rows.map(r=>+r.selection_rate_top50),backgroundColor:'#68d39155',borderColor:'#68d391',borderWidth:2},
      ]},
      options:{responsive:true,maintainAspectRatio:false,
        scales:{y:{min:0,max:0.4,grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},
        plugins:{legend:{position:'bottom',labels:{font:{size:10}}}}}
    });
  });
  document.getElementById('fairness-table').innerHTML=`<thead><tr>
    <th>Group</th><th>Value</th><th>N</th><th>Actual Attrition</th>
    <th>Mean Pred. Prob</th><th>TPR</th><th>FPR</th><th>Selection Rate (Top50)</th></tr></thead>
  <tbody>${D.fairness.map(r=>`<tr>
    <td style="font-weight:600;color:var(--accent1)">${r.group_col}</td>
    <td>${r.group_value}</td><td>${r.n}</td>
    <td>${(+r.actual_attrition_rate*100).toFixed(1)}%</td>
    <td>${(+r.mean_predicted_prob).toFixed(3)}</td>
    <td>${(+(r.true_positive_rate||0)*100).toFixed(1)}%</td>
    <td>${(+(r.false_positive_rate||0)*100).toFixed(1)}%</td>
    <td>${(+r.selection_rate_top50*100).toFixed(1)}%</td>
  </tr>`).join('')}</tbody>`;
}

// ── Calibration ───────────────────────────────────────────────────────────────
function buildCalibration(){
  const cal=D.calibration;
  new Chart(document.getElementById('ch-cal-bar'),{
    type:'bar',
    data:{labels:cal.map(r=>r.model),datasets:[
      {label:'Brier Score',data:cal.map(r=>+r.brier),backgroundColor:['#f6ad5555','#68d39155'],borderColor:['#f6ad55','#68d391'],borderWidth:2},
      {label:'ECE',data:cal.map(r=>+r.ece),backgroundColor:['#fc818155','#63b3ed55'],borderColor:['#fc8181','#63b3ed'],borderWidth:2},
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{y:{min:0,max:0.14,grid:{color:'rgba(255,255,255,.05)'}},x:{grid:{display:false}}},
      plugins:{legend:{position:'bottom'}}}
  });
  document.getElementById('cal-table').innerHTML=`<thead><tr>
    <th>Model</th><th>Brier</th><th>ECE</th><th>ROC-AUC</th><th>PR-AUC</th><th>Assessment</th></tr></thead>
  <tbody>${cal.map(r=>`<tr>
    <td style="font-weight:600">${r.model}</td>
    <td style="color:${+r.brier<0.1?'#68d391':'#f6ad55'};font-weight:700">${(+r.brier).toFixed(4)}</td>
    <td style="color:${+r.ece<0.05?'#68d391':'#fc8181'};font-weight:700">${(+r.ece).toFixed(4)}</td>
    <td>${(+r.roc_auc).toFixed(4)}</td>
    <td>${(+r.pr_auc).toFixed(4)}</td>
    <td>${r.model.includes('uncal')?'<span style="color:#f6ad55">Overconfident</span>':'<span style="color:#68d391">Well-calibrated (-72% ECE)</span>'}</td>
  </tr>`).join('')}</tbody>`;
}

buildOverview(); buildModels(); buildBudget(); buildEmployees(); buildFairness(); buildCalibration();
"""

BODY = """
<header>
  <div class="header-inner">
    <div class="logo">
      <div class="logo-icon">RIQ</div>
      <div class="logo-text">Retain<span>IQ</span></div>
    </div>
    <div class="badge">Research Prototype &mdash; Synthetic Benchmark</div>
  </div>
</header>
<nav>
  <button class="active" onclick="switchTab('overview',this)">Overview</button>
  <button onclick="switchTab('models',this)">Models &amp; Accuracy</button>
  <button onclick="switchTab('budget',this)">Budget Experiment</button>
  <button onclick="switchTab('employees',this)">Employee Lookup</button>
  <button onclick="switchTab('fairness',this)">Fairness Audit</button>
  <button onclick="switchTab('calibration',this)">Calibration</button>
</nav>
<main>

<!-- OVERVIEW -->
<div id="tab-overview" class="tab-panel active">
  <div class="disclaimer"><strong>DISCLAIMER:</strong> RetainIQ is a benchmark research prototype on the IBM HR Analytics <em>synthetic</em> dataset. Probabilities, costs, and rankings are model estimates under researcher-defined assumptions. Must NOT be used for real employment decisions.</div>
  <div id="stats-grid" class="stats-grid"></div>
  <div class="grid-2">
    <div class="card"><div class="section-title"><div class="dot"></div>Target Distribution</div><div class="chart-wrap"><canvas id="ch-target"></canvas></div></div>
    <div class="card"><div class="section-title"><div class="dot"></div>Accuracy / ROC-AUC / PR-AUC by Model</div><div class="chart-wrap"><canvas id="ch-accuracy"></canvas></div></div>
  </div>
  <div class="grid-2">
    <div class="card"><div class="section-title"><div class="dot"></div>Final Model &mdash; Key Metrics (Logistic Regression)</div><div id="metric-bars"></div></div>
    <div class="card"><div class="section-title"><div class="dot"></div>Feature Ablation: Baseline vs Engineered (PR-AUC)</div><div class="chart-wrap"><canvas id="ch-ablation"></canvas></div></div>
  </div>
</div>

<!-- MODELS -->
<div id="tab-models" class="tab-panel">
  <div class="card" style="margin-bottom:1.5rem"><div class="section-title"><div class="dot"></div>All Model Results (OOF, Calibrated, Engineered Features)</div><div class="table-wrap"><table id="model-table"></table></div></div>
  <div class="grid-2">
    <div class="card"><div class="section-title"><div class="dot"></div>PR-AUC vs ROC-AUC</div><div class="chart-wrap"><canvas id="ch-models-bar"></canvas></div></div>
    <div class="card"><div class="section-title"><div class="dot"></div>Brier Score &amp; ECE (lower = better)</div><div class="chart-wrap"><canvas id="ch-brier"></canvas></div></div>
  </div>
  <div class="card" style="margin-top:1.5rem"><div class="section-title"><div class="dot"></div>Feature Ablation &mdash; Full Table</div><div class="table-wrap"><table id="ablation-table"></table></div></div>
</div>

<!-- BUDGET -->
<div id="tab-budget" class="tab-panel">
  <div class="disclaimer">Evaluation uses <strong>realized out-of-fold outcomes</strong> (ground-truth attrition labels), not predicted probabilities. Costs are researcher-assumed hypothetical parameters.</div>
  <div class="grid-2">
    <div class="card"><div class="section-title"><div class="dot"></div>Actual Leavers Captured by Strategy</div><div class="chart-wrap-tall"><canvas id="ch-budget-leavers"></canvas></div></div>
    <div class="card"><div class="section-title"><div class="dot"></div>Realized Cost Exposure Captured ($k)</div><div class="chart-wrap-tall"><canvas id="ch-budget-cost"></canvas></div></div>
  </div>
  <div class="card" style="margin-top:0"><div class="section-title"><div class="dot"></div>Budget Results Table</div><div class="table-wrap"><table id="budget-table"></table></div></div>
</div>

<!-- EMPLOYEES -->
<div id="tab-employees" class="tab-panel">
  <div id="emp-card">
    <div class="emp-header">
      <div><div class="emp-name" id="ec-name"></div><div class="emp-sub" id="ec-role"></div></div>
      <div id="ec-risk" class="risk-badge"></div>
    </div>
    <div class="emp-grid">
      <div class="emp-item"><div class="lbl">P(Attrition)</div><div class="val" id="ec-prob"></div></div>
      <div class="emp-item"><div class="lbl">Risk Rank</div><div class="val" id="ec-rrank"></div></div>
      <div class="emp-item"><div class="lbl">ERL Priority Rank</div><div class="val" id="ec-erank"></div></div>
      <div class="emp-item"><div class="lbl">Monthly Income</div><div class="val" id="ec-income"></div></div>
      <div class="emp-item"><div class="lbl">Annual Salary</div><div class="val" id="ec-salary"></div></div>
      <div class="emp-item"><div class="lbl">Expected Replacement Loss</div><div class="val" id="ec-erl"></div></div>
      <div class="emp-item"><div class="lbl">Job Level</div><div class="val" id="ec-level"></div></div>
      <div class="emp-item"><div class="lbl">Years at Company</div><div class="val" id="ec-years"></div></div>
      <div class="emp-item"><div class="lbl">OverTime</div><div class="val" id="ec-ot"></div></div>
      <div class="emp-item"><div class="lbl">Actual Outcome (OOF)</div><div class="val" id="ec-actual"></div></div>
    </div>
    <div style="margin-top:1rem;font-size:.72rem;color:var(--text2);border-top:1px solid var(--glassborder);padding-top:.75rem">
      Model-associated features are statistical associations, NOT causal explanations. Do NOT use for real employment decisions.
    </div>
  </div>
  <div class="search-bar">
    <input type="number" id="emp-id-input" placeholder="Search by Employee ID..." min="1"/>
    <select id="emp-dept"><option value="">All Departments</option><option>Sales</option><option>Research &amp; Development</option><option>Human Resources</option></select>
    <select id="emp-risk"><option value="">All Risk Levels</option><option value="HIGH">High Risk</option><option value="MODERATE">Moderate Risk</option><option value="LOW">Low Risk</option></select>
    <select id="emp-sort"><option value="erl">Sort by ERL (Economic Priority)</option><option value="risk">Sort by Attrition Risk</option></select>
  </div>
  <div class="card"><div class="section-title"><div class="dot"></div>Employee Priority List &mdash; Click any row to inspect</div><div class="table-wrap"><table id="emp-table"></table></div><div style="margin-top:.75rem;font-size:.72rem;color:var(--text2)">Showing top 60. LEFT = actual leaver (realized OOF label).</div></div>
</div>

<!-- FAIRNESS -->
<div id="tab-fairness" class="tab-panel">
  <div class="disclaimer">Age, Gender, and MaritalStatus were <strong>excluded from model training</strong>. This is a post-hoc diagnostic only. No legal compliance is claimed. Disparities reflect dataset characteristics.</div>
  <div class="grid-3">
    <div class="card"><div class="section-title"><div class="dot"></div>By Gender</div><div class="chart-wrap"><canvas id="ch-fair-gender"></canvas></div></div>
    <div class="card"><div class="section-title"><div class="dot"></div>By Marital Status</div><div class="chart-wrap"><canvas id="ch-fair-marital"></canvas></div></div>
    <div class="card"><div class="section-title"><div class="dot"></div>By Age Band</div><div class="chart-wrap"><canvas id="ch-fair-age"></canvas></div></div>
  </div>
  <div class="card"><div class="section-title"><div class="dot"></div>Fairness Audit Table</div><div class="table-wrap"><table id="fairness-table"></table></div></div>
</div>

<!-- CALIBRATION -->
<div id="tab-calibration" class="tab-panel">
  <div class="grid-2">
    <div class="card"><div class="section-title"><div class="dot"></div>Calibration: Brier Score &amp; ECE</div><div class="chart-wrap"><canvas id="ch-cal-bar"></canvas></div></div>
    <div class="card"><div class="section-title"><div class="dot"></div>Why Calibration Matters for ERL</div>
      <div style="font-size:.85rem;line-height:1.7;color:var(--text2);padding-top:.5rem">
        <p>The ERL formula is:</p>
        <p style="margin:.75rem 0;background:var(--bg3);padding:.75rem 1rem;border-radius:8px;font-family:monospace;color:#63b3ed">ERL = P(attrition) &times; ReplacementCost</p>
        <p>Poorly calibrated probabilities distort ERL, making the economic prioritisation invalid.</p>
        <p style="margin-top:.75rem">Sigmoid calibration reduced ECE by <strong style="color:#68d391">72%</strong> (0.0953 &rarr; 0.0264), validating the ERL layer.</p>
        <p style="margin-top:.75rem;color:#f6ad55;font-size:.78rem">Calibration was fitted inside each outer training fold (fold-safe) to prevent leakage.</p>
      </div>
    </div>
  </div>
  <div class="card"><div class="section-title"><div class="dot"></div>Calibration Results Table</div><div class="table-wrap"><table id="cal-table"></table></div></div>
</div>

</main>
"""

HTML = ("<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'/>"
        "<meta name='viewport' content='width=device-width,initial-scale=1.0'/>"
        "<title>RetainIQ - Attrition Research Dashboard</title>"
        "<meta name='description' content='RetainIQ: Cost-Weighted ML Framework for Employee Attrition Prediction'/>"
        "<script src='https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'></script>"
        "<style>" + CSS + "</style>"
        "</head><body><div class='wrapper'>"
        + BODY +
        "<script>window.__DATA__ = " + DATA_JSON + ";\n" + JS + "</script>"
        "</div></body></html>")

out_path = rc.ROOT / "dashboard.html"
out_path.write_text(HTML, encoding="utf-8")
print("[saved] dashboard.html ->", out_path)
print("Open: file:///" + str(out_path).replace("\\", "/"))
