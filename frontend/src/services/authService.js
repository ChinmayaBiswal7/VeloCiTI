// VeloCiTI Team Authentication & Role-Based Access Control
// Configured with pre-authorized team credentials & whitelist

// Team accounts are kept out of source control. To use real accounts, create
// src/config/teamMembers.local.js (git-ignored) exporting TEAM_MEMBERS in the same shape as the demo account.
import { DEMO_TEAM_MEMBERS } from "../config/teamMembers.example.js";

const localAccounts = import.meta.glob("../config/teamMembers.local.js", { eager: true });
export const AUTHORIZED_TEAM_MEMBERS = Object.values(localAccounts)[0]?.TEAM_MEMBERS ?? DEMO_TEAM_MEMBERS;

const AUTH_STORAGE_KEY = "velociti_auth_session";



/**
 * Authenticate team member credentials with smart typo tolerance
 */
export function login(email, password) {
  let normalized = (email || "").trim().toLowerCase();
  const trimmedPassword = (password || "").trim();

  // Smart tolerance: fix @kiit.acin missing dot, or allow entering just roll number
  if (normalized.endsWith("@kiit.acin")) {
    normalized = normalized.replace("@kiit.acin", "@kiit.ac.in");
  } else if (!normalized.includes("@") && normalized.length >= 6) {
    normalized = `${normalized}@kiit.ac.in`;
  }

  const user = AUTHORIZED_TEAM_MEMBERS.find(member => {
    const memberEmail = member.email.toLowerCase();
    const isEmailMatch = (
      memberEmail === normalized ||
      memberEmail.replace(".ac.in", ".acin") === normalized ||
      memberEmail.split("@")[0] === normalized.split("@")[0]
    );
    const isPassMatch = member.password === trimmedPassword;
    return isEmailMatch && isPassMatch;
  });

  if (user) {
    const sessionData = {
      email: user.email,
      name: user.name,
      role: user.role,
      badge: user.badge,
      department: user.department,
      loginTime: Date.now(),
    };
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(sessionData));
    return { success: true, user: sessionData };
  }

  return { success: false, error: "Access Denied: Unrecognized email or incorrect security passcode." };
}

/**
 * Retrieve current logged in user session
 */
export function getCurrentUser() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Clear session and sign out
 */
export function logout() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

/**
 * Check if current browser has active authorized session
 */
export function isAuthenticated() {
  return !!getCurrentUser();
}
