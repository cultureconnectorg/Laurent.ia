import { motion } from "framer-motion";

/**
 * OrbeLaurentIA — radar bleu électrique concentrique.
 * Inspiré des screenshots CVL Brain : anneaux concentriques avec un noyau central.
 * Compact (utilisé en hero), pas plein écran.
 *
 * Props:
 *   state: "idle" | "listening" | "thinking" | "speaking"
 *   size:  px (default 220)
 */
export const OrbeLaurentIA = ({ state = "idle", size = 220 }) => {
  const colorByState = {
    idle:      { ring: "rgba(45, 111, 224, 0.35)", core: "#2D6FE0", spot: "#6BB8FF", glow: "rgba(45, 111, 224, 0.45)" },
    listening: { ring: "rgba(107, 184, 255, 0.55)", core: "#3D8BF5", spot: "#A8D4FF", glow: "rgba(107, 184, 255, 0.65)" },
    thinking:  { ring: "rgba(180, 210, 255, 0.45)", core: "#5BA0FF", spot: "#E6F0FF", glow: "rgba(180, 210, 255, 0.55)" },
    speaking:  { ring: "rgba(75, 140, 230, 0.5)",  core: "#3D8BF5", spot: "#A8D4FF", glow: "rgba(75, 140, 230, 0.55)" },
  };
  const c = colorByState[state] || colorByState.idle;

  const pulseSpeed = state === "listening" ? 1.6 : state === "thinking" ? 1.2 : 3.4;

  return (
    <div
      className="relative pointer-events-none select-none"
      style={{ width: size, height: size }}
      data-testid="orbe-laurentia"
      aria-label={`orb-${state}`}
    >
      {/* outer rings — radar */}
      {[0, 1, 2, 3].map((i) => (
        <motion.div
          key={i}
          className="absolute inset-0 rounded-full border"
          style={{
            borderColor: c.ring,
            transform: `scale(${1 - i * 0.18})`,
            opacity: 0.6 - i * 0.12,
          }}
          animate={{
            scale: [1 - i * 0.18, 1 - i * 0.18 + 0.06, 1 - i * 0.18],
            opacity: [0.6 - i * 0.12, 0.85 - i * 0.12, 0.6 - i * 0.12],
          }}
          transition={{ duration: pulseSpeed, repeat: Infinity, ease: "easeInOut", delay: i * 0.18 }}
        />
      ))}

      {/* soft glow halo */}
      <motion.div
        className="absolute inset-[18%] rounded-full blur-2xl"
        style={{ background: c.glow }}
        animate={{ opacity: [0.55, 0.85, 0.55], scale: [0.95, 1.05, 0.95] }}
        transition={{ duration: pulseSpeed * 0.8, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* core sphere */}
      <motion.div
        className="absolute inset-[30%] rounded-full"
        style={{
          background: `radial-gradient(circle at 50% 38%, ${c.spot} 0%, ${c.core} 40%, #0E1B36 90%)`,
          boxShadow: `0 0 40px ${c.glow}, inset 0 0 30px rgba(255,255,255,0.06)`,
        }}
        animate={{
          scale: state === "thinking" ? [1, 1.06, 0.96, 1.03, 1] : [1, 1.03, 1],
        }}
        transition={{ duration: pulseSpeed * 0.6, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* center focal point */}
      <motion.div
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{
          width: size * 0.04,
          height: size * 0.04,
          background: c.spot,
          boxShadow: `0 0 ${size * 0.06}px ${size * 0.02}px ${c.spot}`,
        }}
        animate={{ opacity: state === "idle" ? [0.7, 1, 0.7] : [0.9, 1, 0.9] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
};

export default OrbeLaurentIA;
