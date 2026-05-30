import { motion } from "framer-motion";

/**
 * OrbeLaurentIA v1.2-PRODUCTION — Noyau de données complexes.
 *
 * Architecture en couches concentriques :
 *   1. Anneaux radar extérieurs (4 niveaux, opacité dégressive)
 *   2. Halo glow (blur 2xl)
 *   3. Anneau particulaire (32 dots positionnés en cercle, pulsation décalée)
 *   4. Arcs orbitaux (2 demi-cercles rotatifs : or + cyan)
 *   5. Anneau d'iris (gradient conique fait des lignes énergétiques)
 *   6. Noyau sphérique avec spot et reflet (radial-gradient + boxShadow)
 *   7. Point focal pulsant
 *
 * Palette : Or `#C9A24B / #E7C566` + Cyan profond `#17a2b8`.
 * Réagit aux states : idle / listening / thinking / speaking / sealing.
 */
export const OrbeLaurentIA = ({ state = "idle", size = 240 }) => {
  const palette = {
    idle:      { ring: "rgba(23, 162, 184, 0.35)", core: "#1A4D6C", spot: "#5BD0E0", glow: "rgba(23, 162, 184, 0.45)", arc1: "#17a2b8", arc2: "#C9A24B66" },
    listening: { ring: "rgba(91, 208, 224, 0.55)", core: "#2A6A88", spot: "#9FF0FF", glow: "rgba(91, 208, 224, 0.65)", arc1: "#5BD0E0", arc2: "#E7C566" },
    thinking:  { ring: "rgba(180, 220, 240, 0.4)", core: "#1F5878", spot: "#C8F0FF", glow: "rgba(180, 220, 240, 0.5)", arc1: "#17a2b8", arc2: "#C9A24B" },
    speaking:  { ring: "rgba(75, 180, 220, 0.45)", core: "#225878", spot: "#A8E0F0", glow: "rgba(75, 180, 220, 0.55)", arc1: "#5BD0E0", arc2: "#E7C566" },
    sealing:   { ring: "rgba(201, 162, 75, 0.75)", core: "#5C4422", spot: "#F4E0AA", glow: "rgba(231, 197, 102, 0.75)", arc1: "#E7C566", arc2: "#17a2b8" },
  };
  const c = palette[state] || palette.idle;
  const pulseSpeed = state === "listening" ? 1.6 : state === "thinking" ? 1.2 : state === "sealing" ? 0.9 : 3.4;

  // 32 points autour de l'anneau particulaire à r=46%
  const particleCount = 32;
  const particles = Array.from({ length: particleCount }, (_, i) => {
    const angle = (i / particleCount) * Math.PI * 2;
    const r = 46; // rayon en %
    return {
      x: 50 + r * Math.cos(angle),
      y: 50 + r * Math.sin(angle),
      delay: (i / particleCount) * 1.4,
      gold: i % 7 === 0, // ~14% des points dorés
    };
  });

  return (
    <div
      className="relative pointer-events-none select-none"
      style={{ width: size, height: size }}
      data-testid="orbe-laurentia"
      data-state={state}
      aria-label={`orb-${state}`}
    >
      {/* 1. Anneaux radar extérieurs */}
      {[0, 1, 2, 3].map((i) => (
        <motion.div
          key={`ring-${i}`}
          className="absolute inset-0 rounded-full border"
          style={{
            borderColor: c.ring,
            transform: `scale(${1 - i * 0.16})`,
            opacity: 0.55 - i * 0.10,
          }}
          animate={{
            scale: [1 - i * 0.16, 1 - i * 0.16 + 0.05, 1 - i * 0.16],
            opacity: [0.55 - i * 0.10, 0.8 - i * 0.10, 0.55 - i * 0.10],
          }}
          transition={{ duration: pulseSpeed, repeat: Infinity, ease: "easeInOut", delay: i * 0.18 }}
        />
      ))}

      {/* 2. Halo glow doux */}
      <motion.div
        className="absolute inset-[20%] rounded-full blur-2xl"
        style={{ background: c.glow }}
        animate={{ opacity: [0.55, 0.85, 0.55], scale: [0.95, 1.06, 0.95] }}
        transition={{ duration: pulseSpeed * 0.8, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* 3. Anneau particulaire — 32 dots dansants */}
      {particles.map((p, i) => (
        <motion.span
          key={`dot-${i}`}
          className="absolute rounded-full"
          style={{
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.gold ? 3 : 2,
            height: p.gold ? 3 : 2,
            transform: "translate(-50%, -50%)",
            background: p.gold ? "#E7C566" : "#5BD0E0",
            boxShadow: p.gold
              ? "0 0 6px rgba(231,197,102,0.85)"
              : "0 0 5px rgba(91,208,224,0.7)",
          }}
          animate={{ opacity: [0.35, 1, 0.35], scale: [0.8, 1.2, 0.8] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut", delay: p.delay }}
        />
      ))}

      {/* 4. Arcs orbitaux contre-rotatifs (cyan + or) */}
      <motion.div
        className="absolute inset-[12%] rounded-full"
        style={{
          border: `1.5px solid transparent`,
          borderTopColor: c.arc1,
          borderRightColor: c.arc1 + "55",
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: 14, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute inset-[18%] rounded-full"
        style={{
          border: `1px solid transparent`,
          borderBottomColor: c.arc2,
          borderLeftColor: c.arc2 + "55",
        }}
        animate={{ rotate: -360 }}
        transition={{ duration: 22, repeat: Infinity, ease: "linear" }}
      />

      {/* 5. Iris énergétique — gradient conique en fond, pulsation */}
      <motion.div
        className="absolute inset-[26%] rounded-full"
        style={{
          background: `conic-gradient(from 0deg, ${c.arc1}33, ${c.arc2}11, ${c.arc1}55, ${c.arc2}22, ${c.arc1}33)`,
          filter: "blur(8px)",
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
      />

      {/* 6. Noyau sphérique avec spot lumière */}
      <motion.div
        className="absolute inset-[32%] rounded-full"
        style={{
          background: `radial-gradient(circle at 38% 32%, ${c.spot} 0%, ${c.core} 38%, #07101F 92%)`,
          boxShadow: `0 0 48px ${c.glow}, inset 0 0 36px rgba(255,255,255,0.05), inset -4px -8px 24px rgba(0,0,0,0.4)`,
        }}
        animate={{
          scale: state === "thinking" ? [1, 1.05, 0.97, 1.03, 1] : [1, 1.03, 1],
        }}
        transition={{ duration: pulseSpeed * 0.6, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* 7. Point focal hyper-vif */}
      <motion.div
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{
          width: size * 0.05,
          height: size * 0.05,
          background: c.spot,
          boxShadow: `0 0 ${size * 0.08}px ${size * 0.025}px ${c.spot}`,
        }}
        animate={{ opacity: state === "idle" ? [0.7, 1, 0.7] : [0.85, 1, 0.85] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
};

export default OrbeLaurentIA;
