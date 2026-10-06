# Laurent.ia — Cadrage produit V1

> Statut : **proposition à valider** (décisions D1–D7 en §10) · Octobre 2026
> Méthode : audit → architecture canonique → décisions → exécution. Pas de reconstruction : on réutilise ce qui existe, on gèle ce qui sort du périmètre, on n'ajoute que ce qui manque.

---

## 0. Audit de l'existant (état réel du dépôt)

Le dépôt contient ~14 500 lignes (FastAPI + MongoDB + React). Ce qui a été construit est un **produit SaaS grand public multi-tenant** pour la diaspora, pas un opérateur personnel.

| Brique | État réel | Verdict V1 |
|---|---|---|
| Chat SSE (`routes/laurentia_gateway.py`) | Un appel LLM unique + system prompt + N derniers échanges. Streaming **simulé** (réponse complète découpée en mots, `services/cvl_brain.py`). | **Garder**, remplacer le moteur |
| Accès LLM | `emergentintegrations` + `EMERGENT_LLM_KEY` (proxy tiers), modèle `claude-sonnet-4-5` figé. Pas de tool use, pas de prompt caching. | **Remplacer** (dépendance fournisseur intermédiaire = risque de souveraineté) |
| Mémoire | Fenêtre glissante d'échanges, chiffrée AES-256-GCM. Aucune mémoire structurée (faits, décisions, engagements), aucune recherche. | **Garder le chiffrement**, construire la mémoire |
| « 20 agents » (`orchestrator/`) | Handlers regex/log en mode SHADOW sur un bus d'événements. Aucun ne raisonne ni n'agit. | **Requalifier** en couche d'observabilité/garde-fous, cesser de les appeler « agents » |
| Doctrine (`services/cvl_brain_knowledge.py`) | Persona grand public, centrée dissimulation (ne jamais nommer CVLN, le modèle, l'infra). | **Réécrire** pour un principal unique |
| Contrat `laurentia.briefing@1.0` (`routes/brain.py`) | Façade JSON authentifiée par clé de service dédiée, testée. | **Garder** — c'est le modèle des futurs contrats |
| Auth (Google, FREK-ID, ANON, clés API) | Multi-utilisateurs, anonymes, empreinte navigateur. | **Réduire** à un principal + clés de service |
| Billing Stripe, paywall, tiers, PDF scellé, Échos viraux, agent social, pipeline corpus, rapports d'upsell | Mécanique de croissance B2C. | **Geler** derrière flags (hors V1) |
| Front React (Composer, ChatBubble, RichContent `<json>`/`<artifact>`, voix) | Solide et réutilisable. | **Garder**, retirer les surfaces commerciales |
| Tests | 128 tests annoncés dans le PRD. **Non revérifiés** ici (dépendance `emergentintegrations` sur index privé). | À réexécuter au Lot 0 |

**Points de vigilance relevés**
1. **Identité de produit incohérente** : le PRD dit « intelligence personnelle de chaque utilisateur », le README dit « infrastructure souveraine de la diaspora », la doctrine parle à un public anonyme. Aucune version ne décrit un opérateur du fondateur.
2. **Nommage qui brouille les frontières** : dans ce dépôt, `cvl_brain.py` n'est qu'un wrapper LLM. Tant que Laurent.ia contient des modules nommés « CVL Brain », la frontière avec le vrai CVL Brain restera floue.
3. **Conformité** : (a) empreinte navigateur sans consentement — la CNIL l'assimile à un traceur soumis à consentement ; (b) la doctrine interdit de mentionner l'usage des échanges pour l'entraînement alors qu'un pipeline corpus existe — incompatible avec l'obligation d'information RGPD. Non bloquant pour un usage mono-principal, **bloquant** pour toute réouverture grand public.
4. **Souveraineté réelle vs affichée** : le cœur cognitif passe par un proxy tiers. Pour un actif stratégique, l'accès modèle doit être direct, contractuel et substituable.

---

## 1. Mission exacte

**Laurent.ia est l'opérateur cognitif propriétaire du fondateur de CVLN Group.**
Il transforme l'intention du fondateur en décisions instruites et en actions préparées ou exécutées sur l'ensemble du groupe, et il est la mémoire canonique de ces décisions.

> Voir l'ensemble. Retenir l'essentiel. Instruire la décision. Exécuter sous contrôle.

**Ce qu'il est**
- Un **chief of staff augmenté** à principal unique : briefe, instruit, rédige, arbitre les options, suit les engagements.
- Le **registre de décision** du groupe (qui a décidé quoi, pourquoi, sur quelles hypothèses, avec quel statut).
- Un **point d'orchestration** : il commande les autres systèmes du groupe via des contrats, il ne les remplace pas.

**Ce qu'il n'est pas (V1)**
- Pas un chatbot grand public, pas un SaaS à abonnement, pas un outil de croissance virale.
- Pas le cerveau partagé des produits du groupe (→ CVL Brain).
- Pas une fabrique ni un hébergeur d'agents métier (→ Agent Factory).

**Pourquoi ce choix à l'échelle groupe** : les plateformes mondiales ont presque toutes construit leur infrastructure pour un usage interne exigeant avant de l'externaliser (l'infrastructure interne d'Amazon devenue AWS). Un opérateur à principal unique, construit avec des contrats de niveau plateforme, est à la fois l'outil de pilotage du groupe et le prototype de l'actif IP qu'on pourra ensuite déployer à d'autres dirigeants (V2+ : opérateurs pour les dirigeants des filiales, puis offre externe).

**Indicateurs de réussite V1**
- Brief quotidien produit et lu chaque jour ouvré.
- 100 % des décisions structurantes consignées dans le registre, avec justification et hypothèses.
- Taux d'engagements suivis jusqu'à clôture.
- Part des livrables (notes, mails, specs, plans) acceptés sans réécriture majeure.

---

## 2. Ce qu'il sait / ne sait pas

**Il sait (couches de connaissance, par ordre de priorité)**
1. **Doctrine** : principes COEURVOLAN, prisme « groupe mondial » (holding, infrastructure, IA, propriété intellectuelle, écosystème), critères d'arbitrage (scalabilité, IP, autonomie, valeur long terme).
2. **Registre de décisions** : décisions validées, en cours, abandonnées — avec contexte et hypothèses.
3. **Carte du groupe** : entités, produits (CVLN, Kiltikonet, LabelOS, Agent Factory, CC2026…), leur état, leurs responsables, leurs dépendances.
4. **Engagements** : ce qui a été promis, à qui, pour quand.
5. **Personnes et relations** : interlocuteurs, rôles, historique d'échanges pertinents.
6. **Documents** déposés ou connectés (specs, contrats, notes, dépôts de code du groupe).

**Il ne sait pas — et le dit**
- Les données individuelles des utilisateurs des produits du groupe : il n'accède qu'à des agrégats via contrat.
- Les secrets (clés, sels, identifiants) : jamais en mémoire, jamais dans le contexte.
- Ce qui n'est pas sourcé : toute affirmation factuelle porte sa source ou est marquée **hypothèse**.

**Règle de vérité** : envers son principal, Laurent.ia est transparent sur ses sources, ses limites et le modèle utilisé. La confidentialité s'applique envers les tiers, pas envers le fondateur.

---

## 3. Mémoire et données

| Type | Contenu | Écriture | Lecture |
|---|---|---|---|
| **Épisodique** | Conversations, chiffrées (existant) | Automatique | Recherche |
| **Faits** | Entités, attributs, relations, avec source et date | Proposée par Laurent, auto-acceptée si sourcée | Recherche + injection contextuelle |
| **Décisions** | Énoncé, options, justification, hypothèses, statut, date de revue | **Validée par le fondateur** | Toujours prioritaire |
| **Engagements** | Quoi, qui, échéance, statut | Proposée, confirmée en un geste | Brief quotidien |
| **Documents** | Fichiers et sources connectées, découpés et indexés | Dépôt ou connecteur | Recherche avec citation |

**Principes**
- **Provenance obligatoire** : chaque élément porte `source`, `created_at`, `confidence`.
- **Mémoire canonique sous contrôle humain** : Laurent propose, le fondateur valide ce qui engage (décisions). Rien de structurant n'entre silencieusement.
- **Inspectable et corrigeable** : écran « Ce que Laurent sait » (consulter, corriger, oublier).
- **Stockage** : MongoDB conservé (pas de migration), nouvelles collections `lia_facts`, `lia_decisions`, `lia_commitments`, `lia_documents` ; recherche vectorielle via MongoDB Atlas Vector Search. Chiffrement AES-256-GCM existant étendu aux champs sensibles.
- **Pas d'entraînement** sur ces données en V1.

---

## 4. Agents et outils

**Un seul agent en V1 : l'opérateur.** Boucle native de tool use (raisonnement → appel d'outil → observation → réponse). Les « 20 agents » actuels deviennent la couche **garde-fous & observabilité** (détection, journalisation, alerte SMS), ce qu'ils sont réellement.

**Outils V1**

| Outil | Niveau | Rôle |
|---|---|---|
| `memory.search` / `memory.propose` | L0 / L1 | Rechercher, proposer un fait |
| `decisions.list` / `decisions.propose` | L0 / L1 | Lire le registre, proposer une décision |
| `commitments.*` | L0 / L1 | Suivre les engagements |
| `documents.search` | L0 | Rechercher dans les documents avec citation |
| `web.search` | L0 | Veille et vérification externe |
| `repos.read` | L0 | Lire les dépôts GitHub du groupe |
| `cvln.call(contract, payload)` | L1–L2 | Appeler un service du groupe via contrat versionné |

**Niveaux d'action (moteur de politique)**
- **L0 Lire** : libre.
- **L1 Préparer** (brouillon, proposition) : libre, visible.
- **L2 Exécuter réversible** (créer une tâche, déclencher un job interne) : confirmation en un geste.
- **L3 Irréversible ou externe** (envoyer, publier, payer, supprimer) : validation explicite du fondateur, toujours journalisée. Aucune exception en V1.

---

## 5. Interface

On garde le front React existant (Composer, ChatBubble, RichContent `<json>`/`<artifact>`, voix) et on change la structure :

1. **Conversation** — l'existant, avec citations de sources et affichage des actions proposées (boutons Valider / Modifier / Refuser pour L2–L3).
2. **Brief du jour** — décisions à prendre, engagements à échéance, signaux des entités, points de revue.
3. **Registre des décisions** — liste filtrable, fiche décision, statut, date de revue.
4. **Ce que Laurent sait** — inspection et correction de la mémoire.

**Retirés de la surface V1** : PricingModal, paywall, Échos, quotas, chips écosystème, mode anonyme.
**Accès** : un seul principal (Google du fondateur + liste blanche), PWA mobile, voix conservée.

---

## 6. Architecture technique

```
 Interface (React PWA)
        │
 Gateway FastAPI ── auth principal unique · clés de service inter-CVLN
        │
 Cœur opérateur ── doctrine v2 · boucle tool use · moteur de politique L0–L3
        │                         │
 Service mémoire            Couche outils / connecteurs
 (Mongo + vecteurs,          (contrats versionnés laurentia.* / cvln.*)
  chiffrement)                    │
                     CVL Brain · Agent Factory · KORA · Kiltikonet · LabelOS · GitHub
        │
 Garde-fous & observabilité (ex-orchestrateur 20 agents, SMS OVH, journaux)
```

**Choix techniques**
- **Accès modèle direct** : SDK Anthropic officiel à la place de `emergentintegrations` — streaming réel, tool use natif, prompt caching sur la doctrine. Routage : Sonnet 5.5 par défaut, Opus 5.5 pour l'instruction de décisions lourdes, Haiku 4.5 pour les tâches légères (classement, extraction mémoire). Une interface `llm/` interne rend le fournisseur substituable.
- **Contrats** : tout échange inter-systèmes passe par un contrat nommé et versionné (`laurentia.briefing@1.0` existe déjà). Schémas Pydantic, tests de contrat, clés de service dédiées par consommateur.
- **Gel B2C** : un flag `LAURENTIA_MODE=operator` désactive billing, échos, agent social, pipeline corpus, empreinte et rapports d'upsell. Code conservé, non supprimé.
- **Renommage** : `services/cvl_brain*.py` → `llm/` et `operator/` pour que « CVL Brain » désigne uniquement le système externe.
- **Conservés tels quels** : MongoDB, chiffrement, rate-limit, SMS OVH, parsing de fichiers, export PDF (sans sceau commercial).

---

## 7. Frontières avec CVL Brain / KORA / Agent Factory

**Principe** : Laurent.ia **sert une personne et instruit/commande** ; les autres systèmes **servent les produits et exécutent**. Laurent.ia ne possède jamais les données d'un autre système : il les lit ou les commande via contrat.

| Système | Rôle (compréhension actuelle) | Relation avec Laurent.ia |
|---|---|---|
| **CVL Brain** | Intelligence et connaissance partagées du groupe, au service des produits (héritage Kiltikonet). | Laurent **consomme** (lecture de connaissance groupe) et **expose** `laurentia.briefing` aux consommateurs CVLN de confiance. Pas de mémoire partagée : la mémoire du fondateur reste dans Laurent. |
| **Agent Factory** | Conception, déploiement et exécution des agents métier du groupe. | Laurent **commande** (demande de création ou d'exécution d'un agent, lecture de statut) via contrat. Il n'héberge aucun agent métier. |
| **KORA** | **À définir** — aucune trace dans ce dépôt. | Frontière à fixer dès réception d'une définition (D7). |
| **Kiltikonet / LabelOS** | Produits et sources de données. | Lecture d'agrégats via bridges existants, jamais de données individuelles. |

**Test de frontière** pour toute nouvelle fonctionnalité : *sert-elle le fondateur (→ Laurent.ia) ou un produit/ses utilisateurs (→ autre système) ?*

---

## 8. MVP réellement livrable

Livrable par lots, chacun déployable et testable seul.

**Lot 0 — Assainissement (prérequis)**
- Flag `LAURENTIA_MODE=operator`, gel des modules B2C.
- Auth principal unique.
- Réexécution de la suite de tests ; correction des régressions.
- *Terminé quand* : l'app démarre en mode opérateur, sans surface commerciale, tests verts.

**Lot 1 — Cœur opérateur**
- SDK Anthropic direct, streaming réel, boucle tool use, interface `llm/` substituable.
- Doctrine v2 (principal unique, transparence envers lui, prisme groupe mondial).
- Moteur de politique L0–L3 + journal d'actions.
- *Terminé quand* : une conversation appelle un outil, l'affiche, et une action L2 exige une confirmation.

**Lot 2 — Mémoire canonique**
- Collections faits / décisions / engagements / documents, recherche vectorielle, provenance.
- Écrans « Registre des décisions » et « Ce que Laurent sait ».
- *Terminé quand* : une décision proposée en conversation est validée, retrouvée et citée dans une conversation ultérieure.

**Lot 3 — Brief quotidien**
- Génération planifiée (réutilise le planificateur des rapports, cron Martinique) à partir des décisions, engagements et sources connectées ; écran dédié ; alerte SMS optionnelle.
- *Terminé quand* : le brief arrive chaque matin et ne contient que des éléments sourcés.

**Lot 4 — Premiers contrats**
- Contrat sortant `laurentia.decision@1.0` (lecture des décisions par les services CVLN autorisés).
- Premier connecteur entrant : dépôts GitHub du groupe en lecture.
- Gabarit de contrat sortant vers Agent Factory (stub tant que l'API n'est pas fixée).
- *Terminé quand* : un service CVLN lit une décision via contrat testé.

**Hors MVP (explicitement)** : multi-tenant, SDK public, widget, découpage open-core, fine-tuning, publication sociale, actions L3 automatiques, mail/agenda (V1.1).

---

## 9. Après la V1 (trajectoire)

1. **V1.1** — connecteurs mail et agenda, actions L3 assistées.
2. **V2** — opérateurs pour les dirigeants des entités du groupe : même cœur, mémoires isolées, registre de décisions fédéré au niveau holding.
3. **V3** — offre externe d'opérateurs pour dirigeants, une fois la conformité (consentement, information sur les données) refaite. L'existant B2C gelé devient alors un actif réutilisable, pas une dette.

---

## 10. Décisions à valider

| # | Décision | Recommandation |
|---|---|---|
| **D1** | Positionnement V1 | Opérateur à **principal unique (fondateur)**, plutôt que produit grand public par utilisateur |
| **D2** | Sort de la couche B2C | **Gel** derrière flag (ni suppression, ni maintenance active) |
| **D3** | Accès modèle | **SDK Anthropic direct** à la place du proxy Emergent |
| **D4** | Stockage | **MongoDB conservé** + recherche vectorielle Atlas (pas de migration) |
| **D5** | Nommage | Renommer les modules `cvl_brain*` internes en `llm/` et `operator/` |
| **D6** | Doctrine | Transparence totale envers le principal, confidentialité envers les tiers |
| **D7** | Frontières | Définitions officielles de **KORA** et **Agent Factory** à fournir |
