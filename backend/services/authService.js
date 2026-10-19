// backend/services/authService.js
// ===============================
// JWT Authentication & User Management service for RetainIQ.

import jwt from "jsonwebtoken";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const USERS_PATH = path.join(__dirname, "../../data/users.json");

const JWT_SECRET = process.env.JWT_SECRET || "retainiq_super_secret_jwt_key_2026_academic_prod";

// Default seed users
const DEFAULT_USERS = [
  {
    id: "USR-001",
    email: "hr@enterprise.com",
    username: "admin",
    password: "RetainIQ@2026",
    name: "HR Operations Director",
    organization: "Global Enterprise Corp",
    role: "HR_DIRECTOR",
  },
  {
    id: "USR-002",
    email: "recruiter@enterprise.com",
    username: "recruiter",
    password: "Password@123",
    name: "Senior Talent Partner",
    organization: "Global Enterprise Corp",
    role: "TALENT_ACQUISITION",
  },
];

function loadUsers() {
  try {
    if (!fs.existsSync(USERS_PATH)) {
      fs.writeFileSync(USERS_PATH, JSON.stringify(DEFAULT_USERS, null, 2), "utf-8");
      return DEFAULT_USERS;
    }
    const data = fs.readFileSync(USERS_PATH, "utf-8");
    return JSON.parse(data);
  } catch (err) {
    console.error("[authService] Failed reading users:", err.message);
    return DEFAULT_USERS;
  }
}

function saveUsers(users) {
  try {
    fs.writeFileSync(USERS_PATH, JSON.stringify(users, null, 2), "utf-8");
  } catch (err) {
    console.error("[authService] Failed saving users:", err.message);
  }
}

/**
 * Register a new user
 */
export function registerUser({ email, password, name, organization = "Acme Corp", role = "HR_MANAGER" }) {
  if (!email || !password) {
    return { success: false, error: "Email and password are required" };
  }

  const users = loadUsers();
  const existing = users.find(u => u.email.toLowerCase() === email.toLowerCase());
  if (existing) {
    return { success: false, error: "An account with this email address already exists" };
  }

  const newUser = {
    id: `USR-${Date.now().toString().slice(-4)}`,
    email: email.trim().toLowerCase(),
    username: email.split("@")[0],
    password: password.trim(),
    name: name || email.split("@")[0],
    organization,
    role,
    created_at: new Date().toISOString(),
  };

  users.push(newUser);
  saveUsers(users);

  const payload = {
    id: newUser.id,
    email: newUser.email,
    name: newUser.name,
    organization: newUser.organization,
    role: newUser.role,
  };
  const token = jwt.sign(payload, JWT_SECRET, { expiresIn: "24h" });

  return {
    success: true,
    token,
    user: payload,
  };
}

/**
 * Authenticate user credentials (email or username)
 */
export function authenticate(identifier, password) {
  if (!identifier || !password) {
    return { success: false, error: "Identifier and password required" };
  }

  const users = loadUsers();
  const cleanId = identifier.trim().toLowerCase();
  const cleanPass = password.trim();

  // Match email or username
  const matched = users.find(
    u => (u.email.toLowerCase() === cleanId || u.username.toLowerCase() === cleanId) && u.password === cleanPass
  );

  // Fallback support for admin default
  if (!matched && cleanId === "admin" && cleanPass === "RetainIQ@2026") {
    const adminUser = users[0];
    const payload = {
      id: adminUser.id,
      email: adminUser.email,
      name: adminUser.name,
      organization: adminUser.organization,
      role: adminUser.role,
    };
    const token = jwt.sign(payload, JWT_SECRET, { expiresIn: "24h" });
    return { success: true, token, user: payload };
  }

  if (matched) {
    const payload = {
      id: matched.id,
      email: matched.email,
      name: matched.name,
      organization: matched.organization,
      role: matched.role,
    };
    const token = jwt.sign(payload, JWT_SECRET, { expiresIn: "24h" });
    return {
      success: true,
      token,
      user: payload,
    };
  }

  return {
    success: false,
    error: "Invalid email/username or password. (Demo: hr@enterprise.com / RetainIQ@2026)",
  };
}

/**
 * Verify JWT token middleware
 */
export function verifyAuth(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return res.status(401).json({
      error: "Unauthorized",
      detail: "Session token missing. Please sign in to access HR decision modules.",
    });
  }

  const token = authHeader.split(" ")[1];
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({
      error: "Unauthorized",
      detail: "Session expired. Please sign in again.",
    });
  }
}
