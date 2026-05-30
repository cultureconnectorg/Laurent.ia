/**
 * AuthContext — provider global pour l'identité utilisateur.
 * Source de vérité côté serveur : /api/auth/me (cookie httpOnly).
 *
 * Expose:
 *   user, loading, login(), logout(), refresh()
 *   isAuthenticated, frekId
 */
import { createContext, useCallback, useContext, useEffect, useState } from "react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch(`${API}/auth/me`, { credentials: "include" });
      if (r.ok) {
        const data = await r.json();
        setUser(data);
      } else {
        setUser(null);
      }
    } catch (_) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // CRITICAL: If returning from OAuth callback (hash with session_id),
    // skip the /me check. AuthCallback will exchange the session_id first.
    if (window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    refresh();
  }, [refresh]);

  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const login = useCallback(() => {
    const redirectUrl = window.location.origin + "/";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${API}/auth/logout`, { method: "POST", credentials: "include" });
    } catch (_) {}
    setUser(null);
    // Soft redirect to root
    window.location.href = "/";
  }, []);

  // Connexion via un FREK-ID existant (membre écosystème).
  // Retourne { ok: true } | { ok: false, error }.
  const loginWithFrekId = useCallback(async (frekId) => {
    try {
      const r = await fetch(`${API}/auth/frek`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ frek_id: frekId }),
      });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        return { ok: false, error: data.detail || `Erreur ${r.status}` };
      }
      const data = await r.json();
      setUser(data.user);
      return { ok: true, user: data.user };
    } catch (e) {
      return { ok: false, error: e.message || "Erreur réseau" };
    }
  }, []);

  const value = {
    user,
    loading,
    login,
    loginWithFrekId,
    logout,
    refresh,
    isAuthenticated: !!user,
    frekId: user?.frek_id || null,
    ecosystemMember: !!user?.ecosystem_member,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside <AuthProvider>");
  return ctx;
}
