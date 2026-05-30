import { useEffect, useState } from "react";
import useLaurentIA from "@/hooks/useLaurentIA";
import OrbeLaurentIA from "@/components/laurentia/OrbeLaurentIA";
import StateIndicator from "@/components/laurentia/StateIndicator";
import ConversationZone from "@/components/laurentia/ConversationZone";
import FreKIDBadge from "@/components/laurentia/FreKIDBadge";
import StatusBar from "@/components/laurentia/StatusBar";
import MicButton from "@/components/laurentia/MicButton";

/**
 * LaurentIA — Single page voice-first.
 * - Aucun chrome, aucune navigation.
 * - Tap mic → STT → POST /api/laurentia/query (SSE) → stream tokens → TTS.
 * - Fallback texte: si STT indisponible, un champ texte discret s'active sur ESPACE.
 */
export default function LaurentIA() {
  // FREK-ID: récupéré depuis localStorage ou URL ?frek_id=... sinon DEMO-SAYD
  const [frekId] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return (
      params.get("frek_id") ||
      window.localStorage.getItem("laurentia_frek_id") ||
      "DEMO-SAYD"
    );
  });

  const {
    state,
    transcript,
    response,
    meta,
    error,
    startListening,
    stopListening,
    sendQuery,
    cancel,
  } = useLaurentIA({ frekId, appContext: "direct" });

  const [textInput, setTextInput] = useState("");
  const [showTextFallback, setShowTextFallback] = useState(false);

  // Détecte si Web Speech API est dispo, sinon active fallback texte
  useEffect(() => {
    const hasSTT = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    if (!hasSTT) setShowTextFallback(true);
  }, []);

  // Raccourci clavier: ESPACE pour démarrer/arrêter
  useEffect(() => {
    const onKey = (e) => {
      if (e.code === "Space" && !showTextFallback && e.target.tagName !== "INPUT") {
        e.preventDefault();
        if (state === "idle") startListening();
        else if (state === "listening") stopListening();
        else if (state === "thinking" || state === "speaking") cancel();
      }
      if (e.code === "Escape") cancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [state, startListening, stopListening, cancel, showTextFallback]);

  const submitText = (e) => {
    e?.preventDefault?.();
    if (!textInput.trim()) return;
    sendQuery(textInput.trim());
    setTextInput("");
  };

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#0A0A0A] grain-overlay" data-testid="laurentia-page">
      {/* Vignette atmosphérique */}
      <div
        className="absolute inset-0 z-[1] pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(10,10,10,0) 0%, rgba(10,10,10,0.85) 80%)",
        }}
      />

      <div className="relative z-10 w-full h-full">
        <FreKIDBadge firstName={meta.first_name} />
        <StatusBar
          version={meta.version}
          tokensRemaining={meta.tokens_remaining}
          jccBalance={0}
          quotaWarning={meta.quota_warning}
        />

        <OrbeLaurentIA state={state} />
        <StateIndicator state={state} hidden={!!response} />

        <ConversationZone
          transcript={transcript}
          response={response}
          error={error}
          state={state}
        />

        {showTextFallback ? (
          <form
            onSubmit={submitText}
            className="absolute left-1/2 -translate-x-1/2 bottom-10 z-30 w-full max-w-xl px-6"
            data-testid="text-fallback-form"
          >
            <div className="flex items-center gap-3 backdrop-blur-xl bg-white/[0.04] border border-white/10 rounded-full px-5 py-3 shadow-[0_8px_32px_rgba(0,0,0,0.45)]">
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-[#D97736]/70">›</span>
              <input
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Parle à Laurent.ia…"
                className="flex-1 bg-transparent outline-none font-mono text-sm text-[#F3EFE7] placeholder:text-white/30"
                data-testid="text-fallback-input"
              />
              <button
                type="submit"
                disabled={!textInput.trim() || state !== "idle"}
                className="font-mono text-[10px] uppercase tracking-[0.28em] text-[#F3EFE7]/80 hover:text-[#D97736] disabled:opacity-30 transition-colors"
                data-testid="text-fallback-submit"
              >
                Envoyer
              </button>
            </div>
          </form>
        ) : (
          <MicButton
            state={state}
            onStart={startListening}
            onStop={stopListening}
            onCancel={cancel}
          />
        )}

        {/* CTA Pro discret en cas de quota warning */}
        {meta.quota_warning && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-40 font-mono text-[10px] uppercase tracking-[0.28em] text-[#D97736]/90" data-testid="quota-warning-cta">
            Quota atteint · <button className="underline" data-testid="upgrade-pro-cta">Activer Pro</button>
          </div>
        )}
      </div>
    </div>
  );
}
