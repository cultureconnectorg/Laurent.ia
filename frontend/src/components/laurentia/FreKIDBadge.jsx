import { motion } from "framer-motion";

export const FreKIDBadge = ({ firstName = "Hôte" }) => {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.2, duration: 0.6 }}
      className="absolute top-7 left-7 z-20"
      data-testid="frekid-badge"
    >
      <div className="backdrop-blur-xl bg-white/[0.04] border border-white/10 rounded-full px-5 py-2.5 shadow-[0_8px_32px_rgba(0,0,0,0.45)]">
        <div className="flex items-center gap-3">
          <div className="w-1.5 h-1.5 rounded-full bg-[#D97736] shadow-[0_0_8px_#D97736]" />
          <span className="font-serif italic text-base text-[#F3EFE7]/90 tracking-wide">
            {firstName}
          </span>
        </div>
      </div>
    </motion.div>
  );
};

export default FreKIDBadge;
