/**
 * WhiteLabelKiller — Neutralise toute trace de tiers (notamment "Made with Emergent")
 * dans le DOM, qu'elle soit injectée par CSS, iframe, ou script asynchrone.
 *
 * Stratégie en 3 couches :
 *   1) CSS : règles globales display:none sur sélecteurs connus (rapide, sans JS).
 *   2) MutationObserver : intercepte toute injection dynamique et supprime le nœud.
 *   3) Périodique : balayage toutes les 2s comme filet de sécurité.
 *
 * Aucune dépendance externe.
 */
import { useEffect } from "react";

// Sélecteurs visés (mots-clés "emergent" agnostiques de casse)
const SELECTORS = [
  '[data-emergent]',
  '[class*="emergent"]',
  '[class*="Emergent"]',
  '[id*="emergent"]',
  '[id*="Emergent"]',
  'a[href*="emergent.sh"]',
  'a[href*="emergentagent.com"]',
];

// Texte cible (case insensitive) — repère "Made with Emergent" et variantes
const TEXT_PATTERNS = [
  /made\s+with\s+emergent/i,
  /built\s+with\s+emergent/i,
  /powered\s+by\s+emergent/i,
];

function nodeContainsBranding(el) {
  if (!el || el.nodeType !== 1) return false;
  const t = (el.textContent || "").trim();
  if (!t || t.length > 80) return false; // ignore long content
  return TEXT_PATTERNS.some((p) => p.test(t));
}

function purge(root = document) {
  try {
    // 1) sélecteurs connus
    for (const sel of SELECTORS) {
      root.querySelectorAll?.(sel).forEach((el) => {
        try { el.remove(); } catch (_) {}
      });
    }
    // 2) liens / boutons textuels
    root.querySelectorAll?.("a, button, div, span, p, footer").forEach((el) => {
      if (nodeContainsBranding(el)) {
        try { el.remove(); } catch (_) {}
      }
    });
  } catch (_) {}
}

export const WhiteLabelKiller = () => {
  useEffect(() => {
    // Premier passage
    purge();

    // MutationObserver : intercepte les injections asynchrones (e.g. iframes Emergent
    // ou scripts qui ajoutent un badge après le mount React).
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          if (node.nodeType === 1) {
            // Check matching selectors directly
            for (const sel of SELECTORS) {
              if (node.matches?.(sel)) {
                try { node.remove(); } catch (_) {}
                break;
              }
            }
            // Check text branding
            if (node.parentNode && nodeContainsBranding(node)) {
              try { node.remove(); } catch (_) {}
              continue;
            }
            // Drill into children
            purge(node);
          }
        }
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: false,
    });

    // Filet de sécurité : balayage périodique léger (toutes les 2s)
    const interval = setInterval(() => purge(document), 2000);

    return () => {
      observer.disconnect();
      clearInterval(interval);
    };
  }, []);

  return null;
};

export default WhiteLabelKiller;
