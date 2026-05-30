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

## 5. Implémenté (v0.1 — 30/05/2026)

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
