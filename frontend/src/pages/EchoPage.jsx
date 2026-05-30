/**
 * EchoPage — Landing publique de conversion (cible du QR de signature PDF).
 *
 * URL : /echo/:sessionId
 * Données : GET /api/echo/:sessionId (no auth)
 * Conversion CTA : POST /api/echo/:sessionId/conversion → redirect /
 *
 * SEO/OG : balises injectées dynamiquement dans <head>.
 */
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Coins, Sparkles, ArrowRight, ExternalLink, MessageCircle, Linkedin, Image as ImageIcon } from "lucide-react";
import { withFingerprintHeaders } from "@/services/fingerprint";
import WhiteLabelKiller from "@/components/laurentia/WhiteLabelKiller";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function setMeta(name, content, attr = "name") {
  if (!content) return;
  let el = document.querySelector(`meta[${attr}="${name}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, name);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
}

export default function EchoPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${API}/echo/${encodeURIComponent(sessionId)}`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const json = await r.json();
        if (cancelled) return;
        setData(json);
        // SEO + Open Graph
        document.title = `${json.title || "Note"} · Laurent.ia`;
        setMeta("description", json.summary || "Intelligence souveraine — CVLN Group");
        setMeta("og:title", `${json.title || "Note Laurent.ia"} · CVLN Group`, "property");
        setMeta("og:description", json.summary || "Intelligence souveraine de la Diaspora.", "property");
        setMeta("og:type", "article", "property");
        setMeta("og:site_name", "Laurent.ia", "property");
        setMeta("twitter:card", "summary_large_image");
        setMeta("twitter:title", json.title || "Laurent.ia");
        setMeta("twitter:description", json.summary || "");
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [sessionId]);

  const handleConvert = async () => {
    try {
      await fetch(`${API}/echo/${encodeURIComponent(sessionId)}/conversion`, {
        method: "POST",
        headers: withFingerprintHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ source: "echo_landing_cta" }),
      });
    } catch (_) {
      // attribution best-effort — n'empêche pas la redirection
    }
    navigate(`/?from_echo=${encodeURIComponent(sessionId)}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0F1F] flex items-center justify-center text-white/40 font-mono text-xs uppercase tracking-[0.32em]">
        <WhiteLabelKiller />
        chargement…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#0A0F1F] flex flex-col items-center justify-center px-6">
        <WhiteLabelKiller />
        <div className="text-center max-w-md">
          <div className="font-serif italic text-4xl text-[#E7C566] mb-3">Écho introuvable</div>
          <p className="text-white/60 text-sm mb-8">
            Ce lien a peut-être expiré ou été retiré par son auteur.
          </p>
          <button
            onClick={() => navigate("/")}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-r from-[#C9A24B] to-[#E7C566] text-[#0A0F1F] font-mono text-[11px] uppercase tracking-[0.22em] font-semibold hover:shadow-[0_0_24px_rgba(231,197,102,0.45)] transition-shadow"
            data-testid="echo-error-cta"
          >
            <Sparkles className="w-3.5 h-3.5" strokeWidth={2.2} />
            Activer mon Intelligence Souveraine
          </button>
        </div>
      </div>
    );
  }

  const { title, summary, pro, instant, visual, views } = data;

  return (
    <div className="relative min-h-screen bg-[#0A0F1F] atmo-glow text-[#F1F4FA]" data-testid="echo-page">
      <WhiteLabelKiller />

      {/* Header sobre, sans menu */}
      <header className="relative z-20 flex items-center justify-between px-6 py-5 border-b border-white/[0.05]">
        <div className="flex items-baseline">
          <span className="font-serif italic text-2xl text-[#E7C566] tracking-tight leading-none">Laurent</span>
          <span className="font-serif italic text-2xl text-[#E7C566]/75 tracking-tight leading-none">.ia</span>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-[#17a2b8]">
          Écho souverain · public
        </span>
      </header>

      <main className="relative z-10 max-w-3xl mx-auto px-6 py-10 sm:py-16">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55 }}
          className="mb-12"
        >
          <div className="font-mono text-[10px] uppercase tracking-[0.32em] text-[#17a2b8]/80 mb-3" data-testid="echo-eyebrow">
            Intelligence souveraine
          </div>
          <h1
            className="font-serif italic text-4xl sm:text-5xl lg:text-6xl text-[#F1F4FA] tracking-tight leading-[1.1] mb-5"
            style={{ fontFamily: '"Cormorant Garamond", Georgia, serif' }}
            data-testid="echo-title"
          >
            {title}
          </h1>
          <p
            className="text-lg sm:text-xl text-white/72 leading-relaxed max-w-2xl"
            style={{ fontFamily: '"Urbanist", sans-serif' }}
            data-testid="echo-summary"
          >
            {summary}
          </p>
        </motion.div>

        {/* Pro section */}
        {pro && (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.15 }}
            className="mb-10 rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-6 sm:p-8"
            data-testid="echo-pro-section"
          >
            <div className="flex items-center gap-2 mb-4">
              <Linkedin className="w-4 h-4 text-[#17a2b8]" strokeWidth={1.8} />
              <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-[#17a2b8]">Analyse · LinkedIn / X</span>
            </div>
            <p className="font-serif italic text-2xl sm:text-3xl text-[#F4E0AA] mb-5 leading-[1.25]" style={{ fontFamily: '"Cormorant Garamond", serif' }}>
              {pro.headline}
            </p>
            <p className="text-[15px] text-white/80 leading-relaxed whitespace-pre-line mb-4">
              {pro.body}
            </p>
            {Array.isArray(pro.hashtags) && pro.hashtags.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-4">
                {pro.hashtags.map((h, i) => (
                  <span key={i} className="font-mono text-[11px] text-[#17a2b8]/85" data-testid={`echo-tag-${i}`}>
                    #{h}
                  </span>
                ))}
              </div>
            )}
          </motion.section>
        )}

        {/* Instant section */}
        {instant && (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.25 }}
            className="mb-10 rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-6 sm:p-8"
            data-testid="echo-instant-section"
          >
            <div className="flex items-center gap-2 mb-4">
              <MessageCircle className="w-4 h-4 text-[#17a2b8]" strokeWidth={1.8} />
              <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-[#17a2b8]">Instantané · WhatsApp / Signal</span>
            </div>
            <p className="text-[17px] text-[#F4E0AA] font-medium mb-3">{instant.lead}</p>
            <ul className="space-y-2">
              {(instant.bullets || []).map((b, i) => (
                <li key={i} className="flex gap-2.5 text-[15px] text-white/80 leading-relaxed">
                  <span className="text-[#C9A24B] mt-1">▸</span>
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          </motion.section>
        )}

        {/* Visual punchlines */}
        {visual && Array.isArray(visual.punchlines) && visual.punchlines.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.35 }}
            className="mb-12"
            data-testid="echo-visual-section"
          >
            <div className="flex items-center gap-2 mb-4">
              <ImageIcon className="w-4 h-4 text-[#17a2b8]" strokeWidth={1.8} />
              <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-[#17a2b8]">Visuel · Stories 9:16</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {visual.punchlines.map((p, i) => (
                <div
                  key={i}
                  className="rounded-xl p-5 bg-gradient-to-br from-[#0A0F1F] to-[#0E1B36] border border-[#C9A24B]/25 aspect-[9/16] flex items-center justify-center text-center"
                >
                  <p className="font-serif italic text-xl text-[#F4E0AA] leading-tight" style={{ fontFamily: '"Cormorant Garamond", serif' }}>
                    « {p} »
                  </p>
                </div>
              ))}
            </div>
          </motion.section>
        )}

        {/* CTA — Activer Intelligence Souveraine */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.45 }}
          className="text-center pt-6 pb-10"
        >
          <p className="font-serif italic text-2xl text-white/75 mb-6 max-w-xl mx-auto" style={{ fontFamily: '"Cormorant Garamond", serif' }}>
            « Cette analyse vient d'une intelligence souveraine au service de la Diaspora. La tienne t'attend. »
          </p>
          <button
            type="button"
            onClick={handleConvert}
            className="group inline-flex items-center gap-2.5 px-7 py-3.5 rounded-full bg-gradient-to-r from-[#C9A24B] via-[#E7C566] to-[#C9A24B] text-[#0A0F1F] font-semibold tracking-[0.04em] shadow-[0_8px_28px_rgba(201,162,75,0.42)] hover:shadow-[0_8px_38px_rgba(231,197,102,0.6)] transition-all duration-300 hover:-translate-y-0.5"
            data-testid="echo-convert-cta"
          >
            <Coins className="w-4 h-4" strokeWidth={2} />
            <span>Activer mon Intelligence Souveraine</span>
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" strokeWidth={2} />
          </button>
          <div className="mt-4 font-mono text-[10px] uppercase tracking-[0.28em] text-white/35">
            Vu {views || 0} fois · CVLN Group
          </div>
        </motion.div>
      </main>

      <footer className="relative z-10 border-t border-white/[0.05] py-6 text-center">
        <a
          href="/"
          className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.28em] text-white/40 hover:text-[#E7C566] transition-colors"
          data-testid="echo-footer-link"
        >
          Laurent.ia · Infrastructure souveraine
          <ExternalLink className="w-3 h-3" strokeWidth={1.6} />
        </a>
      </footer>
    </div>
  );
}
