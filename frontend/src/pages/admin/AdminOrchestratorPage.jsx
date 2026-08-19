/**
 * AdminOrchestratorPage — /admin/orchestrator
 *
 * Vue 20 agents WARM (vert/orange/rouge) + incidents ouverts + décisions Founder.
 * Auto-refresh toutes les 8s (le tableau bord doit refléter le live).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Cpu, Loader2, ShieldCheck, ShieldOff, RefreshCw } from "lucide-react";
import AdminLayout from "./AdminLayout";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DEPT_LABEL = {
  strategie: "Stratégie",
  operations: "Opérations",
  creation: "Création",
  interface: "Interface",
};

const STATUS_PALETTE = {
  green:  { dot: "#39D98A", ring: "rgba(57, 217, 138, 0.20)", label: "OK" },
  orange: { dot: "#E7C566", ring: "rgba(231, 197, 102, 0.20)", label: "Doute" },
  red:    { dot: "#FF5C7A", ring: "rgba(255, 92, 122, 0.25)", label: "Alerte" },
};

export default function AdminOrchestratorPage() {
  const [stats, setStats] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);  // incident_id en cours de décision
  const [autoRefresh, setAutoRefresh] = useState(true);

  const load = useCallback(async () => {
    try {
      const [r1, r2] = await Promise.all([
        fetch(`${API}/admin/orchestrator/status`, { credentials: "include" }),
        fetch(`${API}/admin/orchestrator/alerts?status_filter=open`, { credentials: "include" }),
      ]);
      if (r1.ok) setStats(await r1.json());
      if (r2.ok) {
        const d = await r2.json();
        setIncidents(d.incidents || []);
      }
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    if (!autoRefresh) return;
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, [load, autoRefresh]);

  const decide = async (incidentId, decision) => {
    setBusy(incidentId);
    try {
      const r = await fetch(`${API}/admin/orchestrator/decisions`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incident_id: incidentId, decision }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        toast(d.detail || "Erreur décision");
      } else {
        toast(`Incident ${decision === "validate" ? "validé" : decision === "block" ? "bloqué" : "marqué"}`);
        await load();
      }
    } catch (e) {
      toast(e.message || "Erreur réseau");
    }
    setBusy(null);
  };

  const grouped = useMemo(() => {
    const out = { strategie: [], operations: [], creation: [], interface: [] };
    (stats?.agents || []).forEach((a) => { (out[a.department] || []).push(a); });
    return out;
  }, [stats]);

  const busBlocked = stats?.breaker?.blocked_sessions ?? 0;
  const breakerMode = stats?.breaker?.active_mode ? "ACTIVE" : "SHADOW";

  return (
    <AdminLayout title="Orchestrateur — 20 agents" subtitle={`Mode ${breakerMode} · ${busBlocked} session(s) bloquée(s)`}>
      {/* Topline */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <ToplineCard icon={<Cpu className="w-4 h-4" />} label="Agents WARM" value={stats?.agents?.length ?? "—"} accent="#A78BFA" />
        <ToplineCard icon={<CheckCircle2 className="w-4 h-4" />} label="Green" value={(stats?.agents || []).filter(a => a.status === "green").length} accent="#39D98A" />
        <ToplineCard icon={<AlertTriangle className="w-4 h-4" />} label="Orange / Red" value={(stats?.agents || []).filter(a => a.status !== "green").length} accent="#E7C566" />
        <ToplineCard icon={<ShieldOff className="w-4 h-4" />} label="Incidents ouverts" value={incidents.length} accent="#FF5C7A" />
      </div>

      {/* Auto-refresh control */}
      <div className="flex items-center justify-end gap-3 text-[11px] font-mono uppercase tracking-[0.22em]">
        <label className="flex items-center gap-2 text-white/50 cursor-pointer" data-testid="auto-refresh-toggle">
          <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} className="w-3 h-3" />
          Refresh 8s
        </label>
        <button onClick={load} className="text-white/60 hover:text-white inline-flex items-center gap-1" data-testid="manual-refresh-btn">
          <RefreshCw className="w-3 h-3" /> Actualiser
        </button>
      </div>

      {/* Grid agents par département */}
      {loading ? (
        <div className="flex items-center gap-2 text-white/40 text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Chargement…</div>
      ) : (
        Object.entries(grouped).map(([dept, agents]) => (
          <section key={dept} data-testid={`dept-${dept}`}>
            <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.28em] text-white/40">
              {DEPT_LABEL[dept]} · {agents.length}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {agents.map((a) => (
                <AgentCard key={a.id} agent={a} />
              ))}
            </div>
          </section>
        ))
      )}

      {/* Incidents ouverts */}
      <section>
        <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.28em] text-[#FF5C7A]/80">
          Incidents ouverts — Décisions Founder
        </div>
        {incidents.length === 0 ? (
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 text-center font-mono text-[11px] uppercase tracking-[0.22em] text-white/30" data-testid="incidents-empty">
            Aucun incident à arbitrer
          </div>
        ) : (
          <div className="space-y-2">
            {incidents.map((inc) => (
              <IncidentRow key={inc.incident_id} inc={inc} busy={busy === inc.incident_id} onDecide={decide} />
            ))}
          </div>
        )}
      </section>

      {/* Bus stats — debug technique discret */}
      {stats?.bus && (
        <details className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-3">
          <summary className="cursor-pointer font-mono text-[10px] uppercase tracking-[0.22em] text-white/40">
            Bus stats · {stats.bus.dropped} drop(s)
          </summary>
          <pre className="mt-3 text-[11px] text-white/60 overflow-x-auto">{JSON.stringify(stats.bus, null, 2)}</pre>
        </details>
      )}
    </AdminLayout>
  );
}

function ToplineCard({ icon, label, value, accent }) {
  return (
    <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4" data-testid={`topline-${label.toLowerCase()}`}>
      <div className="flex items-center gap-2 text-white/50 mb-2">
        <span style={{ color: accent }}>{icon}</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.22em]">{label}</span>
      </div>
      <div className="font-sans text-2xl font-semibold" style={{ color: accent }}>{value}</div>
    </div>
  );
}

function AgentCard({ agent }) {
  const palette = STATUS_PALETTE[agent.status] || STATUS_PALETTE.green;
  return (
    <div
      className="relative rounded-xl border border-white/[0.06] bg-white/[0.02] p-3"
      style={{ boxShadow: `inset 0 0 0 1px ${palette.ring}` }}
      data-testid={`agent-${agent.id}`}
    >
      <div className="flex items-start gap-2">
        <span className="mt-1 w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: palette.dot, boxShadow: `0 0 8px ${palette.dot}` }} />
        <div className="min-w-0 flex-1">
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/40 truncate">
            {agent.id.replace("agent-", "")}
          </div>
          <div className="font-sans text-[12px] text-white/90 mt-0.5 line-clamp-2">
            {agent.role.split(" — ")[0]}
          </div>
          <div className="mt-2 flex items-center justify-between font-mono text-[9px] uppercase tracking-[0.2em] text-white/40">
            <span>{agent.total_signals} signaux</span>
            <span style={{ color: palette.dot }}>{palette.label}</span>
          </div>
          {agent.last_detail && agent.status !== "green" && (
            <div className="mt-1 font-mono text-[9px] text-white/30 truncate" title={agent.last_detail}>
              {agent.last_detail}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function IncidentRow({ inc, busy, onDecide }) {
  return (
    <div className="rounded-xl border border-[#FF5C7A]/20 bg-[#FF5C7A]/[0.04] p-3" data-testid={`incident-${inc.incident_id}`}>
      <div className="flex items-start gap-3">
        <ShieldOff className="w-4 h-4 text-[#FF5C7A] mt-1 shrink-0" strokeWidth={1.6} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/40">{inc.incident_id}</span>
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#E7C566]/80">{inc.agent}</span>
            {inc.session_id && <span className="font-mono text-[9px] text-white/30">sess: {inc.session_id.slice(-8)}</span>}
          </div>
          <div className="font-sans text-sm text-white/90 mt-0.5">
            {inc.reason} {inc.summary && <span className="text-white/50">— {inc.summary}</span>}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <DecideBtn label="Valider" decision="validate" inc={inc} busy={busy} onClick={onDecide} accent="#39D98A" testIdSuffix="validate" />
            <DecideBtn label="Bloquer" decision="block"    inc={inc} busy={busy} onClick={onDecide} accent="#FF5C7A" testIdSuffix="block" />
            <DecideBtn label="Modifier" decision="modify"  inc={inc} busy={busy} onClick={onDecide} accent="#E7C566" testIdSuffix="modify" />
          </div>
        </div>
      </div>
    </div>
  );
}

function DecideBtn({ label, decision, inc, busy, onClick, accent, testIdSuffix }) {
  return (
    <button
      onClick={() => onClick(inc.incident_id, decision)}
      disabled={busy}
      data-testid={`decide-${testIdSuffix}-${inc.incident_id}`}
      className="px-3 py-1 rounded-full font-mono text-[10px] uppercase tracking-[0.18em] border transition-colors disabled:opacity-40"
      style={{ borderColor: `${accent}55`, color: accent, backgroundColor: `${accent}10` }}
    >
      {busy ? "…" : label}
    </button>
  );
}
