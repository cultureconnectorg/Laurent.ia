import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import useLaurentIA from "@/hooks/useLaurentIA";
import Header from "@/components/laurentia/Header";
import HeroPanel from "@/components/laurentia/HeroPanel";
import SuggestionChips from "@/components/laurentia/SuggestionChips";
import ChatBubble from "@/components/laurentia/ChatBubble";
import Composer from "@/components/laurentia/Composer";
import BottomTabBar from "@/components/laurentia/BottomTabBar";
import OrbeLaurentIA from "@/components/laurentia/OrbeLaurentIA";

/**
 * LaurentIA — page principale chat-first.
 *
 * Layout :
 *   [Header bar]
 *   [Hero panel (empty state) OR Conversation thread]
 *   [Suggestion chips]
 *   [Composer]
 *   [BottomTabBar]
 */
export default function LaurentIA() {
  // FREK-ID source
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
    history,
    meta,
    error,
    startListening,
    stopListening,
    sendQuery,
    cancel,
  } = useLaurentIA({ frekId, appContext: "direct" });

  const [composerValue, setComposerValue] = useState("");
  const scrollRef = useRef(null);
  const composerRef = useRef(null);

  // Auto-scroll to bottom on new message
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

  const handleSubmit = (text) => {
    setComposerValue("");
    sendQuery(text);
  };

  const handlePickChip = (prompt) => {
    setComposerValue(prompt);
    // focus composer textarea
    setTimeout(() => composerRef.current?.focus?.(), 30);
  };

  const conversationEmpty = history.length === 0 && !response && !transcript;
  const streamingAssistant = (state === "thinking" || state === "speaking") && response;

  return (
    <div
      className="relative w-full h-screen overflow-hidden bg-[#0A0F1F] atmo-glow flex flex-col"
      data-testid="laurentia-page"
    >
      {/* Header */}
      <Header
        firstName={meta.first_name}
        kt={10}
        version={meta.version}
      />

      {/* Main scroll area */}
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
              className="min-h-full flex flex-col items-center justify-center pt-2"
            >
              <HeroPanel state={state} />
              <div className="w-full mt-6 mb-2">
                <SuggestionChips onPick={handlePickChip} disabled={state !== "idle"} />
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
              {/* Conversation history */}
              {history.map((m, i) => (
                <ChatBubble key={`h-${i}`} role={m.role === "laurentia" ? "assistant" : m.role} text={m.text} />
              ))}

              {/* Live transcript (during listening) */}
              {transcript && state === "listening" && (
                <ChatBubble role="user" text={transcript} />
              )}

              {/* Streaming assistant response */}
              {streamingAssistant && (
                <ChatBubble role="assistant" text={response} streaming />
              )}

              {/* Thinking placeholder before first token */}
              {state === "thinking" && !response && (
                <div className="flex justify-start" data-testid="thinking-indicator">
                  <div className="rounded-2xl px-4 py-3 bg-white/[0.025] border border-white/[0.06]">
                    <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-[#6BA8FF] mb-1.5">
                      Laurent.ia
                    </div>
                    <div className="dot-typing text-[#6BA8FF] text-base leading-none">
                      <span>·</span><span>·</span><span>·</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Error banner */}
              {error && (
                <div
                  className="rounded-xl border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-300 font-mono"
                  data-testid="conversation-error"
                >
                  ! {error}
                </div>
              )}

              {/* Quota warning CTA */}
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

              {/* Small breathing orb in thread mode (when state is active) */}
              {state !== "idle" && state !== "thinking" && (
                <div className="flex justify-center py-2 opacity-60">
                  <OrbeLaurentIA state={state} size={64} />
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Composer */}
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
        />
      </div>

      {/* Bottom tab bar */}
      <BottomTabBar active="brain" />
    </div>
  );
}
