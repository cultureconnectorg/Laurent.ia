import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUp, Mic, Square, Loader2, Paperclip, X, FileText, Lock } from "lucide-react";

/**
 * Composer — barre d'entrée style Claude / ChatGPT.
 *  - Textarea auto-grow
 *  - Bouton micro (toggle voice mode)
 *  - Bouton trombone (pièces jointes — Creator/Infinite seulement)
 *  - Bouton envoyer
 *  - "Laurent.ia v0.1" sous l'input
 *
 * Props:
 *   state: "idle" | "listening" | "thinking" | "speaking"
 *   value, onChange, onSubmit(text, files), onStartVoice, onStopVoice, onCancel
 *   tier: "free" | "creator" | "infinite"  — gate upload
 *   onUpgradeClick?: () => void          — appelé si tier free tente upload
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

  const canUpload = UPLOAD_TIERS.has(tier);

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

  const totalBytes = useMemo(() => files.reduce((s, f) => s + f.size, 0), [files]);

  const handleSubmit = (e) => {
    e?.preventDefault?.();
    if (!value.trim() || isBusy) return;
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

  const handleVoiceClick = () => {
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
    e.target.value = ""; // reset so same file can be re-picked
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
    <div className="w-full max-w-2xl mx-auto px-4 pb-3" data-testid="composer">
      {/* Liste des pièces jointes */}
      {files.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2" data-testid="composer-attachments">
          {files.map((f, i) => (
            <div
              key={`${f.name}-${i}`}
              className="flex items-center gap-2 rounded-xl border border-[#E7C566]/25 bg-[#E7C566]/[0.04] pl-2 pr-1 py-1"
              data-testid={`composer-attachment-${i}`}
            >
              <FileText className="w-3.5 h-3.5 text-[#E7C566]" strokeWidth={1.6} />
              <span className="text-[12px] text-[#F1F4FA] max-w-[180px] truncate" title={f.name}>
                {f.name}
              </span>
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

      <motion.form
        onSubmit={handleSubmit}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className={`composer-ring relative flex items-end gap-2 rounded-3xl border bg-white/[0.03] backdrop-blur-xl px-3 py-2.5 ${
          isListening ? "border-[#6BA8FF]/50 shadow-[0_0_30px_rgba(107,168,255,0.22)]" : "border-white/[0.07]"
        }`}
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

        <button
          type="button"
          onClick={handleAttachClick}
          aria-label={canUpload ? "Joindre un fichier" : "Activer un plan pour joindre un fichier"}
          title={canUpload ? "PDF, DOCX, TXT, MD · 10 Mo / fichier" : "Upload réservé aux plans Creator / Infinite"}
          className={`w-9 h-9 flex items-center justify-center rounded-full transition-all duration-200 self-end pb-0.5 ${
            canUpload
              ? "bg-white/[0.04] border border-white/[0.08] text-white/70 hover:text-[#E7C566] hover:bg-[#E7C566]/[0.06] hover:border-[#E7C566]/30"
              : "bg-white/[0.02] border border-white/[0.06] text-white/30 hover:text-white/50"
          }`}
          data-testid="composer-attach-button"
          disabled={isBusy}
        >
          {canUpload ? (
            <Paperclip className="w-4 h-4" strokeWidth={1.7} />
          ) : (
            <Lock className="w-3.5 h-3.5" strokeWidth={1.8} />
          )}
        </button>

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isListening ? "Laurent.ia écoute…" :
            isBusy ? "Laurent.ia réfléchit…" :
            files.length ? "Décris ce que tu veux faire avec ces fichiers…" :
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
