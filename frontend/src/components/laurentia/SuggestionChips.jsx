import { motion } from "framer-motion";
import { Fingerprint, Sparkles, Music, Building2, Briefcase, Coins } from "lucide-react";

/**
 * SuggestionChips — quick-action pills (style Kiltikonet home).
 * 6 entrées par défaut. Click → injecte le prompt associé dans le composer.
 */
const DEFAULT_CHIPS = [
  { id: "kiltikonet", label: "Kiltikonet",  icon: Sparkles,    prompt: "Présente-moi Kiltikonet et ce que ça veut dire pour moi." },
  { id: "jcc",        label: "Jeton CC",    icon: Coins,       prompt: "Comment fonctionnent les Jetons CC et à quoi je peux les utiliser ?" },
  { id: "cc2026",     label: "CC2026",      icon: Building2,   prompt: "Donne-moi le programme essentiel du festival CC2026." },
  { id: "frek",       label: "Mon FREK-ID", icon: Fingerprint, prompt: "Explique-moi mon profil culturel FREK-ID en 7 dimensions." },
  { id: "pro",        label: "Espace Pro",  icon: Briefcase,   prompt: "Qu'est-ce que l'Espace Pro m'apporte ?" },
  { id: "culture",    label: "Culture",     icon: Music,       prompt: "Parle-moi de la musique afro-caribéenne d'aujourd'hui." },
];

export const SuggestionChips = ({ chips = DEFAULT_CHIPS, onPick, disabled = false }) => {
  return (
    <div className="w-full max-w-2xl mx-auto px-4" data-testid="suggestion-chips">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
        {chips.map((chip, i) => {
          const Icon = chip.icon;
          return (
            <motion.button
              key={chip.id}
              type="button"
              onClick={() => !disabled && onPick?.(chip.prompt)}
              disabled={disabled}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.05, duration: 0.35 }}
              whileHover={!disabled ? { y: -1, borderColor: "rgba(107,168,255,0.35)" } : {}}
              whileTap={!disabled ? { scale: 0.97 } : {}}
              className="group flex items-center justify-center gap-2 px-3 py-2.5 rounded-full
                bg-white/[0.03] border border-white/[0.07] hover:bg-white/[0.05]
                text-white/80 text-sm font-sans transition-colors duration-200
                disabled:opacity-40 disabled:cursor-not-allowed"
              data-testid={`chip-${chip.id}`}
            >
              <Icon className="w-3.5 h-3.5 text-[#6BA8FF]/80 group-hover:text-[#6BA8FF]" strokeWidth={1.6} />
              <span className="truncate">{chip.label}</span>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
};

export default SuggestionChips;
