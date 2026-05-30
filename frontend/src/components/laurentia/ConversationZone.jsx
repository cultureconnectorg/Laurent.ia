import { useEffect, useRef } from "react";
import { motion } from "framer-motion";

/**
 * ConversationZone — affichage du texte streamé.
 * Affiche transcript utilisateur (discret) + réponse Laurent.ia (proéminente).
 */
export const ConversationZone = ({ transcript = "", response = "", error = null, state = "idle" }) => {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [response, transcript]);

  return (
    <div
      className="absolute left-1/2 -translate-x-1/2 bottom-[160px] w-full max-w-2xl px-6 z-10"
      data-testid="conversation-zone"
    >
      <div
        ref={ref}
        className="conversation-fade max-h-[36vh] overflow-y-auto pr-2 space-y-5 scroll-smooth"
        style={{ scrollbarWidth: "none" }}
      >
        {transcript && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="font-mono text-xs uppercase tracking-[0.2em] text-white/35"
            data-testid="conversation-transcript"
          >
            <span className="text-[#D97736]/70">› </span>
            {transcript}
          </motion.div>
        )}

        {response && (
          <motion.p
            key="response"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="font-mono text-lg md:text-xl leading-relaxed text-[#F3EFE7] token-in"
            data-testid="conversation-response"
          >
            {response}
            {(state === "thinking" || state === "speaking") && (
              <span className="inline-block w-[8px] h-[18px] align-middle ml-1 bg-[#D97736]/80 animate-pulse" />
            )}
          </motion.p>
        )}

        {error && (
          <div className="font-mono text-xs uppercase tracking-[0.2em] text-red-400/80" data-testid="conversation-error">
            ! {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default ConversationZone;
