# Laurent.ia — Cadrage produit V1 (référence canonique)

> Statut : **v2 — corrigée** suite aux arbitrages de Laurent (D1–D8) · Octobre 2026
> Remplace la v1 de ce document (qui recommandait à tort un accès direct à un LLM externe et un index vectoriel cloud).
> Méthode : audit → architecture canonique → décisions → exécution. **Evidence First : aucun « fait » sans preuve.**
> Ce document prévaut sur `README.md`, `ARCHITECTURE.md` et `memory/PRD.md`, qui décrivent l'ancien produit B2C.
> La spécification exécutable de la V1 (objets, contrats, user stories, DONE/NOT DONE) est le [**Product Contract**](./LAURENTIA_V1_PRODUCT_CONTRACT.md). Il précise et, en cas d'écart, remplace les §4.2, §5 et §9 ci-dessous.

---

## 1. Ce qu'est Laurent.ia

**Laurent.ia est le Personal Intelligence OS de Laurent** : une infrastructure d'intelligence personnelle et souveraine, conçue pour Laurent en premier, avec une trajectoire vers un actif technologique externalisable.

Ce n'est **pas** :
- un SaaS B2C, un chatbot public ou un outil de croissance virale ;
- une surcouche d'un fournisseur de LLM (Anthropic, OpenAI, Google, Emergent ou autre) ;
- une IA qui « joue à être Laurent » : il n'y a pas de persona. La doctrine est une **configuration**, pas une identité.

Il doit pouvoir :
1. comprendre le contexte de Laurent ;
2. conserver une mémoire structurée et sourcée ;
3. connaître sa doctrine, ses décisions et ses systèmes ;
4. raisonner sur ses projets ;
5. préparer des décisions ;
6. utiliser ses outils ;
7. piloter des agents sous contrat ;
8. exécuter certaines actions selon ses niveaux d'autorisation ;
9. tenir un registre fiable de **ce qu'il sait, ce qu'il suppose et ce qu'il a fait**.

**Lecture « groupe mondial »** : l'avantage durable n'est pas le modèle de langage (il se remplace), c'est l'ensemble **données propriétaires + mémoire structurée + évaluations + orchestration + contrats**. C'est cet ensemble qui constitue la propriété intellectuelle et qui sera externalisable. Le modèle local est un composant substituable de cet ensemble, jusqu'au jour où il deviendra lui-même un actif (cf. §6).

---

## 2. Définition de la production et règle de souveraineté (D8)

**Production** = tout système qui traite des données réelles de Laurent, ou qui a une capacité d'action réelle sur son environnement.

**Règle** : la production est entièrement souveraine pour l'inférence et les données cognitives. **Aucun LLM externe ne reçoit de données, prompts, mémoire, documents ou contexte de production.**

**R&D isolée** : des services externes peuvent être utilisés uniquement avec des données synthétiques ou publiques, sans aucune dépendance opérationnelle de la production. Cela inclut les outils de développement (dont l'assistant de code utilisé sur ce dépôt) : **aucune donnée réelle de Laurent ne doit être versionnée dans ce dépôt ni transmise à un outil de développement.**

**Applications concrètes**
- Un « LLM externe » inclut aussi les services cognitifs indirects : reconnaissance vocale cloud, analytics avec enregistrement de session, scripts tiers capables de lire la page.
- Les serveurs d'inférence locaux (vLLM, llama.cpp, etc.) exposent souvent une API au **format** OpenAI. C'est un protocole HTTP, pas un fournisseur : c'est autorisé tant que l'hôte appelé est sur l'infrastructure de Laurent.
- La règle est **vérifiée par le code**, pas seulement écrite (cf. §7.3).

Détail complet : [`docs/decisions/D8-sovereign-local-intelligence.md`](../decisions/D8-sovereign-local-intelligence.md).

---

## 3. Audit de l'existant — fonctionnel, simulé, à désactiver

Méthode : lecture du code et recensement par recherche exhaustive (`grep`) des appels sortants. Chaque ligne cite sa preuve.
**Limite assumée** : la suite de tests (128 tests annoncés dans `memory/PRD.md`) **n'a pas encore été réexécutée** — elle dépend de `emergentintegrations`, distribué hors PyPI. La réexécuter est la première preuve exigée au Lot 0. Tout ce qui est marqué « fonctionnel » ci-dessous l'est **par lecture du code**, pas encore par exécution.

### 3.1 Violations de souveraineté actuelles (bloquantes pour toute production)

| # | Fuite | Preuve | Données exposées |
|---|---|---|---|
| S1 | Tout le raisonnement passe par Emergent → Anthropic | `backend/services/cvl_brain.py:16-28` ; appelé par `routes/laurentia_gateway.py:396`, `routes/brain.py:50` et `:67` (contrat briefing), `routes/omega.py:32`, `routes/echo.py:123`, `jobs/social_agent.py:112` | Prompts, mémoire récente, pièces jointes, contexte |
| S2 | **Enregistrement de session PostHog** (serveurs US), iframes comprises | `frontend/public/index.html:108-115` (`session_recording`, `recordCrossOriginIframes: true`) | Tout ce qui est tapé et affiché, réponses comprises |
| S3 | Script tiers Emergent chargé sur chaque page | `frontend/public/index.html:30` (`assets.emergent.sh/scripts/emergent-main.js`) | Accès complet au DOM |
| S4 | Reconnaissance vocale du navigateur | `frontend/src/hooks/useLaurentIA.js:130` (`webkitSpeechRecognition`) — sous Chrome, l'audio est transcrit sur les serveurs de Google | La voix de Laurent |
| S5 | Identité déléguée à Emergent | `frontend/src/contexts/AuthContext.jsx:70`, `backend/routes/auth.py:22` | Identité, jetons de session |
| S6 | Stripe via le SDK Emergent | `backend/routes/billing.py:17` | Hors V1 (gelé), mais empêche de retirer la dépendance Emergent tant que le module est importé |
| S7 | Polices Google chargées depuis Google | `frontend/public/index.html:8-14`, `routes/pdf_export.py:360` | Adresse IP, usage (fuite faible, à auto-héberger) |

### 3.2 Ce qui est réellement fonctionnel et utile (à conserver)

| Brique | Preuve | Rôle dans la cible |
|---|---|---|
| Gateway FastAPI + streaming SSE côté HTTP | `routes/laurentia_gateway.py` | Interface → Core |
| Chiffrement AES-256-GCM au repos | `services/crypto.py` | Memory (chiffrement) |
| Parsing PDF/DOCX/TXT/MD | `services/file_parser.py` | Knowledge (ingestion) |
| Contrat `laurentia.briefing@1.0` authentifié par clé de service dédiée, testé | `routes/brain.py:54-73`, `tests/test_briefing_contract.py` | Modèle des contrats |
| Bus d'événements + journal des incidents | `orchestrator/event_bus.py`, `orchestrator/orchestrator.py` | Evaluation / observabilité |
| Circuit breaker et décisions validate/block/modify | `orchestrator/circuit_breaker.py` | Decision / Action (embryon de validation humaine) |
| Alerte SMS OVH (fournisseur français, contenu non cognitif) | `orchestrator/sms_ovh.py` | Canal d'alerte vers Laurent |
| Planificateur cron (heure Martinique) | `jobs/reports.py` | Brief quotidien |
| Clés API hachées, révocables | `services/api_keys.py` | Contracts (clés de service) |
| Rate-limit MongoDB | `services/rate_limit_mongo.py` | Garde-fou |
| Front React : composer, bulles, rendu `<json>` (graphiques) et `<artifact>` (iframe sandbox), synthèse vocale | `frontend/src/components/laurentia/*` | Interface |

### 3.3 Ce qui est simulé ou factice (ne pas compter dessus)

| Élément | Preuve | Réalité |
|---|---|---|
| Streaming « token par token » | `services/cvl_brain.py:43-66` | Réponse complète reçue, puis découpée en mots avec une pause artificielle |
| Mémoire | `routes/laurentia_gateway.py:482-499` (`$slice: -50`), `:384-392` (troncature à 300 caractères) | Les 50 derniers échanges seulement ; **tout le reste est effacé**. Chaque message réinjecté est coupé à 300 caractères. Pas de faits, pas de décisions, pas de recherche |
| « 20 agents » | `orchestrator/agents.py` | Filtres regex et journalisation en mode observation. Aucun ne raisonne ni n'agit |
| « 10 agents CVL Brain » | `services/cvl_brain_agents.py:12-23` | Un registre statique de noms hérité de Kiltikonet, sans implémentation ici |
| Comptage de tokens | `routes/laurentia_gateway.py:410-411` | `len(texte) // 4`, une estimation |
| « Temps économisé » des rapports | `services/value_estimator.py` | Ratios fixes (5 min par requête), pas une mesure |
| Anti-jailbreak | `orchestrator/agents.py`, `services/cvl_brain_knowledge.py` §5–7 | Listes de motifs + persona de dissimulation, sans objet pour un usage personnel |
| Persona | `services/cvl_brain_knowledge.py` | Persona grand public fondée sur la dissimulation (cacher le modèle, l'infrastructure, la collecte de données) : contraire à D6 |

### 3.4 Ancien produit B2C — à désactiver, sans supprimer (D2)

Billing Stripe et tiers (`routes/billing.py`), paywall et quotas, PricingModal, Échos et landing publique (`routes/echo.py`, `pages/EchoPage.jsx`), agent social (`jobs/social_agent.py`), pipeline corpus vers S3 (`jobs/corpus_pipeline.py`), empreinte navigateur et persistance fantôme (`services/fingerprint.py`, `frontend/src/services/fingerprint.js`), mode anonyme ANON, migration ANON→FREK, rapports d'upsell, export PDF « scellé », `WhiteLabelKiller.jsx`, routes `/api/omega`.

### 3.5 MongoDB (D4) — verdict fondé sur l'audit

- **Le problème n'est pas MongoDB, c'est le schéma** : toute la mémoire d'un utilisateur tient dans un document unique, plafonné à 50 échanges (`$slice: -50`). C'est inadapté par construction.
- **MongoDB convient** à ce qu'exige la mémoire cible : documents typés (faits, décisions, engagements, actions), journal en ajout seul, index secondaires, chiffrement champ par champ déjà en place. Aucune raison solide de migrer **le stockage structuré**.
- **Correction de la v1** : la v1 proposait MongoDB **Atlas** Vector Search, un service cloud. C'est incompatible avec D8 et retiré. La recherche vectorielle sera **locale** ; le moteur (recherche vectorielle de MongoDB auto-hébergé, Qdrant, pgvector…) sera choisi au Lot 2 **sur benchmark**, pas sur préférence.

---

## 4. Architecture cible

```
                          LAURENT.IA — Personal Intelligence OS
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ Interface (PWA React)          Contracts (entrants / sortants, versionnés) │
 ├────────────────────────────────────────────────────────────────────────────┤
 │ LAURENT CORE — orchestration de la boucle, état de session, politique      │
 │   Reasoning ── planification, instruction des décisions, traçabilité       │
 │   Agents    ── agents spécialisés internes et agents externes sous contrat │
 │   Tools     ── capacités atomiques typées (lire, chercher, écrire, appeler)│
 │   Decision / Action ── READ · PROPOSE · EXECUTE, approbation, journal    │
 ├────────────────────────────────────────────────────────────────────────────┤
 │ Local LLM (interface unique, moteurs substituables, hôtes internes)        │
 │ Memory (épisodes, faits, décisions, engagements, journal des actions)      │
 │ Knowledge (doctrine, carte des systèmes, documents indexés)                │
 ├────────────────────────────────────────────────────────────────────────────┤
 │ Evaluation — jeux de tests de Laurent, benchmarks, régression, métriques   │
 └────────────────────────────────────────────────────────────────────────────┘
          │ contrats uniquement
          ▼
  CVL Brain · Agent Factory · KORA · Kiltikonet · LabelOS · systèmes CVLN
```

### 4.1 Responsabilités par couche

| Couche | Responsable de | N'est jamais responsable de | Existant réutilisé |
|---|---|---|---|
| **Laurent Core** | Boucle de traitement, routage vers les couches, état de session, application de la politique | Stocker de la connaissance ; parler directement à un système externe | `laurentia_gateway.py` (à amincir) |
| **Local LLM** | Une interface unique `generate / stream / tool_call / embed` ; adaptateurs vers moteurs locaux ; un adaptateur factice pour les tests | Tout appel vers un hôte non autorisé ; tout état métier | `cvl_brain.py` (remplacé) |
| **Memory** | Écrire et retrouver épisodes, faits, décisions, engagements, actions — chacun avec provenance et **statut épistémique** (§5) | Inventer ; écrire une décision sans validation | `crypto.py`, collections Mongo |
| **Knowledge** | Doctrine versionnée, carte des systèmes et entités, documents découpés et indexés avec citation | Les données propres des autres systèmes (lues via contrat, jamais copiées en masse) | `file_parser.py`, `cvl_brain_knowledge.py` (doctrine à réécrire) |
| **Reasoning** | Décomposer une demande, instruire une décision (options, critères, hypothèses, risques), expliciter l'incertitude | Exécuter | — (à construire) |
| **Agents** | Spécialisations internes (ex. instruction de décision, veille, rédaction) et pilotage d'agents externes **sous contrat** | Héberger les agents d'Agent Factory | `orchestrator/agents.py` → requalifié en garde-fous |
| **Tools** | Capacités atomiques, typées, déclarant leur niveau d'action | Décider seules | `file_parser`, bridges |
| **Decision / Action** | Niveaux READ · PROPOSE · EXECUTE, approbations, journal immuable de ce qui a été fait | Contourner une validation | `circuit_breaker.py`, `sms_ovh.py` |
| **Evaluation** | Jeux de tests issus des vraies tâches de Laurent, benchmark des modèles (D8), régression à chaque changement de modèle ou de prompt, métriques de qualité | — | `event_bus.py`, journaux d'incidents |
| **Contracts** | Schémas versionnés `laurentia.*`, authentification par clé de service dédiée par consommateur, tests de contrat | Exposer de la mémoire brute | `laurentia.briefing@1.0` |

### 4.2 Niveaux d'action

Trois niveaux, définis dans le [Product Contract §7](./LAURENTIA_V1_PRODUCT_CONTRACT.md) : 🟢 **READ** (automatique) · 🟡 **PROPOSE** (préparé, sans effet) · 🔴 **EXECUTE** (confirmation explicite à chaque fois en V1). Ils remplacent les niveaux L0–L3 de la version précédente de ce document.

### 4.3 Structure du code (transformation progressive, sans big bang)

```
backend/laurent/
  core/        llm/        memory/      knowledge/   reasoning/
  agents/      tools/      action/      evaluation/  contracts/
```
Les routes et services existants restent en place et sont **rebranchés couche par couche**. Chaque déplacement est un commit testé. Les modules gelés restent dans `routes/`, `jobs/`, `services/` et ne sont plus montés en mode opérateur.

---

## 5. Mémoire et connaissances

**Statut épistémique obligatoire** pour tout élément :

| Statut | Signification | Qui l'écrit |
|---|---|---|
| `known` | Fait sourcé (document, système, déclaration de Laurent) | Laurent.ia, avec source |
| `assumed` | Hypothèse ou inférence, avec raisonnement | Laurent.ia, toujours affiché comme tel |
| `decided` | Décision validée | **Laurent uniquement** |
| `done` | Action exécutée, avec résultat et preuve | Couche Action, automatiquement |

Ces quatre statuts forment le registre demandé : **ce qu'il sait / ce qu'il suppose / ce qui a été décidé / ce qu'il a fait.**

**Types d'éléments** : épisodes (conversations, chiffrées), faits (entités, attributs, relations), décisions (énoncé, options, critères, justification, hypothèses, date de revue), engagements (quoi, qui, échéance), documents (morceaux indexés avec citation), actions (journal en ajout seul).

**Principes**
- Provenance sur tout : `source`, `created_at`, `confidence`, `status`.
- Rien n'est jamais effacé silencieusement (fin du `$slice: -50`) ; l'oubli est une action explicite de Laurent, journalisée.
- Écran « Ce que Laurent.ia sait » : consulter, corriger, oublier.
- **Ces données sont l'actif d'entraînement futur** (§6) : chaque correction de Laurent est conservée, localement, comme signal de spécialisation.

---

## 6. Trajectoire du modèle — trois niveaux distincts

| Niveau | Ce que c'est | Quand | Condition d'entrée |
|---|---|---|---|
| **N1 — Open-weight local** | Un modèle publié avec ses poids, exécuté sur l'infrastructure de Laurent, sans modification. La spécialisation vient de la mémoire, des connaissances et des outils. | **V1** | Benchmark D8 réalisé (Lot 1) |
| **N2 — Spécialisation (fine-tuning)** | Adaptation d'un modèle existant (LoRA/QLoRA, puis apprentissage par préférences) sur les données de Laurent : doctrine, style, décisions, traces d'usage d'outils, corrections. Les poids adaptés sont un actif propriétaire si la licence du modèle de base le permet. | Après plusieurs mois d'usage | Jeux d'évaluation stables + volume suffisant de corrections + gain mesuré sur N1 |
| **N2+ — Pré-entraînement continu** | Poursuite de l'entraînement d'un modèle existant sur un corpus de domaine (créoles, économie de la diaspora, corpus CVLN). | Si N2 plafonne | Corpus propre, licencié, sourcé |
| **N3 — Modèle propre from scratch** | Entraîner un modèle entier depuis zéro. Coût en calcul, données et équipe d'un autre ordre de grandeur. | Horizon long, décision de groupe | Un avantage démontré qu'aucun modèle open-weight spécialisé ne peut atteindre |

**Conséquence dès la V1** : on choisit un modèle de base dont la **licence autorise la modification et l'usage commercial des dérivés** (critère éliminatoire, §8), et on construit dès maintenant les évaluations et la collecte locale des corrections. Ce sont elles qui rendent N2 possible.

---

## 7. Frontières et verrous

### 7.1 Avec les autres systèmes (D7)

**Principe** : Laurent.ia sert Laurent ; il **instruit et commande**. Les autres systèmes servent leurs produits et exécutent. Laurent.ia n'absorbe ni leur responsabilité ni leurs données : il lit ou commande **via contrat**.

**Responsabilités de CVL Brain, Agent Factory et KORA : non établies.** Ce dépôt n'en contient aucune spécification (KORA n'y apparaît nulle part ; « CVL Brain » n'y désigne qu'un wrapper LLM local et un registre de noms). Aucune intégration ne sera construite avant que leurs contrats réels aient été établis à partir de leur code ou de leur documentation.

Ce qui existe déjà, de façon vérifiable : le contrat `laurentia.briefing@1.0` (consommé par « Meta CVLN » selon `routes/brain.py:56`) et des bridges sortants vers Kiltikonet, LabelOS et Frekcore (`services/*_bridge.py`), dont les contrats sont implicites et seront formalisés.

### 7.2 Clarification des noms (D5)

`services/cvl_brain.py`, `cvl_brain_knowledge.py` et `cvl_brain_agents.py` n'ont rien à voir avec le système CVL Brain. Ils seront renommés et déplacés : `laurent/llm/`, `laurent/knowledge/doctrine`, et le registre hérité dans un module `legacy/`. Les routes `/api/brain/*` sont conservées (le contrat briefing est consommé), avec la mention qu'elles appartiennent à Laurent.ia.

### 7.3 Verrous vérifiés par le code

1. **Aucun SDK de LLM externe dans le chemin de production** : un test échoue si un module de production importe `emergentintegrations`, `anthropic`, `openai`, `google.generativeai`, `litellm` ou équivalent.
2. **Liste blanche des hôtes d'inférence** : l'adaptateur LLM refuse tout hôte non déclaré dans la liste interne ; au démarrage en `LAURENTIA_ENV=production`, le service refuse de démarrer si un adaptateur externe est configuré.
3. **Frontières entre couches** : règles d'imports vérifiées en CI (ex. `import-linter`) — `llm` n'importe pas `memory`, seuls `contracts` parlent aux systèmes externes, etc.
4. **Front sans tiers** : un test échoue si `index.html` ou le bundle référence un domaine tiers non autorisé.
5. **Réseau** (au déploiement) : filtrage sortant de l'hôte de production, seuls les hôtes autorisés sont joignables.

---

## 8. Benchmark du modèle local (D8)

**Critères** (pondérés avec Laurent avant mesure) : qualité de raisonnement · français (et créoles) · contexte long · tool calling · latence · consommation mémoire · coût d'inférence · confidentialité · possibilité de fine-tuning · licence · possibilité d'évolution vers un modèle propriétaire.

**Éliminatoires** : licence interdisant la modification ou l'usage commercial des dérivés ; impossibilité d'exécution hors ligne.

**Protocole**
1. Jeu d'évaluation construit **localement** à partir de vraies tâches de Laurent (instruction de décision, synthèse de documents, appels d'outils, rédaction en français), plus un jeu public pour comparaison.
2. Chaque candidat est servi sur l'infrastructure cible, dans la même configuration de quantification.
3. Mesures automatiques (exactitude des appels d'outils, contexte long, latence, mémoire) + notation à l'aveugle par Laurent pour la qualité.
4. Rapport chiffré versionné dans `docs/benchmarks/`. Le choix est une décision tracée, révisable à chaque nouveau modèle.

**Candidats initiaux** (liste à rafraîchir le jour du benchmark, licences à vérifier sur la version exacte) : familles Mistral (éditeur français ; certaines versions sous Apache 2.0), Qwen (plusieurs versions sous Apache 2.0), DeepSeek (certaines versions sous MIT), Llama et Gemma (licences propres à l'éditeur, avec restrictions à examiner). Les modèles open-weight de toutes origines (y compris ceux publiés par des fournisseurs cités en D8, ex. gpt-oss, Gemma) sont **autorisés** lorsqu'ils tournent localement pour enrichir le système de Laurent (**D11**).

---

## 9. Exécution — lots et preuves exigées

> Remplacé par le [Product Contract §13](./LAURENTIA_V1_PRODUCT_CONTRACT.md). Conservé ci-dessous pour mémoire.

Aucun lot n'est « terminé » sans les preuves listées. Chaque preuve est versionnée (`docs/evidence/lot-N.md` : commandes, sorties, captures).

**Lot 0 — Assainissement souverain**
- Réexécuter la suite de tests existante ; documenter ce qui passe et ce qui échoue.
- Interface `laurent/llm` + adaptateur factice pour les tests ; l'adaptateur Emergent est isolé en R&D et interdit en production.
- Mode `LAURENTIA_MODE=operator` : modules B2C non montés (§3.4), sans suppression.
- Retrait de PostHog et du script Emergent du front ; polices auto-hébergées ; reconnaissance vocale navigateur désactivée en production (synthèse vocale locale conservée).
- Renommage des modules `cvl_brain*` (D5).
- Verrous §7.3 points 1, 3 et 4.
- *Preuves* : rapport de tests avant/après ; test « aucun SDK LLM externe » vert ; test « front sans tiers » vert ; liste des routes montées en mode opérateur.
- *Note* : à l'issue du Lot 0, l'assistant n'a plus de moteur cognitif en production jusqu'au Lot 1. C'est voulu : mieux vaut aucun cerveau qu'un cerveau qui fuit.

**Lot 1 — Moteur local et évaluation**
- Infrastructure d'inférence (D9), serveur d'inférence local, adaptateur `llm/local`.
- Couche Evaluation et benchmark D8 (§8) ; choix du modèle par décision tracée.
- Streaming réel et tool calling natif via le moteur local.
- Auth locale à principal unique (remplace Emergent OAuth).
- *Preuves* : rapport de benchmark ; capture réseau montrant zéro appel sortant pendant une conversation ; test de bout en bout conversation → appel d'outil.

**Lot 2 — Mémoire et connaissances canoniques**
- Nouveau schéma (§5) avec statut épistémique et provenance ; migration des épisodes existants ; fin de l'effacement à 50 échanges.
- Recherche vectorielle locale choisie sur benchmark ; doctrine réécrite sans persona.
- Écrans « Ce que Laurent.ia sait » et « Registre des décisions ».
- *Preuves* : une décision validée en conversation est retrouvée et citée plus tard ; un élément `assumed` n'est jamais présenté comme `known` (test).

**Lot 3 — Outils, action et journal**
- Outils typés avec niveau d'action ; validation L2/L3 dans l'interface (et par SMS, réutilisation de l'existant) ; journal `done` immuable.
- *Preuves* : une action L3 est impossible sans validation (test) ; chaque action figure au journal avec son résultat.

**Lot 4 — Brief quotidien**
- Généré localement chaque matin à partir des décisions, engagements et sources connectées.
- *Preuves* : sept briefs consécutifs générés, chaque affirmation reliée à une source.

**Lot 5 — Contrats avec les systèmes du groupe**
- Établissement des contrats réels de CVL Brain, Agent Factory et KORA à partir de leur code ou documentation (D7), puis intégration une par une.
- *Preuves* : tests de contrat verts des deux côtés.

**Hors V1** : multi-tenant, SDK public, widget, découpage open-core, fine-tuning (N2), publication sociale, actions L3 automatiques.

---

## 10. Registre des décisions

| # | Décision | Statut |
|---|---|---|
| **D1** | V1 personnelle : Laurent est l'unique principal | **Validée** |
| **D2** | B2C, paywall et mécaniques virales désactivés ; rien supprimé inutilement | **Validée** |
| **D3** | Accès au modèle **local uniquement** ; aucun fournisseur de LLM externe en production (corrige la v1) | **Validée** (corrigée, cf. D8) |
| **D4** | MongoDB conservé pour la mémoire structurée (audit §3.5) ; schéma refait ; recherche vectorielle locale choisie sur benchmark | **Validée sous condition** de preuve au Lot 2 |
| **D5** | Renommer les modules `cvl_brain*` pour ne plus confondre Laurent.ia et CVL Brain | **Validée** |
| **D6** | Transparence totale envers Laurent ; confidentialité stricte envers les tiers ; pas de persona | **Validée** |
| **D7** | Aucune responsabilité de KORA, Agent Factory ou CVL Brain n'est supposée ; contrats établis avant intégration | **Validée** |
| **D8** | Sovereign Local Intelligence (§2, §8, fichier dédié) | **Validée** |
| **D9** | Infrastructure d'inférence et données : **un serveur détenu par Laurent**, pas d'hébergeur externe | **Validée** (6 oct. 2026) |
| **D10** | Licence du dépôt : la BSL 1.1 actuelle (`LICENSE.md`) décrit des offres commerciales B2C | **À revoir**, non bloquant |
| **D11–D15** | Modèles open-weight toutes origines, recherche web, contrat briefing, registres du groupe, validation du contrat | Voir [Product Contract §14](./LAURENTIA_V1_PRODUCT_CONTRACT.md) |
