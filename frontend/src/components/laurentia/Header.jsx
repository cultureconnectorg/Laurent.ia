import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Menu, Inbox, Zap, Volume2, VolumeX, Square } from "lucide-react";

/**
 * Header — top bar de l'app.
 * Layout (de gauche à droite) :
 *   ☰  Laurent.ia                       🔊/🔇   📥   ⚡ 10 KT   (Avatar prénom)
 *
 * Props additionnels :
 *   speakingState: "active" | "idle"  — affiche un bouton STOP si TTS en cours
 *   onStopSpeaking: () => void        — interrompt la voix
 */
export const Header = ({
  firstName = "Hôte",
  kt = null,
  version = "free",
  picture = null,
  onMenuClick,
  speakingState = "idle",
  onStopSpeaking,
}) => {
  const initials = (firstName || "H").slice(0, 2).toUpperCase();
  const showKt = kt !== null && kt !== undefined && Number(kt) > 0;
  const [voiceOn, setVoiceOn] = useState(() => {
    if (typeof window === "undefined") return true;
    return window.localStorage.getItem("laurentia_voice") !== "off";
  });

  useEffect(() => {
    window.localStorage.setItem("laurentia_voice", voiceOn ? "on" : "off");
    if (!voiceOn) {
      try { window.speechSynthesis?.cancel(); } catch (_) {}
    }
  }, [voiceOn]);

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

      {/* right — voice + inbox + KT + avatar */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Bouton STOP voix en cours (visible uniquement pendant TTS) */}
        {speakingState === "active" && (
          <button
            type="button"
            onClick={onStopSpeaking}
            aria-label="Couper la lecture vocale en cours"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-[#E7C566]/[0.08] border border-[#E7C566]/40 text-[#E7C566] hover:bg-[#E7C566]/[0.14] transition-all"
            data-testid="header-stop-speaking"
          >
            <Square className="w-3 h-3" fill="currentColor" strokeWidth={0} />
            <span className="font-mono text-[10px] uppercase tracking-[0.18em]">Stop voix</span>
          </button>
        )}

        {/* Toggle TTS ON/OFF persistant */}
        <button
          type="button"
          onClick={() => setVoiceOn((v) => !v)}
          aria-label={voiceOn ? "Désactiver la lecture vocale" : "Activer la lecture vocale"}
          title={voiceOn ? "Lecture vocale active" : "Lecture vocale coupée"}
          className={`p-2 rounded-full transition-colors ${
            voiceOn
              ? "text-[#6BA8FF] hover:text-white hover:bg-white/[0.06]"
              : "text-white/35 hover:text-white/70 hover:bg-white/[0.04]"
          }`}
          data-testid="header-voice-toggle"
          data-voice-on={voiceOn ? "true" : "false"}
        >
          {voiceOn ? <Volume2 className="w-4 h-4" strokeWidth={1.6} /> : <VolumeX className="w-4 h-4" strokeWidth={1.6} />}
        </button>

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
          className="flex items-center gap-2.5 pl-1.5 pr-3 py-1 rounded-full bg-white/[0.04] border border-white/10 relative"
          data-testid="frekid-badge"
        >
          {picture ? (
            <img src={picture} alt={firstName} className="w-7 h-7 rounded-full ring-1 ring-[#C9A24B]/40 object-cover" />
          ) : (
            <div
              className="relative w-7 h-7 rounded-full flex items-center justify-center ring-1 ring-[#C9A24B]/55"
              style={{
                background: "radial-gradient(circle at 32% 28%, #F4E0AA 0%, #C9A24B 55%, #0A0F1F 100%)",
                boxShadow: "0 0 12px rgba(201,162,75,0.42), inset 0 0 6px rgba(0,0,0,0.35)",
              }}
              data-testid="frekid-avatar-seal"
            >
              <span
                className="font-serif italic text-[11px] font-bold text-[#0A0F1F]"
                style={{ fontFamily: '"Cormorant Garamond", serif', textShadow: "0 1px 0 rgba(255,255,255,0.2)" }}
              >
                {initials}
              </span>
            </div>
          )}
          <div className="flex flex-col leading-none">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-[#E7C566]/85" data-testid="header-cvln-label">
              CVLN
            </span>
            <span className="font-mono text-[8.5px] uppercase tracking-[0.22em] text-white/40 mt-0.5">
              Group
            </span>
          </div>
        </div>
      </div>
    </motion.header>
  );
};

export default Header;
