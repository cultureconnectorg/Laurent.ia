# Audit des frontières — Laurent.ia et les systèmes de l'écosystème CVLN

> Statut : **audit en lecture seule**, 6 octobre 2026. Aucun dépôt audité n'a été modifié.
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
| KORA (second nom donné) | `cultureconnectorg/KORA` | ❌ **Refusé** : « introuvable ou pas d'accès » (outil d'attachement) ; `git ls-remote` demande une authentification | — | — |
| **Agent Factory** | `frekcore/CVLNAgentfactory` (branche `CVLN-AGENT-FACTORY`) | ❌ **Refusé** : même réponse ; `git ls-remote` demande une authentification | — | — |
| Meta CVLN | `cultureconnectorg/Metacvln-Sept2026` | Lecture | `7673bfc` | 25 sept. 2026 |
| Kiltikonet | `cultureconnectorg/Kiltikonet-Aout2026` | Lecture | `4645777` | 6 oct. 2026 |
| CVL Brain | Pas de dépôt dédié identifié | — | — | — |

**Contraintes d'accès ouvertes** : `cultureconnectorg/KORA` et `frekcore/CVLNAgentfactory`. Ce qui est dit d'Agent Factory ci-dessous vient **uniquement de ses consommateurs** (Meta CVLN, KORA, Kiltikonet) et n'est pas vérifié sur son code. Si `cultureconnectorg/KORA` est un dépôt distinct de `kora2024/Kora-app`, il n'est pas couvert par cet audit.

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

### 3.1 CVL Brain — un nom, trois implémentations

| Où | Ce que c'est | Modèle | Preuve |
|---|---|---|---|
| Kiltikonet | Client LLM unique pour toutes les surfaces « BRAIN » (chat, analyses, agents, assistant, recommandations), routes d'administration `/api/brain/*` | `claude-sonnet-4-5`, via Anthropic ou Emergent | `Kiltikonet-Aout2026/backend/services/brain_llm.py:1-20`, `backend/routes/brain.py:61-104` |
| Meta CVLN | Assistant du système d'exploitation du groupe, `/api/brain/ask`, historique par utilisateur (`brain_messages`) | `claude-sonnet-4-6` via Emergent | `Metacvln-Sept2026/backend/server.py:1478-1533` |
| Laurent.ia | Wrapper LLM (sans lien fonctionnel avec les deux autres) | `claude-sonnet-4-5` via Emergent | `Laurent.ia/backend/services/cvl_brain.py` |

**Constat** : CVL Brain n'est pas aujourd'hui un système avec une API propre ; c'est un nom porté par des modules d'IA de plusieurs produits. Kiltikonet décrit même son pont Laurent.ia comme « Laurent.ia (CVL Brain externalisé) » (`backend/routes/laurentia_bridge.py:2`), ce qui confond les deux identités.

### 3.2 Agent Factory — connu seulement par ses consommateurs

| Source | Ce qu'elle déclare | Preuve |
|---|---|---|
| Meta CVLN (registre) | « Control Plane », création / composition / cycle de vie des agents ; 4 points d'entrée dits « vérifiés » : `/api/monitoring/health`, `/api/runtime/status`, `/api/missions/orchestrate`, `/api/frek-workforce/capabilities` ; adaptateur « NOT_CONNECTED » | `Metacvln-Sept2026/backend/registry_data.py:128-162` |
| KORA (CI) | `GET /api/autonomous/mode`, `POST /api/autonomous/cycle`, jeton Bearer | `.github/workflows/cvln-agent-factory-autonomous.yml` |
| KORA (architecture) | « 284 agents », bus d'événements, registre d'entités, audit, supervision ; 6 capacités consommées | `memory/KORA_Master_Prompt_Architecture.md:28, 344-363` |
| Kiltikonet | Pont qualité avec un « runner » et un webhook GitHub | `backend/.env.example:192-198`, `backend/routes/quality_agent_factory.py` |

**Non vérifié** : le code d'Agent Factory lui-même. Aucune frontière avec Laurent.ia n'est fixée tant que ce dépôt n'est pas lu.

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
| **Agent Factory** | Création, composition, cycle de vie et orchestration d'agents (selon ses consommateurs) | Agents mutualisés du groupe | **Non vérifiée** (dépôt inaccessible) | **Non vérifiée** | « 284 agents » (déclaratif, non vérifié) | Missions, cycles autonomes | Produits du groupe, CI | **Aucune dans le code observé** |
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
| Agents, missions, capacités | **Agent Factory** (non vérifié) | Inconnu | À établir après accès au dépôt |

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

1. `cultureconnectorg/KORA` est-il un dépôt distinct de `kora2024/Kora-app` (autre version, autre brique) ? Accès nécessaire pour l'auditer.
2. Code réel d'Agent Factory (`frekcore/CVLNAgentfactory`) : accès nécessaire.
3. Le « Laurentia » de l'architecture de KORA (assistant d'abonnés) doit-il garder ce nom, devenir une capacité d'un autre système (CVL Brain, Agent Factory), ou être un produit distinct de Laurent.ia ?
4. Les conversations de Laurent avec CVL Brain dans Meta CVLN doivent-elles rester dans Meta CVLN, ou ce rôle d'assistant de Laurent revient-il à Laurent.ia ?
5. Les points de sécurité de KORA (§2.9) doivent être traités dans KORA. Ils ne l'ont pas été ici, conformément à la consigne de lecture seule.
