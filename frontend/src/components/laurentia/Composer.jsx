import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Square, Loader2, X, FileText, Lock } from "lucide-react";

/**
 * Composer v1.2-PRODUCTION — fente noire translucide + Ancrage linguistique.
 *
 *  • Placeholder principal en CRÉOLE : "Djis poze keksion ou..."
 *  • Bandeau multilingue défilant sous la barre : Yoruba, Swahili, Amharique, Wolof...
 *  • Onde sonore encapsulée dans cercle bleu néon #1D8CF8
 *  • Trombone wireframe filaire (sans fond)
 *  • Flèche-Sagaie sculptée avec particules d'or au survol/saisie
 *  • Focus : scale 1.01 + halo cyan profond
 */
const UPLOAD_TIERS = new Set(["creator", "infinite"]);
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const MAX_TOTAL_BYTES = 25 * 1024 * 1024;
const MAX_FILES = 4;
const ACCEPT = ".pdf,.docx,.txt,.md,.markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown";

// Concepts de commerce, plan, échange dans les langues de la Diaspora.
// Sera défilé en boucle sous le composer. Sépare visuellement avec '·'.
const DIASPORA_CONCEPTS = [
  "Kowe Ètò Ìṣòwò",                  // Yoruba — Plan de commerce
  "ቢዘሮ ፕላን",                          // Amharique — Plan business
  "Andika Mpango wa Biashara",       // Swahili — Rédiger plan d'affaires
  "ਬੀਤ ਪਲਾਨ",                          // Punjabi — Plan d'avenir
  "Soso lajan · Tontin' modèn",      // Créole — Tontine moderne
  "Bògòlanfini · Òṣiṣẹ́",              // Bambara/Yoruba — Tisser le travail
  "Analize kontra trans-Latlantik",  // Créole haïtien — Accord trans-Atlantique
  "Tey ñàddu réew",                  // Wolof — Diriger le pays
  "Mpango wa Ukuaji wa Biashara",    // Swahili — Plan de croissance business
];

function formatBytes(n) {
  if (n < 1024) return `${n} o`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} Ko`;
  return `${(n / 1024 / 1024).toFixed(1)} Mo`;
}

/** Onde sonore animée — bars verticales OR/BLEU, encapsulée dans un cercle bleu néon */
const SoundWave = ({ active }) => {
  const bars = [3, 7, 5, 9, 4, 8, 6];
  return (
    <div
      className="relative flex items-end gap-[3px] h-6 px-2"
      data-testid="composer-sound-wave"
      data-active={active ? "true" : "false"}
      role="button"
      aria-label={active ? "Dictée en cours — clique pour arrêter" : "Démarrer la dictée vocale"}
    >
      {/* Cercle de résonance bleu néon — visible uniquement quand active */}
      {active && <span className="sonic-ring sonic-ring-pulse" aria-hidden="true" />}
      {bars.map((h, i) => (
        <motion.span
          key={i}
          className="relative w-[2.5px] rounded-full"
          style={{
            background: active
              ? "linear-gradient(180deg, #E7C566 0%, #1D8CF8 100%)"
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
    </div>
  );
};

/** Flèche-Sagaie : pièce sculptée or avec texture de particules */
const GoldArrow = ({ armed }) => (
  <span className="relative w-4 h-4 flex items-center justify-center" aria-hidden="true">
    <svg viewBox="0 0 24 24" width="16" height="16" className="relative z-10">
      <defs>
        <linearGradient id="arrow-gold" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#F4E0AA" />
          <stop offset="50%" stopColor="#E7C566" />
          <stop offset="100%" stopColor="#C9A24B" />
        </linearGradient>
      </defs>
      <path
        d="M12 3 L12 21 M5 10 L12 3 L19 10"
        stroke={armed ? "url(#arrow-gold)" : "currentColor"}
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
    {armed && (
      <>
        {/* Particules d'or scintillantes autour de la flèche */}
        {[0, 1, 2, 3].map((i) => {
          const angle = (i / 4) * Math.PI * 2;
          const r = 10;
          return (
            <motion.span
              key={i}
              className="absolute w-[3px] h-[3px] rounded-full"
              style={{
                left: `calc(50% + ${Math.cos(angle) * r}px)`,
                top: `calc(50% + ${Math.sin(angle) * r}px)`,
                background: "#E7C566",
                boxShadow: "0 0 5px #E7C566",
                transform: "translate(-50%, -50%)",
              }}
              animate={{ opacity: [0, 1, 0], scale: [0.5, 1, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.3 }}
            />
          );
        })}
      </>
    )}
  </span>
);

/** Trombone wireframe filaire (or fin) */
const WirePaperclip = ({ tone = "gold" }) => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" aria-hidden="true">
    <path
      d="M21.44 11.05 12.25 20.24a6 6 0 0 1-8.49-8.49l8.57-8.57a4 4 0 0 1 5.66 5.66l-8.58 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"
      stroke={tone === "gold" ? "#E7C566" : "rgba(255,255,255,0.35)"}
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

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
    // Le trombone ouvre TOUJOURS l'input file natif caché. Si le tier ne permet
    // pas l'upload, le serveur renverra 403 au moment du submit et le frontend
    // déclenchera la PricingModal. C'est plus naturel : tu choisis ton document,
    // tu vois ce que tu pourrais faire, puis le paywall s'active.
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

        {/* Trombone wireframe — toujours interactif, ouvre le file picker natif.
            Si tier=Free, on ajoute un petit cadenas en sur-couche pour signaler
            le paywall qui arrivera au submit. */}
        <button
          type="button"
          onClick={handleAttachClick}
          aria-label="Joindre un fichier"
          title={canUpload ? "PDF, DOCX, TXT, MD · 10 Mo / fichier" : "Joindre un fichier — Creator requis pour l'envoi"}
          disabled={isBusy}
          className="relative w-9 h-9 flex items-center justify-center self-end pb-0.5 transition-transform duration-200 hover:scale-110"
          data-testid="composer-attach-button"
          data-can-upload={canUpload ? "true" : "false"}
        >
          <WirePaperclip tone="gold" />
          {!canUpload && (
            <span
              className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-[#0A0F1F] flex items-center justify-center ring-1 ring-[#C9A24B]/40"
              aria-hidden="true"
            >
              <Lock className="w-2 h-2 text-[#C9A24B]" strokeWidth={2.4} />
            </span>
          )}
        </button>

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={
            isListening ? "Laurent.ia ap koute…" :
            isBusy ? "Laurent.ia ap reflechi…" :
            files.length ? "Décris ce que tu veux faire avec ces fichiers…" :
            "Djis poze keksion ou…"
          }
          rows={1}
          disabled={isBusy}
          className="flex-1 resize-none bg-transparent outline-none border-0 font-sans text-[15px] text-[#F1F4FA]
            placeholder:text-white/40 leading-relaxed py-1.5 px-2 max-h-[168px] thin-scroll"
          data-testid="composer-input"
          style={{ scrollbarWidth: "thin", fontFamily: '"Urbanist", sans-serif' }}
        />

        <div className="flex items-center gap-1.5 self-end pb-0.5">
          {/* Onde sonore : remplace le micro statique — clic active la dictée */}
          <button
            type="button"
            onClick={handleSoundWaveClick}
            className={`relative flex items-center justify-center rounded-full p-1.5
              ${isListening ? "bg-[#1D8CF8]/[0.06]" : "hover:bg-white/[0.04]"}
              transition-all duration-200`}
            aria-label={isListening ? "Arrêter la dictée" : "Démarrer la dictée vocale"}
            data-testid="composer-mic-wave"
          >
            <SoundWave active={isListening} />
          </button>

          {/* Flèche-Sagaie — mutation OR LIQUIDE dès le 1er caractère */}
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
                : "bg-white/[0.04] text-white/35"
              }`}
            data-testid="composer-submit"
            data-armed={hasContent && !isBusy ? "true" : "false"}
          >
            {isBusy ? <Loader2 className="w-4 h-4 animate-spin" strokeWidth={1.8} />
              : isListening ? <Square className="w-3.5 h-3.5" fill="currentColor" strokeWidth={0} />
              : <GoldArrow armed={hasContent} />}
          </motion.button>
        </div>
      </motion.form>

      {/* Bandeau multilingue défilant — ancrage culturel permanent */}
      <div
        className="mt-2 overflow-hidden px-2"
        data-testid="diaspora-marquee-container"
        aria-hidden="true"
      >
        <div
          className="diaspora-marquee font-mono text-[10px] uppercase tracking-[0.28em] text-[#C9A24B]/40"
          style={{ fontFamily: '"Urbanist", sans-serif', fontWeight: 500 }}
        >
          {[...DIASPORA_CONCEPTS, ...DIASPORA_CONCEPTS].map((c, i) => (
            <span key={i} className="whitespace-nowrap px-3">
              {c} <span className="text-[#17a2b8]/35 mx-2">·</span>
            </span>
          ))}
        </div>
      </div>

      <div className="mt-1 flex items-center justify-between px-2 font-mono text-[10px] uppercase tracking-[0.28em] text-white/30">
        <span data-testid="composer-version">Laurent.ia · v1.2 · CVLN Group</span>
        <span className="hidden sm:inline">Entrée = envoyer</span>
      </div>
    </div>
  );
};

export default Composer;
