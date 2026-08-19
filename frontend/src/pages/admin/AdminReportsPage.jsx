/**
 * AdminReportsPage — /admin/reports
 *
 * Bilan founder global : tenants actifs, time saved, latence p50/p95,
 * tier distribution, top incidents, top tenants, paid_subscribers (weekly).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
  CartesianGrid,
} from "recharts";
import {
  Activity, AlertOctagon, Clock, Crown, Loader2, RefreshCw, Users,
} from "lucide-react";
import AdminLayout from "./AdminLayout";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TIER_COLORS = {
  free: "#9CA3AF",
  creator: "#E7C566",
  pro: "#A78BFA",
  infinite: "#A78BFA",
};

export default function AdminReportsPage() {
  const [range, setRange] = useState("daily"); // daily | weekly
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [snapshotting, setSnapshotting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/admin/reports/${range}`, { credentials: "include" });
      if (r.ok) setReport(await r.json());
    } catch (_) {}
    setLoading(false);
  }, [range]);

  useEffect(() => { load(); }, [load]);

  const triggerSnapshot = async () => {
    setSnapshotting(true);
    try {
      const r = await fetch(`${API}/admin/reports/snapshot`, { method: "POST", credentials: "include" });
      if (r.ok) {
        const d = await r.json();
        toast(`Snapshot OK · ${d.tenant_daily_reports || 0} rapports tenants`);
        await load();
      } else {
        toast("Erreur snapshot");
      }
    } catch (e) { toast(e.message || "Erreur"); }
    setSnapshotting(false);
  };

  const tierDist = useMemo(() => {
    const d = report?.tier_distribution || {};
    return Object.entries(d).map(([k, v]) => ({ name: k, value: v, color: TIER_COLORS[k] || "#9CA3AF" }));
  }, [report]);

  const topTenants = useMemo(() => {
    return (report?.top_tenants || []).slice(0, 8).map((t) => ({
      ...t,
      short_id: (t.frek_id || "").slice(-8),
      hours: Math.round((t.time_saved_min / 60.0) * 10) / 10,
    }));
  }, [report]);

  return (
    <AdminLayout
      title="Bilan global"
      subtitle={range === "daily" ? "Snapshot 24h" : "Snapshot 7j"}
    >
      <div className="flex flex-wrap items-center gap-3 justify-between">
        <div className="flex rounded-full bg-white/[0.04] p-0.5 border border-white/[0.06]">
          {["daily", "weekly"].map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              data-testid={`reports-range-${r}`}
              className={`px-3 py-1.5 rounded-full text-[11px] font-mono uppercase tracking-[0.2em] transition-colors ${
                range === r ? "bg-white text-black" : "text-white/60 hover:text-white"
              }`}
            >
              {r === "daily" ? "24h" : "7j"}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 text-[11px] font-mono uppercase tracking-[0.22em]">
          <button onClick={triggerSnapshot} disabled={snapshotting} className="text-white/60 hover:text-white inline-flex items-center gap-1 disabled:opacity-40" data-testid="trigger-snapshot-btn">
            {snapshotting ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
            Snapshot manuel
          </button>
        </div>
      </div>

      {/* Topline */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <ToplineCard icon={<Users className="w-4 h-4" />} label="Tenants actifs" value={loading ? "—" : (report?.active_tenants ?? 0)} accent="#A78BFA" testId="kpi-tenants" />
        <ToplineCard icon={<Clock className="w-4 h-4" />} label="Heures économisées" value={loading ? "—" : `${report?.time_saved_hours ?? 0}h`} accent="#E7C566" testId="kpi-hours" />
        <ToplineCard icon={<Activity className="w-4 h-4" />} label="Actions" value={loading ? "—" : (report?.total_actions ?? 0)} accent="#39D98A" testId="kpi-actions" />
        <ToplineCard icon={<AlertOctagon className="w-4 h-4" />} label="Breach attempts" value={loading ? "—" : (report?.breach_attempts ?? 0)} accent="#FF5C7A" testId="kpi-breach" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Distribution tiers */}
        <Card title="Distribution tiers" sub={`${tierDist.length} segments actifs`} testId="card-tier-dist">
          {loading ? <Skeleton className="h-[200px] w-full bg-white/[0.04]" /> : tierDist.length === 0 ? (
            <Empty>Pas d'activité tenant sur la période</Empty>
          ) : (
            <div className="h-[200px]">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={tierDist} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={2}>
                    {tierDist.map((e) => <Cell key={e.name} fill={e.color} stroke="#0A0A0B" strokeWidth={2} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#15151A", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* Latence */}
        <Card title="Latence chat" sub="p50 / p95 (ms)" testId="card-latency">
          {loading ? <Skeleton className="h-[200px] w-full bg-white/[0.04]" /> : (
            <div className="h-[200px] flex items-center justify-around">
              <Gauge label="p50" value={report?.latency_ms_p50} color="#39D98A" />
              <Gauge label="p95" value={report?.latency_ms_p95} color="#E7C566" />
              {range === "weekly" && (
                <Gauge label="Payants" value={report?.paid_subscribers} suffix="users" color="#A78BFA" />
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Top tenants */}
      <Card title="Top tenants" sub="par nombre d'actions" testId="card-top-tenants">
        {loading ? <Skeleton className="h-[180px] w-full bg-white/[0.04]" /> : topTenants.length === 0 ? (
          <Empty>Pas de tenant à afficher</Empty>
        ) : (
          <div className="h-[200px]">
            <ResponsiveContainer>
              <BarChart data={topTenants} layout="vertical">
                <CartesianGrid stroke="rgba(255,255,255,0.04)" horizontal={false} />
                <XAxis type="number" stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="short_id" stroke="rgba(255,255,255,0.4)" fontSize={10} tickLine={false} axisLine={false} width={70} />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.04)" }}
                  contentStyle={{ background: "#15151A", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, fontSize: 12 }}
                  formatter={(v, key, p) => [v, key === "actions" ? "Actions" : key]}
                />
                <Bar dataKey="actions" radius={[0, 6, 6, 0]}>
                  {topTenants.map((t) => <Cell key={t.frek_id} fill={TIER_COLORS[t.tier] || "#9CA3AF"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      {/* Top incidents */}
      <Card title="Incidents souverains" sub={`${(report?.top_incidents || []).length} récents`} testId="card-top-incidents">
        {loading ? <Skeleton className="h-[140px] w-full bg-white/[0.04]" /> : (report?.top_incidents || []).length === 0 ? (
          <Empty>Aucun incident sur la période</Empty>
        ) : (
          <ul className="space-y-1.5">
            {(report?.top_incidents || []).map((i) => (
              <li key={i.incident_id} className="flex items-center gap-3 text-[12px]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#FF5C7A] shrink-0" />
                <span className="font-mono text-[10px] text-white/40 shrink-0">{i.incident_id.slice(-8)}</span>
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#E7C566]/80 shrink-0">{i.agent}</span>
                <span className="text-white/80 truncate">{i.reason}{i.summary ? ` — ${i.summary}` : ""}</span>
                <span className={`ml-auto font-mono text-[9px] uppercase tracking-[0.2em] ${i.status === "closed" ? "text-white/30" : "text-[#FF5C7A]"}`}>{i.status}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {range === "weekly" && (
        <Card title="Souveraineté corpus" sub="Score moyen pipeline hebdo" testId="card-corpus-score">
          <div className="font-sans text-3xl font-semibold text-[#A78BFA]">
            {report?.corpus_score_avg !== null && report?.corpus_score_avg !== undefined
              ? report.corpus_score_avg
              : "—"}
          </div>
          <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/40 mt-1">
            Cible : ≥ 0.70 · Seuil corpus pipeline
          </div>
        </Card>
      )}

      <div className="pt-2 pb-10 text-center font-mono text-[10px] uppercase tracking-[0.28em] text-white/30">
        Généré le {report?.generated_at?.slice(0, 19).replace("T", " ")} UTC
      </div>
    </AdminLayout>
  );
}

function ToplineCard({ icon, label, value, accent, testId }) {
  return (
    <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4" data-testid={testId}>
      <div className="flex items-center gap-2 text-white/50 mb-2">
        <span style={{ color: accent }}>{icon}</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.22em]">{label}</span>
      </div>
      <div className="font-sans text-2xl font-semibold" style={{ color: accent }}>{value}</div>
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

function Empty({ children }) {
  return (
    <div className="text-center py-8 font-mono text-[11px] uppercase tracking-[0.22em] text-white/30">
      {children}
    </div>
  );
}

function Gauge({ label, value, suffix = "ms", color = "#39D98A" }) {
  const display = value === null || value === undefined ? "—" : value;
  return (
    <div className="text-center">
      <div className="font-mono text-[10px] uppercase tracking-[0.28em] text-white/40">{label}</div>
      <div className="font-sans text-3xl font-semibold mt-1" style={{ color }}>
        {display}
        {value !== null && value !== undefined && <span className="text-sm text-white/40 ml-1">{suffix}</span>}
      </div>
    </div>
  );
}
