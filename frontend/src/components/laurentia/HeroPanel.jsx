import { motion } from "framer-motion";
import OrbeLaurentIA from "./OrbeLaurentIA";

/**
 * HeroPanel v1.2 — orb agrandi, typographie blindée (Cormorant Garamond + Urbanist),
 * couleurs souveraines : INTELLIGENCE SOUVERAINE en teal `#17a2b8`, Laurent.ia
 * en italique or `#E7C566`.
 */
export const HeroPanel = ({ state = "idle", subtitle = "Posez votre question. Je vous écoute." }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.55, ease: "easeOut" }}
      className="flex flex-col items-center justify-center text-center px-6 py-3 sm:py-6"
      data-testid="hero-panel"
    >
      <div className="block sm:hidden">
        <OrbeLaurentIA state={state} size={140} />
      </div>
      <div className="hidden sm:block">
        <OrbeLaurentIA state={state} size={260} />
      </div>

      <div
        className="mt-3 sm:mt-6 font-mono text-[10px] sm:text-[11px] uppercase text-[#17a2b8]"
        style={{ letterSpacing: "0.32em", fontFamily: '"Urbanist", sans-serif' }}
        data-testid="hero-eyebrow"
      >
        Intelligence souveraine
      </div>
      <h1
        className="mt-1 sm:mt-3 italic text-3xl sm:text-5xl lg:text-6xl tracking-tight"
        style={{
          fontFamily: '"Cormorant Garamond", Georgia, serif',
          fontWeight: 500,
          background: "linear-gradient(180deg, #F4E0AA 0%, #C9A24B 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        }}
        data-testid="hero-title"
      >
        Laurent.ia
      </h1>
      <p
        className="mt-1.5 sm:mt-3 max-w-md text-[13px] sm:text-base text-white/55 leading-relaxed hidden sm:block"
        style={{ fontFamily: '"Urbanist", sans-serif' }}
        data-testid="hero-subtitle"
      >
        {subtitle}
      </p>
    </motion.div>
  );
};

export default HeroPanel;
