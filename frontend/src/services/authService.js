// VeloCiTI Team Authentication & Role-Based Access Control

const AUTH_STORAGE_KEY = "velociti_auth_session";

/**
 * Sign in. Credentials are verified by the backend (POST /api/auth/login); the browser only keeps the
 * signed-in user's profile so the UI can show who is logged in.
 */
export async function login(email, password) {
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (data.success) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(data.user));
      return { success: true, user: data.user };
    }
    return { success: false, error: data.error || "Access Denied: Unrecognized email or incorrect security passcode." };
  } catch {
    return { success: false, error: "Cannot reach the sign-in service. Is the backend running?" };
  }
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
