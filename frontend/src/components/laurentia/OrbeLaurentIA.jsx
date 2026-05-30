import { motion, AnimatePresence } from "framer-motion";

/**
 * OrbeLaurentIA — Le présence centrale.
 * State: "idle" | "listening" | "thinking" | "speaking"
 * Aucune image — composition de divs floutés en blend-mode screen.
 */
export const OrbeLaurentIA = ({ state = "idle" }) => {
  const colors = {
    idle: ["#1A3B3B", "#0E2A2A", "#1A3B3B"],
    listening: ["#D97736", "#8C3D14", "#F4A259"],
    thinking: ["#E6E2D8", "#9C9890", "#E6E2D8"],
    speaking: ["#D97736", "#C56624", "#E6E2D8"],
  };
  const c = colors[state] || colors.idle;

  const breath = {
    idle:      { scale: [1, 1.05, 1],   opacity: [0.35, 0.55, 0.35], transition: { duration: 4.5, repeat: Infinity, ease: "easeInOut" } },
    listening: { scale: [1.05, 1.18, 1.05], opacity: [0.65, 0.9, 0.65], transition: { duration: 1.2, repeat: Infinity, ease: "easeInOut" } },
    thinking:  { scale: [1, 1.08, 0.98, 1.04, 1], rotate: [0, 1.5, -1.5, 0.8, 0], opacity: [0.5, 0.8, 0.6, 0.85, 0.5], transition: { duration: 1.6, repeat: Infinity, ease: "easeInOut" } },
    speaking:  { scale: [1.04, 1.12, 1.04], opacity: [0.7, 0.95, 0.7], transition: { duration: 0.9, repeat: Infinity, ease: "easeInOut" } },
  };

  return (
    <div
      className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none select-none"
      style={{ width: "min(60vmin, 560px)", height: "min(60vmin, 560px)" }}
      data-testid="orbe-laurentia"
      aria-label={`orb-${state}`}
    >
      {/* outer halo */}
      <motion.div
        className="absolute inset-0 rounded-full blur-3xl"
        style={{ backgroundColor: c[0], mixBlendMode: "screen" }}
        animate={breath[state]}
      />
      {/* middle ring */}
      <motion.div
        className="absolute inset-[12%] rounded-full blur-2xl"
        style={{ backgroundColor: c[1], mixBlendMode: "screen" }}
        animate={{
          scale: state === "thinking" ? [1, 1.12, 0.95, 1.06, 1] : [1, 1.06, 1],
          opacity: [0.5, 0.75, 0.5],
          transition: { duration: state === "listening" ? 1.0 : 3.2, repeat: Infinity, ease: "easeInOut" },
        }}
      />
      {/* inner core */}
      <motion.div
        className="absolute inset-[28%] rounded-full blur-xl"
        style={{
          background: `radial-gradient(circle at 50% 45%, ${c[2]}, ${c[1]} 70%)`,
          mixBlendMode: "screen",
        }}
        animate={{
          scale: state === "thinking" ? [1, 1.1, 0.9, 1] : [1, 1.04, 1],
          opacity: [0.8, 1, 0.8],
          transition: { duration: state === "listening" ? 0.8 : 2.6, repeat: Infinity, ease: "easeInOut" },
        }}
      />
      {/* thin focal point */}
      <AnimatePresence>
        {(state === "listening" || state === "speaking") && (
          <motion.div
            initial={{ opacity: 0, scale: 0.3 }}
            animate={{ opacity: 0.9, scale: 1 }}
            exit={{ opacity: 0, scale: 0.3 }}
            transition={{ duration: 0.4 }}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{
              width: "10px",
              height: "10px",
              background: "#F3EFE7",
              boxShadow: "0 0 20px 6px rgba(243,239,231,0.8)",
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

export default OrbeLaurentIA;
