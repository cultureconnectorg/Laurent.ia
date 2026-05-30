/**
 * ecosystemChips — chips affichés UNIQUEMENT pour un membre écosystème authentifié.
 * Pour un visiteur commercial standard : chips génériques (Cf. SuggestionChips DEFAULT_CHIPS).
 */
import { Sparkles, Coins, Building2, Fingerprint, Briefcase, Music } from "lucide-react";

export const ECOSYSTEM_CHIPS = [
  { id: "kilti",  label: "Mon Kiltikonet", icon: Sparkles,    prompt: "Aide-moi à faire le point sur mon profil Kiltikonet aujourd'hui." },
  { id: "jcc",    label: "Mes Jetons CC",  icon: Coins,       prompt: "Quelle est ma situation actuelle en Jetons CC ? Que puis-je en faire ?" },
  { id: "cc",     label: "CC2026",         icon: Building2,   prompt: "Donne-moi un point d'étape sur le festival CC2026 et ce qui me concerne." },
  { id: "frek",   label: "Mon FREK-ID",    icon: Fingerprint, prompt: "Explique-moi ma signature culturelle FREK-ID en 7 dimensions." },
  { id: "pro",    label: "Espace Pro",     icon: Briefcase,   prompt: "Quelles actions me proposes-tu dans mon Espace Pro cette semaine ?" },
  { id: "label",  label: "LabelOS",        icon: Music,       prompt: "Aide-moi à organiser ma prochaine sortie via LabelOS." },
];

export default ECOSYSTEM_CHIPS;
