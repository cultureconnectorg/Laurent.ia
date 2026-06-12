/**
 * ReportsPage — /me/reports
 *
 * Dashboard utilisateur "Bilan Souverain Laurent.ia" :
 *   - Courbe time-saved 7 derniers jours (Recharts)
 *   - Breakdown actions (BarChart)
 *   - Carte tenant (X/20 agents)
 *   - Upsell card SOFT (visible UNIQUEMENT si seuils dépassés, jamais en popup)
 *
 * Logique anti-spam : on consomme `upsell_hint` du backend, qui ne renvoie
 * de hint qu'après 3 jours d'usage ET 20 actions / 60min cumulées (Free).
 * Le hint apparaît comme une CARTE non-interruptive en bas de page.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { ArrowLeft, Brain, Clock, Sparkles, TrendingUp, Users } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { PricingModal } from "@/components/laurentia/PricingModal";
import { Skeleton } from "@/components/ui/skeleton";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ACTION_LABELS = {
  QUERY_PROCESSED: "Questions",
  PDF_EXPORT: "PDF signés",
  ECHO_SHARED: "Échos partagés",
  FILE_PROCESSED: "Fichiers analysés",
  VOICE_TRANSCRIBED: "Vocaux",
  SOCIAL_POST: "Posts sociaux",
};

const TIER_COPY = {
  free: { label: "Free", color: "#9CA3AF", agentsMax: 3 },
  creator: { label: "Creator", color: "#E7C566", agentsMax: 10 },
  pro: { label: "Pro", color: "#A78BFA", agentsMax: 20 },
  infinite: { label: "Infinite", color: "#A78BFA", agentsMax: 20 },
};

const fmtDay = (iso) => {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("fr-FR", { weekday: "short", day: "2-digit" });
  } catch { return iso; }
};

export default function ReportsPage() {
  const navigate = useNavigate();
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [report, setReport] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [range, setRange] = useState("daily"); // daily | weekly
  const [loading, setLoading] = useState(true);
  const [pricingOpen, setPricingOpen] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      navigate("/");
      return;
    }
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const [r1, r2] = await Promise.all([
          fetch(`${API}/me/report/${range}`, { credentials: "include" }),
          fetch(`${API}/me/tenant`, { credentials: "include" }),
        ]);
        if (active && r1.ok) setReport(await r1.json());
        if (active && r2.ok) setTenant(await r2.json());
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [range, isAuthenticated, authLoading, navigate]);

  const tierKey = (report?.tier || user?.tier || "free").toLowerCase();
  const tierInfo = TIER_COPY[tierKey] || TIER_COPY.free;

  const timeline = useMemo(() => {
    return (report?.timeline || []).map((p) => ({
      ...p,
      label: fmtDay(p.date),
      hours: Math.round((p.minutes / 60.0) * 10) / 10,
    }));
  }, [report]);

  const actions = useMemo(() => {
    return (report?.by_action || []).slice(0, 6).map((a) => ({
      action: ACTION_LABELS[a.action] || a.action,
      count: a.count,
      minutes: a.time_saved_min,
    }));
  }, [report]);

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-white" data-testid="reports-page">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-[#0A0A0B]/95 backdrop-blur border-b border-white/[0.06]">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="p-2 -ml-2 rounded-lg hover:bg-white/[0.06] transition-colors text-white/70 hover:text-white"
            data-testid="reports-back-btn"
            aria-label="Retour au chat"
          >
            <ArrowLeft className="w-5 h-5" strokeWidth={1.6} />
          </button>
          <div className="flex-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.28em] text-white/40">
              Bilan Souverain
            </div>
            <div className="font-sans text-base font-medium">
              {range === "daily" ? "Aujourd'hui" : "Cette semaine"}
            </div>
          </div>
          <div className="flex rounded-full bg-white/[0.04] p-0.5 border border-white/[0.06]">
            {["daily", "weekly"].map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-3 py-1.5 rounded-full text-[11px] font-mono uppercase tracking-[0.2em] transition-colors ${
                  range === r ? "bg-white text-black" : "text-white/60 hover:text-white"
                }`}
                data-testid={`reports-range-${r}`}
              >
                {r === "daily" ? "24h" : "7j"}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-6 space-y-5">
        {/* Stats topline */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            icon={<Clock className="w-4 h-4" strokeWidth={1.6} />}
            label="Temps économisé"
            value={loading ? "—" : `${report?.time_saved_hours ?? 0} h`}
            sub={loading ? "" : `${report?.time_saved_min ?? 0} min cumulées`}
            accent="#E7C566"
            testId="stat-time-saved"
          />
          <StatCard
            icon={<TrendingUp className="w-4 h-4" strokeWidth={1.6} />}
            label="Actions traitées"
            value={loading ? "—" : `${report?.total_actions ?? 0}`}
            sub={loading ? "" : `${report?.alerts ?? 0} alertes`}
            accent="#FFFFFF"
            testId="stat-actions"
          />
          <StatCard
            icon={<Users className="w-4 h-4" strokeWidth={1.6} />}
            label="Agents actifs"
            value={loading ? "—" : `${tenant?.agent_count ?? tierInfo.agentsMax} / 20`}
            sub={`Tier ${tierInfo.label}`}
            accent={tierInfo.color}
            testId="stat-agents"
          />
          <StatCard
            icon={<Brain className="w-4 h-4" strokeWidth={1.6} />}
            label="Souveraineté"
            value={loading ? "—" : (report?.alerts === 0 ? "Stable" : "Vigilance")}
            sub={report?.top_incidents?.length ? `${report.top_incidents.length} incidents` : "Aucun incident"}
            accent="#A78BFA"
            testId="stat-souverainete"
          />
        </div>

        {/* Courbe temps économisé */}
        <Card title="Temps économisé" sub="Évolution heures par jour" testId="chart-time-saved">
          {loading ? (
            <Skeleton className="h-[200px] w-full bg-white/[0.04]" />
          ) : (
            <div className="h-[200px] w-full">
              <ResponsiveContainer>
                <AreaChart data={timeline}>
                  <defs>
                    <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#E7C566" stopOpacity={0.45} />
                      <stop offset="100%" stopColor="#E7C566" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                  <XAxis dataKey="label" stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} axisLine={false} width={26} />
                  <Tooltip
                    cursor={{ stroke: "rgba(231,197,102,0.3)", strokeWidth: 1 }}
                    contentStyle={{
                      background: "#15151A", border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: 12, fontSize: 12,
                    }}
                    labelStyle={{ color: "rgba(255,255,255,0.7)" }}
                    formatter={(v) => [`${v} h`, "Temps gagné"]}
                  />
                  <Area type="monotone" dataKey="hours" stroke="#E7C566" strokeWidth={2}
                        fill="url(#goldGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* Breakdown actions */}
        {actions.length > 0 && (
          <Card title="Tes actions principales" sub="Répartition par type" testId="chart-actions">
            <div className="h-[200px] w-full">
              <ResponsiveContainer>
                <BarChart data={actions}>
                  <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                  <XAxis dataKey="action" stroke="rgba(255,255,255,0.4)" fontSize={10} tickLine={false} axisLine={false} interval={0} />
                  <YAxis stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} axisLine={false} width={26} />
                  <Tooltip
                    cursor={{ fill: "rgba(255,255,255,0.04)" }}
                    contentStyle={{
                      background: "#15151A", border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: 12, fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" fill="#A78BFA" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}

        {/* Upsell SOFT — visible UNIQUEMENT si backend renvoie upsell_hint */}
        {report?.upsell_hint && (
          <div
            className="rounded-2xl border border-[#E7C566]/30 bg-gradient-to-br from-[#E7C566]/10 to-transparent p-5"
            data-testid="upsell-card"
          >
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-[#E7C566]/20 border border-[#E7C566]/40 flex items-center justify-center shrink-0">
                <Sparkles className="w-5 h-5 text-[#E7C566]" strokeWidth={1.6} fill="#E7C566" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-sans text-base font-medium text-[#E7C566]">
                  {report.upsell_hint.headline}
                </div>
                <div className="font-sans text-sm text-white/70 mt-1">
                  {report.upsell_hint.reason}
                </div>
                <button
                  onClick={() => setPricingOpen(true)}
                  className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#E7C566] text-black text-sm font-medium hover:bg-[#F4D680] transition-colors"
                  data-testid="upsell-cta-btn"
                >
                  {report.upsell_hint.cta || "Voir les options"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tier explainer (transparence — pas un upsell) */}
        {tenant && (
          <Card title="Ton allocation actuelle" sub={`Tier ${tierInfo.label} · ${tenant.agent_count} agents`} testId="tenant-allocation">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {(tenant.allowed_agents || []).map((a) => (
                <div key={a} className="px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.05] font-mono text-[11px] text-white/70">
                  {a.replace("agent-", "")}
                </div>
              ))}
            </div>
            {tenant.agent_count < 20 && (
              <div className="mt-3 text-[11px] font-mono uppercase tracking-[0.2em] text-white/40">
                {20 - tenant.agent_count} agents supplémentaires sur Pro/Infinite
              </div>
            )}
          </Card>
        )}

        <div className="pt-4 pb-10 text-center font-mono text-[10px] uppercase tracking-[0.28em] text-white/30">
          Calcul ROI — ratios configurables · {report?.generated_at?.slice(0, 19).replace("T", " ")} UTC
        </div>
      </div>

      <PricingModal open={pricingOpen} onOpenChange={setPricingOpen} currentTier={tierKey} />
    </div>
  );
}

function StatCard({ icon, label, value, sub, accent, testId }) {
  return (
    <div
      className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4"
      data-testid={testId}
    >
      <div className="flex items-center gap-2 text-white/50 mb-2">
        <span style={{ color: accent }}>{icon}</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.22em]">{label}</span>
      </div>
      <div className="font-sans text-2xl font-semibold" style={{ color: accent }}>
        {value}
      </div>
      <div className="font-sans text-xs text-white/40 mt-1 truncate">{sub}</div>
    </div>
  );
}

function Card({ title, sub, children, testId }) {
  return (
    <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4" data-testid={testId}>
      <div className="mb-3">
        <div className="font-sans text-sm font-medium">{title}</div>
        {sub && <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/40">{sub}</div>}
      </div>
      {children}
    </div>
  );
}
