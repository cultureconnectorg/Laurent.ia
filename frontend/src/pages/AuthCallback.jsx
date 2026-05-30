/**
 * AuthCallback — page traversée juste après le retour de Emergent Auth.
 * URL: /#session_id=xxx
 * Synchrone : récupère le hash → POST /api/auth/session → navigue vers /.
 */
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AuthCallback() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const hasProcessed = useRef(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash || "";
    const m = hash.match(/session_id=([^&]+)/);
    if (!m) {
      navigate("/", { replace: true });
      return;
    }
    const sessionId = decodeURIComponent(m[1]);

    (async () => {
      try {
        const r = await fetch(`${API}/auth/session`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ session_id: sessionId }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        await refresh();
        // Clear hash and go home
        window.history.replaceState({}, "", "/");
        navigate("/", { replace: true, state: { user: data.user } });
      } catch (e) {
        setError(e.message || "Erreur authentification");
        setTimeout(() => navigate("/", { replace: true }), 2000);
      }
    })();
  }, [navigate, refresh]);

  return (
    <div className="w-full h-screen flex items-center justify-center bg-[#0A0F1F]" data-testid="auth-callback">
      <div className="text-center">
        <div className="w-12 h-12 mx-auto mb-4 rounded-full border-2 border-[#6BA8FF]/30 border-t-[#6BA8FF] animate-spin" />
        <div className="font-mono text-[10px] uppercase tracking-[0.32em] text-white/50">
          {error ? `Erreur · ${error}` : "Authentification en cours…"}
        </div>
      </div>
    </div>
  );
}
