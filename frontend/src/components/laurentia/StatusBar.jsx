import { motion } from "framer-motion";

export const StatusBar = ({ version = "free", tokensRemaining = 10000, jccBalance = 0, quotaWarning = false }) => {
  return (
    <motion.div
      initial={{ opacity: 0, x: 8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.25, duration: 0.6 }}
      className="absolute top-7 right-7 z-20 font-mono text-[10px] uppercase tracking-[0.28em] text-white/50"
      data-testid="status-bar"
    >
      <div className="flex items-center gap-6 px-4 py-2 border-b border-white/10">
        <div className="flex items-center gap-2" data-testid="status-bar-version">
          <span className="text-white/30">v</span>
          <span className="text-[#F3EFE7]/80">0.1 · {version === "pro" ? "Pro" : "Souverain"}</span>
        </div>
        <span className="text-white/15">·</span>
        <div className="flex items-center gap-2" data-testid="status-bar-tokens">
          <span className="text-white/30">tokens</span>
          <span className={quotaWarning ? "text-[#D97736]" : "text-[#F3EFE7]/80"}>{tokensRemaining}</span>
        </div>
        <span className="text-white/15">·</span>
        <div className="flex items-center gap-2" data-testid="status-bar-jcc">
          <span className="text-white/30">jcc</span>
          <span className="text-[#F3EFE7]/80">{jccBalance}</span>
        </div>
      </div>
    </motion.div>
  );
};

export default StatusBar;
