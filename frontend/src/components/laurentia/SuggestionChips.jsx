import { motion } from "framer-motion";
import { PenLine, FileText, Lightbulb, Search, Target, Code2 } from "lucide-react";

/**
 * SuggestionChips — propositions intelligentes affichées en hero.
 *
 * Par défaut : 6 prompts universels (productivité/créativité/no-code) — pas de
 * référence à l'écosystème interne (FREK / CC / Kiltikonet etc.).
 *
 * Le parent peut injecter des `chips` personnalisés issus de l'historique
 * utilisateur pour rendre les suggestions plus pertinentes au fil du temps.
 */
const DEFAULT_CHIPS = [
  { id: "write",      label: "Aide-moi à écrire",       icon: PenLine,    prompt: "Aide-moi à écrire un texte clair et impactant. Pose-moi d'abord les bonnes questions pour cadrer." },
  { id: "summarize",  label: "Synthétise une idée",     icon: FileText,   prompt: "Je veux synthétiser une idée complexe en quelques points clairs. Démarrons." },
  { id: "brainstorm", label: "Brainstorm créatif",      icon: Lightbulb,  prompt: "Je veux brainstormer une idée. Pose-moi 3 questions pour démarrer." },
  { id: "no-code",    label: "Crée-moi une mini-app",   icon: Code2,      prompt: "Crée-moi une mini-app fonctionnelle en HTML/CSS/JS pur, encapsulée dans un bloc <artifact>. Sujet : calculatrice de tontine moderne avec champs montant, nombre de participants, durée. Affichage soigné, charte bleu nuit et or." },
  { id: "analyze",    label: "Analyse un texte",        icon: Search,     prompt: "J'ai un texte à analyser. Je vais te le coller — explique-moi ce que tu vois." },
  { id: "plan",       label: "Plan d'action",           icon: Target,     prompt: "Aide-moi à construire un plan d'action sur un sujet précis." },
];

export const SuggestionChips = ({ chips = DEFAULT_CHIPS, onPick, disabled = false }) => {
  return (
    <div className="w-full max-w-2xl mx-auto px-4" data-testid="suggestion-chips">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
        {chips.map((chip, i) => {
          const Icon = chip.icon || Lightbulb;
          const isNoCode = chip.id === "no-code";
          return (
            <motion.button
              key={chip.id}
              type="button"
              onClick={() => !disabled && onPick?.(chip.prompt)}
              disabled={disabled}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.05, duration: 0.35 }}
              whileHover={!disabled ? { y: -1 } : {}}
              whileTap={!disabled ? { scale: 0.97 } : {}}
              className={`group flex items-center justify-center gap-2 px-3 py-2.5 rounded-full
                ${isNoCode
                  ? "bg-gradient-to-r from-[#C9A24B]/[0.10] to-[#E7C566]/[0.04] border border-[#E7C566]/30 hover:border-[#E7C566]/55 hover:from-[#C9A24B]/[0.18]"
                  : "bg-white/[0.03] border border-white/[0.07] hover:bg-white/[0.05] hover:border-[#6BA8FF]/35"}
                text-white/80 text-sm font-sans transition-colors duration-200
                disabled:opacity-40 disabled:cursor-not-allowed`}
              data-testid={`chip-${chip.id}`}
            >
              <Icon className={`w-3.5 h-3.5 ${isNoCode ? "text-[#E7C566]" : "text-[#6BA8FF]/80 group-hover:text-[#6BA8FF]"}`} strokeWidth={1.6} />
              <span className={`truncate ${isNoCode ? "text-[#F4E0AA]" : ""}`}>{chip.label}</span>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
};

export default SuggestionChips;
