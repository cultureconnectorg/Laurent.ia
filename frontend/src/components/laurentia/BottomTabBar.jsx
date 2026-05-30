import { Brain, Wallet, User, Sparkles, MessageSquare } from "lucide-react";
import { toast } from "sonner";

/**
 * BottomTabBar — cohérence visuelle avec la home Kiltikonet.
 * Seul l'onglet 'brain' (Laurent.ia) est actif. Les autres affichent "Bientôt disponible".
 */
const TABS = [
  { id: "feed",   label: "Feed",   icon: Sparkles },
  { id: "chats",  label: "Chats",  icon: MessageSquare },
  { id: "brain",  label: "Laurent", icon: Brain, primary: true },
  { id: "wallet", label: "Wallet", icon: Wallet },
  { id: "profil", label: "Profil", icon: User },
];

export const BottomTabBar = ({ active = "brain", onSelect }) => {
  return (
    <nav
      className="relative z-30 flex items-end justify-between px-2 sm:px-6 pt-1.5 pb-2 border-t border-white/[0.04] bg-[#0A0F1F]/80 backdrop-blur-xl"
      data-testid="bottom-tab-bar"
    >
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = tab.id === active;
        const handleClick = () => {
          if (tab.id !== "brain") {
            toast("Bientôt disponible", {
              description: `L'onglet ${tab.label} arrive très vite.`,
              duration: 1800,
            });
            return;
          }
          onSelect?.(tab.id);
        };
        return (
          <button
            key={tab.id}
            type="button"
            onClick={handleClick}
            className={`flex flex-col items-center justify-end gap-0.5 flex-1 transition-colors duration-200
              ${tab.primary ? "-mt-3" : "py-1.5"}
              ${isActive ? "text-[#6BA8FF]" : "text-white/35 hover:text-white/60"}`}
            data-testid={`tab-${tab.id}`}
            aria-label={tab.label}
          >
            {tab.primary ? (
              <div className={`w-12 h-12 rounded-full flex items-center justify-center border-2
                ${isActive
                  ? "bg-gradient-to-br from-[#2D6FE0] to-[#5BA0FF] border-[#E7C566]/50 shadow-[0_6px_22px_rgba(45,111,224,0.45)]"
                  : "bg-white/[0.04] border-white/[0.08]"}`}>
                <Icon className="w-5 h-5 text-white" strokeWidth={1.8} />
              </div>
            ) : (
              <Icon className={`w-[18px] h-[18px] ${isActive ? "" : "opacity-90"}`} strokeWidth={1.6} />
            )}
            <span className="font-mono text-[9px] uppercase tracking-[0.2em] mt-0.5">
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
};

export default BottomTabBar;
