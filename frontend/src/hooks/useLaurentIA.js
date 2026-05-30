/**
 * useLaurentIA — Hook React qui pilote la session vocale.
 * Gère: input (texte ou voix), envoi à /api/laurentia/query, parsing SSE token-by-token,
 * state machine (idle / listening / thinking / speaking).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { withFingerprintHeaders } from "@/services/fingerprint";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const initialMeta = {
  first_name: "Hôte",
  version: "free",
  tier: "free",
  tokens_remaining: 10000,
  quota_warning: false,
  session_id: null,
};

export default function useLaurentIA({ frekId = "DEMO-SAYD", appContext = "direct" } = {}) {
  const [state, setState] = useState("idle"); // idle | listening | thinking | speaking
  const [phase, setPhase] = useState(null);   // "connecting" | "analyzing" | "synthesizing" | "rendering" | null
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const [history, setHistory] = useState([]); // [{role, text}]
  const [meta, setMeta] = useState(initialMeta);
  const [error, setError] = useState(null);

  const recognitionRef = useRef(null);
  const abortRef = useRef(null);

  // ------------- Reset / Load session -------------
  const resetSession = useCallback(() => {
    setHistory([]);
    setResponse("");
    setTranscript("");
    setError(null);
    setState("idle");
    setMeta((m) => ({ ...m, session_id: null }));
    window.speechSynthesis?.cancel();
    if (abortRef.current) abortRef.current.abort();
  }, []);

  const loadSession = useCallback(
    async (sessionId) => {
      if (!sessionId) return;
      try {
        const url = `${API}/laurentia/sessions/${encodeURIComponent(sessionId)}?frek_id=${encodeURIComponent(frekId)}`;
        const r = await fetch(url, { credentials: "include" });
        if (!r.ok) return;
        const data = await r.json();
        const msgs = (data.messages || []).map((m) => ({
          role: m.role === "user" ? "user" : "laurentia",
          text: m.text,
        }));
        setHistory(msgs);
        setResponse("");
        setTranscript("");
        setError(null);
        setState("idle");
        setMeta((m) => ({ ...m, session_id: sessionId }));
      } catch (_) {}
    },
    [frekId]
  );

  // ------------- Init instance -------------
  useEffect(() => {
    let mounted = true;
    // Skip silencieux pour ANON-* — la persistance fantôme s'en charge via /resolve
    // (évite le 401 cosmétique au premier paint d'un utilisateur anonyme).
    if (!frekId || frekId.startsWith("ANON-")) {
      return;
    }
    (async () => {
      try {
        const r = await fetch(`${API}/laurentia/instances/${encodeURIComponent(frekId)}`);
        if (!r.ok) return;
        const data = await r.json();
        if (!mounted) return;
        setMeta((m) => ({
          ...m,
          first_name: data.first_name || "Hôte",
          version: data.instance?.version || "free",
          tier: data.instance?.tier || data.instance?.version || "free",
          tokens_remaining: Math.max(
            0,
            (data.instance?.tokens_limit_month || 10000) - (data.instance?.tokens_used_month || 0)
          ),
        }));
      } catch (e) {
        // silencieux — premier load
      }
    })();
    return () => {
      mounted = false;
    };
  }, [frekId]);

  // ------------- Web Speech Recognition -------------
  const startListening = useCallback(() => {
    setError(null);
    setTranscript("");
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      // pas de reconnaissance vocale → fallback: state listening sans STT
      setState("listening");
      return;
    }
    const rec = new SR();
    rec.lang = "fr-FR";
    rec.interimResults = true;
    rec.continuous = false;
    let finalText = "";
    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalText += t;
        else interim += t;
      }
      setTranscript((finalText + interim).trim());
    };
    rec.onerror = (e) => {
      setError(e.error || "Erreur reconnaissance vocale");
      setState("idle");
    };
    rec.onend = () => {
      if (finalText.trim()) {
        sendQuery(finalText.trim());
      } else {
        setState("idle");
      }
    };
    recognitionRef.current = rec;
    setState("listening");
    try {
      rec.start();
    } catch (_) {}
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (_) {}
    } else {
      setState("idle");
    }
  }, []);

  // ------------- Speech Synthesis -------------
  // Sélection préférentielle d'une voix française à coloration caribéenne/chaleureuse.
  // Heuristique : priorise les voix premium (Thomas, Audrey, Amélie, Antilles, Caribbean),
  // puis les voix Google FR, puis tout fr-* par défaut.
  const VOICE_PRIORITY = [
    /antill|caribb|créol|creol|guadel|martin|haiti/i,        // 1. Voix créole / antillaise
    /^Thomas$|^Audrey$|^Amélie$|^Amelie$|^Aurélie$|premium/i, // 2. Voix Apple premium FR
    /Google.*français|Google.*French/i,                       // 3. Google FR
    /Microsoft.*Henri|Microsoft.*Julie|Microsoft.*Paul/i,     // 4. Microsoft FR Premium
  ];

  const pickFrenchVoice = useCallback(() => {
    if (!("speechSynthesis" in window)) return null;
    const voices = window.speechSynthesis.getVoices() || [];
    const frVoices = voices.filter((v) => /^fr/i.test(v.lang));
    if (!frVoices.length) return null;
    for (const pattern of VOICE_PRIORITY) {
      const found = frVoices.find((v) => pattern.test(v.name) || pattern.test(v.lang));
      if (found) return found;
    }
    // Préfère voix masculines pour le ton noble protecteur
    const male = frVoices.find((v) => /thomas|paul|henri|antoine|mathieu|guillaume/i.test(v.name));
    return male || frVoices[0];
  }, []);

  // Précharge la liste des voix (Chrome la lazy-load)
  useEffect(() => {
    if (!("speechSynthesis" in window)) return;
    const w = window;
    if (w.speechSynthesis.getVoices().length === 0) {
      w.speechSynthesis.onvoiceschanged = () => {};
    }
  }, []);

  const speak = useCallback((text) => {
    if (window.localStorage.getItem("laurentia_voice") === "off") return;
    if (!("speechSynthesis" in window)) return;
    try {
      const u = new SpeechSynthesisUtterance(text);
      const voice = pickFrenchVoice();
      if (voice) u.voice = voice;
      u.lang = voice?.lang || "fr-FR";
      // Ton noble protecteur : légèrement plus grave et plus lent
      u.rate = 0.95;
      u.pitch = 0.92;
      u.volume = 1.0;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    } catch (_) {}
  }, [pickFrenchVoice]);

  const stopSpeaking = useCallback(() => {
    try { window.speechSynthesis?.cancel(); } catch (_) {}
  }, []);

  // ------------- Send Query (SSE) -------------
  const sendQuery = useCallback(
    async (text, files = []) => {
      if (!text || !text.trim()) return;
      setError(null);
      setState("thinking");
      setPhase("connecting");
      setResponse("");
      const hasFiles = Array.isArray(files) && files.length > 0;
      const userBubble = hasFiles
        ? { role: "user", text, files: files.map((f) => ({ name: f.name, size: f.size })) }
        : { role: "user", text };
      setHistory((h) => [...h, userBubble]);

      try {
        const ctrl = new AbortController();
        abortRef.current = ctrl;

        let fetchOpts;
        if (hasFiles) {
          const fd = new FormData();
          fd.append(
            "payload",
            JSON.stringify({
              frek_id: frekId,
              input: text,
              context: { app: appContext, session_id: meta.session_id },
            })
          );
          files.forEach((f) => fd.append("files", f, f.name));
          fetchOpts = {
            method: "POST",
            body: fd,
            headers: withFingerprintHeaders({ Accept: "text/event-stream" }),
            signal: ctrl.signal,
            credentials: "include",
          };
        } else {
          fetchOpts = {
            method: "POST",
            headers: withFingerprintHeaders({
              "Content-Type": "application/json",
              Accept: "text/event-stream",
            }),
            body: JSON.stringify({
              frek_id: frekId,
              input: text,
              context: { app: appContext, session_id: meta.session_id },
            }),
            signal: ctrl.signal,
            credentials: "include",
          };
        }

        const r = await fetch(`${API}/laurentia/query`, fetchOpts);
        if (!r.ok || !r.body) {
          let detail = `HTTP ${r.status}`;
          try {
            const j = await r.json();
            if (j?.detail) detail = j.detail;
          } catch (_) {}
          throw new Error(detail);
        }
        const reader = r.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        let full = "";

        // Switch to speaking state on first token
        let switchedToSpeaking = false;

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          // SSE: events separated by \n\n
          let idx;
          while ((idx = buffer.indexOf("\n\n")) !== -1) {
            const raw = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            const evt = parseSSE(raw);
            if (!evt) continue;
            if (evt.event === "meta") {
              setPhase("analyzing");
              setMeta((m) => ({
                ...m,
                first_name: evt.data.first_name || m.first_name,
                version: evt.data.version || m.version,
                tier: evt.data.tier || evt.data.version || m.tier,
                tokens_remaining: evt.data.tokens_remaining ?? m.tokens_remaining,
                quota_warning: !!evt.data.quota_warning,
                session_id: evt.data.session_id || m.session_id,
              }));
              // Si meta.files contient des stats serveur (pages, chars), enrichit
              // la dernière bulle utilisateur pour faire briller la puce en or.
              const serverFiles = evt.data.files;
              if (Array.isArray(serverFiles) && serverFiles.length > 0) {
                setHistory((h) => {
                  if (!h.length) return h;
                  const last = h[h.length - 1];
                  if (last.role !== "user" || !last.files) return h;
                  const enriched = last.files.map((f, i) => ({
                    ...f,
                    ...(serverFiles[i] || {}),
                    digested: true,
                  }));
                  return [...h.slice(0, -1), { ...last, files: enriched }];
                });
              }
            } else if (evt.event === "token") {
              full += evt.data.text || "";
              setResponse(full);
              if (!switchedToSpeaking) {
                switchedToSpeaking = true;
                setState("speaking");
                setPhase("synthesizing");
              }
              // Détection de bloc spécial → indication visuelle distincte
              if (/<json>|<artifact>/.test(full) && !/(<\/json>|<\/artifact>)/.test(full)) {
                setPhase("rendering");
              } else if (phase === "rendering" && /(<\/json>|<\/artifact>)/.test(full)) {
                setPhase("synthesizing");
              }
            } else if (evt.event === "done") {
              setHistory((h) => [...h, { role: "laurentia", text: full }]);
              setMeta((m) => ({
                ...m,
                tokens_remaining: Math.max(0, m.tokens_remaining - (evt.data.tokens_used || 0)),
              }));
              setState("idle");
              setPhase(null);
              speak(full);
            } else if (evt.event === "error") {
              setError(evt.data.message || "Erreur");
              setState("idle");
              setPhase(null);
            }
          }
        }
      } catch (e) {
        if (e.name !== "AbortError") {
          setError(e.message || "Erreur réseau");
        }
        setState("idle");
        setPhase(null);
      } finally {
        abortRef.current = null;
      }
    },
    [frekId, appContext, meta.session_id, speak, phase]
  );

  const cancel = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    window.speechSynthesis?.cancel();
    setState("idle");
    setPhase(null);
  }, []);

  const exportPdf = useCallback(
    async ({ title, subtitle, content_md, footer_note }) => {
      const r = await fetch(`${API}/export/pdf`, {
        method: "POST",
        headers: withFingerprintHeaders({ "Content-Type": "application/json" }),
        credentials: "include",
        body: JSON.stringify({
          title: title || "Note Laurent.ia",
          subtitle: subtitle || null,
          content_md,
          footer_note: footer_note || "Document généré par Laurent.ia · CVLN Group",
        }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        const e = new Error(err.detail || `Export PDF impossible (HTTP ${r.status})`);
        e.status = r.status;
        e.payload = err;
        throw e;
      }
      const blob = await r.blob();
      const slug = (title || "rapport").toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 50);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `laurentia-${slug}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
      // Lecture des en-têtes : quota / signature
      return {
        signature: r.headers.get("X-Laurentia-Signature") === "1",
        free_exports_used: parseInt(r.headers.get("X-Laurentia-Free-Used") || "0", 10),
        free_exports_limit: parseInt(r.headers.get("X-Laurentia-Free-Limit") || "0", 10),
      };
    },
    []
  );

  return {
    state,
    phase,
    transcript,
    response,
    history,
    meta,
    error,
    startListening,
    stopListening,
    sendQuery,
    cancel,
    resetSession,
    loadSession,
    exportPdf,
    stopSpeaking,
  };
}

function parseSSE(raw) {
  const lines = raw.split("\n");
  let event = "message";
  let dataStr = "";
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
  }
  if (!dataStr) return null;
  try {
    return { event, data: JSON.parse(dataStr) };
  } catch (_) {
    return { event, data: { text: dataStr } };
  }
}
