/**
 * EnergyBraids — Tresses de Données : flux vectoriels d'or et bleu reliant
 * le composer et les capsules de suggestion à l'orbe central. Z-index 0,
 * pointer-events:none, drop-shadow gold/blue pour la profondeur.
 *
 * Métaphore : flux financiers de la tontine moderne et réseaux transcontinentaux.
 */
import { motion } from "framer-motion";

const GOLD = "#C9A24B";
const GOLD_BRIGHT = "#E7C566";
const BLUE = "#1D8CF8";
const BLUE_DEEP = "#17a2b8";

// Chaque tresse : path bezier qui part du bas (x, 100%) et converge vers
// l'orbe (x:50%, y:42%). On varie les courbures pour donner un effet "racines".
const BRAIDS = [
  { from: 15,  ctrl1x: 12,  ctrl1y: 80, ctrl2x: 28, ctrl2y: 60, color: "gold",  width: 0.6, delay: 0.0 },
  { from: 22,  ctrl1x: 18,  ctrl1y: 72, ctrl2x: 35, ctrl2y: 55, color: "blue",  width: 0.5, delay: 0.4 },
  { from: 32,  ctrl1x: 26,  ctrl1y: 76, ctrl2x: 42, ctrl2y: 52, color: "gold",  width: 0.4, delay: 0.8 },
  { from: 42,  ctrl1x: 38,  ctrl1y: 68, ctrl2x: 46, ctrl2y: 48, color: "blue",  width: 0.55, delay: 1.2 },
  { from: 50,  ctrl1x: 50,  ctrl1y: 70, ctrl2x: 50, ctrl2y: 50, color: "gold",  width: 0.7, delay: 0.2 },
  { from: 58,  ctrl1x: 62,  ctrl1y: 68, ctrl2x: 54, ctrl2y: 48, color: "blue",  width: 0.55, delay: 0.6 },
  { from: 68,  ctrl1x: 74,  ctrl1y: 76, ctrl2x: 58, ctrl2y: 52, color: "gold",  width: 0.4, delay: 1.0 },
  { from: 78,  ctrl1x: 82,  ctrl1y: 72, ctrl2x: 65, ctrl2y: 55, color: "blue",  width: 0.5, delay: 1.4 },
  { from: 85,  ctrl1x: 88,  ctrl1y: 80, ctrl2x: 72, ctrl2y: 60, color: "gold",  width: 0.6, delay: 0.1 },
];

export const EnergyBraids = () => {
  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 0 }}
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      data-testid="energy-braids"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="braidGold" x1="0%" y1="100%" x2="0%" y2="0%">
          <stop offset="0%"   stopColor={GOLD} stopOpacity="0" />
          <stop offset="30%"  stopColor={GOLD} stopOpacity="0.35" />
          <stop offset="70%"  stopColor={GOLD_BRIGHT} stopOpacity="0.55" />
          <stop offset="100%" stopColor={GOLD_BRIGHT} stopOpacity="0" />
        </linearGradient>
        <linearGradient id="braidBlue" x1="0%" y1="100%" x2="0%" y2="0%">
          <stop offset="0%"   stopColor={BLUE_DEEP} stopOpacity="0" />
          <stop offset="35%"  stopColor={BLUE_DEEP} stopOpacity="0.30" />
          <stop offset="75%"  stopColor={BLUE} stopOpacity="0.45" />
          <stop offset="100%" stopColor={BLUE} stopOpacity="0" />
        </linearGradient>
        <filter id="braidGoldGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="0.4" result="blur" />
          <feFlood floodColor={GOLD} floodOpacity="0.5" />
          <feComposite in2="blur" operator="in" />
          <feMerge>
            <feMergeNode />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="braidBlueGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="0.4" result="blur" />
          <feFlood floodColor={BLUE} floodOpacity="0.5" />
          <feComposite in2="blur" operator="in" />
          <feMerge>
            <feMergeNode />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {BRAIDS.map((b, i) => {
        const d = `M ${b.from} 100 C ${b.ctrl1x} ${b.ctrl1y}, ${b.ctrl2x} ${b.ctrl2y}, 50 42`;
        const isGold = b.color === "gold";
        return (
          <motion.path
            key={i}
            d={d}
            fill="none"
            stroke={isGold ? "url(#braidGold)" : "url(#braidBlue)"}
            strokeWidth={b.width}
            strokeLinecap="round"
            filter={isGold ? "url(#braidGoldGlow)" : "url(#braidBlueGlow)"}
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: [0, 1, 1], opacity: [0, 0.9, 0.55] }}
            transition={{
              duration: 3.8,
              delay: b.delay,
              repeat: Infinity,
              repeatDelay: 1.2,
              ease: "easeInOut",
            }}
          />
        );
      })}
    </svg>
  );
};

export default EnergyBraids;
