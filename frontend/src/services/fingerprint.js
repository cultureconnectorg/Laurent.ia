/**
 * fingerprint.js — Empreinte matérielle stable pour identifier l'appareil
 * sans cookies ni mot de passe. Sert le header `X-Device-Fingerprint`.
 *
 * Sources d'entropie (toutes côté navigateur, aucune donnée perso) :
 *  - Canvas 2D rendu (sub-pixel rendering propre au GPU)
 *  - WebGL VENDOR + RENDERER (carte graphique)
 *  - hardwareConcurrency, deviceMemory, screen.{w,h,colorDepth}, timezone, langue, platform
 *
 * Le frontend N'envoie PAS de hash :
 *   - on envoie la chaîne assemblée brute (compacte, ~200 chars)
 *   - le backend HMAC-SHA256 avec son sel pour produire le `device_id` final.
 *
 * Cache : valeur conservée en localStorage (`laurentia_device_fp`). Toute
 * collision est résolue côté backend (HMAC), donc la stabilité prime sur
 * l'unicité absolue.
 */

const STORAGE_KEY = "laurentia_device_fp";

function safe(fn, fallback = "?") {
  try { return fn(); } catch (_) { return fallback; }
}

function canvasSignature() {
  return safe(() => {
    const c = document.createElement("canvas");
    c.width = 220; c.height = 60;
    const ctx = c.getContext("2d");
    if (!ctx) return "no2d";
    ctx.textBaseline = "top";
    ctx.font = "14px 'Arial'";
    ctx.fillStyle = "#0A0F1F";
    ctx.fillRect(0, 0, 220, 60);
    ctx.fillStyle = "#E7C566";
    ctx.fillText("Laurent.ia ✦ FREK-ID 𝛂2026", 8, 8);
    ctx.fillStyle = "#5BA0FFcc";
    ctx.fillRect(40, 32, 120, 14);
    // Le data URL exécute le pipeline de rendu — chaque GPU/driver produit un hash différent
    const url = c.toDataURL();
    // Compact : on garde seulement la fin (la signature pixel)
    return url.slice(-90);
  });
}

function webglSignature() {
  return safe(() => {
    const c = document.createElement("canvas");
    const gl = c.getContext("webgl") || c.getContext("experimental-webgl");
    if (!gl) return "nowebgl";
    const dbg = gl.getExtension("WEBGL_debug_renderer_info");
    const vendor = dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR);
    const renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    return `${vendor}|${renderer}`;
  });
}

function hardwareSignature() {
  const cpu = safe(() => navigator.hardwareConcurrency, "?");
  const mem = safe(() => navigator.deviceMemory, "?");
  const platform = safe(() => navigator.platform, "?");
  const lang = safe(() => navigator.language, "?");
  const tz = safe(() => Intl.DateTimeFormat().resolvedOptions().timeZone, "?");
  const w = safe(() => window.screen.width, 0);
  const h = safe(() => window.screen.height, 0);
  const cd = safe(() => window.screen.colorDepth, 0);
  return `cpu:${cpu}|mem:${mem}|plat:${platform}|lang:${lang}|tz:${tz}|s:${w}x${h}x${cd}`;
}

/**
 * Retourne une empreinte stable (string ~180-260 chars).
 * Cache en localStorage pour cohérence inter-onglets.
 */
export function getDeviceFingerprint() {
  try {
    const cached = localStorage.getItem(STORAGE_KEY);
    if (cached && cached.length > 60) return cached;
  } catch (_) {}

  const fp = [
    `c:${canvasSignature()}`,
    `g:${webglSignature()}`,
    `h:${hardwareSignature()}`,
  ].join("||");

  try { localStorage.setItem(STORAGE_KEY, fp); } catch (_) {}
  return fp;
}

/**
 * Helper fetch — fusionne le header X-Device-Fingerprint avec les autres.
 * À utiliser pour TOUS les appels à /api/laurentia/* et /api/export/*.
 */
export function withFingerprintHeaders(extra = {}) {
  return { ...extra, "X-Device-Fingerprint": getDeviceFingerprint() };
}
