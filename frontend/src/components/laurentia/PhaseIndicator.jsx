import { motion, AnimatePresence } from "framer-motion";
import { Cpu, Sparkles, BarChart3, Wifi } from "lucide-react";

/**
 * PhaseIndicator — Affiche le statut courant du moteur Laurent.ia
 * pendant le streaming SSE. Style emergent.sh : message + animation.
 *
 * phase: "connecting" | "analyzing" | "synthesizing" | "rendering" | null
 */
const PHASES = {
  connecting:   { label: "Connexion à la matrice…",      Icon: Wifi,       color: "#5BA0FF" },
  analyzing:    { label: "Analyse contextuelle…",         Icon: Cpu,        color: "#6BA8FF" },
  synthesizing: { label: "Synthèse souveraine…",          Icon: Sparkles,   color: "#9BC4FF" },
  rendering:    { label: "Génération du graphique…",      Icon: BarChart3,  color: "#E7C566" },
};

export const PhaseIndicator = ({ phase }) => {
  return (
    <AnimatePresence mode="wait">
      {phase && PHASES[phase] && (
        <motion.div
          key={phase}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.28 }}
          className="flex items-center gap-2"
          data-testid={`phase-indicator-${phase}`}
          data-phase={phase}
        >
          {(() => {
            const { Icon, color, label } = PHASES[phase];
            return (
              <>
                <motion.span
                  className="inline-flex items-center justify-center w-5 h-5 rounded-full"
                  style={{ background: `${color}22`, color }}
                  animate={{ scale: [1, 1.18, 1] }}
                  transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
                >
                  <Icon className="w-3 h-3" strokeWidth={2} />
                </motion.span>
                <span
                  className="font-mono text-[10px] uppercase tracking-[0.22em]"
                  style={{ color }}
                >
                  {label}
                </span>
                <span className="dot-typing leading-none" style={{ color }}>
                  <span>·</span><span>·</span><span>·</span>
                </span>
              </>
            );
          })()}
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default PhaseIndicator;
