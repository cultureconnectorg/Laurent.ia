import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import useLaurentIA from "@/hooks/useLaurentIA";
import { useAuth } from "@/contexts/AuthContext";
import Header from "@/components/laurentia/Header";
import HeroPanel from "@/components/laurentia/HeroPanel";
import SuggestionChips from "@/components/laurentia/SuggestionChips";
import ChatBubble from "@/components/laurentia/ChatBubble";
import Composer from "@/components/laurentia/Composer";
import OrbeLaurentIA from "@/components/laurentia/OrbeLaurentIA";
import MenuDrawer from "@/components/laurentia/MenuDrawer";
import { PricingModal } from "@/components/laurentia/PricingModal";
import PhaseIndicator from "@/components/laurentia/PhaseIndicator";
import WhiteLabelKiller from "@/components/laurentia/WhiteLabelKiller";
import EnergyBraids from "@/components/laurentia/EnergyBraids";
import { ECOSYSTEM_CHIPS } from "@/components/laurentia/ecosystemChips";
import { withFingerprintHeaders } from "@/services/fingerprint";
import { toast } from "sonner";

/**
 * LaurentIA — page principale chat-first.
 *
 * Auth: si l'utilisateur est connecté (Emergent Google), on utilise son FREK-ID dérivé.
 * Sinon mode démo (URL ?frek_id= ou localStorage ou DEMO-SAYD par défaut).
 */
export default function LaurentIA() {
  const { user, isAuthenticated, ecosystemMember, loading: authLoading } = useAuth();
  const navigate = useNavigate();

  // FREK-ID anonyme par browser quand pas authentifié.
  // Évite l'effet "pollution" où un visiteur voit l'historique d'un autre.
  // Une fois login → on bascule sur le FREK-ID réel issu de l'auth.
  const [anonFrekId] = useState(() => {
    let v = window.localStorage.getItem("laurentia_anon_frek");
    if (!v) {
      v = "ANON-" + Math.random().toString(36).slice(2, 12).toUpperCase();
      window.localStorage.setItem("laurentia_anon_frek", v);
    }
    return v;
  });

  // Résout le FREK-ID : auth > anonyme
  const frekId = isAuthenticated && user?.frek_id ? user.frek_id : anonFrekId;

  const {
    state,
    phase,
    transcript,
    response,
    history,
    meta,
    error,
    startListening,
    stopListening,
    paywallEvent,
    sendQuery,
    cancel,
    resetSession,
    loadSession,
    exportPdf,
    stopSpeaking,
  } = useLaurentIA({ frekId, appContext: "direct" });

  const [composerValue, setComposerValue] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [pricingOpen, setPricingOpen] = useState(false);
  const [sealing, setSealing] = useState(false);
  const scrollRef = useRef(null);
  const composerRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [history.length, response, transcript]);

  // ESC to cancel
  useEffect(() => {
    const onKey = (e) => {
      if (e.code === "Escape") cancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cancel]);

  // Poll Stripe checkout status si retour de succès
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const session = params.get("session_id");
    const upgrade = params.get("upgrade");
    if (upgrade === "cancel") {
      toast("Upgrade annulé");
      window.history.replaceState({}, "", "/");
      return;
    }
    if (upgrade !== "success" || !session) return;
    let cancelled = false;
    let attempts = 0;
    const poll = async () => {
      if (cancelled || attempts >= 6) return;
      attempts += 1;
      try {
        const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/billing/status/${session}`, { credentials: "include" });
        if (r.ok) {
          const d = await r.json();
          if (d.payment_status === "paid") {
            toast("Pro activé. Bienvenue.");
            window.history.replaceState({}, "", "/");
            return;
          }
        }
      } catch (_) {}
      setTimeout(poll, 2000);
    };
    poll();
    return () => { cancelled = true; };
  }, []);

  // Load shared session from ?session=
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sid = params.get("session");
    if (sid) {
      loadSession(sid);
      window.history.replaceState({}, "", "/");
    }
  }, [loadSession]);

  // Persistance Fantôme — Résout l'historique depuis le device_id côté serveur
  // dès le premier paint, si l'utilisateur n'a pas de frek_id authentifié.
  useEffect(() => {
    if (authLoading || isAuthenticated) return;
    if (history.length > 0) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/laurentia/resolve`, {
          headers: withFingerprintHeaders({}),
          credentials: "include",
        });
        if (!r.ok) return;
        const data = await r.json();
        if (cancelled) return;
        if (data.last_session_id && !history.length) {
          loadSession(data.last_session_id);
        }
      } catch (_) {
        // silencieux : pas de session = pas de friction
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated]);

  const handleSubmit = (text, files) => {
    setComposerValue("");
    sendQuery(text, files || []);
  };

  const handleAttachUpgrade = () => {
    if (!isAuthenticated) {
      toast("Connecte-toi pour activer Creator (€15/mois) et joindre des fichiers.");
      setMenuOpen(true);
      return;
    }
    setPricingOpen(true);
  };

  const handlePickChip = (prompt) => {
    setComposerValue(prompt);
    setTimeout(() => composerRef.current?.focus?.(), 30);
  };

  const handleExportStart = () => {
    setSealing(true);
  };
  const handleExportEnd = (result) => {
    setSealing(false);
    if (result?.signature && typeof result?.free_exports_used === "number") {
      const remaining = (result.free_exports_limit || 2) - result.free_exports_used;
      if (remaining <= 0) {
        toast("Dernier export PDF gratuit utilisé. Creator 🪙 = exports illimités.");
      } else if (remaining === 1) {
        toast(`Encore ${remaining} export PDF gratuit ce mois. Passe à Creator 🪙 pour illimité.`);
      }
    }
  };
  const handlePaywall = (payload) => {
    toast("Quota PDF Free atteint. Active Creator 🪙 pour des exports illimités sans signature.");
    setPricingOpen(true);
  };

  // Paywall : ZÉRO auto-popup (comportement Claude).
  // On affiche seulement un toast actionnable, jamais de modale forcée.
  // L'utilisateur ouvre PricingModal uniquement via le bouton explicite
  // "Améliorer mon plan" dans le menu hamburger ou la carte upsell de /me/reports.
  useEffect(() => {
    if (!paywallEvent) return;
    const msg = paywallEvent.reason === "luciole"
      ? (paywallEvent.detail || "Énergie Luciole épuisée. Repasse demain ou active Creator pour libérer ta puissance.")
      : paywallEvent.reason === "upload_tier"
        ? "Upload réservé à Creator / Infinite."
        : "Quota atteint. Voir Creator pour continuer.";
    toast(msg, {
      action: { label: "Mon bilan", onClick: () => navigate("/me/reports") },
      duration: 6000,
    });
  }, [paywallEvent, navigate]);

  const handlePickSession = (sessionId) => {
    loadSession(sessionId);
  };

  const handleNewSession = () => {
    resetSession();
  };

  const displayFirstName = user?.name?.split(" ")[0] || meta.first_name;
  const conversationEmpty = history.length === 0 && !response && !transcript;
  const streamingAssistant = (state === "thinking" || state === "speaking") && response;

  return (
    <div
      className="relative w-full h-screen overflow-hidden bg-[#0A0F1F] atmo-glow flex flex-col"
      data-testid="laurentia-page"
    >
      <WhiteLabelKiller />

      {/* Rituel visuel : pulsation Or + Bleu lors de l'export PDF (gravure souveraine) */}
      <AnimatePresence>
        {sealing && (
          <motion.div
            key="sealing-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
            className="fixed inset-0 z-40 pointer-events-none flex items-center justify-center"
            data-testid="sealing-overlay"
          >
            <div className="absolute inset-0 bg-[#0A0F1F]/55 backdrop-blur-sm" />
            <div className="relative flex flex-col items-center">
              <OrbeLaurentIA state="sealing" size={180} />
              <div className="mt-6 font-mono text-[10px] uppercase tracking-[0.32em] text-[#E7C566]">
                Gravure souveraine en cours…
              </div>
              <div className="mt-1 font-serif italic text-base text-[#F4E0AA]">
                Apposition du sceau de la constellation
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <Header
        firstName={displayFirstName}
        kt={null}
        version={meta.version}
        picture={user?.picture}
        onMenuClick={() => setMenuOpen(true)}
        speakingState={state === "speaking" ? "active" : "idle"}
        onStopSpeaking={stopSpeaking}
      />

      <MenuDrawer
        open={menuOpen}
        onOpenChange={setMenuOpen}
        onPickSession={handlePickSession}
        onNewSession={handleNewSession}
        currentSessionId={meta.session_id}
      />

      <main
        ref={scrollRef}
        className="relative flex-1 overflow-y-auto thin-scroll pb-2"
        data-testid="conversation-zone"
      >
        <AnimatePresence mode="wait">
          {conversationEmpty ? (
            <motion.div
              key="hero"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
              className="relative min-h-full flex flex-col items-center justify-center pt-2"
            >
              <EnergyBraids />
              <div className="relative z-10 w-full flex flex-col items-center">
                <HeroPanel state={sealing ? "sealing" : state} />
                <div className="w-full mt-6 mb-2">
                  <SuggestionChips chips={ecosystemMember ? ECOSYSTEM_CHIPS : undefined} onPick={handlePickChip} disabled={state !== "idle"} />
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="thread"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
              className="w-full max-w-2xl mx-auto px-4 pt-4 pb-4 space-y-4"
              data-testid="conversation-thread"
            >
              {history.map((m, i) => (
                <ChatBubble
                  key={`h-${i}`}
                  role={m.role === "laurentia" ? "assistant" : m.role}
                  text={m.text}
                  files={m.files}
                  onExportPdf={exportPdf}
                  onExportStart={handleExportStart}
                  onExportEnd={handleExportEnd}
                  onPaywall={handlePaywall}
                />
              ))}

              {transcript && state === "listening" && (
                <ChatBubble role="user" text={transcript} />
              )}

              {streamingAssistant && (
                <ChatBubble role="assistant" text={response} streaming />
              )}

              {state === "thinking" && !response && (
                <div className="flex justify-start" data-testid="thinking-indicator">
                  <div className="rounded-2xl px-4 py-3 bg-white/[0.025] border border-white/[0.06] min-w-[260px]">
                    <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-[#6BA8FF] mb-2">
                      Laurent.ia
                    </div>
                    <PhaseIndicator phase={phase} />
                    {!phase && (
                      <div className="dot-typing text-[#6BA8FF] text-base leading-none">
                        <span>·</span><span>·</span><span>·</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {streamingAssistant && phase === "rendering" && (
                <div className="pl-2 -mt-2">
                  <PhaseIndicator phase={phase} />
                </div>
              )}

              {error && (
                <div
                  className="rounded-xl border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-300 font-mono"
                  data-testid="conversation-error"
                >
                  ! {error}
                </div>
              )}

              {meta.quota_warning && (
                <div className="flex items-center justify-between rounded-xl border border-[#E7C566]/30 bg-[#E7C566]/[0.04] px-4 py-3" data-testid="quota-warning-cta">
                  <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-[#E7C566]">
                    Quota mensuel atteint
                  </span>
                  <button className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#E7C566] underline" data-testid="upgrade-pro-cta">
                    Activer Pro
                  </button>
                </div>
              )}

              {state !== "idle" && state !== "thinking" && (
                <div className="flex justify-center py-2 opacity-60">
                  <OrbeLaurentIA state={state} size={64} />
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <div className="relative z-30 pt-1 bg-gradient-to-t from-[#0A0F1F] via-[#0A0F1F]/95 to-[#0A0F1F]/0">
        <Composer
          value={composerValue}
          onChange={setComposerValue}
          onSubmit={handleSubmit}
          state={state}
          onStartVoice={startListening}
          onStopVoice={stopListening}
          onCancel={cancel}
          externalValueRef={composerRef}
          tier={meta.tier || meta.version || "free"}
          onUpgradeClick={handleAttachUpgrade}
        />
      </div>

      <PricingModal
        open={pricingOpen}
        onOpenChange={setPricingOpen}
        currentTier={meta.tier || meta.version || "free"}
      />
    </div>
  );
}
