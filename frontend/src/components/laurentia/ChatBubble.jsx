import { motion } from "framer-motion";
import { useState } from "react";
import { FileText, FileType2, Coins, Loader2, Check, AlertCircle } from "lucide-react";
import RichContent from "./RichContent";

/**
 * ChatBubble — bulle utilisateur ou assistant.
 *
 * Props:
 *   role: "user" | "assistant"
 *   text: string — markdown pour assistant, plain pour user
 *   streaming: bool
 *   files: array — pour role=user, liste {name, size, kind?, pages?, chars?, digested?}
 *                  enrichie côté hook après réception du meta SSE.
 *   onExportPdf: fn — appelée pour exporter ce message en PDF (assistant only)
 */

const KIND_LABEL = {
  pdf: "PDF",
  docx: "DOCX",
  txt: "TXT",
  md: "MD",
};

const FILE_ICONS = {
  pdf: FileType2,
  docx: FileText,
  txt: FileText,
  md: FileText,
};

function pageWord(n, kind) {
  if (!n) return "";
  if (kind === "pdf") return `${n} page${n > 1 ? "s" : ""} digérée${n > 1 ? "s" : ""}`;
  if (kind === "docx") return `${n} paragraphe${n > 1 ? "s" : ""} digéré${n > 1 ? "s" : ""}`;
  return `${n} ligne${n > 1 ? "s" : ""} digérée${n > 1 ? "s" : ""}`;
}

const FileChip = ({ file }) => {
  const kind = file.kind || "txt";
  const Icon = FILE_ICONS[kind] || FileText;
  const digested = !!file.digested;
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-lg px-2 py-1 border ${
        digested
          ? "border-[#C9A24B]/55 bg-gradient-to-r from-[#C9A24B]/[0.12] to-[#E7C566]/[0.06] shadow-[0_0_12px_rgba(201,162,75,0.15)]"
          : "border-white/10 bg-white/[0.04]"
      }`}
      data-testid="user-bubble-file-chip"
      data-digested={digested ? "true" : "false"}
    >
      <Icon
        className={`w-3.5 h-3.5 ${digested ? "text-[#E7C566]" : "text-white/60"}`}
        strokeWidth={1.7}
      />
      <span className={`text-[12px] font-medium ${digested ? "text-[#F4E0AA]" : "text-white/80"} max-w-[160px] truncate`} title={file.name}>
        {file.name}
      </span>
      <span className={`font-mono text-[9.5px] uppercase tracking-[0.18em] ${digested ? "text-[#C9A24B]" : "text-white/40"}`}>
        {KIND_LABEL[kind] || kind?.toUpperCase()}{file.pages ? ` · ${pageWord(file.pages, kind)}` : ""}
      </span>
      {digested && <Check className="w-3 h-3 text-[#E7C566]" strokeWidth={2.2} />}
    </div>
  );
};

export const ChatBubble = ({
  role = "assistant",
  text = "",
  streaming = false,
  files,
  onExportPdf,
  onExportStart,
  onExportEnd,
  onPaywall,
}) => {
  const isUser = role === "user";
  const [exportState, setExportState] = useState("idle"); // idle | loading | done | error
  const [exportErr, setExportErr] = useState(null);

  const hasFiles = Array.isArray(files) && files.length > 0;
  const canExport = !isUser && !streaming && text && text.length > 80 && typeof onExportPdf === "function";

  const handleExport = async () => {
    if (exportState === "loading") return;
    setExportState("loading");
    setExportErr(null);
    onExportStart?.();
    try {
      // Titre auto : première ligne markdown ou tronqué
      const firstLine = (text.split("\n").find((l) => l.trim()) || "Note Laurent.ia")
        .replace(/^[#>*\-\s]+/, "")
        .slice(0, 90);
      const result = await onExportPdf({
        title: firstLine,
        subtitle: "Note Laurent.ia · CVLN Group",
        content_md: text,
      });
      setExportState("done");
      onExportEnd?.(result);
      setTimeout(() => setExportState("idle"), 2500);
    } catch (e) {
      if (e?.status === 402) {
        onPaywall?.(e.payload || {});
        setExportState("idle");
        onExportEnd?.(null);
        return;
      }
      setExportState("error");
      setExportErr(e.message || "Échec de l'export");
      onExportEnd?.(null);
      setTimeout(() => setExportState("idle"), 3500);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"} bubble-in`}
      data-testid={isUser ? "user-bubble" : "assistant-bubble"}
    >
      <div className={`max-w-[85%] sm:max-w-[78%] rounded-2xl px-4 py-3 ${
        isUser
          ? "bg-gradient-to-br from-[#1E3A6E] to-[#2A5BAF]/85 border border-[#3B6FCC]/30 shadow-[0_6px_24px_rgba(45,111,224,0.18)]"
          : "bg-white/[0.025] border border-white/[0.06]"
      }`}>
        <div
          className={`font-mono text-[10px] uppercase tracking-[0.22em] mb-1.5 ${
            isUser ? "text-[#9FC4FF]" : "text-[#6BA8FF]"
          }`}
          data-testid={isUser ? "user-bubble-label" : "assistant-bubble-label"}
        >
          {isUser ? "Toi" : "Laurent.ia"}
        </div>

        {hasFiles && (
          <div className="mb-2 flex flex-wrap gap-1.5" data-testid="user-bubble-files">
            {files.map((f, i) => (
              <FileChip key={`${f.name}-${i}`} file={f} />
            ))}
          </div>
        )}

        <div className="font-sans text-[15px] sm:text-base leading-relaxed text-[#F1F4FA] break-words">
          {isUser ? (
            <div className="whitespace-pre-wrap">{text}</div>
          ) : (
            <div>
              <RichContent text={text || ""} />
              {streaming && (
                <span className="inline-block w-[7px] h-[16px] align-[-2px] ml-1 bg-[#6BA8FF]/85 animate-pulse rounded-[1px]" />
              )}
            </div>
          )}
        </div>

        {canExport && (
          <div className="mt-2.5 flex items-center justify-end" data-testid="assistant-export-row">
            <button
              type="button"
              onClick={handleExport}
              disabled={exportState === "loading"}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-mono uppercase tracking-[0.16em] transition-all duration-200
                ${exportState === "error"
                  ? "border border-red-500/40 bg-red-500/[0.06] text-red-300"
                  : exportState === "done"
                    ? "border border-[#E7C566]/60 bg-[#E7C566]/[0.10] text-[#F4E0AA]"
                    : "border border-[#C9A24B]/35 bg-[#C9A24B]/[0.06] text-[#E7C566] hover:bg-[#C9A24B]/[0.12] hover:border-[#C9A24B]/60 hover:shadow-[0_0_16px_rgba(201,162,75,0.25)]"
                }`}
              title={exportErr || "Exporter en PDF souverain"}
              data-testid="assistant-export-pdf-button"
            >
              {exportState === "loading" ? (
                <Loader2 className="w-3 h-3 animate-spin" strokeWidth={2} />
              ) : exportState === "error" ? (
                <AlertCircle className="w-3 h-3" strokeWidth={2} />
              ) : (
                <Coins className="w-3 h-3" strokeWidth={2} />
              )}
              <span>
                {exportState === "loading" ? "Génération…" :
                 exportState === "done" ? "PDF téléchargé" :
                 exportState === "error" ? "Échec" :
                 "Exporter PDF"}
              </span>
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default ChatBubble;
