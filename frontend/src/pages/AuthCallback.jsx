/**
 * AuthCallback — traite le retour du flux Google OIDC local.
 * Le backend a déjà validé l'identité et posé le cookie de session.
 */
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { refresh, migrateAnonIfAny } = useAuth();
  const hasProcessed = useRef(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash || "";
    if (hash.includes("auth=error")) {
      setError("La connexion Google a échoué. Réessaie.");
      window.history.replaceState({}, "", "/");
      const timer = window.setTimeout(() => navigate("/", { replace: true }), 2200);
      return () => window.clearTimeout(timer);
    }

    if (!hash.includes("auth=success")) {
      navigate("/", { replace: true });
      return;
    }

    (async () => {
      try {
        await refresh();
        await migrateAnonIfAny();
        window.history.replaceState({}, "", "/");
        navigate("/", { replace: true });
      } catch (_) {
        setError("Connexion établie, mais le chargement du profil a échoué.");
        window.history.replaceState({}, "", "/");
        window.setTimeout(() => navigate("/", { replace: true }), 2200);
      }
    })();
  }, [navigate, refresh, migrateAnonIfAny]);

  return (
    <div className="w-full h-screen flex items-center justify-center bg-[#0A0F1F]" data-testid="auth-callback">
      <div className="text-center">
        <div className="w-12 h-12 mx-auto mb-4 rounded-full border-2 border-[#6BA8FF]/30 border-t-[#6BA8FF] animate-spin" />
        <div className="font-mono text-[10px] uppercase tracking-[0.32em] text-white/50">
          {error || "Authentification en cours…"}
        </div>
      </div>
    </div>
  );
}
