import { motion } from "framer-motion";
import OrbeLaurentIA from "./OrbeLaurentIA";

/**
 * HeroPanel — affiché quand la conversation est vide.
 * Reproduit l'écran d'accueil CVL Brain : orbe + INTELLIGENCE + brand + sous-titre.
 */
export const HeroPanel = ({ state = "idle", subtitle = "Posez vos questions. Man la pou ou." }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.55, ease: "easeOut" }}
      className="flex flex-col items-center justify-center text-center px-6 py-8"
      data-testid="hero-panel"
    >
      <OrbeLaurentIA state={state} size={220} />

      <div className="mt-8 font-mono text-[11px] uppercase tracking-[0.32em] text-[#6BA8FF]/70" data-testid="hero-eyebrow">
        Intelligence souveraine
      </div>
      <h1 className="mt-2 font-serif italic text-4xl sm:text-5xl text-[#F1F4FA] tracking-tight" data-testid="hero-title">
        Laurent.ia
      </h1>
      <p className="mt-3 max-w-md font-sans text-[15px] sm:text-base text-white/55 leading-relaxed" data-testid="hero-subtitle">
        {subtitle}
      </p>
    </motion.div>
  );
};

export default HeroPanel;
