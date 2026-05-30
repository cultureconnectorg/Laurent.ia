import { motion } from "framer-motion";
import { Menu, Inbox, Zap } from "lucide-react";

/**
 * Header — top bar de l'app.
 * Layout (de gauche à droite) :
 *   ☰  Laurent.ia (wordmark italique doré subtil)    📥   ⚡ 10 KT   (Avatar prénom)
 */
export const Header = ({ firstName = "Hôte", kt = null, version = "free", picture = null, onMenuClick }) => {
  const initials = (firstName || "H").slice(0, 2).toUpperCase();
  const showKt = kt !== null && kt !== undefined && Number(kt) > 0;

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      className="relative z-30 flex items-center justify-between px-4 sm:px-6 py-4 border-b border-white/[0.04]"
      data-testid="app-header"
    >
      {/* left — menu + brand */}
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Menu"
          className="text-white/60 hover:text-white transition-colors p-1 -ml-1"
          data-testid="header-menu-btn"
        >
          <Menu className="w-5 h-5" strokeWidth={1.5} />
        </button>
        <div className="flex items-baseline" data-testid="header-brand">
          <span className="font-serif italic text-xl sm:text-2xl text-[#E7C566] tracking-tight leading-none">
            Laurent
          </span>
          <span className="font-serif italic text-xl sm:text-2xl text-[#E7C566]/75 tracking-tight leading-none">
            .ia
          </span>
        </div>
      </div>

      {/* right — inbox + KT + avatar */}
      <div className="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          aria-label="Inbox"
          className="hidden sm:inline-flex text-white/45 hover:text-white/80 transition-colors p-2 rounded-full"
          data-testid="header-inbox-btn"
        >
          <Inbox className="w-4 h-4" strokeWidth={1.5} />
        </button>

        {showKt && (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-white/[0.04] border border-white/10"
            data-testid="header-kt-pill"
          >
            <Zap className="w-3.5 h-3.5 text-[#E7C566]" fill="#E7C566" strokeWidth={1.5} />
            <span className="font-mono text-xs font-medium text-[#F1F4FA]">{kt}</span>
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/45 ml-0.5">KT</span>
          </div>
        )}

        <div
          className="flex items-center gap-2 pl-1.5 pr-2.5 py-1 rounded-full bg-white/[0.04] border border-white/10"
          data-testid="frekid-badge"
        >
          {picture ? (
            <img src={picture} alt={firstName} className="w-6 h-6 rounded-full ring-1 ring-white/20 object-cover" />
          ) : (
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#2D6FE0] to-[#5BA0FF] flex items-center justify-center ring-1 ring-white/20">
              <span className="font-mono text-[10px] font-semibold text-white">{initials}</span>
            </div>
          )}
          {version === "pro" && (
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#E7C566] hidden sm:inline">Pro</span>
          )}
        </div>
      </div>
    </motion.header>
  );
};

export default Header;
