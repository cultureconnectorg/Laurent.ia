# Laurent.ia — PRD (Product Requirements Doc)

> v0.1 — MVP voice-first single-page · Mai 2026

## 1. Problème original (extrait)
Laurent.ia est l'infrastructure d'intelligence souveraine du groupe CVLN. Système multi-tenant qui déploie automatiquement une instance IA personnelle pour chaque utilisateur (FREK-ID), invisiblement dérivée d'un cerveau central (CVL Brain, héritage kiltikonet.fr). L'utilisateur ne voit qu'une expérience : Laurent.ia — son intelligence personnelle.

## 2. Architecture cible
- **Serveur A** kiltikonet.fr (externe, inchangé) — expose `/api/users/validate/{frek_id}` et `/api/users/{frek_id}/profile`
- **Serveur B** Laurent.ia (ce projet) — MongoDB dédiée `laurentia`, gateway `/api/laurentia/*`
- **Serveur C** LabelOS (externe) — expose `/api/artists/{frek_id}/context`

## 3. Personas
- **Sayd** (fondateur CVLN) — usage personnel intime, conversations stratégiques
- **Mira** (artiste signée LabelOS) — accompagnement créatif, planning sortie
- **Visiteur CC2026** (festival terrain) — mode offline dégradé

## 4. Core requirements (statiques)
- Voice-first, single page, zero scroll, premium dark
- Streaming token-by-token (SSE)
- Multi-tenant isolé (1 instance par FREK-ID)
- Données chiffrées AES-256 (au repos), tenant_id = SHA-256(frek_id+SALT) dans tous les logs
- Quota mensuel 10 000 tokens (free) → dégradation gracieuse, jamais 429
- Bridges inter-services kiltikonet + LabelOS
- Doctrine COEURVOLAN injectée dans le system prompt
- L'UI ne dévoile JAMAIS : CVLN, CVL Brain, agents, phases internes

## 5. Implémenté

### v1.2-PRODUCTION — Phase 5 : Ancrage Culturel & Échos (30/05/2026)
**Batch C — Pipeline d'Échos :**
- ✅ **POST /api/laurentia/echo** : génère 3 reformulations (Pro LinkedIn/X, Instant WhatsApp, Visuel Stories 9:16) via Claude — JSON strict + persistance `laurentia_echoes`.
- ✅ **GET /api/echo/{session_id}** (public, no auth) : payload SEO-ready + incrément views post-read.
- ✅ **POST /api/echo/{session_id}/conversion** : attribution HMAC via X-Device-Fingerprint, redirect `/?from_echo={sid}`, doc `laurentia_echo_attributions`.
- ✅ **EchoPage.jsx** : landing publique `/echo/:sessionId` — Cormorant Garamond + Urbanist, fond bleu nuit, sections Pro/Instant/Visual, OG meta dynamiques, CTA « Activer mon Intelligence Souveraine 🪙 ».

**Persona v1.2 — Anti-jailbreak :**
- ✅ Section 7 dans `cvl_brain_knowledge.py` : refus noble + réorientation business, ne nomme jamais Claude/Anthropic/OpenAI.

**Cron RGPD J+90 :**
- ✅ `services/rgpd_purge.py` + `POST /api/admin/rgpd/purge` (idempotent) + scheduler 24h au startup. Vide `device_ids` des instances inactives, anonymise `visitor_device_id` des attributions.

**Cosmétique :**
- ✅ Skip silencieux `GET /api/laurentia/instances/ANON-*` dans `useLaurentIA.js` (élimine 401 cosmétique).

### v1.2-PRODUCTION — Phase 6 : Injection Culturelle Diaspora (30/05/2026)
**Ancrage linguistique double lecture :**
- ✅ **Composer placeholder créole** : « Djis poze keksion ou… » (vs. « Posez votre question… »)
- ✅ **Bandeau multilingue défilant** (38s loop) sous le composer : Yoruba (Kowe Ètò Ìṣòwò), Amharique (ቢዘሮ ፕላን), Swahili (Andika Mpango wa Biashara), Punjabi (ਬੀਤ ਪਲਾਨ), Créole haïtien (Tontin' modèn), Wolof (Tey ñàddu réew). Pause au hover.
- ✅ **SuggestionChips bilingues** : chaque chip a un subtitle Urbanist 10px or/cyan opacité 40-65% (Kowe Ètò Ìṣòwò, Analize kontra trans-Latlantik, Mpango wa Ukuaji wa Biashara, etc.). Structure flex-col stack.

**Tresses d'Énergie :**
- ✅ **EnergyBraids.jsx** : 9 courbes de Bézier SVG montant depuis le bas vers l'orbe (z-index 0, pointer-events none). 5 or + 4 cyan, drop-shadow Gaussian Blur, animation pathLength + opacity en boucle décalée (3.8s ± 1.2s repeat).

**Composer Racines & Technologie :**
- ✅ **GoldArrow sculptée** : SVG triangle isocèle aérodynamique avec gradient `#F4E0AA→#C9A24B`, 4 particules d'or scintillantes orbitant à r=10px au survol/saisie (motion infinite, opacity 0→1→0, scale 0.5→1→0.5).
- ✅ **WirePaperclip filaire** : SVG path 1.4px stroke or, sans fond solide.
- ✅ **SoundWave + Cercle de Résonance** : 7 barres verticales gradient or→bleu encapsulées dans un cercle bleu néon `#1D8CF8` (box-shadow + inset glow) animé `sonic-pulse` 1.4s scale 0.92↔1.08.

**Header v1.2 :**
- ✅ Avatar sceau doré + **label "CVLN · Group"** stack vertical à droite (data-testid `header-cvln-label`).

**Tests :**
- ✅ **64/64 pytest GREEN** (phases 1-4 + cleanup).

### v1.2 — Phase 3 : Persistance Fantôme + Signature Constellation + UX Souveraine (30/05/2026)
**Batch A — Souveraineté Sensorielle :**
- ✅ **TTS toggle** dans Header (data-testid `header-voice-toggle`) avec persistance localStorage, et bouton **Stop voix** transitoire pendant lecture (`header-stop-speaking`).
- ✅ **Voix française premium** : sélection automatique (Antilles/Caribbean → Apple Thomas/Audrey/Amélie → Google FR → MS premium → fallback masculin). Pitch=0.92, rate=0.95 (ton noble protecteur).
- ✅ **PhaseIndicator** style emergent.sh : 4 phases — connecting (#5BA0FF) → analyzing (#6BA8FF) → synthesizing (#9BC4FF) → rendering (#E7C566 or pour <json>/<artifact>). Icônes lucide animées, label monospace.
- ✅ **Chip no-code** dans SuggestionChips (gradient or) → prompt `<artifact>` (calculatrice tontine HTML/CSS/JS).

**Batch 1 — Effacement & Persistance :**
- ✅ **WhiteLabelKiller** : MutationObserver + CSS `display:none` sur `[class*=emergent]`, `a[href*=emergent.sh]`, etc. + balayage périodique 2s + détection textuelle "Made with Emergent". Le badge est purgé sous 100ms après injection.
- ✅ **Persistance Fantôme** : `GET /api/laurentia/resolve` retourne `frek_id` + instance + last_session_id à partir du header `X-Device-Fingerprint` seul. Chaque `/query` lie `device_id` → `laurentia_instances.device_ids` via `$addToSet`. Frontend appelle `/resolve` au paint et `loadSession()` automatiquement.

**Batch 2 — Signature de la Constellation :**
- ✅ **Page de Signature finale** WeasyPrint (Free tier uniquement) : médaillon or, titre Cormorant Garamond *« Certifié par l'Infrastructure Laurent.ia »*, sous-titre « Connaissance Souveraine de la Diaspora · CVLN Group », QR code → `{LAURENTIA_PUBLIC_URL}/echo/{session_id}`, ribbon italique *« La parole reste. Le sceau valide. La constellation veille. »*, timestamp scellé.
- ✅ **QR code natif** via `qrcode[pil]` → data URI PNG inline (pas de fetch externe au build).
- ✅ **Compteur exports Free 2/mois** : collection `laurentia_pdf_exports` indexée par `(device_id, month)`. 3ème tentative → **HTTP 402** avec detail noble + headers `X-Laurentia-Paywall='creator'`, `X-Laurentia-Free-Used`, `X-Laurentia-Free-Limit`.
- ✅ **Creator/Infinite** : signature finale absente, compteur non incrémenté, exports illimités.
- ✅ **Endpoint diagnostic** : `GET /api/export/pdf/quota` → état du quota Free pour le device courant.
- ✅ **Orb sealing animation** : nouvel état `state="sealing"` (couleurs or `#C9A24B` + bleu) sur OrbeLaurentIA. Overlay plein écran `data-testid="sealing-overlay"` durant la génération PDF : *« Gravure souveraine en cours… / Apposition du sceau de la constellation »*.
- ✅ **Paywall UX** : ChatBubble intercepte HTTP 402 → `onPaywall()` ouvre PricingModal + toast contextuel.
- ✅ **Tests Phase 3** : `tests/test_phase3_ghost_signature.py` (12 tests) → QR PNG valide, signature HTML, resolve null/avec-FP/lié, quota initial, incrémentation 1→2→402, Creator no-signature, PDF Free ≥2 pages avec sceau.

**Total tests : 41/41 GREEN.**

### v1.1 — Phase 2 : Policière Invisible + Conversion Gold (30/05/2026)
- ✅ **Device Fingerprinting frontend** (`frontend/src/services/fingerprint.js`) : Canvas 2D + WebGL (VENDOR/RENDERER) + hardware (CPU, RAM, screen, TZ, lang, platform), cache localStorage `laurentia_device_fp` (~284 chars). Helper `withFingerprintHeaders()` propage le header `X-Device-Fingerprint` sur tous les fetch `/api/laurentia/*` et `/api/export/*`.
- ✅ **HMAC-SHA256 backend** (`services/fingerprint.py`) : `device_id = HMAC(LAURENTIA_SECRET_SALT, fingerprint)` → 64 hex. Sel rotaté en valeur production-grade (48 bytes secrets.token_urlsafe).
- ✅ **Rate-limiter sliding-window MongoDB** (`services/rate_limit_mongo.py`) : collection `laurentia_rate_limits` avec TTL index `expires_at` (expireAfterSeconds=0) + index `(key, ts)`. Quotas par tier : Free 10/min 60/h, Creator 60/min 1200/h, Infinite 240/min illimité-h. `ensure_indexes()` au startup.
- ✅ **Message noble HTTP 429** : « Votre Énergie Luciole est temporairement épuisée… Passez au tier Creator 🪙 pour libérer votre puissance. »
- ✅ **`ParsedFile.pages`** : nb pages PDF (pypdf), paragraphes DOCX (python-docx), lignes TXT/MD. Exposé dans event SSE `meta.files[]`.
- ✅ **Chip Gold dans ChatBubble** : avant retour serveur → chip neutre ; après `meta` SSE → gradient `#C9A24B → #E7C566`, icône Check, label « X pages digérées / paragraphes digérés ». data-testid `user-bubble-file-chip` + attr `data-digested`.
- ✅ **Bouton « Exporter PDF 🪙 »** sur ChatBubble assistant (text > 80 chars, post-streaming) : data-testid `assistant-export-pdf-button`, icône Coins, états idle/loading/done/error avec couleurs gold.
- ✅ **POST /api/export/pdf** (`routes/pdf_export.py`) : WeasyPrint + bleach + markdown lib. Charte CVLN : fond blanc, Cormorant Garamond (titres), Urbanist (UI), accents `#C9A24B`, bleu nuit `#0A0F1F`. Pied de page + numérotation auto. Payload max 50 000 chars (Pydantic). PDF ~11-17 Ko, magic %PDF-1.7.
- ✅ **Sanitization** : `<script>` strippés via bleach (tags/attrs whitelist).
- ✅ **Tests Phase 2** : `tests/test_phase2_policiere_export.py` (14 tests) → HMAC déterministe, TTL index, sliding-window, 429 noble, pages count, PDF rendu valide, sanitization.

### v1.0 — Phase 1 : Blindage SecOps & Data (30/05/2026)
- ✅ **Chiffrement AES-256-GCM au repos** (cryptography lib) : `services/crypto.py` (encrypt_text/decrypt_text) avec nonce 96 bits aléatoire par chiffrement, format `{v:1,n,c}` stockable BSON. `LAURENTIA_ENCRYPTION_KEY` figé en .env (production-grade). Rétro-compat : str legacy renvoyé tel quel par decrypt.
- ✅ **Collections chiffrées** : `laurentia_interactions.input_text/output_text` ET `laurentia_memory.sessions[*].input/output` sont désormais des dicts `{v:1,n,c}` (vérifié en MongoDB).
- ✅ **LAURENTIA_SECRET_SALT** figé (déjà en place) — pas de tokens orphelins au reboot.
- ✅ **Upload fichiers multipart** sur `POST /api/laurentia/query` : champ JSON `payload` + 1..N champs `files`. Tier gate Creator/Infinite (HTTP 403 sinon avec CTA commercial).
- ✅ **Parsing PDF (pypdf), DOCX (python-docx), TXT, MD** : `services/file_parser.py`. Limites : 10 Mo/fichier, 25 Mo total, 30 000 caractères extraits/fichier, 4 fichiers max. Texte extrait injecté dans le prompt sous forme de bloc Markdown `## Pièces jointes utilisateur`.
- ✅ **Endpoint `/api/laurentia/upload-limits`** : expose publiquement les limites pour la UI.
- ✅ **Composer.jsx** : bouton trombone (creator/infinite) ↔ cadenas (free, click → PricingModal/MenuDrawer). Chips d'attachement, suppression individuelle, jauge volume total / 25 Mo, message d'erreur dédié.
- ✅ **RichContent.jsx — Buffer de sécurisation** : balise `<json>` ou `<artifact>` non fermée → rendu d'un `PendingBlock` (skeleton + spinner), AUCUN parsing Markdown du contenu tronqué. Indestructible en streaming.
- ✅ **Tests automatisés** : `tests/test_phase1_security_uploads.py` (17 tests) + `tests/test_phase1_integration_http.py` (6 tests) — 23/23 GREEN. Couvre crypto round-trip, nonce unique, rétrocompat, PDF/DOCX/TXT/MD parsing, limites taille, gate tier 403, encryption at rest, decrypt round-trip via API.
- ✅ **conftest.py** : load_dotenv au démarrage des tests pour cohérence clé.

### v0.9 — Doctrine Laurent.ia v0.8 + multi-formats (JSON charts + Artifacts) (30/05/2026)
- ✅ **System prompt souverain v0.8** appliqué : Diaspora, Daemon Luciole (silencieux), Crédits Computation, multi-agents Stitch, couplage NFC. Secret Défense strict (politique J+90 publique, jamais d'allusion fine-tuning/pipeline). Refus jailbreak.
- ✅ **Bloc `<json>` → Recharts** : bar/line/area/pie auto-rendus depuis `RichContent.jsx`. Schéma `{type, title, data, xKey, series}`. Thème Laurent.ia (palette bleue + accents gold). Tooltip noir, légende blanche.
- ✅ **Bloc `<artifact>` → iframe sandboxée** : `srcDoc` + `sandbox="allow-scripts"` + bouton aperçu/code + bouton expand. Pour génération de mini-sites/apps autoportés.
- ✅ **Validation live** : prompt remittances Caraïbe → Laurent.ia génère natif un `<json type=bar>` avec Haïti/Jamaïque/République Dominicaine + analyse Markdown structurée avec termes-clés en gold (37% du PIB, +6% annuelle, etc.) — rendu impeccable
- 🟡 **Pipeline /echo (LinkedIn/X/WhatsApp/Stories)** : prompt en place mais endpoint dédié pas encore créé (l'utilisateur peut déjà demander un format dans le chat)
- 🟡 **PDF/DOCX export** : prompt prévoit l'interception serveur mais endpoint pas implémenté
- ✅ **frekcore production branché** : `FREKCORE_API_URL=https://frekcore.com` + `FREKCORE_API_KEY=cvl-brain` (client ID FREK). Bridge avec `follow_redirects=True`, headers `X-API-Key` + `X-Client-ID`. Routage intelligent : `DEMO-*` → whitelist locale (toujours), autres → frekcore réel
- ✅ **Migration instances** : 6 instances existantes mises à jour avec `tier=free` + nouveaux quotas (`tokens_limit_month=100k`, `tokens_limit_day=15k`, `memory_window=10`, `rate_per_min=10`)
- ✅ **Memory window enforcement** : le gateway charge uniquement les N derniers échanges (`memory_window` du tier) et les injecte dans le system prompt — économies tokens + isolation tier
- ✅ **Daily quota** : compteur `tokens_used` par jour dans `laurentia_usage` (bucket `{frek_id, day}`), dégradation gracieuse si dépassement
- ✅ **Markdown rendering** dans les bulles assistant via `react-markdown + remark-gfm` + thème CSS Laurent.ia (titres bleu, gras gold, code mono, tables, blockquotes). User reste en texte brut
- ✅ **SettingsModal** (Paramètres) : tier + usage tokens (barre de progression) + toggle voix + toggle détection langue + URL de partage de la session courante (1-click copy)
- ✅ **Partage session** : URL `?session={sid}` détectée au chargement → `loadSession(sid)` → conversation entière restaurée
- ✅ **Détection langue auto** : system prompt mis à jour ("français par défaut, créole martiniquais/guadeloupéen si l'interlocuteur t'écrit en créole, anglais s'il t'écrit en anglais") — Claude détecte natif
- ✅ **Service Worker** (`/sw.js`) : cache shell léger pour graceful offline (l'API n'est jamais cachée, message hors-ligne renvoyé sinon)
- ✅ **Voix respect setting** : `localStorage.laurentia_voice === "off"` désactive le TTS

### v0.7 — 3 tiers Free/Creator/Infinite + quotas intelligents + PricingModal (30/05/2026)
- ✅ **Modèle 3-tiers** : `Free` (gratuit, 10 échanges mémoire, 100k tokens/mois) · `Creator €15/mois` (100 échanges, 2M tokens, upload fichiers) · `Infinite €39/mois` (500 échanges, 10M tokens, agents IA, vitesse prioritaire, multi-modèles à venir). Source de vérité serveur : `PACKAGES` dict dans `routes/billing.py`
- ✅ **Rate limiting per-min par tier** via `services/rate_limit.py` (sliding window in-memory, Redis-ready) ; le gateway `/api/laurentia/query` lève 429 si dépassement
- ✅ **PricingModal** : 3 cards (Free / Creator / Infinite) avec badge "RECOMMANDÉ" gold sur Infinite. CTA contextuel (Ton plan actuel / Activer Creator / Activer Infinite). Endpoint `GET /api/billing/packages` côté serveur
- ✅ **Menu drawer dynamique** : bouton "Améliorer mon plan" → ouvre le modal ; texte change selon tier (Creator → "Passer à Infinite") ; masqué si déjà Infinite
- ✅ **`/api/auth/me` enrichi** : retourne `tier`, `tokens_used_month`, `tokens_limit_month` depuis l'instance — le frontend connaît le tier réel après reload
- ✅ **Activation Pro tier-aware** : status polling + webhook propagent les bons quotas/mémoire/rate-limit selon le `package_id` acheté (`creator` ou `infinite`)
- 🟡 Les instances existantes gardent leurs anciens quotas (10k tokens) — réindexation à prévoir avec un migration script léger

### v0.6 — Stripe Pro · Migration ANON→FREK · Écosystème conditionnel (30/05/2026)
- ✅ **Stripe Checkout Pro €15/mois** via `emergentintegrations.payments.stripe` : `POST /api/billing/create-checkout` (auth-gated) → URL Stripe + session_id ; polling `GET /api/billing/status/{sid}` (frontend retombe sur la home avec `?upgrade=success&session_id=...` et active Pro de manière idempotente) ; webhook `POST /api/webhook/stripe` également idempotent (`credit_applied` flag dans `payment_transactions`)
- ✅ **Bouton "Activer Pro"** visible dans le menu drawer (style gold, sous-titre "€15/mois · Conversations illimitées"), uniquement pour les utilisateurs authentifiés non-Pro
- ✅ **Migration ANON→FREK** : nouveau `POST /api/auth/migrate-anon` → reaffecte les `laurentia_interactions` du `tenant_id(ANON-XXXX)` vers `tenant_id(user.frek_id)`. Appel automatique après chaque login (Google + FREK-ID) depuis `AuthContext.migrateAnonIfAny()`. localStorage anon vidé
- ✅ **Chips conditionnels** : si `ecosystemMember=true` → chips spécialisés (Mon Kiltikonet · Mes Jetons CC · CC2026 · Mon FREK-ID · Espace Pro · LabelOS) ; sinon chips génériques universels. Switch live, zéro hardcoding visible aux utilisateurs hors écosystème
- ✅ **Activation Pro idempotente** : double protection (status polling + webhook), `credit_applied=true` flag dans `payment_transactions` empêche le double-crédit
- ✅ **PACKAGES côté serveur uniquement** : `{pro_monthly: €15}` — jamais le frontend ne décide du prix
- 🟡 Le user object exposé à `useAuth().user` ne contient pas encore `version` (le check `user?.version !== "pro"` fonctionne en attendant que `/api/auth/me` renvoie `version` depuis l'instance — TODO P1)

### v0.5 — Auth FREK-ID (frekcore) + anonymat propre (30/05/2026)
- ✅ **2 chemins d'auth dans le menu** : `Continuer avec Google` (onboarding nouveaux) + `Mon identifiant` (FREK-ID code direct pour membres écosystème)
- ✅ Nouveau service **`services/frekcore_bridge.py`** — séparé, structure HTTP-ready. Swap zéro-code en prod via `FREKCORE_API_URL` + `FREKCORE_API_KEY` (ajoutés au `.env`). En dev : liste blanche stricte `{DEMO-SAYD, DEMO-ARTIST, DEMO-PRO}` qui rejette correctement les codes inconnus (404)
- ✅ Backend `POST /api/auth/frek` — valide via frekcore, upsert user avec flag `ecosystem_member=true`, crée tenant Laurent.ia + memory si nouveau, dépose cookie 7j
- ✅ Frontend AuthContext étendu (`loginWithFrekId`, `ecosystemMember`), MenuDrawer rebuilt avec input FREK-ID
- ✅ **Anonymat propre** : visiteur non-loggué reçoit un `ANON-XXXXXXXX` unique par browser (localStorage), ne voit AUCUN historique d'autres utilisateurs. Plus de pollution DEMO-SAYD
- ✅ **Historique verrouillé tant que non auth** : message "Connecte-toi pour retrouver tes conversations" affiché à la place de la liste
- 🟡 Conversations anonymes orphelines au login (pas de migration ANON→FREK pour l'instant — feature P1)

### v0.4 — Pivot commercial : écosystème invisible (30/05/2026)
- ✅ **SuggestionChips** : remplacement des 6 chips écosystème (Kiltikonet, Jeton CC, CC2026, Mon FREK-ID, Espace Pro, Culture) par 6 prompts génériques universels (Aide-moi à écrire, Synthétise une idée, Brainstorm créatif, Analyse un texte, Plan d'action, Explique-moi) — Laurent.ia parle à tout utilisateur, pas qu'à un membre CVLN
- ✅ **Header** : label "FREK-ID" supprimé du pill avatar, pill KT masqué par défaut (`kt={null}` → render conditionnel `kt > 0`)
- ✅ **HeroPanel** : sous-titre "Man la pou ou" remplacé par "Posez votre question. Je vous écoute." (neutre, pas de pré-cadrage culturel)
- ✅ **BottomTabBar** : supprimée. Le menu ☰ et le composer suffisent (style Claude/ChatGPT)
- ✅ **Vérification automatique** : aucune mention de FREK-ID, Kiltikonet, CC2026, Jeton CC, Espace Pro, Culture, créole dans le DOM
- 🟡 La cohésion écosystème (KT pill, mentions Kiltikonet, etc.) sera **conditionnelle** : visible uniquement si l'utilisateur authentifié possède un compte CVLN connecté (jcc_balance > 0 ou flag `ecosystem_connected`). À implémenter en P1.

### v0.3 — Auth Emergent Google + Menu drawer + Historique (30/05/2026)
- ✅ **Emergent Managed Google Auth** intégré : `/api/auth/session`, `/api/auth/me`, `/api/auth/logout` (cookie httpOnly 7j, samesite=None, secure)
- ✅ **Dérivation FREK-ID** stable depuis email : `FREK-G-{sha256(email)[:10]}` — création auto de l'instance Laurent.ia
- ✅ **MenuDrawer (☰)** : profil utilisateur (avatar/nom/FREK-ID), bouton « Connexion avec Google », « Nouvelle conversation », **liste des sessions historiques** (titre + nb messages), suppression RGPD, paramètres, logout
- ✅ **Reprise de session** : click sur une entrée d'historique → recharge le thread complet via `GET /api/laurentia/sessions/{sid}`
- ✅ **CORS fix** : `allow_origin_regex='.*'` + `allow_credentials=True` pour supporter les cookies cross-origin
- ✅ Auth optionnelle : tout le flow continue de fonctionner en mode démo FREK-ID

### v0.2 — Pivot UI chat-first (30/05/2026)
- ✅ Refonte complète de l'interface vers un layout **chat-first** inspiré des screenshots Kiltikonet/CVL Brain + Claude + ChatGPT
- ✅ Nouvelle palette : navy `#0A0F1F` + orbe radar bleu électrique + accent gold subtil pour wordmark/KT pill
- ✅ Nouveaux composants `Header`, `HeroPanel`, `SuggestionChips`, `ChatBubble`, `Composer`, `BottomTabBar`
- ✅ Bulles utilisateur "TOI" (gradient bleu) + bulles assistant "LAURENT.IA" (dark glass) — match IMG_3673
- ✅ 6 suggestion chips (Kiltikonet · Jeton CC · CC2026 · Mon FREK-ID · Espace Pro · Culture)
- ✅ Composer style Claude/ChatGPT (textarea auto-grow + mic + send, Enter pour envoyer)
- ✅ Bottom tab bar mobile-feel avec Laurent.ia central actif + toasts "Bientôt disponible" pour les autres
- ✅ Police IBM Plex Sans pour le body, Cormorant Garamond italique pour wordmark uniquement
- ✅ Backend inchangé — l'orbe reste blue radar, transitions framer-motion idle/listening/thinking/speaking

### Backend (v0.1)
- ✅ `/app/backend/services/cvl_brain.py` — wrapper Claude Sonnet 4.5 via emergentintegrations + EMERGENT_LLM_KEY (bug fix #1 : modèle migré vers `claude-sonnet-4-5-20250929`)
- ✅ `/app/backend/services/cvl_brain_agents.py` — registre 10 agents + `log_write()` activé (bug fix #2)
- ✅ `/app/backend/services/cvl_brain_knowledge.py` — doctrine + system prompt builder
- ✅ `/app/backend/services/kiltikonet_bridge.py` — **MOCKÉ** (profils 7D fictifs pour DEMO-SAYD, DEMO-ARTIST)
- ✅ `/app/backend/services/labelos_bridge.py` — **MOCKÉ**
- ✅ `/app/backend/services/security.py` — tenant_id SHA-256
- ✅ `/app/backend/routes/laurentia_gateway.py` — gateway principal
  - `POST /api/laurentia/query` → **SSE streaming** (bug fix #3)
  - `POST /api/laurentia/instances/init`
  - `GET  /api/laurentia/instances/{frek_id}`
  - `GET  /api/laurentia/memory/{frek_id}`
  - `POST /api/laurentia/feedback`
- ✅ `/app/backend/routes/brain.py` — `/api/brain/health`, `/api/brain/agents`, `/api/brain/chat-enriched`
- ✅ `/app/backend/routes/omega.py` — `/api/omega/chat-enriched` SSE
- ✅ Collections MongoDB : `laurentia_instances`, `laurentia_memory`, `laurentia_interactions`, `laurentia_usage`, `cvl_brain_agent_status`, `agent_logs`
- ✅ Anonymisation : `tenant_id` SHA-256 dans `laurentia_interactions`, JAMAIS le `frek_id` brut
- ✅ `corpus_eligible=False` par défaut (opt-in explicite uniquement)
- ✅ Dégradation gracieuse quand quota atteint (JAMAIS 429)

### Frontend
- ✅ Single page voice-first `/app/frontend/src/pages/LaurentIA.jsx`
- ✅ Composants framer-motion (`OrbeLaurentIA`, `StateIndicator`, `ConversationZone`, `FreKIDBadge`, `StatusBar`, `MicButton`)
- ✅ Hook `useLaurentIA.js` — pipeline STT (Web Speech) → SSE → tokens streamés → TTS (Web Speech Synthesis)
- ✅ Fallback texte si STT indisponible
- ✅ Raccourci ESPACE/ESC
- ✅ Fonts Cormorant Garamond + IBM Plex Mono
- ✅ Theme dark obsidian + accent Caribbean Amber (#D97736)
- ✅ Pas de chrome, pas de navigation — zone unique focalisée

### Mocked / différé
- 🟡 **kiltikonet_bridge** et **labelos_bridge** sont MOCKÉS (pas de serveur externe disponible)
- 🟡 Auth FREK-ID : mode démo (param URL ou localStorage), pas de Magic Link
- 🟡 Chiffrement AES-256 mémoire : `encryption_key_ref` stocké mais chiffrement effectif différé
- 🟡 Service Worker offline CC2026 : non implémenté

## 6. Backlog priorisé

### P0 — Critique pour prod
- [ ] Connecter kiltikonet_bridge à l'API réelle de kiltikonet.fr (httpx réel)
- [ ] Implémenter Magic Link auth (Brevo/SES) ou Emergent Google Auth
- [ ] Chiffrement AES-256 effectif des sessions mémoire
- [ ] Stripe Checkout Pro €15/mois + webhook + JCC 150

### P1 — Important
- [ ] Connecter labelos_bridge à l'API réelle
- [ ] Service Worker offline + GPS zone festival CC2026
- [ ] Dashboard admin agents (réutilisation héritage)
- [ ] Email séquences Brevo onboarding
- [ ] Streaming Anthropic natif (au lieu du pseudo-stream chunké actuel)

### P2 — Nice-to-have
- [ ] Multilingue détection auto (cr/en)
- [ ] Upload fichiers + recherche web (Brave API)
- [ ] Export RGPD utilisateur (cascade delete)

## 7. Next tasks
1. Demander à l'utilisateur les credentials production (kiltikonet, LabelOS, Stripe, Brevo)
2. Implémenter l'auth choisie
3. Activer le chiffrement AES-256 réel des sessions
