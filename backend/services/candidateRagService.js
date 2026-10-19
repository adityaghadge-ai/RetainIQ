// backend/services/candidateRagService.js
// =====================================
// Candidate RAG & Multi-Criteria Retrieval Engine for RetainIQ.
// Provides explainable matching against replacement requirements.

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DB_PATH = path.join(__dirname, "../../data/candidates/candidates.json");

/**
 * Read candidates database
 */
function loadCandidates() {
  try {
    if (!fs.existsSync(DB_PATH)) {
      return [];
    }
    const data = fs.readFileSync(DB_PATH, "utf-8");
    return JSON.parse(data);
  } catch (err) {
    console.error("[candidateRagService] Error reading candidate database:", err.message);
    return [];
  }
}

/**
 * Save candidate to database
 */
function saveCandidates(candidates) {
  fs.writeFileSync(DB_PATH, JSON.stringify(candidates, null, 2), "utf-8");
}

/**
 * Normalize text for string matching
 */
function normalize(str) {
  return (str || "").toLowerCase().trim();
}

/**
 * Tokenize string into alphanumeric keywords
 */
function tokenize(str) {
  return (str || "")
    .toLowerCase()
    .replace(/[^a-z0-9+#]/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

/**
 * Search candidates with multi-criteria explainable scoring
 */
export function searchCandidates(query = {}) {
  const {
    role = "",
    minExperience = 0,
    skills = [],
    maxSalary = Infinity,
    maxNoticePeriod = 180,
  } = query;

  const candidates = loadCandidates();

  const queryRoleTokens = tokenize(role);
  const querySkills = Array.isArray(skills)
    ? skills.map((s) => s.trim().toLowerCase())
    : tokenize(skills);

  const results = candidates.map((cand) => {
    // 1. Role match (0.0 to 1.0)
    let roleScore = 0.5; // neutral baseline
    if (queryRoleTokens.length > 0) {
      const candRoleTokens = tokenize(cand.role);
      const shared = queryRoleTokens.filter((t) => candRoleTokens.includes(t));
      roleScore = shared.length / Math.max(1, queryRoleTokens.length);
      // bonus if exact substring
      if (normalize(cand.role).includes(normalize(role)) || normalize(role).includes(normalize(cand.role))) {
        roleScore = Math.max(roleScore, 0.9);
      }
    }

    // 2. Skill match & breakdown
    const candSkillsLower = (cand.skills || []).map((s) => s.toLowerCase());
    const matchingSkills = [];
    const missingSkills = [];

    if (querySkills.length > 0) {
      querySkills.forEach((reqSkill) => {
        const found = candSkillsLower.some((cs) => cs.includes(reqSkill) || reqSkill.includes(cs));
        if (found) {
          matchingSkills.push(reqSkill);
        } else {
          missingSkills.push(reqSkill);
        }
      });
    }

    const skillScore = querySkills.length > 0
      ? matchingSkills.length / querySkills.length
      : 0.75;

    // 3. Experience match
    const candExp = cand.experience_years || 0;
    let expScore = 1.0;
    if (candExp < minExperience) {
      const deficit = minExperience - candExp;
      expScore = Math.max(0.2, 1.0 - deficit * 0.25);
    } else {
      // mild bonus for optimal experience without massive over-qualification
      const surplus = candExp - minExperience;
      expScore = surplus > 8 ? 0.85 : 1.0;
    }

    // 4. Salary compatibility
    let salaryScore = 1.0;
    const salary = cand.salary_expectation || 0;
    if (maxSalary && maxSalary > 0 && salary > maxSalary) {
      const excessRatio = (salary - maxSalary) / maxSalary;
      salaryScore = Math.max(0.1, 1.0 - excessRatio * 1.5);
    }

    // 5. Notice period compatibility
    let noticeScore = 1.0;
    const notice = cand.notice_period_days || 30;
    if (notice > maxNoticePeriod) {
      noticeScore = Math.max(0.3, 1.0 - ((notice - maxNoticePeriod) / 60));
    }

    // Weighted composite match score (Skill 40%, Role 25%, Exp 20%, Salary 15%)
    const rawComposite =
      skillScore * 0.40 +
      roleScore * 0.25 +
      expScore * 0.20 +
      salaryScore * 0.15;

    const match_score = Math.min(0.99, Math.max(0.15, Math.round(rawComposite * 100) / 100));

    return {
      ...cand,
      is_demo: true,
      source: "DEMO DATA",
      match_score,
      match_pct: Math.round(match_score * 100),
      matching_skills: matchingSkills,
      missing_skills: missingSkills,
      score_breakdown: {
        skill_score: Math.round(skillScore * 100),
        role_score: Math.round(roleScore * 100),
        experience_score: Math.round(expScore * 100),
        salary_score: Math.round(salaryScore * 100),
        notice_score: Math.round(noticeScore * 100),
      },
      evaluation_notes: `Similarity against supplied replacement requirements. Skill coverage: ${matchingSkills.length}/${querySkills.length || 1}.`,
      disclaimer: "Match score against supplied requirements. NOT a personal recommendation.",
    };
  });

  // Sort descending by match score
  results.sort((a, b) => b.match_score - a.match_score);

  return {
    candidates: results,
    total: results.length,
    disclaimer: "All profiles are synthetic DEMO DATA. Match scores represent similarity to the supplied replacement requirements, not a claim of best candidate.",
  };
}

/**
 * Add / upload candidate
 */
export function addCandidate(candidate) {
  const candidates = loadCandidates();
  const newCandidate = {
    id: candidate.id || `CAND-${Date.now().toString().slice(-4)}`,
    name: candidate.name || "Anonymous Candidate",
    role: candidate.role || "Specialist",
    experience_years: Number(candidate.experience_years) || 1,
    skills: Array.isArray(candidate.skills) ? candidate.skills : tokenize(candidate.skills),
    education: candidate.education || "Bachelor's Degree",
    salary_expectation: Number(candidate.salary_expectation) || 800000,
    location: candidate.location || "Hybrid",
    notice_period_days: Number(candidate.notice_period_days) || 30,
    projects: candidate.projects || "Enterprise system development",
    certifications: candidate.certifications || [],
    source: candidate.source || "user_upload",
    uploaded_at: new Date().toISOString(),
  };

  candidates.unshift(newCandidate);
  saveCandidates(candidates);
  return newCandidate;
}

/**
 * Get all candidates
 */
export function getAllCandidates() {
  return loadCandidates();
}
