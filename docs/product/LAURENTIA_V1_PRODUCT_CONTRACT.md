# LAURENT.IA V1 — Product Contract

> Statut : **proposition — non canonique** tant que D15 n'est pas validée · révisé le 11 octobre 2026 avec l'[audit des frontières de l'écosystème](../audit/ECOSYSTEM_BOUNDARIES_AUDIT.md)
> Ce contrat est la spécification exécutable de la V1. Il s'appuie sur :
> - le cadrage produit V1 de Laurent (positionnement, 6 couches, 5 surfaces, 5 rôles, 3 niveaux d'action, 7 règles de confiance) ;
> - le cadrage canonique [`LAURENTIA_V1_CADRAGE.md`](./LAURENTIA_V1_CADRAGE.md) (audit du dépôt, souveraineté) ;
> - la décision [D8 — Sovereign Local Intelligence](../decisions/D8-sovereign-local-intelligence.md).
>
> En cas de contradiction : **D8 prévaut**, puis ce contrat, puis le cadrage.
> Aucune ligne de code n'est écrite avant validation de ce contrat.

---

## 0. Positionnement

**Laurent.ia est l'intelligence personnelle de Laurent Cœurvolan** : une couche de mémoire, de raisonnement, d'exécution et de pilotage qui connaît son contexte, respecte ses décisions et agit sous son autorité.

> **Laurent.ia ne pense pas à la place de Laurent. Il lui donne une mémoire, une vision et des mains.**

**Mission V1** : réduire le coût cognitif de Laurent sans lui retirer le contrôle.
Question directrice : *« De quoi ai-je besoin pour comprendre, décider et agir maintenant ? »*

**Chaîne** : Mémoire → Contexte → Intelligence → Décision → Action → Preuve.

**Principe fondateur** : **la mémoire appartient à Laurent.** Modèles, agents, interface et fournisseurs sont remplaçables ; la mémoire et les décisions restent.

**Ce n'est pas** : un chatbot personnalisé · un simple RAG · KORA renommé · CVL Brain sous un autre nom · un agent autonome qui peut tout faire · un clone de ChatGPT avec un nom · un SaaS multi-utilisateur.

---

## 1. Périmètre exact

### 1.1 Dans la V1

| # | Capacité | Couche | Surface |
|---|---|---|---|
| 1 | Converser avec contexte | Context + Reasoning | Chat |
| 2 | Mémoire persistante, sourcée, corrigeable | Memory | Memory |
| 3 | Recherche documentaire avec citation | Memory (documents) | Chat, Memory |
| 4 | Compréhension des projets | Memory (projets) + Context | Projects |
| 5 | Registre des décisions | Memory (décisions) | Decisions |
| 6 | Analyse / audit | Reasoning | Chat |
| 7 | Planification | Reasoning | Chat, Projects |
| 8 | Recherche web (D12, échelle de confiance) | Action (READ sortant) | Chat |
| 9 | Proposer des actions | Action (PROPOSE) | Actions |
| 10 | Exécuter avec autorisation | Action (EXECUTE) | Actions |

### 1.2 Hors V1 (explicitement)

Pas d'AGI · pas d'autonomie illimitée · pas de fine-tuning massif · pas de robotique ni de domotique · pas de marketplace d'agents · pas de réseau social · **pas de produit commercial multi-utilisateur** · pas de 50 agents · pas de matériel dédié autre que l'infrastructure d'inférence et de données · pas de remplacement de tous les outils de Laurent.

### 1.3 Contraintes non négociables

1. **Souveraineté (D8)** : aucun LLM externe ne reçoit de donnée de production. Le moteur de langage, la mémoire et le runtime tournent **sur une infrastructure contrôlée par Laurent** (D9). *Local-first* est une doctrine d'autonomie, pas une contrainte mono-machine : cette infrastructure peut compter plusieurs machines.
2. **Principal unique** : Laurent est le seul utilisateur et l'autorité finale.
3. **Evidence First** : aucune capacité n'est « DONE » sans preuve (§10).

---

## 2. Les 6 couches

| Couche | Rôle | Possède | Ne possède jamais |
|---|---|---|---|
| **L1 Identity** | Qui est Laurent : identité, rôles, valeurs, préférences, objectifs, contraintes, principes, règles personnelles | Le profil de Laurent (objets mémoire `identity`) | Une identité inventée ou une persona |
| **L2 Memory** | Le cœur du produit : épisodes, savoirs, décisions, projets, relations, préférences, avec dimension temporelle | Tous les objets mémoire et leur provenance | Les données propres des autres systèmes (référencées, jamais copiées en masse) |
| **L3 Context Engine** | « Qu'est-ce qui est pertinent maintenant ? » : assemble le contexte d'une demande | Les règles de sélection et le **paquet de contexte** | Le raisonnement final |
| **L4 Reasoning Engine** | Six modes : analyse, décision, stratégie, audit, synthèse, exécution | Les gabarits de raisonnement | Le droit d'agir |
| **L5 Action Layer** | READ / PROPOSE / EXECUTE, approbations, exécution des outils | Les manifestes d'outils, les approbations | Le droit de contourner une approbation |
| **L6 Evidence & Governance** | Pourquoi chaque réponse ; journal infalsifiable de ce qui a été su, supposé, décidé, fait | Le journal de preuve | — |

Transverses : **Model Gateway** (accès unique aux modèles locaux, §8) et **Evaluation** (mesure de la qualité et des KPI, §11).

### 2.1 Séparation des briques techniques

Les six couches produit reposent sur sept briques techniques distinctes, à ne jamais confondre :

| Brique | Définition | Propriétaire | Remplaçable |
|---|---|---|---|
| **Modèle local / moteur d'inférence** | Poids du modèle et serveur d'inférence | Infrastructure de Laurent | Oui, sur benchmark |
| **Runtime Laurent.ia** | Boucle, rôles, Context Engine, politique d'action | Laurent.ia | Évolue, reste propriété de Laurent |
| **Mémoire** | Objets mémoire, provenance, journal de preuve | **Laurent** | Non : actif durable, exportable en format ouvert |
| **Outils** | Capacités atomiques déclarées (READ / PROPOSE / EXECUTE) | Laurent.ia | Oui |
| **Agents** | Rôles internes ; agents externes sous contrat | Laurent.ia (internes) ; leurs systèmes (externes) | Oui |
| **Données métier** | Données des produits du groupe (KORA, Kiltikonet, Meta CVLN…) | Chaque système métier | Hors Laurent.ia : lues par contrat, jamais absorbées |
| **Interfaces externes** | Contrats versionnés entrants et sortants | Partagé, versionné | Oui, par version |

**Doctrine** : Laurent.ia ne dépend structurellement d'aucun LLM propriétaire externe en production. Les modèles sont des moteurs interchangeables ; la mémoire, les données, les contrats, les décisions et la gouvernance appartiennent à l'infrastructure de Laurent (D8).

---

## 3. User stories (V1)

Format : *En tant que Laurent, je veux… afin de…* — avec critère d'acceptation vérifiable.

**Chat & contexte**
- **US-01** Poser une question sur un sujet déjà connu **sans réexpliquer le contexte**. *Acceptation* : la réponse cite au moins un élément de mémoire pertinent ; le panneau « Pourquoi » liste les mémoires utilisées.
- **US-02** Demander « Est-ce que je dois lancer X maintenant ? » et obtenir une réponse construite à partir de l'état du projet, des décisions récentes, des objectifs et des contraintes. *Acceptation* : le paquet de contexte contient ces quatre catégories (ou indique explicitement qu'une catégorie est vide).
- **US-03** Choisir ou laisser choisir le mode de raisonnement (analyse, décision, stratégie, audit, synthèse, exécution). *Acceptation* : la sortie suit le gabarit du mode (§6.2).
- **US-04** Obtenir « je ne sais pas » quand l'information manque. *Acceptation* : jeu de test de questions sans réponse en mémoire → 100 % de réponses qui le disent, aucune invention.

**Mémoire**
- **US-05** Voir ce que Laurent.ia sait de moi, avec la source et la date de chaque élément. *Acceptation* : chaque élément affiche source, date, confiance, statut épistémique.
- **US-06** Corriger une mémoire. *Acceptation* : l'ancienne version est remplacée (`superseded`), consultable dans l'historique, plus jamais utilisée comme vraie.
- **US-07** Oublier une mémoire. *Acceptation* : le contenu est effacé ; la trace qu'un oubli a eu lieu reste dans le journal de preuve.
- **US-08** Voir les mémoires proposées par Laurent.ia avant qu'elles ne deviennent actives. *Acceptation* : aucune préférence, aucun élément d'identité ni aucune décision n'est actif sans ma confirmation.
- **US-09** Déposer un document et l'interroger. *Acceptation* : les réponses citent le document et le passage.

**Projets**
- **US-10** Voir une fiche projet : statut, objectif, phase, décisions, risques, questions ouvertes, prochaines actions, liens. *Acceptation* : fiche générée et maintenue à partir de la mémoire ; chaque champ renvoie à ses sources.

**Décisions**
- **US-11** Demander « Pourquoi avais-je décidé ça ? » six mois plus tard. *Acceptation* : la décision d'origine est retrouvée (question, options, analyse, justification, preuves), pas une conversation vaguement similaire.
- **US-12** Voir les décisions ouvertes, prises et à revoir. *Acceptation* : les décisions dont la date de revue est passée apparaissent dans le contexte de l'accueil.

**Actions**
- **US-13** Recevoir une proposition (mail, commit, changement) et l'approuver, la modifier ou la refuser. *Acceptation* : rien ne part sans approbation ; l'approbation porte sur le contenu exact affiché.
- **US-14** Voir l'historique des actions : proposées, autorisées, exécutées, avec leur résultat. *Acceptation* : journal complet, sans trou.
- **US-15** Voir, pour toute recherche web, la requête exacte qui sort de mon infrastructure. *Acceptation* : conforme à D12.

---

## 4. Objets de données

Identifiants : ULID (triables dans le temps). Toutes les dates en UTC ISO 8601. Champs sensibles chiffrés au repos (AES-256-GCM, existant `services/crypto.py`).

### 4.1 Enveloppe commune `MemoryItem`

| Champ | Type | Rôle |
|---|---|---|
| `id` | ULID | Identifiant |
| `kind` | `identity` · `episodic` · `semantic` · `decision` · `project` · `relationship` · `preference` · `document` | Tiroir mémoire |
| `epistemic` | `fact` · `preference` · `inference` · `hypothesis` · `decision` | **fait ≠ préférence ≠ inférence ≠ hypothèse ≠ décision** |
| `content` | objet typé selon `kind` + `text` lisible | Contenu |
| `source` | `{type, ref, excerpt}` ; `type` ∈ `laurent_statement` · `document` · `conversation` · `system_contract` · `web` · `inference` | **Provenance obligatoire** |
| `created_at` | date | Écriture |
| `valid_from` / `valid_to` | date / null | **Dimension temporelle** : ce qui était vrai à une période donnée |
| `confidence` | 0–1 | Confiance |
| `status` | `proposed` · `active` · `superseded` · `retracted` · `forgotten` | Cycle de vie |
| `last_verified_at` / `verify_after` | date | Fraîcheur ; au-delà de `verify_after`, l'élément est signalé « à vérifier » |
| `supersedes` / `superseded_by` | ULID | Historique des corrections |
| `sensitivity` | `normal` · `sensitive` · `critical` | Règles d'accès et d'affichage |
| `links` | liste d'ULID | Projets, personnes, décisions liés |

> **Choix d'architecture** : « Temporal » n'est pas un tiroir séparé mais **une dimension de chaque mémoire** (`valid_from`/`valid_to`). Cela permet de répondre à « qu'est-ce qui était vrai en mars ? » pour n'importe quel type d'objet, sans dupliquer. Ce modèle bi-temporel est celui de Graphiti (Apache-2.0).

### 4.2 Objets spécialisés

**Decision** (`kind=decision`)
`question` · `options[]` (libellé, avantages, risques) · `criteria[]` · `analysis` · `decision` · `rationale` · `assumptions[]` (ULID d'hypothèses) · `owner` · `status` (`open` · `decided` · `to_review` · `reversed`) · `decided_at` · `review_date` · `evidence[]` (ULID de preuves).

**Project** (`kind=project`)
`name` · `status` · `objective` · `current_phase` · `decisions[]` · `risks[]` · `open_questions[]` · `next_actions[]` · `related[]` (projets, systèmes, personnes) · `external_refs[]` (identifiants dans Meta CVLN ou d'autres systèmes, §9).

**Relationship** (`kind=relationship`)
`entity_type` (`person` · `organisation`) · `name` · `roles[]` · `relation_to_laurent` · `context` · `last_interaction_at`.

**Identity** (`kind=identity`)
`facet` ∈ `identity` · `role` · `value` · `preference` · `objective` · `constraint` · `principle` · `personal_rule` · `statement`.

**Episode** (`kind=episodic`)
Conversation ou événement : `session_id` · `messages[]` chiffrés · `summary` · `extracted_items[]` (propositions de mémoire issues de l'épisode).

**Document** (`kind=document`)
Fichier source + morceaux indexés (`chunk_id`, position, texte) pour la citation.

**Action** (hors mémoire, journal L5)
`id` · `tool` · `level` · `payload` · `payload_hash` · `proposed_by` (rôle d'agent) · `rationale` · `status` (`proposed` · `approved` · `rejected` · `executed` · `failed`) · `approval` (`by`, `at`, `payload_hash`) · `result` · `evidence_id`.

**EvidenceRecord** (journal L6) — cf. §7.4.

---

## 5. Memory Contract

### 5.1 Qui peut écrire quoi

| `epistemic` | Laurent.ia peut | Devient `active` |
|---|---|---|
| `fact` | Proposer, avec source vérifiable | Automatiquement si la source est un document, un contrat système ou une déclaration explicite de Laurent ; sinon après confirmation |
| `preference` | Proposer | **Uniquement après confirmation de Laurent** |
| `inference` | Écrire, avec le raisonnement et les éléments d'origine | Actif mais **toujours affiché comme inférence** |
| `hypothesis` | Écrire | Actif mais **toujours affiché comme hypothèse**, jamais présenté comme fait |
| `decision` | Proposer (brouillon de décision) | **Uniquement par Laurent** |
| tout `identity` | Proposer | **Uniquement après confirmation de Laurent** |

### 5.2 Opérations

`propose` · `confirm` · `correct` (crée une nouvelle version, l'ancienne passe `superseded`) · `retract` (l'élément était faux) · `forget` (contenu effacé, trace d'oubli conservée dans le journal) · `verify` (met à jour `last_verified_at`).
Inspiration : les opérations ADD / UPDATE / DELETE / NOOP de Mem0 (Apache-2.0), **mais sans aucune modification silencieuse** : toute opération est journalisée.

### 5.3 Garanties

1. Aucune mémoire n'est effacée automatiquement (fin du `$slice: -50` de l'existant).
2. Aucun élément `sensitive` ou `critical` n'est modifié sans autorisation.
3. Un élément `hypothesis` ou `inference` n'est jamais présenté comme `fact` (test automatisé).
4. Un élément expiré (`verify_after` dépassé) est signalé comme « à vérifier » dans toute réponse qui l'utilise.
5. La mémoire est exportable intégralement dans un format ouvert (JSON Lines) à tout moment : **c'est la garantie que la mémoire appartient à Laurent, indépendamment du logiciel.**

---

## 6. Context, Reasoning et Agent Contract

### 6.1 Context Engine

**Entrée** : la demande, la session, le mode de raisonnement.
**Sortie** : un `ContextPack`, journalisé :

| Section | Contenu |
|---|---|
| `identity` | Principes, contraintes et règles personnelles applicables |
| `projects` | Projets concernés et leur état |
| `decisions` | Décisions liées (prises, ouvertes, à revoir) |
| `memories` | Faits, préférences, inférences, hypothèses pertinents |
| `documents` | Passages cités |
| `stale` | Éléments utilisés mais à vérifier |
| `gaps` | Ce qui manque pour bien répondre |
| `selection_log` | Pourquoi chaque élément a été retenu (score, règle) |

Règle : chaque élément porte son statut épistémique jusque dans le prompt du modèle, pour que le modèle ne puisse pas confondre fait et hypothèse.

### 6.2 Modes de raisonnement

| Mode | Sortie attendue |
|---|---|
| Analyse | Situation, faits, inconnues, lecture |
| Décision | Question, options, critères, comparaison, recommandation, risques, réversibilité |
| Stratégie | Objectif, leviers, séquence, dépendances, jalons |
| Audit | Incohérences, risques, trous, preuves manquantes, priorisation |
| Synthèse | Vision exploitable en quelques points, avec sources |
| Exécution | Décision validée → actions typées (PROPOSE) |

### 6.3 Agent Contract

Les agents V1 sont des **rôles** exécutés par le même runtime et le même modèle local, avec des outils et des droits différents. Ce ne sont pas des services séparés.

| Rôle | Mission | Outils | Niveau max | Écrit en mémoire |
|---|---|---|---|---|
| **Core** | Intelligence générale, routage vers les autres rôles | Tous en lecture | PROPOSE | Propositions |
| **Researcher** | Recherche, collecte, vérification | Mémoire, documents, web (D12), lecture de dépôts | READ (+ sortant selon D12) | `fact` avec source, `hypothesis` |
| **Analyst** | Analyse, audit, comparaison | Mémoire, documents | READ | `inference`, `hypothesis` |
| **Planner** | Plans, priorités, séquençage | Mémoire, projets, décisions | PROPOSE | Brouillons de plans et de décisions |
| **Operator** | Exécution des actions autorisées | Outils EXECUTE | **EXECUTE après approbation uniquement** | Résultats d'action (journal) |

Chaque rôle déclare : `role_id` · `version` · `mission` · `allowed_tools[]` · `max_level` · `budget` (étapes, durée) · `output_schema` · `evidence_required: true`.

**Agents externes (Agent Factory et autres)** : pilotés uniquement via contrat versionné. Leur résultat entre comme `source.type = system_contract`, avec une confiance déclarée. **Un agent externe ne peut jamais déclencher une action EXECUTE au nom de Laurent.**

Plus tard (V2) : Creative, Finance, Legal, Tech, Personal, Communication.

---

## 7. Action / Permission et Evidence Contract

### 7.1 Niveaux

| Niveau | Sens | Règle V1 |
|---|---|---|
| 🟢 **READ** | Lire, analyser, rechercher, consulter | Automatique, journalisé |
| 🟡 **PROPOSE** | Préparer un mail, un commit, un changement, un plan | Automatique, visible, **sans effet** sur l'environnement |
| 🔴 **EXECUTE** | Envoyer, supprimer, déployer, modifier une base, payer, publier | **Confirmation explicite obligatoire à chaque fois** |

> « Je peux faire » ≠ « Laurent m'autorise à faire ».

### 7.2 Manifeste d'outil

Chaque outil déclare : `name` · `version` · `description` · `level` · `side_effects` · `reversible` · `data_egress` (`none` · `internal` · `external`) · `input_schema` · `output_schema`.
Format compatible **Model Context Protocol** (SDK MIT) pour que les outils et les agents d'Agent Factory puissent être branchés sans adaptateur ad hoc.

### 7.3 Règles d'approbation

1. Une approbation est **liée à l'empreinte exacte du contenu** (`payload_hash`) : si le contenu change après approbation, l'approbation est invalide.
2. Une approbation est à usage unique.
3. Tout outil avec `data_egress = external` affiche **le contenu exact qui sort** avant exécution.
4. En V1, chaque outil démarre au niveau de confiance le plus bas de l'échelle ci-dessous ; les autorisations permanentes sont hors V1.

### 7.3 bis Échelle de confiance (évolution des autorisations)

L'approbation manuelle de chaque appel est **le point de départ, pas l'état final**. Chaque outil (dont la recherche web, D12) progresse sur une échelle de confiance :

| Niveau | Comportement | Exemple : recherche web |
|---|---|---|
| **T0 — Approbation à chaque fois** | Laurent voit et approuve chaque appel | Chaque requête est affichée et approuvée (V1) |
| **T1 — Automatique dans un périmètre** | Automatique pour les appels qui respectent des règles déclarées ; le reste repasse en T0 | Automatique si la requête ne contient ni nom de personne, ni entité marquée `sensitive`, ni extrait de mémoire |
| **T2 — Autorisation permanente** | Automatique dans un périmètre élargi, limitée en durée, avec relevé périodique | Automatique sur des sujets ou domaines autorisés, avec relevé quotidien des requêtes parties |

**Règles de l'échelle**
- Une promotion est **proposée** par Laurent.ia sur la base de preuves (ex. N approbations consécutives sans modification, zéro incident) et **décidée par Laurent**. Rien ne monte automatiquement.
- Toute autorisation est limitée en portée et en durée, et révocable à tout moment.
- Un incident (refus a posteriori, fuite détectée, erreur) **rétrograde** immédiatement l'outil en T0.
- Les actions EXECUTE irréversibles (payer, supprimer, publier, envoyer à un tiers) restent en T0 en V1 et V1.1.
- Chaque appel reste journalisé, quel que soit le niveau.

### 7.4 Evidence Contract

Toute réponse importante porte un bloc **POURQUOI** :

```
POURQUOI
├── Sources           (documents, systèmes, web — avec lien)
├── Mémoires utilisées (id + statut épistémique)
├── Décisions concernées
├── Hypothèses
├── Niveau de confiance
└── Actions proposées
```

Trois réponses légitimes : *« Je pense X parce que A + B + C »* · *« Je ne sais pas »* · *« Cette information date de … et devrait être vérifiée »*.

**Journal de preuve** (`EvidenceRecord`) : `id` · `at` · `type` (`answer` · `memory_op` · `action` · `approval` · `contract_call` · `model_call`) · `actor` · `inputs_ref` · `outputs_ref` · `model` (nom, version, empreinte des poids) · `context_pack_id` · `prev_hash` · `hash`.
En ajout seul, chaîné par SHA-256 (même principe que la chaîne de confiance de Meta CVLN). La signature Ed25519 et l'ancrage via Meta CVLN sont prévus en V2.

### 7.5 Contrat de confiance — et comment il est garanti

| Règle | Garantie technique |
|---|---|
| 1. Ne prétend jamais savoir ce qu'il ne sait pas | Jeu de test « questions sans réponse » ; obligation de `gaps` dans le ContextPack |
| 2. Distingue mémoire, inférence et hypothèse | Champ `epistemic` obligatoire, propagé jusqu'au prompt et à l'affichage ; test |
| 3. Montre la provenance quand elle compte | Bloc POURQUOI ; `source` obligatoire |
| 4. Ne modifie jamais une donnée critique sans autorisation | `sensitivity=critical` → EXECUTE ; test |
| 5. Ne supprime jamais une mémoire importante silencieusement | Aucun effacement automatique ; toute opération journalisée |
| 6. Laurent peut corriger ou oublier | Opérations `correct` et `forget` exposées dans la surface Memory |
| 7. Laurent reste l'autorité finale | Décisions, préférences, identité et EXECUTE réservés à Laurent |

---

## 8. Architecture et stack

### 8.1 Architecture

```
                    ┌───────────────┐
                    │   Laurent UI  │  Chat · Memory · Projects · Decisions · Actions
                    └───────┬───────┘
                       Gateway API      (auth principal unique · contrats entrants)
                            │
                  ┌─────────▼─────────┐
                  │  Laurent Runtime  │  boucle, rôles, modes
                  └─────────┬─────────┘
            ┌───────────────┼────────────────┐
            ▼               ▼                ▼
      Context Engine   Agent Engine     Action Engine
            └───────────────┼────────────────┘
                            ▼
      Model Gateway (local)     MEMORY LAYER (DB · Search · Files)
                            ▼
                      Evidence Log  ·  Evaluation
```

### 8.2 Structure du dépôt

```
backend/laurent/
  identity/    memory/     context/    reasoning/   agents/
  actions/     evidence/   models/     evaluation/  contracts/   runtime/
```
Transformation progressive de l'existant (cadrage §3) : chaque brique conservée est déplacée ou rebranchée par un commit testé ; les modules B2C restent dans `routes/`, `jobs/`, `services/`, non montés.

### 8.3 Stack candidate — sur l'infrastructure de Laurent

Le choix final se fait **sur benchmark**, pas sur préférence. Licences relevées sur PyPI le 6 octobre 2026 (licence du paquet ; celle du serveur, si distincte, est à confirmer à l'adoption).

| Besoin | Candidats | Licence relevée | Statut |
|---|---|---|---|
| Inférence GPU | vLLM | Apache-2.0 | Candidat principal |
| Inférence CPU / dev | llama.cpp (`llama-cpp-python`), Ollama | MIT, MIT | Candidats |
| Modèles | Open-weight, **toutes origines** (D11), benchmark D8 | Selon modèle (critère éliminatoire) | À benchmarker (Lot 1) |
| Objets mémoire, journal | **MongoDB** (existant, D4) | — | Retenu sous condition de preuve |
| Recherche plein texte + vectorielle | Meilisearch, Qdrant, recherche vectorielle MongoDB auto-hébergée | MIT (client), Apache-2.0 (client), — | À benchmarker (Lot 2) |
| Fichiers | Volume chiffré local | — | Retenu |
| Recherche web | SearXNG auto-hébergé | À confirmer | Sous condition D12 |
| Protocole outils / agents | Model Context Protocol | MIT (SDK Python) | Retenu |
| Mémoire temporelle (référence) | Graphiti | Apache-2.0 | Modèle de conception, pas une dépendance |
| Mémoire agentique (référence) | Letta, Mem0 | Apache-2.0, Apache-2.0 | Modèles de conception, pas des dépendances |
| Accès distant (mobile) | WireGuard | — | Candidat |
| Voix (V1.1) | Transcription et synthèse locales | À benchmarker | V1.1 |

**Interfaces de référence étudiées, non adoptées telles quelles** : Open WebUI (licence propre à l'éditeur, avec clause de marque) et LibreChat. Laurent.ia garde son front React existant ; on reprend des modèles d'interface, pas le code.

---

## 9. Frontières avec les systèmes du groupe

Source : [audit des frontières de l'écosystème](../audit/ECOSYSTEM_BOUNDARIES_AUDIT.md) (lecture seule, aucun dépôt modifié). Une version précédente de ce contrat affirmait que KORA n'avait ni dépôt ni API : **c'était faux** (cf. audit §0).

### 9.1 Principe

Laurent.ia est la couche personnelle qui comprend et pilote les autres systèmes. **Aucune fusion** : chaque système garde sa mission, ses données et ses frontières. Toute relation passe par un **contrat d'interface** versionné.

### 9.2 Matrice des systèmes (résumé ; détail et preuves dans l'audit §4)

| Système | Mission | Données qu'il possède | Intelligence | Utilisateurs | Relation avec Laurent.ia |
|---|---|---|---|---|---|
| **Laurent.ia** | Intelligence personnelle de Laurent | **Mémoire personnelle de Laurent** | Modèle open-weight local | Laurent seul | — |
| **KORA** (`kora2024/Kora-app`) | DSP culturel souverain (musique + audiovisuel) | Catalogue, abonnés, écoutes, droits, royalties | Aucun LLM dans le code ; recommandation heuristique ; moteur CVE | Abonnés, créateurs, partenaires | **Aucune dans le code** ; son architecture cible prévoit « Laurentia » comme assistant de ses abonnés (D16) |
| **CVL Brain** | Nom des modules d'IA de plusieurs produits (Kiltikonet, Meta CVLN) | `brain_messages` (Meta CVLN) | Claude via Anthropic ou Emergent | Équipes des produits hôtes | Pas d'API propre ; confusion de nom (D5) |
| **Agent Factory** (`frekcore/CVLNAgentfactory`) | Création et orchestration d'agents (selon ses consommateurs) | **Non vérifié** | **Non vérifié** | Produits du groupe, CI | **Aucune dans le code observé** ; dépôt inaccessible |
| **Meta CVLN** | Système d'exploitation interne du groupe | Décisions, projets, personnes, objectifs, preuves **du groupe** | CVL Brain (Claude) | Équipe CVLN | Consomme `laurentia.briefing@1.0` (I1) ; registre obsolète (I8) |
| **Kiltikonet** | Réseau culturel (FREK-ID, badges, jetons, territoires) | Membres, profils culturels | CVL Brain (Claude) | Membres, opérateurs | Interfaces I2, I3, I4 |

### 9.3 Interfaces existantes — toutes conservées en l'état en attendant D13

| # | Sens | Interface | Ce qu'elle fait réellement | État |
|---|---|---|---|---|
| I1 | Meta CVLN → Laurent.ia | `POST /api/brain/briefing` | Briefing à la demande d'un utilisateur Meta CVLN | Déclarée « working » |
| I2 | Kiltikonet → Laurent.ia | `POST /api/brain/briefing`, `GET /api/brain/health` | Utilise Laurent.ia comme **moteur LLM générique** pour la génération de code de Kiltikonet | En place si configurée |
| I3 | Kiltikonet → Laurent.ia | `GET /api/laurentia/me` | Widget « intelligence personnelle » de chaque membre | **Cassée** : route absente de Laurent.ia |
| I4 | Laurent.ia → Kiltikonet | `GET /api/users/validate/{frek_id}`, `/profile` | Fait entrer identité et profil culturel de membres dans Laurent.ia | En place |
| I5 | Laurent.ia → FrekCore | Validation FREK-ID | Authentification des utilisateurs B2C | En place |
| I6 | Laurent.ia → LabelOS | Contexte artiste | Enrichissement B2C | Stub |
| I7 | KORA → Laurent.ia | — | Aucune | Prévue dans un document seulement |
| I8 | Registre Meta CVLN | Fiche de Laurent.ia | Décrit l'ancien produit B2C | Obsolète |

Constat : **aucune interface ne touche aujourd'hui une mémoire personnelle de Laurent**, et aucune ne correspond au rôle d'intelligence personnelle. Elles relèvent de trois rôles différents : service LLM partagé (I1, I2), produit par membre (I3–I6), assistant d'abonnés envisagé (I7).

### 9.4 Propriété des données (D14, vérifiée)

| Domaine | Propriétaire | Règle |
|---|---|---|
| Mémoire personnelle de Laurent | **Laurent.ia** | Propriétaire unique ; n'existe pas encore |
| Décisions, projets, personnes, preuves **du groupe** | **Meta CVLN** (collections existantes) | Canonique dans Meta CVLN ; Laurent.ia garde la vue de Laurent et référence les objets du groupe par identifiant (`external_refs`), lus par contrat |
| Catalogue, abonnés, écoutes, droits | **KORA** | Lecture d'agrégats via l'API de KORA sous contrat ; aucune copie |
| Membres et profils culturels | **Kiltikonet** | Pas d'import de données de membres dans la V1 personnelle |
| Identité, preuve d'existence, `.fk` | **FrekCore** | Hors V1 |
| Agents, missions, capacités | **Agent Factory** | À établir après lecture de son code |

**Doublon réel identifié** : le Decision Engine et les fiches projet de Laurent.ia recouvrent les collections `decisions` et `projects` de Meta CVLN. La règle ci-dessus l'évite : une décision **du groupe** vit dans Meta CVLN ; une décision **de Laurent** (personnelle, ou sa position avant arbitrage du groupe) vit dans Laurent.ia, avec un lien vers l'objet du groupe s'il existe.

### 9.5 Contraintes d'accès ouvertes

- `frekcore/CVLNAgentfactory` : **inaccessible** depuis la session. Les frontières avec Agent Factory ne sont pas fixées ; rien n'est supposé à la place.
- `cultureconnectorg/KORA` : **inaccessible**. S'il diffère de `kora2024/Kora-app`, il n'est pas couvert.

## 10. Critères DONE / NOT DONE

**Une capacité est DONE si et seulement si** :
1. un test automatisé couvre son critère d'acceptation (§3) et passe ;
2. une preuve est versionnée dans `docs/evidence/` (commande, sortie, capture) ;
3. elle fonctionne **sur l'infrastructure de Laurent avec le modèle local** ;
4. une capture réseau montre **zéro appel sortant non déclaré** pendant son exécution ;
5. ses réponses portent le bloc POURQUOI quand elles sont importantes.

**Elle est NOT DONE si** : elle ne fonctionne qu'avec un modèle factice ou externe · elle produit des mémoires sans provenance · elle peut agir sans approbation · elle n'a été vérifiée que « à la main » sans trace · son test dépend d'un service en ligne.

---

## 11. KPI

| Rang | KPI | Mesure |
|---|---|---|
| **1** | **Combien de fois Laurent doit-il réexpliquer son contexte ?** — objectif V1 : presque jamais pour les sujets connus | Bouton « je l'ai déjà dit » dans le Chat + détection des répétitions de faits déjà en mémoire ; compteur hebdomadaire |
| 2 | Combien de décisions importantes Laurent.ia retrouve correctement ? | Jeu d'évaluation « Pourquoi avais-je décidé X ? » rejoué à chaque changement de modèle ; taux de rappel exact |
| 3 | Combien d'actions préparées sont réellement utiles ? | Taux d'approbation sans modification / avec modification / refus |

Non pilotés : nombre de conversations, tokens, nombre d'agents, nombre de fonctionnalités.

---

## 12. Matrice V1 / V1.1 / V2

| Domaine | V1 | V1.1 | V2 |
|---|---|---|---|
| Modèle | Open-weight local choisi sur benchmark | Routage multi-modèles locaux | Fine-tuning sur les données de Laurent (N2) |
| Mémoire | 6 couches, provenance, temporalité, corriger / oublier | Extraction automatique plus fine, déduplication | Graphe de connaissances, raisonnement temporel |
| Contexte | ContextPack journalisé | Contexte proactif (accueil) | Brief quotidien et alertes |
| Agents | 5 rôles | Agents externes Agent Factory sous contrat | Rôles spécialisés (finance, juridique, tech…) |
| Actions | READ / PROPOSE / EXECUTE avec approbation à chaque fois | Autorisations permanentes limitées et révocables | Exécution planifiée |
| Preuve | Journal chaîné SHA-256 | Export de preuve | Signature Ed25519, ancrage Meta CVLN |
| Interface | 5 surfaces, web PWA | Voix locale, mobile via WireGuard | — |
| Intégrations | Lecture de dépôts GitHub du groupe ; interfaces existantes inchangées tant que D13 n'est pas tranchée | Meta CVLN (décisions et projets du groupe, lecture par contrat) | Agent Factory (après audit de son code), KORA (agrégats via son API, si contrat) |
| Produit | Laurent uniquement | — | Trajectoire d'externalisation (opérateurs pour dirigeants) |

---

## 13. Plan d'exécution (après validation de ce contrat)

| Lot | Contenu | Preuves de fin |
|---|---|---|
| **0 — Assainissement** | Tests existants réexécutés ; mode opérateur ; modules B2C non montés ; retrait PostHog, script Emergent et reconnaissance vocale cloud ; renommage `cvl_brain*` ; verrous anti-LLM externe | Rapport de tests avant/après ; tests de verrous verts |
| **1 — Runtime local + évaluation** | Model Gateway, inférence sur ton infrastructure, benchmark D8, streaming réel, tool calling, auth locale | Rapport de benchmark ; capture réseau sans sortie |
| **2 — Memory + Identity** | Objets §4, Memory Contract §5, surface Memory, export JSONL, benchmark recherche | Tests §5.3 ; US-05 à US-09 |
| **3 — Context + Reasoning + Projects + Decisions** | ContextPack, 6 modes, surfaces Projects et Decisions | US-01 à US-04, US-10 à US-12 |
| **4 — Actions + Evidence** | Manifestes, approbations liées à l'empreinte, journal chaîné, surface Actions, bloc POURQUOI | US-13, US-14 ; test « aucune exécution sans approbation » |
| **5 — Agents + Web** | 5 rôles, recherche web selon D12 | US-15 ; jeux d'évaluation par rôle |
| **6 — Contrats groupe** | Selon D13 et D14 | Tests de contrat des deux côtés |

---

## 14. Décisions

| # | Décision | Statut |
|---|---|---|
| D1–D8 | Cf. cadrage §10 | Validées |
| **D9** | Inférence, mémoire et runtime sur **une infrastructure contrôlée par Laurent** (une ou plusieurs machines), pas d'hébergeur externe | **Validée** (6 oct. 2026, précisée le 11 oct. : local-first ≠ mono-machine) |
| **D11** | Les modèles open-weight de **toutes origines** sont autorisés lorsqu'ils tournent localement pour enrichir le système de Laurent ; ils restent soumis au benchmark D8 | **Validée** (6 oct. 2026) |
| **D12** | Recherche web : SearXNG sur l'infrastructure de Laurent ; seule la requête sort, jamais la mémoire ni les documents ; approbation de chaque requête au départ (T0), puis évolution sur l'**échelle de confiance** du §7.3 bis | **Validée** (11 oct. 2026) |
| **D13** | Interfaces existantes (I1–I8, §9.3) : **rien n'est retiré**. Cartographie faite ; décision à prendre interface par interface (maintenir, adapter, remplacer ou supprimer). Garde-fou immédiat : aucune ne doit jamais accéder à la mémoire personnelle de Laurent | **Cartographie faite — décision à prendre** |
| **D14** | Laurent.ia possède la mémoire personnelle de Laurent ; chaque système métier garde ses données ; pas de duplication arbitraire (règles §9.4) | **Validée sur le principe** ; frontières vérifiées sauf Agent Factory (accès) |
| **D15** | Ce Product Contract devient la spécification V1 canonique ; aucun code avant sa validation | **En attente** : audit d'Agent Factory requis |
| **D16** | Le « Laurentia » prévu par l'architecture de KORA (assistant de ses abonnés) n'est pas Laurent.ia : renommer ce rôle, le confier à un autre système, ou en faire un produit distinct | **À trancher** |
| **D17** | Les conversations de Laurent avec CVL Brain dans Meta CVLN restent-elles dans Meta CVLN, ou ce rôle d'assistant de Laurent revient-il à Laurent.ia ? | **À trancher** |
