import { motion } from "framer-motion";
import { Mic, MicOff, Square } from "lucide-react";

export const MicButton = ({ state = "idle", onStart, onStop, onCancel }) => {
  const isActive = state === "listening";
  const isBusy = state === "thinking" || state === "speaking";

  const handleClick = () => {
    if (isBusy) {
      onCancel?.();
      return;
    }
    if (isActive) onStop?.();
    else onStart?.();
  };

  return (
    <div className="absolute left-1/2 -translate-x-1/2 bottom-12 z-30">
      <motion.button
        type="button"
        data-testid="mic-toggle-button"
        onClick={handleClick}
        whileTap={{ scale: 0.92 }}
        whileHover={{ scale: 1.04 }}
        animate={
          isActive
            ? { boxShadow: ["0 0 0 0 rgba(217,119,54,0.45)", "0 0 0 22px rgba(217,119,54,0)"] }
            : {}
        }
        transition={isActive ? { duration: 1.5, repeat: Infinity, ease: "easeOut" } : {}}
        className={`relative flex items-center justify-center w-[84px] h-[84px] rounded-full
          backdrop-blur-xl border transition-colors duration-300
          ${isActive
            ? "bg-[#D97736]/20 border-[#D97736]/60 shadow-[0_0_40px_rgba(217,119,54,0.55)]"
            : isBusy
              ? "bg-white/10 border-white/30 shadow-[0_8px_32px_rgba(0,0,0,0.45)]"
              : "bg-white/[0.04] border-white/15 hover:bg-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.45)]"
          }`}
        aria-label={isActive ? "Arrêter l'écoute" : "Démarrer l'écoute"}
      >
        {isBusy ? (
          <Square className="w-7 h-7 text-[#F3EFE7]" strokeWidth={1.5} />
        ) : isActive ? (
          <MicOff className="w-8 h-8 text-[#F3EFE7]" strokeWidth={1.5} />
        ) : (
          <Mic className="w-8 h-8 text-[#F3EFE7]/90" strokeWidth={1.5} />
        )}
      </motion.button>
    </div>
  );
};

export default MicButton;
