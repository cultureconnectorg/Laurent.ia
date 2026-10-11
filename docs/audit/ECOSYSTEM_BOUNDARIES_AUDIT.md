# Audit des frontières — Laurent.ia et les systèmes de l'écosystème CVLN

> Statut : **audit en lecture seule**, 6 octobre 2026, complété le 11 octobre 2026 (Agent Factory). Aucun dépôt audité n'a été modifié.
> Méthode : Audit → cartographie → frontières → contrats → décisions → exécution. Cet audit couvre les trois premières étapes.
> Règle de preuve : chaque constat cite un fichier et une ligne au commit indiqué. **Un dépôt inaccessible est une contrainte d'accès, jamais une preuve que le système n'existe pas.**

---

## 0. Correction d'une erreur antérieure

Le Product Contract (version du commit `1f353e0`) affirmait : *« KORA : aucun dépôt, aucune API »*. **C'était faux.** Cette conclusion venait seulement de l'absence d'un dépôt nommé exactement « KORA » dans la liste accessible à la session. KORA existe : `kora2024/Kora-app`, avec un backend de 126 routes. Cette affirmation est retirée.

---

## 1. Périmètre et accès

| Système | Dépôt | Accès | Commit audité | Date du commit |
|---|---|---|---|---|
| Laurent.ia | `cultureconnectorg/Laurent.ia` | Lecture et écriture | `de32e56` | 6 oct. 2026 |
| **KORA** | `kora2024/Kora-app` (**public**) | Lecture git anonyme | `c2da615` (branche `main`) | 7 sept. 2026 |
| KORA (autre nom) | `cultureconnectorg/KORA` | Même système que `kora2024/Kora-app` (**déclaration de Laurent, 11 oct. 2026**) ; ce nom n'est pas lisible depuis la session | — | — |
| **Agent Factory** | `cultureconnectorg/Cvlnagentfactory` (**public**) — archive `CVLNAgentfactory-CVLN-AGENT-FACTORY.zip`, export de la branche `CVLN-AGENT-FACTORY` | Lecture git anonyme ; archive extraite sans exécution | `ceb5349` (dépôt) ; **contenu de l'archive daté du 15 sept. 2026** | 11 oct. 2026 (dépôt) |
| Agent Factory (dépôt d'origine) | `frekcore/CVLNAgentfactory` | ❌ Inaccessible depuis la session ; non nécessaire, l'export ci-dessus a été fourni par Laurent | — | — |
| Meta CVLN | `cultureconnectorg/Metacvln-Sept2026` | Lecture | `7673bfc` | 25 sept. 2026 |
| Kiltikonet | `cultureconnectorg/Kiltikonet-Aout2026` | Lecture | `4645777` | 6 oct. 2026 |
| CVL Brain | Pas de dépôt dédié identifié | — | — | — |

**Plus aucune contrainte d'accès.** KORA est entièrement couvert (`cultureconnectorg/KORA` et `kora2024/Kora-app` désignent le même système, déclaration de Laurent). Agent Factory est couvert par l'export fourni par Laurent. **Limite** : cet export est un instantané du 15 septembre 2026, sans historique git ; ce qui a pu changer depuis dans `frekcore/CVLNAgentfactory` n'est pas couvert.

Pour lever ces contraintes : connecter ou reconnecter le compte GitHub sur https://claude.ai/connect-github et, si l'application GitHub Claude n'est pas installée sur l'organisation `frekcore`, l'installer (ou demander à un propriétaire de l'organisation de le faire) depuis la même page. Le dépôt pourra ensuite être attaché à une session.

---

## 2. Audit de KORA (`kora2024/Kora-app`, commit `c2da615`)

### 2.1 Mission et documentation

- `README.md` : une ligne générique (« Here are your Instructions »), pas de documentation produit.
- **Référence produit** : `memory/PRD.md` — *« KORA est le premier DSP (Digital Service Provider) culturel souverain pour la diaspora caribéenne et afro-diasporique »*, expérience premium type Netflix / Apple TV, catalogue musical et audiovisuel alimenté par FrekCore.
- **Architecture cible** : `memory/KORA_Master_Prompt_Architecture.md` (857 lignes) — KORA est décrit comme une **brique d'infrastructure culturelle** du groupe, sur 4 couches : identité (FrekCore) → économie (Wallet CVLN / JCC) → **intelligence (Laurentia + Agent Factory)** → contenu (ligne 15).
- **Spécification** : `memory/KORA_CVE_Specification_Mathematique_v1.0.md` — moteur de valeur culturelle et d'allocation des royalties.
- `AGENTS.md` : instructions pour les agents de développement (Codex), en mode exécution autonome, avec une règle « Evidence-first » et « Anti-hallucination ».

### 2.2 Architecture et code réel

| Élément | Constat | Preuve |
|---|---|---|
| Frontend | React Native / Expo SDK 54, expo-router, Zustand ; TV-first et mobile | `memory/PRD.md` |
| Backend | FastAPI + Motor (MongoDB `kora_db`), **126 routes** dans 16 fichiers | `backend/server.py:709-784` |
| Volume réel | ~180 fichiers de code ; **22 190 fichiers de cache de build versionnés** (`frontend/.metro-cache`) | `git ls-files` |
| Modules | Catalogue, contenu, abonnements, playlists, recommandation, live, podcasts, réputation, publicités, CVE, API v1, développeurs, créateurs, FrekCore, RBAC | `backend/server.py:709-784` |
| Écrans | 8 écrans (Éveil, Globe 3D, Feed, Territoire, Orbite, Nébuleuse, Noyau, Créer) ; **données « MOCKÉES » côté frontend** selon le PRD | `memory/PRD.md` |

### 2.3 API

- **Publique / partenaires** : `/api/v1` (œuvres, sorties, avails, événements, ayants droit) et `/api/developers` (documentation, clés API, webhooks, usage) — `backend/routes/api_v1_routes.py:19`, `backend/routes/developer_routes.py:21`.
- **FrekCore** : `/api/frekcore/feed`, `/feed/audiovisual`, `/feed/trending`, `/feed/territory/{code}`, `/ingest`, `/stats` (`memory/PRD.md`).
- **CVE** : `/api/cve/work/{id}`, `/leaderboard`, `/stats`, `/config/{cycle}`, `/cycle/{id}/process` (`memory/PRD.md`).
- **Paiement** : Stripe (Premium 3,98 €/mois, Famille 7,98 €/mois), webhook `/api/webhook/stripe`.

### 2.4 Mémoire et données

Collections MongoDB (comptage des accès dans le code) : `works` (53), `users` (29), `events` (24), `content` (19), `playlists` (14), `listening_events` (11), `podcast_shows`, `uploads`, `releases`, `cve_records`, `rights_holders`, `api_keys`, `webhooks`, `listening_history`, `royalty_statements`, `royalty_splits`, `ad_impressions`… Ce sont des **données métier** : catalogue, abonnés, écoutes, droits, royalties. **Aucune mémoire d'assistant ni donnée personnelle de Laurent.**

### 2.5 Intelligence et agents

| Élément | Constat | Preuve |
|---|---|---|
| LLM dans le code | **Aucun.** `openai` et `emergentintegrations` figurent dans `requirements.txt` mais ne sont importés par aucun module backend | `grep` des imports dans `backend/` |
| Recommandation | Heuristique sur l'historique d'écoute (pas de modèle) | `backend/routes/recommendation_routes.py:43-73` |
| CVE | Moteur mathématique (TrustScore, CVI, allocation UVC) | `backend/services/cve_service.py`, `memory/PRD.md` |
| Agents à l'exécution | **Aucun** dans le code de KORA | — |
| Agents de développement | Codex avec 4 serveurs MCP : Perplexity, Firecrawl, Context7 et un **pont Agent Factory** qui clone `frekcore/CVLNAgentfactory` et appelle son API | `.codex/config.toml`, `.codex/cvln_agent_factory_bridge.py:10-15` |
| Cycle autonome | GitHub Actions **toutes les 2 heures** : `GET /api/autonomous/mode` puis `POST /api/autonomous/cycle` sur Agent Factory (jeton Bearer) | `.github/workflows/cvln-agent-factory-autonomous.yml:5-7, 36-70` |

### 2.6 Intégrations avec Laurent.ia

- **Dans le code : aucune.** Aucun module de KORA n'appelle Laurent.ia, et Laurent.ia n'appelle pas KORA.
- **Dans l'architecture cible : un rôle incompatible.** La section 11 décrit « Laurentia » comme un **assistant conversationnel grand public, côté abonnés de KORA** : recherche en langage naturel dans le catalogue, recommandation conversationnelle, support de premier niveau, *« consomme les mêmes APIs que le frontend »* (`memory/KORA_Master_Prompt_Architecture.md:333-340`). Les lignes 499, 523, 623 et 630 placent aussi Laurentia comme service transversal du groupe, et la ligne 647 lui attribue une base vectorielle partagée.

### 2.7 Contrats

- Événements métier publiés sur le bus d'Agent Factory : `stream.recorded`, `work.published`, `rights.updated` ; abonnement à `work.validated` de FrekCore (`Master_Prompt_Architecture.md:311`).
- Capacités attendues d'Agent Factory : `content.recommendation`, `content.moderation`, `metadata.generation`, `fraud.detection`, `partner.relations`, `campaign.orchestration` (lignes 344-356).
- Règle déclarée : registre central des schémas d'API hébergé côté Agent Factory (ligne 434).
- **Aucun contrat avec Laurent.ia.**

### 2.8 Tests, branches, production

- **Tests** : 13 fonctions de test (`backend/tests/test_frekcore_bridge.py` : 7 ; `backend_test.py` : 6) et des rapports d'itération dans `test_reports/`. **Non exécutés** dans cet audit en lecture seule.
- **Branches** : 8 — `main`, `Codex`, `codex/agent-factory-autopilot`, `codex/autonomous-kora-runtime`, `codex/context7-mcp`, `codex/durcir-la-configuration-runtime-de-kora`, `codex/firecrawl-mcp`, `codex/perplexity-mcp`.
- **Production** : dossier `.emergent/` (plateforme Emergent) ; aucun déploiement de production identifiable depuis le dépôt.

### 2.9 Points de sécurité relevés (à traiter dans KORA, non modifiés)

Le dépôt est **public** :
1. `memory/test_credentials.md` contient des **e-mails et mots de passe** d'un compte administrateur et d'un compte créateur portant le nom d'une artiste réelle. Les valeurs ne sont pas reproduites ici. Que ces comptes soient réels ou non, ces identifiants doivent être considérés comme compromis.
2. `backend/server.py:31` : secret JWT avec **valeur par défaut codée en dur** — si la variable d'environnement manque, n'importe qui peut forger des jetons.
3. `backend/server.py:36` : clé Stripe avec valeur par défaut codée en dur.
4. 22 190 fichiers de cache de build versionnés.

---

## 3. Les autres systèmes

### 3.1 CVL Brain — un nom, quatre usages

| Où | Ce que c'est | Modèle | Preuve |
|---|---|---|---|
| Kiltikonet | Client LLM unique pour toutes les surfaces « BRAIN » (chat, analyses, agents, assistant, recommandations), routes d'administration `/api/brain/*` | `claude-sonnet-4-5`, via Anthropic ou Emergent | `Kiltikonet-Aout2026/backend/services/brain_llm.py:1-20`, `backend/routes/brain.py:61-104` |
| Meta CVLN | Assistant du système d'exploitation du groupe, `/api/brain/ask`, historique par utilisateur (`brain_messages`) | `claude-sonnet-4-6` via Emergent | `Metacvln-Sept2026/backend/server.py:1478-1533` |
| Laurent.ia | Wrapper LLM (sans lien fonctionnel avec les deux autres) | `claude-sonnet-4-5` via Emergent | `Laurent.ia/backend/services/cvl_brain.py` |
| Agent Factory | **Une entité** du registre (pôle « Infrastructure IA ») qui regroupe des agents (AGT-002, AGT-005, AGT-006) ; les mémoires stratégiques de l'agent AGT-000 lui sont rattachées. Le blueprint d'intégration la désigne comme « couche cognitive commune » du groupe | — | `seed_data.py:22-42`, `cognitive_routes.py:110`, `memory/artifacts/INTEGRATION_ECOSYSTEME.md` |

**Constat** : CVL Brain n'est pas aujourd'hui un système avec une API propre ; c'est un nom porté par des modules d'IA de plusieurs produits. Kiltikonet décrit même son pont Laurent.ia comme « Laurent.ia (CVL Brain externalisé) » (`backend/routes/laurentia_bridge.py:2`), ce qui confond les deux identités.

### 3.2 Agent Factory (`cultureconnectorg/Cvlnagentfactory`, export du 15 sept. 2026)

Chemins relatifs à la racine de l'archive. Le dépôt ne contient que l'archive et un README d'une ligne.

**Mission déclarée** (`memory/PRD.md`) : *« Sovereign Cognitive Operating System — infrastructure cognitive opérationnelle souveraine du groupe CVLN (Laurent, fondateur) : mémoire, doctrine, gouvernance, orchestration, agents, objectifs, journaux, runtime et continuité propriétaires. Les LLM sont des accélérateurs interchangeables, jamais le cœur. Capable de piloter plusieurs entités : Factory Maker Studio, KORA, FREKCORE. »*

| Élément | Constat | Preuve |
|---|---|---|
| Stack | FastAPI + MongoDB (Motor), React, JWT (admin / operator / reader), identités de service `svc_`, PWA, Telegram | `memory/PRD.md` |
| API | **157 routes** dans 29 modules | `backend/server.py:99-127` |
| Points d'entrée annoncés par ses consommateurs | **Tous présents** : `/api/monitoring/health`, `/api/runtime/status`, `/api/missions/orchestrate`, `/api/frek-workforce/capabilities` (Meta CVLN), `/api/autonomous/mode`, `/api/autonomous/cycle` (KORA) | Recensement des décorateurs de routes |
| Agents | Registre `AGT-000` → `AGT-175` (« 176 agents » dans le PRD : 14 en production, 20 en bêta, 135 en brouillon) ; le chiffre de « 284 agents » cité par KORA n'apparaît pas | `memory/PRD.md`, `backend/seed_*.py`, `frek_workforce_catalog.py` |
| Cycle de vie | Brouillon → Prototype → Bêta → Production, agent par agent ; **la mise en production est réservée à Laurent** | `memory/PRD.md` |
| Runtime | États actif / sommeil / attente de validation / erreur / suspendu / terminé, points de reprise, cycle autonome en 9 étapes, `dry_run` par défaut | `memory/PRD.md`, `backend/runtime_routes.py`, `backend/autonomous_routes.py` |
| Porte de permissions | 6 niveaux : observer, analyser, proposer, préparer, exécuter après validation humaine, interdit ; actions critiques (dépense, publication externe, changement de gouvernance…) toujours soumises à Laurent | `backend/gate_routes.py:14-30` |
| Validations de Laurent | Demandes de validation, décision par API, alerte Telegram | `/api/gate/validation-requests`, `/api/gate/validation-requests/{id}/decide` |
| Mémoire | `memory_entries` avec 6 portées (session, persistante, opérationnelle, stratégique, doctrinale, apprentissage), `confidence`, `provenance`, validation humaine | `backend/core_routes.py:52-110` |
| Connaissances | `knowledge_sources` + recherche lexicale MongoDB ; interface prévue vers Qdrant | `backend/knowledge_sources_routes.py`, ADR-005 |
| Doctrine et constitution | Registre de doctrine versionné, constitution de 21 articles, amendements | `backend/doctrine_registry_routes.py`, `backend/constitution_routes.py` |
| Objectifs | Objectifs (OBJ-NNN), objectifs stratégiques par entité, moteur d'alignement | `backend/objectives_routes.py`, `backend/mission_os_routes.py` |
| Briefing et clôture | `GET /api/daily/briefing`, `/api/daily/closings` | `backend/daily_closing_routes.py` |
| **Chat cognitif avec Laurent** | `/api/cognitive/chat`, conversations persistées (`cognitive_conversations`, `cognitive_messages`) | `backend/cognitive_routes.py` |
| **Moteur LLM** | Couche d'adaptation : Anthropic (`claude-sonnet-4-6`), OpenAI (`gpt-5.4`), Gemini (`gemini-3.1-pro-preview`) via `emergentintegrations`. **Stratégie par défaut : `quality`**, qui essaie d'abord les fournisseurs externes. Le moteur « souverain » est un **repli déterministe à base de modèles de réponse, pas un LLM** | `backend/provider_layer.py:17-25, 42-81` |
| Export complet des données | Prévu (« mode souverain complet », P1), **non réalisé** : seul un export par agent existe | `memory/PRD.md`, `/api/registry/agents/{id}/export` |
| Tests | 268 fonctions de test déclarées (le PRD annonce 282) ; **non exécutés** dans cet audit | `backend/tests/` |

**Ce qu'Agent Factory dit de Laurent.ia — deux positions différentes**
- **Code et doctrine** : Laurent.ia est un **système séparé**. Une route `/api/laurent-ia` est réservée et répond `501` : *« Reserved entry point for Laurent.ia (separate system). Interface contract to be defined in V2. »* (`backend/core_routes.py:272-277`). Règle `DOC-COM-03` : *« Les systèmes externes (Laurent.ia, KORA, FREK…) restent indépendants et communiquent uniquement via contrats d'API »* (`backend/doctrine.py:23`).
- **Documents d'architecture** : « Laurentia » est la **couche de présentation** de la Factory (« interface conversationnelle & dashboard », « interface utilisateur unique vers la Factory ») (`memory/artifacts/SYNTHESE_4_COUCHES_Architecture_v2.md:11, 83`, `RAPPORT_AUDIT.md:194`, `MISSION_OS_Specification.md:174`).
- Blueprint d'intégration : *« Core = source de vérité (mémoire / gouvernance / objectifs / connaissances / identités / finances), entités autonomes en exécution, zéro duplication »* (`memory/artifacts/INTEGRATION_ECOSYSTEME.md`).

**Points de sécurité (à traiter dans Agent Factory, non modifiés)** : le dépôt est **public**, et `memory/PRD.md` contient **en clair l'identifiant et le mot de passe du compte administrateur ainsi qu'un jeton de service** (valeurs non reproduites ici). Ils doivent être considérés comme compromis et renouvelés.

### 3.2 bis Recouvrement Agent Factory ↔ Laurent.ia

C'est le constat le plus structurant de l'audit : **une grande partie de ce que le Product Contract prévoit pour Laurent.ia existe déjà, au moins partiellement, dans Agent Factory**, avec Laurent comme utilisateur principal.

| Capacité prévue pour Laurent.ia | Équivalent existant dans Agent Factory | Nature du recouvrement |
|---|---|---|
| Mémoire avec provenance, confiance, validation | `memory_entries` (6 portées, `confidence`, `provenance`, validation humaine) | Fort — mais c'est la mémoire **du groupe et de ses agents**, pas la mémoire personnelle de Laurent |
| Identity / doctrine / principes | Registre de doctrine, constitution, règles | Fort pour la doctrine **du groupe** |
| Projets et objectifs | Objectifs, objectifs stratégiques par entité, alignement | Fort pour les entités **du groupe** |
| Action Layer (READ / PROPOSE / EXECUTE, approbation) | Porte à 6 niveaux, actions critiques réservées à Laurent | Fort pour les actions **des agents** |
| Evidence & journal | Journal d'activité unifié, audit, journal des appels aux modèles | Fort |
| Briefing quotidien | `/api/daily/briefing`, clôtures | Fort |
| Chat contextuel avec Laurent | `/api/cognitive/chat` | **Doublon direct** d'interface et de conversations |
| Souveraineté de l'inférence (D8) | Fournisseurs externes par défaut ; repli non-LLM | **Incompatible** avec D8 en l'état |

**Lecture** : Agent Factory est le système d'exploitation des **agents et des entités du groupe** ; Laurent.ia est l'intelligence **personnelle** de Laurent. Les deux se recouvrent là où Laurent est l'utilisateur d'Agent Factory (chat, briefing, validations). Sans règle explicite, on construirait deux « cerveaux » pour la même personne — exactement la duplication que la règle « une entité = une seule source de vérité » d'Agent Factory interdit aussi.

### 3.3 Meta CVLN

Système d'exploitation interne du groupe : registre de 12 dépôts, notariat Ed25519, 5 contrats versionnés, adaptateurs, et des collections **`decisions`, `projects`, `people`, `objectives`, `obligations`, `evidence`, `finance_snapshot`, `brain_messages`** (`docs/META_CVLN_ARCHITECTURE.md`). Utilisateurs : équipe CVLN avec RBAC (« multi-tenant strict : PARTIAL », `docs/META_CVLN_EXISTING_SYSTEM_AUDIT.md`).

### 3.4 Kiltikonet

Plateforme du réseau culturel (FREK-ID, badges NFC, jetons, association, territoires), 1 419 fichiers versionnés. Se déclare **consommateur** de services partagés dont « Laurentia », sans en être propriétaire (`backend/services/network_economics.py:285-305`).

---

## 4. Matrice comparative

| Système | Mission | Périmètre | Mémoire | Intelligence | Agents | Actions | Utilisateurs | Relation avec Laurent.ia |
|---|---|---|---|---|---|---|---|---|
| **Laurent.ia (cible V1)** | Intelligence personnelle de Laurent : mémoire, raisonnement, exécution sous son autorité | Laurent, ses projets, ses décisions, ses outils | **Mémoire personnelle de Laurent** (identité, épisodes, savoirs, décisions, projets vus par Laurent), sourcée | Modèle open-weight local, interchangeable (D8) | 5 rôles internes (Core, Researcher, Analyst, Planner, Operator) | READ / PROPOSE / EXECUTE sous approbation | **Laurent seul** | — |
| **Laurent.ia (code actuel)** | SaaS grand public diaspora (ancien produit) | Utilisateurs anonymes et FREK-ID, abonnements | 50 derniers échanges par utilisateur, chiffrés | Claude via Emergent | 20 « agents » regex en observation | Chat, PDF, échos, publication sociale | Public | — |
| **KORA** | DSP culturel souverain (musique + audiovisuel) pour la diaspora | Catalogue, lecture, créateurs, abonnements, publicités, podcasts, live, royalties (CVE), API partenaires | **Données métier** : œuvres, abonnés, écoutes, droits, royalties (`kora_db`) | Aucun LLM dans le code ; recommandation heuristique ; moteur CVE mathématique | Aucun à l'exécution ; Codex + Agent Factory pour le développement, cycle autonome toutes les 2 h | Streaming, paiements Stripe, publication, ingestion | Abonnés, créateurs, partenaires, administrateurs | **Aucune dans le code.** L'architecture cible prévoit « Laurentia » comme assistant de ses abonnés |
| **CVL Brain** | Nom des modules d'IA de produits du groupe | Variable selon le produit hôte | `brain_messages` (Meta CVLN) ; non identifiée ailleurs | Claude via Anthropic ou Emergent | Analyses, assistant, recommandations (Kiltikonet) | Lecture et génération | Équipes et administrateurs des produits hôtes | Confusion de nom ; décrit comme « Laurent.ia externalisé » dans Kiltikonet. Pas d'API propre |
| **Agent Factory** | Système d'exploitation cognitif des agents et des entités du groupe (« Sovereign Cognitive OS ») | Agents, missions, entités, doctrine, constitution, objectifs, finances, gouvernance | **Mémoire du groupe et des agents** (6 portées, provenance, confiance) ; connaissances ; conversations cognitives avec Laurent | Anthropic / OpenAI / Gemini via Emergent par défaut ; repli déterministe non-LLM | 176 agents enregistrés (14 en production) ; cycle autonome gouverné | Porte à 6 niveaux ; actions critiques validées par Laurent ; Telegram | Laurent (fondateur), administrateurs, opérateurs, identités de service, CI de KORA | **Route `/api/laurent-ia` réservée (501)** ; doctrine : système séparé sous contrat ; documents : Laurentia = couche de présentation de la Factory. **Fort recouvrement** fonctionnel (§3.2 bis) |
| **Meta CVLN** | Système d'exploitation interne du groupe | Registre, contrats, notariat, décisions et projets du groupe, finances, personnes | **Registres d'organisation** : décisions, projets, personnes, objectifs, preuves | CVL Brain (Claude Sonnet 4.6 via Emergent) | « Executive Briefing Agent » (données de démonstration) | Adaptateurs typés, notarisation | Équipe CVLN (RBAC) | Consomme `laurentia.briefing@1.0` ; son registre décrit Laurent.ia comme « Learning Plane » B2C |
| **Kiltikonet** | Réseau culturel : identité FREK, badges, jetons, territoires | Membres, territoires, association, outils internes | **Données métier** des membres (profils, profils culturels 7D) | CVL Brain (Claude Sonnet 4.5) | Smart engine, agents d'analyse | Nombreuses (paiements, badges, code) | Membres, opérateurs, administrateurs | 3 interfaces actives ou déclarées (§5) |

---

## 5. Inventaire des interfaces existantes avec Laurent.ia (pour D13)

Aucune ne touche aujourd'hui une mémoire personnelle de Laurent : le contrat de briefing construit sa réponse à partir du seul prompt système et de la charge envoyée (`Laurent.ia/backend/routes/brain.py:54-73`).

| # | Sens | Interface | Authentification | Données échangées | État observé | Preuve |
|---|---|---|---|---|---|---|
| **I1** | Meta CVLN → Laurent.ia | `POST /api/brain/briefing` via l'adaptateur `/api/adapters/laurentia/briefing` | `X-API-Key` stockée dans la fiche du registre | Entrées de l'utilisateur Meta CVLN ; réponse journalisée comme preuve dans Meta CVLN | Déclaré « working » par Meta CVLN ; l'URL cible est une prévisualisation Emergent | `Metacvln-Sept2026/backend/server.py:1384-1392, 1321-1334` ; `registry_data.py:164-200` |
| **I2** | Kiltikonet → Laurent.ia | `POST /api/brain/briefing` (émetteur `kiltikonet-code`) et `GET /api/brain/health` | `LAURENTIA_OUTBOUND_API_KEY` | **Prompts de génération de code et contenu du dépôt Kiltikonet** ; Laurent.ia sert de **moteur LLM générique**, avec repli sur CVL Brain s'il est indisponible | Code en place, activé si configuré | `Kiltikonet-Aout2026/backend/routes/kiltikonet_code.py:270-290, 418` ; `services/laurentia_client.py` |
| **I3** | Kiltikonet → Laurent.ia | `GET /api/laurentia/me?frek_id=` (widget membre « Ton intelligence personnelle arrive bientôt ») | `LAURENTIA_API_KEY`, **le même secret que I4** alors que `.env.example` recommande deux clés distinctes | Identifiant FREK d'un membre | **Cassé** : cette route n'existe pas dans Laurent.ia (seule `/api/auth/me` existe) | `Kiltikonet-Aout2026/backend/routes/laurentia_widget.py:27-56` ; `Laurent.ia/backend/routes/auth.py:26, 206` |
| **I4** | Laurent.ia → Kiltikonet | `GET /api/users/validate/{frek_id}`, `GET /api/users/{frek_id}/profile` | `X-API-Key` (`KILTIKONET_API_KEY` côté Laurent.ia, `LAURENTIA_API_KEY` côté Kiltikonet) | **Identité et profil culturel 7D de membres Kiltikonet**, injectés dans les prompts de Laurent.ia | Code en place des deux côtés | `Laurent.ia/backend/services/kiltikonet_bridge.py:84, 122` ; `Kiltikonet-Aout2026/backend/routes/laurentia_bridge.py:96-164` |
| **I5** | Laurent.ia → FrekCore | Validation de FREK-ID (auth des utilisateurs) | `FREKCORE_API_KEY` | Identifiants d'utilisateurs | Code en place | `Laurent.ia/backend/services/frekcore_bridge.py` |
| **I6** | Laurent.ia → LabelOS | Contexte artiste | `LABELOS_API_KEY` | Contexte d'artistes | Repli silencieux sur un stub | `Laurent.ia/backend/services/labelos_bridge.py` |
| **I7** | KORA → Laurent.ia | — | — | — | **Aucune dans le code** ; prévue dans l'architecture cible comme assistant des abonnés | `kora-app/memory/KORA_Master_Prompt_Architecture.md:333-340` |
| **I8** | Registre Meta CVLN | Fiche descriptive de Laurent.ia | — | — | Décrit l'ancien produit (tiers payants, persistance fantôme, échos) | `Metacvln-Sept2026/backend/registry_data.py:164-200` |
| **I9** | Agent Factory ← Laurent.ia | `GET/POST /api/laurent-ia` | — | — | **Réservée, répond 501** ; contrat « à définir en V2 » | `Cvlnagentfactory/…/backend/core_routes.py:272-277` |

**Lecture** : dans l'existant, Laurent.ia est utilisé comme **service partagé du groupe** (I1, I2), comme **produit grand public par membre** (I3, I4, I5) et il est **prévu** comme **assistant d'abonnés** de KORA (I7). Aucun de ces trois rôles n'est celui d'une intelligence personnelle de Laurent. Conformément à ta consigne, **rien n'est retiré** : la décision (maintenir, adapter, remplacer, supprimer) est à prendre interface par interface.

---

## 6. Propriété des données — vérification des frontières réelles (pour D14)

| Domaine de données | Propriétaire réel observé | Risque de duplication avec Laurent.ia | Règle proposée |
|---|---|---|---|
| Mémoire personnelle de Laurent (identité, préférences, décisions personnelles, conversations) | **Personne aujourd'hui** : rien de structuré n'existe dans Laurent.ia | — | **Laurent.ia**, propriétaire unique |
| Décisions, projets, personnes, objectifs, preuves **du groupe** | **Meta CVLN** (collections existantes) | **Élevé** : le Decision Engine et les fiches projet de Laurent.ia recouvrent ces collections | Meta CVLN reste canonique ; Laurent.ia garde la vue de Laurent (ses notes, sa position, ses décisions personnelles) et **référence** les objets du groupe par identifiant, lus par contrat |
| Conversations de Laurent avec CVL Brain dans Meta CVLN | **Meta CVLN** (`brain_messages`) | Moyen : deux historiques d'assistant pour la même personne | Question ouverte (§8) |
| Catalogue, abonnés, écoutes, droits, royalties | **KORA** | Faible si lecture d'agrégats uniquement | Lecture via l'API de KORA (`/api/v1`, `/api/developers`) sous contrat ; aucune copie |
| Membres, profils culturels, jetons | **Kiltikonet** | **Existant** : I4 fait entrer des profils de membres dans Laurent.ia | Ne pas étendre cette logique à la V1 personnelle |
| Identité et preuve d'existence, format `.fk` | **FrekCore** | Faible | Hors périmètre de la V1 |
| Agents, missions, capacités, cycles autonomes | **Agent Factory** | Faible | Agent Factory reste propriétaire ; Laurent.ia pilote par contrat |
| Doctrine, constitution, objectifs et mémoire **du groupe et des agents** | **Agent Factory** (et Meta CVLN pour décisions et projets) | **Élevé** avec Identity, Memory, Projects | Canonique dans Agent Factory ; Laurent.ia en garde la vue de Laurent et référence par identifiant |
| Demandes de validation adressées à Laurent | **Agent Factory** (`validation_requests`) | **Élevé** avec la surface Actions | La demande reste dans Agent Factory ; Laurent.ia peut être l'endroit où Laurent la voit et décide, par contrat |
| Conversations de Laurent avec AGT-000 | **Agent Factory** (`cognitive_conversations`) | **Doublon direct** avec le Chat de Laurent.ia | À trancher (D17 étendue) |

---

## 7. Séparation des couches demandée

| Couche | Définition | Propriétaire | Remplaçable ? |
|---|---|---|---|
| **Modèle local / moteur d'inférence** | Poids du modèle et serveur d'inférence (vLLM, llama.cpp…) | Infrastructure de Laurent | Oui, à tout moment, sur benchmark |
| **Runtime Laurent.ia** | Boucle, rôles, Context Engine, politique d'action | Laurent.ia | Évolue, mais propriété de Laurent |
| **Mémoire** | Objets mémoire de Laurent, provenance, journal de preuve | **Laurent** | Non : c'est l'actif durable (export ouvert garanti) |
| **Outils** | Capacités atomiques déclarées (READ / PROPOSE / EXECUTE) | Laurent.ia (manifestes) | Oui |
| **Agents** | Rôles internes ; agents externes sous contrat | Laurent.ia (internes) ; Agent Factory et autres (externes) | Oui |
| **Données métier** | Données des produits (KORA, Kiltikonet, Meta CVLN…) | Chaque système métier | Hors Laurent.ia : lues par contrat, jamais absorbées |
| **Interfaces externes** | Contrats versionnés entrants et sortants | Partagé, versionné | Oui, par version |

**Local-first ≠ mono-machine** : la doctrine est l'autonomie. Le modèle, la mémoire et le runtime tournent sur une infrastructure contrôlée par Laurent, qui peut compter **plusieurs machines** (par exemple un serveur d'inférence, un serveur de données, une machine de sauvegarde).

---

## 8. Questions ouvertes (aucune hypothèse à leur place)

1. ~~`cultureconnectorg/KORA` est-il distinct de `kora2024/Kora-app` ?~~ **Résolu** le 11 oct. 2026 : même système (déclaration de Laurent).
2. ~~Code réel d'Agent Factory~~ **Résolu** le 11 oct. 2026 (export fourni). Reste ouvert : l'export du 15 sept. est-il à jour par rapport à `frekcore/CVLNAgentfactory` ?
3. Le « Laurentia » de l'architecture de KORA (assistant d'abonnés) doit-il garder ce nom, devenir une capacité d'un autre système (CVL Brain, Agent Factory), ou être un produit distinct de Laurent.ia ?
4. Les conversations de Laurent avec CVL Brain dans Meta CVLN doivent-elles rester dans Meta CVLN, ou ce rôle d'assistant de Laurent revient-il à Laurent.ia ?
5. Les points de sécurité de KORA (§2.9) et d'Agent Factory (§3.2) doivent être traités dans ces dépôts. Ils ne l'ont pas été ici, conformément à la consigne de lecture seule.
6. **Partage des rôles Laurent.ia ↔ Agent Factory** (§3.2 bis) : qui est l'interface de Laurent, où vivent ses conversations, son briefing et ses validations ? Décision D18.

---

## 9. Relecture à partir de Meta CVLN, référence de l'écosystème (11 octobre 2026)

> **Lecture corrigée (correctif E1, 11 oct. 2026).** Les rôles de cette section viennent de la **fiche du registre Meta CVLN** (`registry_data.py`) : ce sont des **déclarations** [DH], pas des règles. En particulier, « Laurent.ia = Learning Plane » et « la mémoire relève de Laurent.ia » sont **remplacés** par les règles canoniques du [registre](../decisions/REGISTER.md), qui sont des **arbitrages du 11 octobre 2026** [AR], non des preuves historiques : cognition et mémoire cognitive → **CVLN Brain** (LIA-D20, LIA-D21) ; Meta CVLN gouverne, Brain détient la doctrine (LIA-D19) ; Laurent.ia = un système, deux rôles (LIA-D23). Les questions du §9.4 sont tranchées par LIA-D19 à LIA-D21. Voir le [rapport de réconciliation](./RECONCILIATION_2026-10-11.md) §2-§3.

**Consigne de Laurent** : *« Meta CVLN dit ce qu'il faut. Agent Factory, ce sont des agents de mon écosystème. »* Les rôles sont donc ceux que définit Meta CVLN (`Metacvln-Sept2026`, commit `7673bfc`). Cette section corrige les lectures précédentes qui traitaient la fiche de Laurent.ia dans Meta CVLN comme simplement « obsolète ».

### 9.1 Ce que Meta CVLN définit

Meta CVLN est le **système d'exploitation méta** du groupe. Il tient :
- le registre des systèmes et leur plan ;
- les 5 contrats versionnés : `Event`, `Capability`, `RoutingDecision`, `SystemState`, `ExecutionPlan` (`backend/contracts.py`) — *« Every cross-entity call, every routing decision, every emitted event MUST conform to one of these contracts »* ;
- le routage des capacités, le notariat Ed25519, le journal de preuves, les validations humaines, et les registres d'organisation (décisions, projets, personnes).

Il attend de chaque système qu'il expose `GET /api/capabilities` (`server.py:663-701`).

| Plan (registre, `registry_data.py`) | Systèmes | Rôle déclaré |
|---|---|---|
| Trust Layer | FREKCORE, FREKANSLA | Identité, provenance, notariat, certification |
| **Control Plane** | **Agent Factory**, Command Center | **Création, composition, réutilisation et cycle de vie des agents** ; classification, routage, alerte |
| **Learning Plane** | **Laurent.ia** | **Cognition, mémoire, évaluation, confiance** |
| Product / Operating | KORA (*« plateforme culturelle »*, entité Operating dans `seed_data.py`), Kiltikonet, CVL Academy, FMS, Gala, Factory Ops | Produits métier |
| Infrastructure | CVLN Wallet, Production Vault | Valeur, stockage souverain |

CVL Brain apparaît comme la **couche cognitive interne de Meta CVLN** (`server.py:1487` : *« Tu ne prends jamais de décision opérationnelle : tu prépares la décision humaine »*), classée elle aussi « Learning » dans les entités.

### 9.2 Ce que cela change dans mes conclusions

| Conclusion antérieure | Lecture corrigée |
|---|---|
| La fiche de Laurent.ia dans Meta CVLN est « obsolète » | **Le plan est juste** : Laurent.ia est le Learning Plane (cognition, mémoire, évaluation, confiance). Seule la **liste de capacités** de la fiche (tiers payants, persistance fantôme, échos) décrit l'ancien produit |
| Agent Factory recouvre Laurent.ia ; proposition d'en faire une interface de Laurent.ia (D18) | Agent Factory est le **Control Plane** : la fabrique et le cycle de vie des agents de l'écosystème. Ses fonctions de mémoire, de chat avec Laurent et de « système cognitif » sortent de ce plan ; la cognition, la mémoire, l'évaluation et la confiance relèvent du Learning Plane, c'est-à-dire de Laurent.ia |
| Le contrat `laurentia.briefing` met l'intelligence de Laurent au service des produits : à restreindre (D13 v1) | C'est **la capacité prévue par Meta CVLN** (`cap-laurentia-briefing`, routée par `RoutingDecision` et `ExecutionPlan`, `contracts.py:170-190`). L'usage par Kiltikonet Code comme moteur LLM générique (I2) reste, lui, hors de ce cadre |

### 9.3 Écarts entre Laurent.ia et ce que Meta CVLN attend

1. Laurent.ia n'expose pas `GET /api/capabilities` : Meta CVLN ne peut pas le découvrir.
2. Laurent.ia ne publie aucun descripteur conforme au contrat `Capability` v1.0 (schémas d'entrée et de sortie, acteurs autorisés, approbation requise).
3. La fiche du registre liste des capacités de l'ancien produit B2C.
4. L'évaluation et la confiance, explicitement attribuées au Learning Plane, n'ont aucune implémentation dans Laurent.ia.

### 9.4 Points à confirmer par Laurent

- **Périmètre du Learning Plane** : Laurent.ia sert Laurent d'abord ; ses capacités (briefing, évaluation, confiance) sont offertes aux autres systèmes **uniquement via les contrats de Meta CVLN**, sa mémoire personnelle n'étant jamais exposée brute. Est-ce la bonne lecture ?
- **CVL Brain et Laurent.ia**, tous deux « Learning » : CVL Brain reste-t-il la couche cognitive propre à Meta CVLN, ou doit-il à terme s'appuyer sur Laurent.ia ?

---

## 10. Audit de `cultureconnectorg/Cvln-ios-v.1` — la doctrine CVLN Intelligence OS (11 octobre 2026)

> **Lecture corrigée (correctif E1, 11 oct. 2026).** CVLN iOS est un **référentiel de cohérence, de preuves, de responsabilités et de contradictions ; il ne commande pas automatiquement l'architecture produit** [DH, Kiltikonet `2ae7bcc7`, 9-10 sept.]. Les niveaux et rôles du §10.2 (« Laurentia, niveau 3, opérateur culturel, enfant d'Agent Factory ») sont des **déclarations** du registre iOS, pas des règles. Les rôles canoniques sont dans le [registre](../decisions/REGISTER.md), sous forme d'arbitrages du 11 octobre 2026 [AR] : LIA-D22 (relations fonctionnelles, sans hiérarchie) et LIA-D23 (identifiants historiques, un système, deux rôles). La proposition du §10.5 est appliquée : préfixe `LIA-`.

Lecture seule, branche la plus récente `claude/cvln-groupe-ecosystem-qf2pj2` (commit `1cedf8a`, 15 sept. 2026, en avance de 53 fichiers sur `main`).

### 10.1 Ce qu'est ce dépôt

Malgré son nom, ce n'est pas une application iOS. C'est **le corpus de doctrine de l'écosystème**, `cvln-intelligence-os/` :
- une constitution ;
- 31 décisions d'architecture (ADR D-001 à D-031, toutes au statut DECIDED) ;
- 5 décisions fondatrices encore ouvertes (FD-001 à FD-005) ;
- des architectures par système, des contrats d'API, des registres et des audits ;
- une application FastAPI + React qui l'affiche et vérifie son gel (« freeze ») par des tests.

Il renvoie aussi à un dépôt `Foundation-Cvln` (`lib/registry/cvlnRegistry.js`, l'arbre fondateur), **non audité ici**.

### 10.2 Les rôles qu'il définit

| Niveau | Système | Rôle (`registry/ECOSYSTEM-REGISTRY.md`) | Statut |
|---|---|---|---|
| −1 | Meta CVLN (entité) | Gouvernance du groupe | OBSERVED |
| 0 | MetaCVLN (logiciel) | Noyau : gouvernance, registre, permissions, état d'exécution | IMPLEMENTED |
| — | CVLN Intelligence OS | Intelligence système, orchestration commune (D-027 : jamais fusionné avec Meta CVLN) | Déclaré |
| 1 | **CVLN Brain** | **Moteur d'intelligence souveraine : doctrine, raisonnement, mémoire** ; cible = un service unique possédant persona, doctrine, mémoire, apprentissage, raisonnement, routage de modèles et comportement d'urgence | TARGET |
| 2 | CVLN Agent Factory | « Système nerveux » : langage de définition d'agents, runtime, portes, bus | IMPLEMENTED |
| 3 | **Laurentia** | **« Opérateur de l'industrie culturelle »** : sessions, artefacts, rapports ; enfant d'Agent Factory dans l'arbre fondateur | PARTIAL |
| 4 | KORA, LabelOS, Wallet, Kiltikonet | Applications | REFERENCED |

### 10.3 Travail déjà fait sur Laurent.ia, à ne pas refaire

**PR #1 de `cultureconnectorg/Laurent.ia`** (« PATCH-007 — Laurentia runtime connection to the CVLN estate », ouverte le 15 sept. 2026, **non fusionnée**, base `public`). Elle apporte, avec 19 tests :
- `GET /api/capabilities` au format `Capability` v1.0, découvrable par Meta CVLN ;
- `/api/system/identity` et `/api/system/state` (`SystemState` v1.0) ;
- l'émission d'`Event` v1.0 vers le bus signé de Meta CVLN ;
- la propagation d'un identifiant de traçage (`X-CVLN-Trace-Id`) ;
- la délégation du choix du modèle au routeur d'Agent Factory (`POST /api/providers/route`).

Le Lot 0 de Laurent.ia doit **partir de cette PR**, pas réimplémenter ces points.

**Conflit avec D8** : cette PR délègue l'inférence au routeur d'Agent Factory, dont la stratégie par défaut appelle Anthropic, OpenAI ou Gemini ; son repli local reste Emergent. Telle quelle, elle est incompatible avec la souveraineté locale. Le reste (identité, capacités, état, événements, traçage) est compatible.

### 10.4 Trois définitions de Laurent.ia qui ne coïncident pas

| Source | Laurent.ia est… |
|---|---|
| Doctrine CVLN Intelligence OS (ADR décidés) | Un **produit** de niveau 3 : opérateur de l'industrie culturelle, enfant d'Agent Factory. L'intelligence souveraine (mémoire, raisonnement, doctrine, routage de modèles) relève de **CVLN Brain**, niveau 1 |
| Registre Meta CVLN | Le **Learning Plane** : cognition, mémoire, évaluation, confiance |
| Vision de Laurent dans cette session (D1, D8) | Le **système d'intelligence personnel et souverain** de Laurent : modèle local, mémoire, raisonnement, actions sous autorisation |

**Observation** : la vision de Laurent (mémoire, raisonnement, modèle local, souveraineté) correspond presque terme à terme à ce que la doctrine attribue à **CVLN Brain**, et dont la définition est précisément la décision fondatrice ouverte **FD-001** (« ce que CVL Brain désigne »). Elle correspond aussi au Learning Plane de Meta CVLN. Elle ne correspond pas au Laurentia « opérateur culturel » de niveau 3.

### 10.5 Collision de numérotation

Les décisions de ce dépôt Laurent.ia (D1 à D18) portent les mêmes numéros que les ADR de l'écosystème (D-001 à D-031), avec des contenus différents. À renommer (par exemple `LIA-D1`…) pour éviter toute confusion.
