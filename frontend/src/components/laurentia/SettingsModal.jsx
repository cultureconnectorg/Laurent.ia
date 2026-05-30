/**
 * SettingsModal — page Paramètres légère.
 * Affiche le tier actuel, usage tokens, langues préférée, partage de session courante.
 */
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Languages, Volume2, Database, Share2, Copy, Check } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";

export const SettingsModal = ({ open, onOpenChange, currentSessionId }) => {
  const { user } = useAuth();
  const [voiceOn, setVoiceOn] = useState(() => window.localStorage.getItem("laurentia_voice") !== "off");
  const [autoLang, setAutoLang] = useState(() => window.localStorage.getItem("laurentia_autolang") !== "off");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    window.localStorage.setItem("laurentia_voice", voiceOn ? "on" : "off");
  }, [voiceOn]);
  useEffect(() => {
    window.localStorage.setItem("laurentia_autolang", autoLang ? "on" : "off");
  }, [autoLang]);

  const tokensUsed = user?.tokens_used_month ?? 0;
  const tokensLimit = user?.tokens_limit_month ?? 100000;
  const pct = Math.min(100, Math.round((tokensUsed / tokensLimit) * 100));
  const tier = user?.tier || "free";

  const shareUrl = currentSessionId
    ? `${window.location.origin}/?session=${encodeURIComponent(currentSessionId)}`
    : null;

  const copyShare = async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
      toast("Lien copié");
    } catch (_) {
      toast("Impossible de copier");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="bg-[#0A0F1F] border border-white/[0.06] text-[#F1F4FA] max-w-md p-0 overflow-hidden"
        data-testid="settings-modal"
      >
        <DialogHeader className="px-6 pt-6 pb-2 text-left">
          <DialogTitle className="font-serif italic text-2xl text-[#E7C566] tracking-tight">Paramètres</DialogTitle>
          <DialogDescription className="font-mono text-[10px] uppercase tracking-[0.28em] text-white/40 mt-1">
            Ton Laurent.ia · {tier}
          </DialogDescription>
        </DialogHeader>

        <div className="px-6 pb-6 space-y-5">
          {/* Usage */}
          <section data-testid="settings-usage">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-3.5 h-3.5 text-[#6BA8FF]" strokeWidth={1.8} />
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/50">Usage du mois</span>
            </div>
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
              <div className="flex items-baseline justify-between font-sans">
                <span className="text-sm text-white/70">{tokensUsed.toLocaleString("fr-FR")} tokens utilisés</span>
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/40">sur {tokensLimit.toLocaleString("fr-FR")}</span>
              </div>
              <div className="mt-2 h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[#2D6FE0] to-[#5BA0FF] transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          </section>

          {/* Toggles */}
          <section className="space-y-3">
            <label className="flex items-center justify-between" data-testid="settings-voice">
              <span className="flex items-center gap-2 text-sm">
                <Volume2 className="w-4 h-4 text-[#6BA8FF]" strokeWidth={1.6} />
                Lecture vocale des réponses
              </span>
              <Switch checked={voiceOn} onCheckedChange={setVoiceOn} />
            </label>
            <label className="flex items-center justify-between" data-testid="settings-autolang">
              <span className="flex items-center gap-2 text-sm">
                <Languages className="w-4 h-4 text-[#6BA8FF]" strokeWidth={1.6} />
                Détection de langue automatique
              </span>
              <Switch checked={autoLang} onCheckedChange={setAutoLang} />
            </label>
          </section>

          {/* Share session */}
          {shareUrl && (
            <section data-testid="settings-share">
              <div className="flex items-center gap-2 mb-2">
                <Share2 className="w-3.5 h-3.5 text-[#6BA8FF]" strokeWidth={1.8} />
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/50">Partager cette conversation</span>
              </div>
              <button
                type="button"
                onClick={copyShare}
                className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-colors text-left"
                data-testid="settings-share-copy"
              >
                <span className="font-mono text-[11px] text-white/65 truncate flex-1">{shareUrl}</span>
                {copied ? (
                  <Check className="w-3.5 h-3.5 text-[#6BA8FF] flex-shrink-0" strokeWidth={2} />
                ) : (
                  <Copy className="w-3.5 h-3.5 text-white/50 flex-shrink-0" strokeWidth={1.8} />
                )}
              </button>
            </section>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default SettingsModal;
