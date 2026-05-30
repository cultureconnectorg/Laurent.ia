/**
 * RichBlocks — détecte et rend les blocs <json>...</json> et <artifact>...</artifact>
 * dans le texte produit par Laurent.ia.
 *
 * - <json> → graphique Recharts (bar/line/area/pie)
 * - <artifact> → iframe sandboxée avec srcDoc=code HTML
 */
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, CartesianGrid,
} from "recharts";
import { Maximize2, Code2 } from "lucide-react";

const COLORS = ["#6BA8FF", "#E7C566", "#5BA0FF", "#A8D4FF", "#2D6FE0", "#D97736"];

const CHART_RE = /<json>([\s\S]*?)<\/json>/g;
const ARTIFACT_RE = /<artifact>([\s\S]*?)<\/artifact>/g;

function parseSegments(text) {
  const segments = [];
  let lastIdx = 0;
  // Combine both patterns: walk in order
  const matches = [];
  for (const m of text.matchAll(CHART_RE)) matches.push({ type: "json", idx: m.index, end: m.index + m[0].length, body: m[1] });
  for (const m of text.matchAll(ARTIFACT_RE)) matches.push({ type: "artifact", idx: m.index, end: m.index + m[0].length, body: m[1] });
  matches.sort((a, b) => a.idx - b.idx);
  for (const m of matches) {
    if (m.idx > lastIdx) segments.push({ type: "md", body: text.slice(lastIdx, m.idx) });
    segments.push(m);
    lastIdx = m.end;
  }
  if (lastIdx < text.length) segments.push({ type: "md", body: text.slice(lastIdx) });
  return segments;
}

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
        return null;
      })}
    </div>
  );
};

export default RichContent;
