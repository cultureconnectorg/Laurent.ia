import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUp, Square, Loader2, Paperclip, X, FileText, Lock, AudioLines } from "lucide-react";

/**
 * Composer v1.2-PRODUCTION — fente noire translucide, sans contour.
 *  - Focus: scale 1.01 + halo bleu nuit profond derrière
 *  - Flèche envoi : grise → mutation Or vif dès le 1er caractère tapé
 *  - Trombone d'élite (sans contour) ouvre l'upload (gated tier)
 *  - Onde sonore animée pendant la dictée vocale (state="listening")
 *  - Bouton "Stop voix" lecture TTS géré dans Header (pas ici)
 *
 * Props:
 *   state: "idle" | "listening" | "thinking" | "speaking"
 *   value, onChange, onSubmit(text, files), onStartVoice, onStopVoice, onCancel
 *   tier: "free" | "creator" | "infinite"
 *   onUpgradeClick?: () => void
 */
const UPLOAD_TIERS = new Set(["creator", "infinite"]);
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const MAX_TOTAL_BYTES = 25 * 1024 * 1024;
const MAX_FILES = 4;
const ACCEPT = ".pdf,.docx,.txt,.md,.markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown";

function formatBytes(n) {
  if (n < 1024) return `${n} o`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} Ko`;
  return `${(n / 1024 / 1024).toFixed(1)} Mo`;
}

/** Onde sonore animée — remplace le micro statique de v1.1 */
const SoundWave = ({ active }) => {
  const bars = [3, 7, 5, 9, 4, 8, 6];
  return (
    <button
      type="button"
      aria-label={active ? "Dictée en cours — clique pour arrêter" : "Démarrer la dictée vocale"}
      className="flex items-end gap-[3px] h-6 px-2"
      data-testid="composer-sound-wave"
      data-active={active ? "true" : "false"}
    >
      {bars.map((h, i) => (
        <motion.span
          key={i}
          className="w-[2.5px] rounded-full"
          style={{
            background: active
              ? `linear-gradient(180deg, #E7C566 0%, #17a2b8 100%)`
              : "rgba(255,255,255,0.22)",
          }}
          animate={
            active
              ? { height: [`${h * 2}px`, `${h * 3.5}px`, `${h * 2}px`] }
              : { height: `${h * 2}px` }
          }
          transition={
            active
              ? { duration: 0.6 + i * 0.05, repeat: Infinity, ease: "easeInOut", delay: i * 0.06 }
              : { duration: 0.2 }
          }
        />
      ))}
    </button>
  );
};

export const Composer = ({
  value = "",
  onChange,
  onSubmit,
  state = "idle",
  onStartVoice,
  onStopVoice,
  onCancel,
  externalValueRef,
  tier = "free",
  onUpgradeClick,
}) => {
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const [files, setFiles] = useState([]);
  const [attachError, setAttachError] = useState(null);
  const [focused, setFocused] = useState(false);

  const canUpload = UPLOAD_TIERS.has(tier);
  const hasContent = value && value.trim().length > 0;

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = Math.min(el.scrollHeight, 168) + "px";
  }, [value]);

  useEffect(() => {
    if (externalValueRef) externalValueRef.current = textareaRef.current;
  }, [externalValueRef]);

  const isBusy = state === "thinking" || state === "speaking";
  const isListening = state === "listening";

  const totalBytes = useMemo(() => files.reduce((s, f) => s + f.size, 0), [files]);

  const handleSubmit = (e) => {
    e?.preventDefault?.();
    if (!hasContent || isBusy) return;
    onSubmit?.(value.trim(), files);
    setFiles([]);
    setAttachError(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSoundWaveClick = () => {
    if (isBusy) return onCancel?.();
    if (isListening) return onStopVoice?.();
    return onStartVoice?.();
  };

  const handleAttachClick = () => {
    if (!canUpload) {
      onUpgradeClick?.();
      return;
    }
    fileInputRef.current?.click();
  };

  const handleFilesPicked = (e) => {
    const picked = Array.from(e.target.files || []);
    e.target.value = "";
    if (!picked.length) return;
    setAttachError(null);

    const next = [...files];
    for (const f of picked) {
      if (next.length >= MAX_FILES) {
        setAttachError(`Maximum ${MAX_FILES} fichiers par message.`);
        break;
      }
      if (f.size > MAX_FILE_BYTES) {
        setAttachError(`"${f.name}" dépasse 10 Mo.`);
        continue;
      }
      if (next.some((x) => x.name === f.name && x.size === f.size)) continue;
      next.push(f);
    }
    const total = next.reduce((s, f) => s + f.size, 0);
    if (total > MAX_TOTAL_BYTES) {
      setAttachError(`Volume total > 25 Mo. Retire un fichier.`);
      return;
    }
    setFiles(next);
  };

  const removeFile = (idx) => {
    setFiles((arr) => arr.filter((_, i) => i !== idx));
    setAttachError(null);
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-3" data-testid="composer">
      {files.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2" data-testid="composer-attachments">
          {files.map((f, i) => (
            <div
              key={`${f.name}-${i}`}
              className="flex items-center gap-2 rounded-xl border border-[#E7C566]/25 bg-[#E7C566]/[0.04] pl-2 pr-1 py-1"
              data-testid={`composer-attachment-${i}`}
            >
              <FileText className="w-3.5 h-3.5 text-[#E7C566]" strokeWidth={1.6} />
              <span className="text-[12px] text-[#F1F4FA] max-w-[180px] truncate" title={f.name}>{f.name}</span>
              <span className="font-mono text-[10px] text-white/40 mr-1">{formatBytes(f.size)}</span>
              <button
                type="button"
                onClick={() => removeFile(i)}
                className="w-5 h-5 flex items-center justify-center rounded-md text-white/50 hover:text-white hover:bg-white/[0.06]"
                aria-label={`Retirer ${f.name}`}
                data-testid={`composer-attachment-remove-${i}`}
              >
                <X className="w-3 h-3" strokeWidth={2} />
              </button>
            </div>
          ))}
          <span className="self-center font-mono text-[10px] uppercase tracking-[0.18em] text-white/35">
            {formatBytes(totalBytes)} / 25 Mo
          </span>
        </div>
      )}

      {attachError && (
        <div
          className="mb-2 px-3 py-2 rounded-lg border border-red-500/30 bg-red-500/5 text-[12px] text-red-300"
          data-testid="composer-attachment-error"
        >
          {attachError}
        </div>
      )}

      {/* Halo bleu nuit profond derrière la barre, accentué au focus */}
      <motion.form
        onSubmit={handleSubmit}
        initial={{ opacity: 0, y: 12 }}
        animate={{
          opacity: 1,
          y: 0,
          scale: focused ? 1.01 : 1,
        }}
        transition={{ duration: 0.35 }}
        className="relative flex items-end gap-2 rounded-3xl px-3 py-2.5"
        style={{
          background: "rgba(10, 15, 31, 0.6)",
          backdropFilter: "blur(14px)",
          WebkitBackdropFilter: "blur(14px)",
          boxShadow: focused
            ? "0 0 0 1px rgba(23, 162, 184, 0.25), 0 18px 48px -16px rgba(23, 162, 184, 0.45), inset 0 1px 0 rgba(255,255,255,0.03)"
            : "0 0 0 1px rgba(255,255,255,0.04), 0 8px 30px -16px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.025)",
          transition: "box-shadow 320ms ease",
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPT}
          onChange={handleFilesPicked}
          className="hidden"
          data-testid="composer-file-input"
        />

        {/* Trombone d'élite — sans contour, juste icône qui réagit */}
        <button
          type="button"
          onClick={handleAttachClick}
          aria-label={canUpload ? "Joindre un fichier" : "Activer un plan pour joindre un fichier"}
          title={canUpload ? "PDF, DOCX, TXT, MD · 10 Mo / fichier" : "Upload réservé aux plans Creator / Infinite"}
          disabled={isBusy}
          className={`w-9 h-9 flex items-center justify-center self-end pb-0.5 transition-all duration-200
            ${canUpload
              ? "text-[#E7C566]/80 hover:text-[#E7C566] hover:scale-110"
              : "text-white/30 hover:text-white/55"}`}
          data-testid="composer-attach-button"
        >
          {canUpload ? <Paperclip className="w-[18px] h-[18px]" strokeWidth={1.7} /> : <Lock className="w-4 h-4" strokeWidth={1.7} />}
        </button>

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
            files.length ? "Décris ce que tu veux faire avec ces fichiers…" :
            "Posez votre question…"
          }
          rows={1}
          disabled={isBusy}
          className="flex-1 resize-none bg-transparent outline-none border-0 font-sans text-[15px] text-[#F1F4FA]
            placeholder:text-white/35 leading-relaxed py-1.5 px-2 max-h-[168px] thin-scroll"
          data-testid="composer-input"
          style={{ scrollbarWidth: "thin", fontFamily: '"Urbanist", sans-serif' }}
        />

        <div className="flex items-center gap-1.5 self-end pb-0.5">
          {/* Onde sonore : remplace le micro statique */}
          <div
            onClick={handleSoundWaveClick}
            className={`flex items-center justify-center cursor-pointer rounded-full
              ${isListening ? "bg-[#17a2b8]/[0.10] shadow-[0_0_18px_rgba(23,162,184,0.40)]" : "hover:bg-white/[0.04]"}
              transition-all duration-200`}
            data-testid="composer-mic-wave"
          >
            <SoundWave active={isListening} />
          </div>

          {/* Bouton submit : MUTATION OR LIQUIDE dès la première lettre tapée */}
          <motion.button
            type="submit"
            disabled={!hasContent || isBusy}
            aria-label="Envoyer"
            animate={hasContent && !isBusy ? {
              boxShadow: [
                "0 4px 18px rgba(201,162,75,0.35)",
                "0 4px 24px rgba(231,197,102,0.55)",
                "0 4px 18px rgba(201,162,75,0.35)",
              ],
            } : { boxShadow: "0 0 0 rgba(0,0,0,0)" }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            className={`w-9 h-9 flex items-center justify-center rounded-full transition-all duration-300
              ${hasContent && !isBusy
                ? "bg-gradient-to-br from-[#C9A24B] to-[#E7C566] text-[#0A0F1F]"
                : "bg-white/[0.04] text-white/30"
              }`}
            data-testid="composer-submit"
            data-armed={hasContent && !isBusy ? "true" : "false"}
          >
            {isBusy ? <Loader2 className="w-4 h-4 animate-spin" strokeWidth={1.8} />
              : isListening ? <Square className="w-3.5 h-3.5" fill="currentColor" strokeWidth={0} />
              : <ArrowUp className="w-4 h-4" strokeWidth={2.4} />}
          </motion.button>
        </div>
      </motion.form>

      <div className="mt-2 flex items-center justify-between px-2 font-mono text-[10px] uppercase tracking-[0.28em] text-white/30">
        <span data-testid="composer-version">Laurent.ia · v1.2 · CVLN Group</span>
        <span className="hidden sm:inline">Entrée = envoyer</span>
      </div>
    </div>
  );
};

export default Composer;
