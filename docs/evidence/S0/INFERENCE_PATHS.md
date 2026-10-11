# Carte des chemins d'inférence — Laurent.ia, `public` = `b898e19`

> 11 octobre 2026 · Lecture statique du code, **confirmée dynamiquement** quand c'était possible (protocole S0, traces du serveur, garde réseau).
> Périmètre : Laurent.ia uniquement. **[F]** fait vérifié dans le code · **[D]** observé à l'exécution · **[H]** hypothèse · **[NV]** non vérifié.
> **Chemin d'inférence** : tout chemin par lequel un prompt, une mémoire, un document ou une réponse part vers un modèle, où qu'il tourne. **Canal connexe** : sortie qui transporte des données cognitives sans être de l'inférence.

## 1. Une seule frontière fournisseur dans le code

| Couche | Élément | Statut |
|---|---|---|
| Enveloppe | `services/cvl_brain.py` : `chat_enriched()` (l. 30-39) et `chat_stream()` (l. 42-60). `chat_stream()` n'est qu'un pseudo-flux construit sur `chat_enriched()` | [F] |
| SDK | `emergentintegrations.llm.chat.LlmChat(...).with_model("anthropic", LAURENTIA_CLAUDE_MODEL)`, clé `EMERGENT_LLM_KEY` | [F] |
| Chaîne indirecte | `emergentintegrations` → `litellm` (installé depuis un fichier hébergé par Emergent) → proxy Emergent → Anthropic | **[NV]** : le source du paquet n'est pas public. `openai`, `google-genai`, `google-generativeai`, `tiktoken` et `huggingface_hub` sont installés comme dépendances, mais **importés nulle part** dans le code |
| Modèle par défaut | `claude-sonnet-4-5-20250929` (`cvl_brain.py:19`, `server.py:54`, `routes/brain.py:36`) | [F] |

**[F]** Aucun autre module n'importe de SDK de LLM. Recherche faite sur `emergentintegrations.llm`, `openai`, `anthropic`, `google.generativeai`, `google.genai`, `litellm`, `cohere`, `mistralai` et `ollama`. `emergentintegrations` est aussi importé par `routes/billing.py`, mais pour les **paiements Stripe**, pas pour l'inférence.

## 2. Appelants directs et indirects

| # | Point d'entrée | Chemin vers `cvl_brain` | Données envoyées au modèle | Déclencheur | Comportement en cas d'échec (repli) | Statut |
|---|---|---|---|---|---|---|
| P1 | `POST /api/laurentia/query` (SSE ; JSON ou multipart) | `laurentia_gateway.py:396` → `chat_stream` | Saisie personnelle ; **contenu extrait des fichiers joints** (PDF, DOCX) ; **N derniers échanges de mémoire, déchiffrés** (`:375-392`) ; contexte **importé de Kiltikonet et de LabelOS** (`:153`, `:317-320`) | Frontal Laurent.ia (`useLaurentIA.js`) | `event: error` envoyé au client (`:512-516`) ; **aucune bascule vers un autre fournisseur**. Hors quota : texte fixe `_degraded_response_text()`, qui n'est pas de l'inférence | [F] + **[D]** (10 traces) |
| P2 | `POST /api/brain/briefing` (`laurentia.briefing@1.0`, clé de service) | `brain.py:67` → `chat_enriched` | Demande + **`context` libre, fourni par l'appelant** | Autres systèmes (Meta CVLN, Kiltikonet Code) | HTTP 500 (aucune gestion) | [F] ; **[D]** sans clé → 403 |
| P3 | `POST /api/brain/chat-enriched` (ancien point d'entrée) | `brain.py:50` → `chat_enriched` | Message brut | **N'importe qui : aucune authentification** | HTTP 500 | **[D]** : une requête anonyme atteint `cvl_brain` |
| P4 | `POST /api/omega/chat-enriched` (SSE) | `omega.py:32` → `chat_stream` | Message brut | **N'importe qui : aucune authentification** | Flux interrompu (HTTP 200, puis erreur) | **[D]** : une requête anonyme atteint `cvl_brain` |
| P5 | `POST /api/laurentia/echo` | `echo.py:123` → `chat_stream` | **Contenu d'une session existante** (`_fetch_session_content`) ou texte brut | Frontal | HTTP 502, avec le message d'erreur | [F] + **[D]** (1 trace) |
| P6 | `jobs/social_agent.py` (planificateur lancé par `server.py:169`) | `social_agent.py:112` → `chat_enriched` | Thème + prompt système | **Automatique** (cron) | 3 essais (attente de 2, 4 puis 8 s), puis la journée est sautée ; **aucun autre fournisseur** | [F] |
| P7 | P6 → `services/image_generator.py` | `POST {SD_API_URL}/sdapi/v1/txt2img` (API Stable Diffusion, format Automatic1111) | `visual_prompt` **produit par P6** | Automatique | Retourne `None` sans signaler l'erreur | [F] ; destination de `SD_API_URL` **[NV]** (souveraine si l'hébergement est le tien) |

**Prompt système et persona** : `services/cvl_brain_knowledge.build_system_prompt()` accompagne chaque appel, de P1 à P6. [F]

**Replis** : [F] aucun repli vers un second modèle ou un second fournisseur n'existe sur `public`. Les seuls replis sont une erreur, un texte fixe ou un saut de la tâche.

## 3. Chemins présents hors de la branche de production

| # | Où | Chemin | Repli | Statut |
|---|---|---|---|---|
| P8 | **PR #1** (`claude/patch-007-runtime-connection`, non fusionnée) | `services/cvln_model_router.py` → `POST {CVLN_MODEL_ROUTER_URL}/api/providers/route` (Agent Factory) → `provider_layer` → Anthropic, OpenAI ou Gemini via Emergent (stratégie par défaut `quality`) | **En cas d'échec : repli sur le chemin local `services/cvl_brain.py`**, c'est-à-dire P1 à P6, donc Emergent (`cvln_model_router.py:55`, `:90-110`) | [F] ; code lu, non exécuté |

## 4. Inférence côté utilisateur (navigateur)

| # | Mécanisme | Ce qui sort | Vers qui | Statut |
|---|---|---|---|---|
| N1 | **Reconnaissance vocale** `webkitSpeechRecognition` (`useLaurentIA.js:130`, `lang=fr-FR`) | **La voix de Laurent** | Serveurs du fournisseur du navigateur (Google pour Chrome) | [F] pour le code ; destination selon le navigateur [H] |
| N2 | **Synthèse vocale** `speechSynthesis`. Ordre de préférence (`useLaurentIA.js:193-198`) : voix créole ou antillaise, voix Apple, **puis « Google français »**, puis Microsoft | **Le texte des réponses de Laurent.ia** | Voix en ligne (Google, Microsoft) quand elles sont choisies ; les voix Apple sont locales | [F] pour le code ; voix réellement choisie [NV] |

## 5. Canaux connexes transportant des données cognitives

| # | Canal | Contenu | Destination | Statut |
|---|---|---|---|---|
| R1 | `jobs/corpus_pipeline.py` (cron hebdomadaire, `server.py:168`) | Interactions éligibles au **corpus d'entraînement** (JSONL, anonymisé par expressions régulières) | OVHcloud S3 si configuré, sinon `/tmp/laurentia_corpus/` | [F] ; configuration de production [NV] |
| R2 | `orchestrator/sms_ovh.py` | Alerte : agent, incident, **60 caractères de résumé** | API SMS d'OVH → téléphone de Laurent | [F] |
| R3 | `social_agent.py:151-212` | Texte produit par P6 | Instagram, LinkedIn, X (publication) | [F] |
| R4 | `routes/pdf_export.py:360,501` | Requête de feuille de style des polices (sans contenu) | `fonts.googleapis.com` | **[D]** 6 tentatives bloquées |
| R5 | Frontal de production, `public/index.html` | Enregistrement de session (tout ce qui est tapé et affiché) | `us.i.posthog.com`, `assets.emergent.sh` | [F] ; corrigé seulement sur la branche E1, pas en production |
| R6 | Authentification | Identité | `auth.emergentagent.com` (`AuthContext.jsx:70`), `demobackend.emergentagent.com` (`auth.py:22`) | [F] |
| R7 | Tests | Les tests visent par défaut l'**hôte d'aperçu Emergent** | `emergent-ai-238.preview.emergentagent.com` (`test_laurentia_backend.py:14`) | **[D]** 9 tentatives bloquées |

## 6. Conséquences pour les garanties (S1 et S2)

- **Une analyse des imports ne suffit pas.** P7 (génération d'images en HTTP simple), P8 (routeur de la PR #1 en `httpx` simple), N1, N2 (navigateur) et R1 à R7 passent tous **sans SDK de LLM**.
- La garantie doit donc reposer sur quatre mécanismes :
  1. une **garde réseau pendant l'exécution** (T3) ;
  2. un **contrôle au démarrage** (T2) qui vérifie **toutes** les URL configurées (`SD_API_URL`, `CVLN_MODEL_ROUTER_URL`, `OVHCLOUD_S3_ENDPOINT`…) ;
  3. un **inventaire du frontal** (T4, étendu aux API vocales) ;
  4. **un test par chemin, de P1 à P8**, exécuté avec un vrai moteur local, qui vérifie qu'aucune sortie n'a eu lieu.
- **Replis** : tant que le moteur souverain n'est pas disponible, chaque chemin doit **échouer de façon visible**, jamais basculer vers un fournisseur externe. Un test le vérifie en coupant le moteur local.
