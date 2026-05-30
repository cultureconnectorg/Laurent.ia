/**
 * RichContent — détecte et rend les blocs <json>...</json> et <artifact>...</artifact>
 * dans le texte produit par Laurent.ia.
 *
 * - <json> → graphique Recharts (bar/line/area/pie)
 * - <artifact> → iframe sandboxée avec srcDoc=code HTML
 *
 * Buffer de sécurisation (streaming) :
 *   - Tant qu'une balise ouvrante (<json> ou <artifact>) n'a pas son fermant
 *     correspondant dans le texte courant, on N'AFFICHE PAS le contenu Markdown
 *     situé après l'ouverture — un placeholder "skeleton" est rendu à la place.
 *   - Cela garantit que ReactMarkdown ne reçoit jamais une chaîne JSON brute ni
 *     du HTML/JS, et que <artifact> ne s'auto-injecte pas dans une iframe à
 *     moitié écrite (qui chargerait du code inexécutable).
 */
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, CartesianGrid,
} from "recharts";
import { Maximize2, Code2, Loader2 } from "lucide-react";

const COLORS = ["#6BA8FF", "#E7C566", "#5BA0FF", "#A8D4FF", "#2D6FE0", "#D97736"];

const CHART_OPEN = "<json>";
const CHART_CLOSE = "</json>";
const ARTIFACT_OPEN = "<artifact>";
const ARTIFACT_CLOSE = "</artifact>";

/**
 * Parse linéaire et tolérant au streaming.
 * Retourne une liste de segments :
 *   {type: "md", body}
 *   {type: "json", body}
 *   {type: "artifact", body}
 *   {type: "pending", kind: "json"|"artifact"}  ← balise ouverte sans fermant
 */
function parseSegments(text) {
  const segments = [];
  let i = 0;
  const len = text.length;

  while (i < len) {
    // Trouve la prochaine balise ouvrante
    const jOpen = text.indexOf(CHART_OPEN, i);
    const aOpen = text.indexOf(ARTIFACT_OPEN, i);

    let nextOpen = -1;
    let kind = null;
    let openTag = "";
    let closeTag = "";

    if (jOpen !== -1 && (aOpen === -1 || jOpen < aOpen)) {
      nextOpen = jOpen;
      kind = "json";
      openTag = CHART_OPEN;
      closeTag = CHART_CLOSE;
    } else if (aOpen !== -1) {
      nextOpen = aOpen;
      kind = "artifact";
      openTag = ARTIFACT_OPEN;
      closeTag = ARTIFACT_CLOSE;
    }

    if (nextOpen === -1) {
      // Plus de balise — reste = markdown
      if (i < len) segments.push({ type: "md", body: text.slice(i) });
      break;
    }

    // Markdown avant la balise
    if (nextOpen > i) {
      segments.push({ type: "md", body: text.slice(i, nextOpen) });
    }

    const bodyStart = nextOpen + openTag.length;
    const close = text.indexOf(closeTag, bodyStart);

    if (close === -1) {
      // Balise ouverte non encore fermée → placeholder skeleton, on STOP le parsing.
      // Le contenu tronqué après l'ouverture n'est pas affiché.
      segments.push({ type: "pending", kind });
      break;
    }

    const body = text.slice(bodyStart, close);
    segments.push({ type: kind, body });
    i = close + closeTag.length;
  }

  return segments;
}

const PendingBlock = ({ kind }) => {
  const isJson = kind === "json";
  const label = isJson ? "Graphique en préparation…" : "Artifact en préparation…";
  return (
    <div
      className={`my-3 rounded-xl border ${isJson ? "border-[#6BA8FF]/20" : "border-[#E7C566]/20"} bg-white/[0.02] p-4 flex items-center gap-3`}
      data-testid={`pending-${kind}-block`}
    >
      <Loader2 className={`w-4 h-4 animate-spin ${isJson ? "text-[#6BA8FF]" : "text-[#E7C566]"}`} strokeWidth={1.8} />
      <span className={`font-mono text-[10px] uppercase tracking-[0.22em] ${isJson ? "text-[#6BA8FF]" : "text-[#E7C566]"}`}>
        {label}
      </span>
    </div>
  );
};

const ChartBlock = ({ spec }) => {
  let data, type, title, xKey, series;
  try {
    const parsed = typeof spec === "string" ? JSON.parse(spec.trim()) : spec;
    type = parsed.type || "bar";
    title = parsed.title;
    data = parsed.data || [];
    xKey = parsed.xKey || "x";
    series = parsed.series || [];
  } catch (e) {
    return (
      <pre className="text-xs text-red-300 bg-white/[0.03] p-2 rounded-lg overflow-x-auto">
        {String(spec).slice(0, 300)}
      </pre>
    );
  }
  const Container = ({ children }) => (
    <div className="my-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3" data-testid="chart-block">
      {title && <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-[#6BA8FF] mb-2">{title}</div>}
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>{children}</ResponsiveContainer>
      </div>
    </div>
  );
  const common = (
    <>
      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
      <XAxis dataKey={xKey} tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} stroke="rgba(255,255,255,0.1)" />
      <YAxis tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} stroke="rgba(255,255,255,0.1)" />
      <Tooltip contentStyle={{ background: "#0A0F1F", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#F1F4FA" }} />
      <Legend wrapperStyle={{ color: "rgba(255,255,255,0.6)", fontSize: 11 }} />
    </>
  );
  if (type === "line") {
    return (
      <Container>
        <LineChart data={data}>
          {common}
          {series.map((s, i) => (
            <Line key={s.key} type="monotone" dataKey={s.key} name={s.label || s.key} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false} />
          ))}
        </LineChart>
      </Container>
    );
  }
  if (type === "area") {
    return (
      <Container>
        <AreaChart data={data}>
          {common}
          {series.map((s, i) => (
            <Area key={s.key} type="monotone" dataKey={s.key} name={s.label || s.key} stroke={COLORS[i % COLORS.length]} fill={COLORS[i % COLORS.length]} fillOpacity={0.25} />
          ))}
        </AreaChart>
      </Container>
    );
  }
  if (type === "pie") {
    const sKey = series[0]?.key || "value";
    return (
      <Container>
        <PieChart>
          <Tooltip contentStyle={{ background: "#0A0F1F", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#F1F4FA" }} />
          <Pie data={data} dataKey={sKey} nameKey={xKey} outerRadius={80} label={{ fill: "rgba(255,255,255,0.7)", fontSize: 11 }}>
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Legend wrapperStyle={{ color: "rgba(255,255,255,0.6)", fontSize: 11 }} />
        </PieChart>
      </Container>
    );
  }
  return (
    <Container>
      <BarChart data={data}>
        {common}
        {series.map((s, i) => (
          <Bar key={s.key} dataKey={s.key} name={s.label || s.key} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} />
        ))}
      </BarChart>
    </Container>
  );
};

const ArtifactBlock = ({ html }) => {
  const [expanded, setExpanded] = useState(false);
  const [showSource, setShowSource] = useState(false);
  return (
    <div className="my-3 rounded-xl border border-[#E7C566]/30 bg-white/[0.02] overflow-hidden" data-testid="artifact-block">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.06]">
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-[#E7C566]">Artifact · Aperçu live</span>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowSource((v) => !v)} aria-label="Voir le code"
            className="p-1 text-white/50 hover:text-white" data-testid="artifact-toggle-source">
            <Code2 className="w-3.5 h-3.5" strokeWidth={1.6} />
          </button>
          <button onClick={() => setExpanded((v) => !v)} aria-label="Agrandir"
            className="p-1 text-white/50 hover:text-white" data-testid="artifact-toggle-expand">
            <Maximize2 className="w-3.5 h-3.5" strokeWidth={1.6} />
          </button>
        </div>
      </div>
      {showSource ? (
        <pre className="text-[11px] text-white/80 bg-[#0A0F1F] p-3 overflow-x-auto max-h-[400px]" style={{ fontFamily: '"IBM Plex Mono", monospace' }}>
          {html}
        </pre>
      ) : (
        <iframe
          srcDoc={html}
          sandbox="allow-scripts"
          title="Artifact preview"
          className="w-full bg-white"
          style={{ height: expanded ? 600 : 320, border: 0 }}
        />
      )}
    </div>
  );
};

export const RichContent = ({ text = "" }) => {
  const segments = useMemo(() => parseSegments(text), [text]);
  return (
    <div className="laurent-md">
      {segments.map((seg, i) => {
        if (seg.type === "md") {
          return <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>{seg.body}</ReactMarkdown>;
        }
        if (seg.type === "json") return <ChartBlock key={i} spec={seg.body} />;
        if (seg.type === "artifact") return <ArtifactBlock key={i} html={seg.body} />;
        if (seg.type === "pending") return <PendingBlock key={i} kind={seg.kind} />;
        return null;
      })}
    </div>
  );
};

export default RichContent;
