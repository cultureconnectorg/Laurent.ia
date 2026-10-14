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

  // Migration anonyme→FREK : appelée silencieusement après chaque login réussi.
  // Définie tôt pour être référencée par le callback Auth (Google).
  const migrateAnonIfAny = useCallback(async () => {
    try {
      const anon = window.localStorage.getItem("laurentia_anon_frek");
      if (!anon || !anon.startsWith("ANON-")) return 0;
      const r = await fetch(`${API}/auth/migrate-anon`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ anon_frek_id: anon }),
      });
      if (r.ok) {
        const d = await r.json();
        // Keep guest identity if the server did not confirm migration.
        window.localStorage.removeItem("laurentia_anon_frek");
        return d.migrated || 0;
      }
      return 0;
    } catch (_) {
      return 0;
    }
  }, []);

  // The backend handles Google OIDC and sets our httpOnly session cookie.
  useEffect(() => {
    if (window.location.hash?.includes("auth=success") || window.location.hash?.includes("auth=error")) {
      setLoading(false);
      return;
    }
    refresh();
  }, [refresh]);

  const login = useCallback(() => {
    window.location.href = `${API}/auth/google/start`;
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
      await migrateAnonIfAny();
      return { ok: true, user: data.user };
    } catch (e) {
      return { ok: false, error: e.message || "Erreur réseau" };
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const value = {
    user,
    loading,
    login,
    loginWithFrekId,
    logout,
    refresh,
    migrateAnonIfAny,
    isAuthenticated: !!user,
    frekId: user?.frek_id || null,
    ecosystemMember: !!user?.ecosystem_member,
    isPro: user?.version === "pro",
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside <AuthProvider>");
  return ctx;
}
