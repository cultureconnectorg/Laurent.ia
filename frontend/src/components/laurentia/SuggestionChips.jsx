import { motion } from "framer-motion";
import { PenLine, Compass, Lightbulb, Target, Coins, Code2 } from "lucide-react";

/**
 * SuggestionChips — propositions « verre noir » épurées.
 *
 * Spec v1.2-PRODUCTION : capsules backdrop-blur, bordure invisible white/5,
 * absorption de la lumière de l'orbe au hover (pas de changement de couleur de texte),
 * écrasement sous le doigt (active:scale-[0.98]). Le chip no-code arbore une couronne
 * d'or discrète.
 */
const DEFAULT_CHIPS = [
  {
    id: "plan-business",
    label: "Rédiger Plan Business d'Élite",
    subtitle: "Kowe Ètò Ìṣòwò",
    icon: PenLine,
    prompt:
      "Aide-moi à rédiger un plan d'affaires d'élite pour un projet de la Diaspora caribéenne. " +
      "Pose-moi d'abord 3 questions stratégiques pour cadrer le secteur, le marché cible et la traction. " +
      "Puis livre la structure complète (executive summary, marché, modèle économique, projections 36 mois, gouvernance).",
  },
  {
    id: "import-export",
    label: "Analyser Accord d'Import-Export",
    subtitle: "Analize kontra trans-Latlantik",
    icon: Compass,
    prompt:
      "J'ai un accord d'import-export entre Caraïbe et Europe à analyser. Je vais te coller les termes — " +
      "déconstruis-moi les risques fiscaux, douaniers et de change, puis liste les clauses à renégocier.",
  },
  {
    id: "innovation",
    label: "Générer Concepts d'Innovation Caribéenne",
    subtitle: "ቢዘሮ ፕላን · Innovation soso",
    icon: Lightbulb,
    prompt:
      "Génère-moi 5 concepts d'innovation business ancrés dans les forces de la Caraïbe " +
      "(remittances, tourisme, agro-industrie, culture, numérique). Chaque concept : pitch 2 lignes, " +
      "marché adressable estimé, premier MVP réalisable en 90 jours.",
  },
  {
    id: "croissance",
    label: "Structurer un Plan de Croissance",
    subtitle: "Mpango wa Ukuaji wa Biashara",
    icon: Target,
    prompt:
      "Mon entreprise stagne. Aide-moi à structurer un plan de croissance en 4 phases sur 12 mois. " +
      "Démarrons par 3 questions de diagnostic ciblées.",
  },
  {
    id: "tontine",
    label: "Analyser les Flux de Tontine Moderne",
    subtitle: "Soso lajan · Tontin' modèn",
    icon: Coins,
    prompt:
      "Analyse les flux financiers d'une tontine moderne (digitalisée, multi-pays). " +
      "Modélise-moi les flux mensuels, le risque de défaut par participant, et propose-moi un schéma " +
      "Recharts (<json>) qui montre la cinétique d'épargne sur 12 mois pour 8 participants.",
  },
  {
    id: "no-code",
    label: "Développer une Application No-Code Souveraine",
    subtitle: "Andika Mpango wa Biashara · ਬੀਤ ਪਲਾਨ",
    icon: Code2,
    prompt:
      "Crée-moi une mini-app no-code totalement fonctionnelle en HTML/CSS/JS pur, " +
      "encapsulée dans un bloc <artifact>. Sujet : calculatrice de tontine moderne (champs : montant " +
      "individuel, nombre de participants, durée). Affichage soigné, charte bleu nuit et or, sans bibliothèque externe.",
  },
];

export const SuggestionChips = ({ chips = DEFAULT_CHIPS, onPick, disabled = false }) => {
  return (
    <div className="w-full max-w-3xl mx-auto px-4" data-testid="suggestion-chips">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {chips.map((chip, i) => {
          const Icon = chip.icon || Lightbulb;
          const isNoCode = chip.id === "no-code";
          return (
            <motion.button
              key={chip.id}
              type="button"
              onClick={() => !disabled && onPick?.(chip.prompt)}
              disabled={disabled}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.18 + i * 0.05, duration: 0.4 }}
              whileTap={!disabled ? { scale: 0.98 } : {}}
              className={`group relative flex items-center gap-3 px-4 py-3 rounded-2xl
                bg-[rgba(10,15,31,0.55)] backdrop-blur-[12px] border border-white/[0.05]
                hover:bg-[rgba(10,15,31,0.7)] hover:border-white/[0.10]
                text-left transition-all duration-200
                disabled:opacity-40 disabled:cursor-not-allowed`}
              style={{
                boxShadow: "inset 0 1px 0 rgba(255,255,255,0.02), 0 8px 24px -16px rgba(0,0,0,0.6)",
              }}
              data-testid={`chip-${chip.id}`}
            >
              <span
                className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center
                  ${isNoCode
                    ? "bg-gradient-to-br from-[#C9A24B]/30 to-[#E7C566]/10 ring-1 ring-[#C9A24B]/40"
                    : "bg-white/[0.03] ring-1 ring-white/[0.05]"}
                  transition-transform duration-200 group-hover:scale-105`}
              >
                <Icon
                  className={`w-4 h-4 ${isNoCode ? "text-[#E7C566]" : "text-[#17a2b8]"}`}
                  strokeWidth={1.7}
                />
              </span>
              <div className="flex flex-col items-start min-w-0 flex-1">
                <span
                  className="text-[14px] sm:text-[13.5px] leading-tight text-[#EDF1F7] font-medium truncate w-full"
                  style={{ fontFamily: '"Urbanist", sans-serif', letterSpacing: "0.005em" }}
                  data-testid={`chip-${chip.id}-label`}
                >
                  {chip.label}
                </span>
                {chip.subtitle && (
                  <span
                    className={`mt-0.5 font-mono text-[10px] uppercase tracking-[0.18em] truncate w-full ${
                      isNoCode ? "text-[#C9A24B]/65" : "text-[#17a2b8]/55"
                    }`}
                    style={{ fontFamily: '"Urbanist", sans-serif', fontWeight: 500 }}
                    data-testid={`chip-${chip.id}-subtitle`}
                  >
                    {chip.subtitle}
                  </span>
                )}
              </div>
              {isNoCode && (
                <span
                  className="absolute top-1.5 right-2 font-mono text-[8px] uppercase tracking-[0.22em] text-[#C9A24B]"
                  aria-hidden="true"
                >
                  ◇
                </span>
              )}
            </motion.button>
          );
        })}
      </div>
    </div>
  );
};

export default SuggestionChips;
