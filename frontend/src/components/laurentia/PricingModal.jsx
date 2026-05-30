/**
 * PricingModal — 3 paliers Free / Creator / Infinite.
 * Style : trio de cards premium, accent gold sur le tier mis en avant.
 */
import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Check, Sparkles, Brain, Loader2 } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TIER_ICONS = {
  free: Sparkles,
  creator: Sparkles,
  infinite: Brain,
};

export const PricingModal = ({ open, onOpenChange, currentTier = "free" }) => {
  const [packages, setPackages] = useState(null);
  const [loadingId, setLoadingId] = useState(null);

  useEffect(() => {
    if (!open || packages) return;
    (async () => {
      try {
        const r = await fetch(`${API}/billing/packages`);
        if (r.ok) setPackages(await r.json());
      } catch (_) {}
    })();
  }, [open, packages]);

  const handleCheckout = async (packageId) => {
    setLoadingId(packageId);
    try {
      const r = await fetch(`${API}/billing/create-checkout`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ origin_url: window.location.origin, package_id: packageId }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        toast(d.detail || "Erreur démarrage paiement");
        setLoadingId(null);
        return;
      }
      const d = await r.json();
      window.location.href = d.url;
    } catch (e) {
      toast(e.message || "Erreur réseau");
      setLoadingId(null);
    }
  };

  const tiers = [];
  if (packages) {
    tiers.push({ ...packages.free, package_id: null });
    tiers.push(...packages.available);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="bg-[#0A0F1F] border border-white/[0.06] text-[#F1F4FA] max-w-3xl p-0 overflow-hidden"
        data-testid="pricing-modal"
      >
        <DialogHeader className="px-7 pt-7 pb-3 text-left">
          <DialogTitle className="font-serif italic text-2xl text-[#E7C566] tracking-tight">
            Choisis ton plan
          </DialogTitle>
          <DialogDescription className="font-mono text-[10px] uppercase tracking-[0.28em] text-white/40 mt-1">
            Laurent.ia s'adapte à ton intensité réelle
          </DialogDescription>
        </DialogHeader>

        {!packages ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-5 h-5 animate-spin text-white/40" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 px-7 pb-7 pt-2">
            {tiers.map((t) => {
              const Icon = TIER_ICONS[t.tier] || Sparkles;
              const isCurrent = currentTier === t.tier;
              const isFlagship = t.tier === "infinite";
              const cardBorder = isFlagship
                ? "border-[#E7C566]/40 bg-gradient-to-b from-[#E7C566]/[0.07] to-transparent"
                : "border-white/[0.07] bg-white/[0.02]";
              return (
                <div
                  key={t.tier}
                  className={`relative rounded-2xl border ${cardBorder} p-5 flex flex-col`}
                  data-testid={`pricing-tier-${t.tier}`}
                >
                  {isFlagship && (
                    <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-[#E7C566] text-[#0A0F1F] font-mono text-[9px] uppercase tracking-[0.22em] font-semibold">
                      Recommandé
                    </div>
                  )}

                  <div className="flex items-center gap-2 mb-1">
                    <Icon className={`w-4 h-4 ${isFlagship ? "text-[#E7C566]" : "text-[#6BA8FF]"}`} strokeWidth={1.8} />
                    <span className="font-sans text-base font-medium">{t.label}</span>
                  </div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/40 mb-4 min-h-[28px]">
                    {t.tagline || ""}
                  </p>

                  <div className="mb-5">
                    <span className="font-serif italic text-4xl text-[#F1F4FA]">
                      {t.amount === 0 ? "Gratuit" : `€${Math.round(t.amount)}`}
                    </span>
                    {t.amount > 0 && (
                      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/40 ml-1">/mois</span>
                    )}
                  </div>

                  <ul className="space-y-2 mb-5 flex-1">
                    {(t.features || []).map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-white/75">
                        <Check className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${isFlagship ? "text-[#E7C566]" : "text-[#6BA8FF]"}`} strokeWidth={2.2} />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>

                  <button
                    type="button"
                    onClick={() => t.package_id && !isCurrent && handleCheckout(t.package_id)}
                    disabled={!t.package_id || isCurrent || loadingId === t.package_id}
                    className={`w-full py-2.5 rounded-full font-sans text-sm font-medium transition-all
                      ${isCurrent
                        ? "bg-white/[0.04] border border-white/10 text-white/50 cursor-default"
                        : !t.package_id
                          ? "bg-white/[0.04] border border-white/10 text-white/50"
                          : isFlagship
                            ? "bg-gradient-to-br from-[#E7C566] to-[#C9A646] text-[#0A0F1F] shadow-[0_6px_22px_rgba(231,197,102,0.35)] hover:shadow-[0_6px_28px_rgba(231,197,102,0.5)]"
                            : "bg-gradient-to-br from-[#2D6FE0] to-[#5BA0FF] text-white shadow-[0_4px_18px_rgba(45,111,224,0.4)] hover:shadow-[0_4px_24px_rgba(45,111,224,0.55)]"
                      }`}
                    data-testid={`pricing-cta-${t.tier}`}
                  >
                    {(t.package_id && loadingId === t.package_id) ? (
                      <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                    ) : isCurrent ? "Ton plan actuel" : !t.package_id ? "Plan par défaut" : `Activer ${t.label}`}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        <div className="px-7 pb-6 font-mono text-[9px] uppercase tracking-[0.22em] text-white/30 text-center">
          Usage intelligent · pas de frais cachés · résiliation 1 click
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default PricingModal;
