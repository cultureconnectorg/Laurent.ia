import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUp, Mic, Square, Loader2 } from "lucide-react";

/**
 * Composer — barre d'entrée style Claude / ChatGPT.
 *  - Textarea auto-grow
 *  - Bouton micro (toggle voice mode)
 *  - Bouton envoyer
 *  - "Laurent.ia v0.1" sous l'input (style "BRAIN V2.4")
 *
 * Props:
 *   state: "idle" | "listening" | "thinking" | "speaking"
 *   value, onChange, onSubmit, onStartVoice, onStopVoice, onCancel
 */
export const Composer = ({
  value = "",
  onChange,
  onSubmit,
  state = "idle",
  onStartVoice,
  onStopVoice,
  onCancel,
  externalValueRef,
}) => {
  const textareaRef = useRef(null);
  const [focused, setFocused] = useState(false);

  // auto-grow
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = Math.min(el.scrollHeight, 168) + "px";
  }, [value]);

  // expose ref for parent (e.g. focus after chip pick)
  useEffect(() => {
    if (externalValueRef) externalValueRef.current = textareaRef.current;
  }, [externalValueRef]);

  const isBusy = state === "thinking" || state === "speaking";
  const isListening = state === "listening";

  const handleSubmit = (e) => {
    e?.preventDefault?.();
    if (!value.trim() || isBusy) return;
    onSubmit?.(value.trim());
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleVoiceClick = () => {
    if (isBusy) return onCancel?.();
    if (isListening) return onStopVoice?.();
    return onStartVoice?.();
  };

  return (
    <div className="w-full max-w-2xl mx-auto px-4 pb-3" data-testid="composer">
      <motion.form
        onSubmit={handleSubmit}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className={`composer-ring relative flex items-end gap-2 rounded-3xl border bg-white/[0.03] backdrop-blur-xl px-3 py-2.5 ${
          isListening ? "border-[#6BA8FF]/50 shadow-[0_0_30px_rgba(107,168,255,0.22)]" : "border-white/[0.07]"
        }`}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={
            isListening ? "Laurent.ia écoute…" :
            isBusy ? "Laurent.ia réfléchit…" :
            "Posez votre question…"
          }
          rows={1}
          disabled={isBusy}
          className="flex-1 resize-none bg-transparent outline-none font-sans text-[15px] text-[#F1F4FA]
            placeholder:text-white/35 leading-relaxed py-1.5 px-2 max-h-[168px] thin-scroll"
          data-testid="composer-input"
          style={{ scrollbarWidth: "thin" }}
        />

        <div className="flex items-center gap-1.5 self-end pb-0.5">
          <button
            type="button"
            onClick={handleVoiceClick}
            aria-label={isListening ? "Arrêter l'écoute" : "Activer la voix"}
            className={`w-9 h-9 flex items-center justify-center rounded-full transition-all duration-200
              ${isListening
                ? "bg-[#2D6FE0] text-white shadow-[0_0_18px_rgba(45,111,224,0.55)]"
                : "bg-white/[0.04] border border-white/[0.08] text-white/70 hover:text-white hover:bg-white/[0.07]"
              }`}
            data-testid="mic-toggle-button"
          >
            {isBusy ? <Square className="w-4 h-4" strokeWidth={1.6} /> :
             isListening ? <Mic className="w-4 h-4" strokeWidth={1.8} /> :
             <Mic className="w-4 h-4" strokeWidth={1.6} />}
          </button>

          <button
            type="submit"
            disabled={!value.trim() || isBusy}
            aria-label="Envoyer"
            className={`w-9 h-9 flex items-center justify-center rounded-full transition-all duration-200
              ${value.trim() && !isBusy
                ? "bg-gradient-to-br from-[#2D6FE0] to-[#5BA0FF] text-white shadow-[0_4px_18px_rgba(45,111,224,0.4)] hover:shadow-[0_4px_22px_rgba(45,111,224,0.55)]"
                : "bg-white/[0.04] text-white/30 border border-white/[0.05]"
              }`}
            data-testid="composer-submit"
          >
            {isBusy ? <Loader2 className="w-4 h-4 animate-spin" strokeWidth={1.8} /> : <ArrowUp className="w-4 h-4" strokeWidth={2.2} />}
          </button>
        </div>
      </motion.form>

      <div className="mt-2 flex items-center justify-between px-2 font-mono text-[10px] uppercase tracking-[0.22em] text-white/30">
        <span data-testid="composer-version">Laurent.ia · v0.1</span>
        <span className="hidden sm:inline">Entrée = envoyer · Shift+Entrée = saut de ligne</span>
      </div>
    </div>
  );
};

export default Composer;
