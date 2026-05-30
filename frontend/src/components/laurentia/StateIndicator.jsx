import { motion, AnimatePresence } from "framer-motion";

const LABELS = {
  idle:      "Tap pour parler",
  listening: "Laurent.ia écoute…",
  thinking:  "Laurent.ia réfléchit…",
  speaking:  "Laurent.ia répond",
};

export const StateIndicator = ({ state = "idle" }) => {
  const label = LABELS[state] || LABELS.idle;
  return (
    <div className="absolute left-1/2 -translate-x-1/2 top-[calc(50%+min(34vmin,300px))] z-10">
      <AnimatePresence mode="wait">
        <motion.div
          key={state}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.35 }}
          className="font-mono text-xs uppercase tracking-[0.32em] text-white/45"
          data-testid="state-indicator"
        >
          {label}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

export default StateIndicator;
