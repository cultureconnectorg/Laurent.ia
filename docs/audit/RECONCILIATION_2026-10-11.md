# Rapport de réconciliation — Architecture souveraine Laurent.ia / CVLN

> 11 octobre 2026 · Audit **en lecture seule** : aucun dépôt, aucune branche, aucune PR modifiés pendant cette phase.
> **Versé dans le dépôt par le correctif E1.** Les arbitrages A1, A2 et A3 du §6 ont depuis été tranchés par Laurent et sont enregistrés comme règles canoniques **LIA-D19, LIA-D20 et LIA-D21** dans le [registre des décisions](../decisions/REGISTER.md), qui prévaut sur ce rapport. Le corps du rapport est conservé tel qu'audité.
> Légende : **[F]** fait vérifié dans le code ou l'historique git · **[DH]** décision historique écrite (source citée) · **[DL]** décision ou formulation donnée par Laurent, absente des dépôts · **[C]** conclusion tirée des preuves · **[H]** hypothèse · **[P]** proposition nouvelle.

## Sources auditées

| Dépôt | Référence | Accès |
|---|---|---|
| `cultureconnectorg/Laurent.ia` | production `public` = `b898e19` (25 sept.) ; PR #1 `claude/patch-007-runtime-connection` = `8a8cdaa` (ouverte) ; branche de cette session `claude/elegant-carson-c07gao` = `cef8203` (non fusionnée) | lecture |
| `cultureconnectorg/Metacvln-Sept2026` | `7673bfc` (25 sept.) | lecture |
| `cultureconnectorg/Kiltikonet-Aout2026` | `4645777`, historique complet (7 587 commits, 28 févr. → 11 oct.) | lecture |
| `kora2024/Kora-app` | `48a9a4e` (main) | lecture |
| `cultureconnectorg/Cvlnagentfactory` | archive de la branche `CVLN-AGENT-FACTORY`, contenu du 15 sept. | lecture |
| `cultureconnectorg/Cvln-ios-v.1` | `1cedf8a` (branche `claude/cvln-groupe-ecosystem-qf2pj2`, 15 sept.) | lecture |
| `kimoune2025-a11y/Foundation-Cvln` | `886ac8c` (31 août) | lecture |

---

## 1. Chronologie des décisions et de leurs évolutions

| Date | Source | Énoncé | Statut |
|---|---|---|---|
| 1er avr. 2026 | Kiltikonet `6e024d0b` | Naissance de CVL Brain dans Kiltikonet (`cvl_brain.py`, agents, doctrine) | F |
| 30 mai | Kiltikonet `memory/LAURENTIA_SYSTEM_PROMPT_EMERGENT_FINAL.md` (`8f8a82ea`) | « **Nom affiché à l'utilisateur : Laurent.ia** · **Nom technique interne : CVL Brain** (héritage kiltikonet — ne pas renommer dans le code) ». Serveur et base dédiés (`laurentia-prod`, `laurentia_*`, `laurentia.cvln.com`). « Déploie une **instance IA personnelle** pour chaque utilisateur, invisiblement dérivée d'un **cerveau central** CVLN. » Le Brain de Kiltikonet est « rebranché → `LAURENTIA_API_URL` ». Le widget Kiltikonet le décrit comme « **Laurent.ia (CVL Brain externalisé)** » | DH |
| 30 mai | Laurent.ia `memory/PRD.md` v0.1 (`8179a2f`) | Même définition ; persona « Sayd (fondateur) — usage personnel intime » | DH |
| juin–juil. | Laurent.ia v1.2 | Dérive vers un SaaS grand public diaspora (abonnements, échos, persona de dissimulation) | F |
| 14 août | Kiltikonet `6ed68bc3` | Première mention d'Agent Factory | F |
| août | Agent Factory `memory/PRD.md` ; `seed_workforce.py:16` ; `external_routes.py:11` ; `core_routes.py:272` | PRD : « Sovereign Cognitive OS » de Laurent ; documents : « Laurentia = couche de présentation de la Factory ». **Code** : « Laurent.ia — Système IA applicatif **indépendant** — communication par **contrats API uniquement** » ; route `/api/laurent-ia` réservée (501) ; « CVLN Brain — couche connaissance et raisonnement stratégique (Knowledge, Doctrine, Mémoire stratégique) » | DH (le code contredit le PRD) |
| 16–19 août | Meta CVLN `registry_data.py`, `seed_data.py` | Fiche `laurentia` « Laurent.ia — Sovereign Decision Infrastructure » = **Learning Plane** (cognition, mémoire, évaluation, confiance) ; Agent Factory = Control Plane | DH |
| 31 août | Foundation-Cvln `cvlnRegistry.js` | Arbre fondateur : Intelligence OS « système commun d'intelligence » ⊃ CVLN Brain (SERVICE, « Intelligence · LLM ») ⊃ Agent Factory (PLATFORM, « système nerveux ») ⊃ **Laurentia** (AGENT, « agent · interface métier »). Statut `DECIDED` / `UNVERIFIED`. Aucune entité « Laurent.ia ». `BASELINE_DATE = 2025-06-15` (incohérent avec le commit) | DH |
| 31 août | CVLN iOS D-025, D-027 | Laurentia et Agent Factory se connectent **par contrats, jamais par absorption** ; Meta CVLN = autorité du groupe, Intelligence OS = intelligence système / orchestration, **jamais fusionnés**. Laurentia = « opérateur de l'industrie culturelle » (niveau 3), décrit à partir de l'audit du code de Laurent.ia | DH |
| **8 sept.** | Archives de Laurent | « **MetaCVLN pense, CVLN iOS organise, Agent Factory exécute, Laurentia fait circuler l'intelligence et l'action.** » | DL |
| 9–10 sept. | Kiltikonet `docs/rebuild/KILTIKONET_CVLN_IOS_REBUILD_BASELINE.md` (`2ae7bcc7`) | « **CVLN iOS est un référentiel de cohérence, preuves, responsabilités et contradictions. TARGET-ARCHITECTURE ne commande pas automatiquement l'architecture produit.** » ; correction du commit `699baf9`, qui avait transformé l'audit iOS en règles produit | DH |
| 15 sept. | CVLN iOS PATCH-007, D-030, D-031 ; Laurent.ia PR #1 | Contrat runtime côté Laurentia : capacités, identité, état, événements, traçage ; inférence déléguée au routeur d'Agent Factory. Identité déclarée : `name: "Laurentia"`, `Layer 3`, `role: "Cultural industry operator"` (reprise du registre iOS) | F |
| 20–25 sept. | Kiltikonet `ARCHITECTURE.md` v1.3.0 FROZEN (`f4dd89f5`) | Services transversaux consommés : « **AGENT FACTORY / LAURENTIA → automatisation / orchestration** » ; « consommer un service ne transfère pas sa propriété » | DH |
| 25 sept. | Meta CVLN `7673bfc` ; Laurent.ia `b898e19` | Adaptateur Meta → briefing de Laurentia aligné ; orchestration d'Agent Factory gouvernée (service ou admin) ; registre d'agents en lecture | F |
| 6–11 oct. | Cette session | Lot 1 (V1 personnelle), D8 (LLM souverain local), D9 (infrastructure contrôlée) ; 11 oct. : « Brain = cœur silencieux du groupe ; Laurent.ia = ma réalisation de Brain, mon LLM, interfaces publique et interne » | DL |

**Évolutions principales**
1. Laurent.ia passe de « CVL Brain externalisé + instance personnelle » (mai) à « SaaS grand public » (juillet), puis est décrit comme « opérateur métier » (août), et enfin recentré sur l'IA personnelle souveraine (octobre).
2. Les relations passent d'une hiérarchie déclarée (Foundation, 31 août) à une **répartition fonctionnelle** : 8 sept., puis Kiltikonet les 20-25 sept., puis le code d'Agent Factory, qui traite Laurent.ia comme système indépendant sous contrat.
3. Le statut de CVLN iOS est clarifié le 9-10 sept. : c'est un **référentiel**, pas une autorité d'implémentation.

---

## 2. Laurent.ia et Laurentia — conclusion la mieux étayée

| Dimension | Valeur | Preuves | Statut |
|---|---|---|---|
| **Nom produit** | **Laurent.ia** | « Nom affiché à l'utilisateur » (30 mai) ; nom du dépôt ; README ; Agent Factory (`Laurent.ia`) ; fiche Meta (« Laurent.ia — … ») | F / DH |
| **Identifiant technique** | **`laurentia`** | Base `laurentia-prod`, collections `laurentia_*`, routes `/api/laurentia/*`, clé de registre Meta `laurentia`, `ENT-LAURENTIA`, `LAURENTIA_API_URL` | F |
| **Nom technique interne du moteur** | **CVL Brain** (à ne pas renommer dans le code) | Prompt fondateur du 30 mai | DH |
| **Rôle 1 — instance personnelle** | Intelligence personnelle souveraine de Laurent, mémoire personnelle, interface interne | 30 mai (« instance IA personnelle », « Sayd usage personnel intime ») ; octobre (V1, D8) | DH + DL |
| **Rôle 2 — opérateur métier** | « Agent · interface métier » (Foundation), « opérateur de l'industrie culturelle » (iOS), « fait circuler l'intelligence et l'action » (8 sept.), « automatisation / orchestration » avec Agent Factory (Kiltikonet) | Foundation, iOS, 8 sept., Kiltikonet | DH + DL |
| **Implémentation** | **Une seule base de code** porte les deux rôles ; aucun dépôt ne sépare un « Laurentia » d'un « Laurent.ia » | Inventaire des 7 dépôts | F |

**[C] Conclusion.** Laurent.ia et Laurentia ne sont **ni deux systèmes**, car rien ne le prouve et un seul code existe, **ni une identité conceptuelle unique**, car leurs rôles ont des périmètres, des utilisateurs et des mémoires différents. La lecture la mieux étayée :
- **Un système** : nom produit **Laurent.ia**, identifiant technique **`laurentia`**, moteur interne historiquement appelé **CVL Brain** ;
- qui porte **deux rôles distincts** :
  - **instance personnelle de Laurent** : interne, mémoire personnelle, souveraineté absolue ;
  - **Laurentia, opérateur métier** : fait circuler l'intelligence et l'action entre les systèmes et les usages métier, via les contrats de Meta CVLN, sans accès à la mémoire personnelle.

**Incertitudes restantes**
- **[H]** Le rôle personnel était « une instance par utilisateur » en mai. Octobre le restreint à Laurent pour la V1 (le B2C est gelé). L'extension future à d'autres dirigeants est une trajectoire, pas une décision.
- **[H]** Une séparation physique future des deux rôles en deux déploiements n'est ni décidée ni exclue. Rien ne l'impose aujourd'hui.

---

## 3. Carte des systèmes, rôles, responsabilités et relations

### 3.1 Cinq fonctions à ne pas confondre

| Fonction | Système | Ce que cela recouvre | Preuves | Implémenté ? |
|---|---|---|---|---|
| **Gouvernance** (« MetaCVLN **pense** ») | Meta CVLN | Décisions du groupe, autorité, registre, 5 contrats, validations humaines, notariat, apprentissage validé par l'humain | 8 sept. ; D-027 (« Group Authority ») ; ré-audit iOS (« governance and oversight, not agent orchestration ») ; code Meta | **Oui** |
| **Cognition** | CVLN Brain | LLM, raisonnement, doctrine, mémoire institutionnelle ; « cœur silencieux », sans interface | Foundation (« Intelligence · LLM ») ; Agent Factory (« connaissance et raisonnement stratégique ») ; 11 oct. | **Non** : aucun service ; fragments dans 4 dépôts |
| **Organisation documentaire** (« CVLN iOS **organise** ») | CVLN Intelligence OS (dépôt `Cvln-ios-v.1`) | Référentiel de cohérence, preuves, responsabilités, contradictions, registres, décisions, gel vérifié par tests | 8 sept. ; 9-10 sept. ; contenu du dépôt | **Oui** (corpus et tests de gel) ; **aucun runtime d'orchestration** (CONN-011) |
| **Orchestration métier** (« Laurentia **fait circuler** ») | Laurentia (rôle 2 de Laurent.ia) | Porte les demandes vers la cognition (Brain) et l'action (Agent Factory), puis les résultats vers les personnes et les systèmes | 8 sept. ; Kiltikonet 20-25 sept. ; cible iOS (Laurentia → Brain, Laurentia → Agent Factory, PROPOSED) | **Partiel** : briefing en production ; aucune liaison vers Agent Factory |
| **Exécution technique** (« Agent Factory **exécute** ») | Agent Factory | Fabrication, cycle de vie, runtime des agents, portes d'exécution, cycles autonomes | 8 sept. ; Foundation (« système nerveux ») ; registre Meta (Control Plane) ; code | **Oui** |

**[C] « MetaCVLN pense »** désigne la pensée de gouvernance : décider, ratifier, valider. Ce n'est pas la cognition du LLM, que l'arbre fondateur attribue à Brain. Preuves : surface réelle de Meta (D-027, ré-audit) ; Foundation. Reste ouvert : qui détient la doctrine de référence (FD-001, contradiction C-002, §6).

**[C] « CVLN iOS organise »** désigne l'organisation **documentaire** : cohérence, preuves, responsabilités. Ce n'est pas une orchestration d'exécution, qui n'a d'ailleurs aucun runtime (CONN-011). Cela concilie D-027 (« orchestration commune », déclarée) et la règle du 9-10 sept.

### 3.2 Relations : voulues ou exécutées

| Relation | Voulue (source) | Exécutée aujourd'hui | Contrat à formaliser |
|---|---|---|---|
| Meta CVLN → Laurentia | Actionnement par contrat (iOS cible, retenu) | **Oui** : adaptateur → `POST /api/brain/briefing` (`laurentia.briefing@1.0`) | `Capability` v1.0 + briefing v1.0, **sans mémoire personnelle** |
| Meta CVLN → Agent Factory | Gouvernance des exécutions (iOS cible) | **Oui** : orchestration gouvernée, registre d'agents en lecture (25 sept.) | Existant, à documenter |
| Laurentia → Agent Factory | **Exécution de capacités** (8 sept. ; iOS cible PROPOSED) | **Non** (CONN-003 UNKNOWN). La PR #1 relie seulement au **routeur de modèles**, ce qui n'est pas une exécution d'agents | `ExecutionPlan` / invocation de `Capability` ; résultats en `Event` |
| Agent Factory → Laurentia | Résultats, événements | **Non** : `/api/laurent-ia` répond 501 | `Event` v1.0 via le bus signé de Meta |
| Laurentia → Brain | **Demandes de cognition** (iOS cible ; 30 mai : Brain = moteur de Laurent.ia) | **En interne au processus** : `services/cvl_brain.py`, qui appelle un fournisseur externe | API Brain : sous-ensemble de `BRAIN-API.md` (PROPOSED) |
| Agent Factory → Brain | Doctrine et raisonnement (iOS cible) | **Non** : couche fournisseurs locale (`provider_layer.py`) | API Brain |
| Kiltikonet → Laurentia | Consommation de service (Kiltikonet 20-25 sept.) | **Oui** : briefing (Kiltikonet Code) ; widget **cassé** (`/api/laurentia/me` absent) ; Laurentia → Kiltikonet (profils de membres) | À revoir (§4) |
| KORA → Laurentia | Assistant des abonnés (architecture KORA) | **Non** | Capacité publique future, hors V1 |
| Laurentia ⊂ Agent Factory | `PART_OF` (Foundation, déclaré `UNVERIFIED`) | **Non** : Agent Factory traite Laurent.ia en système indépendant | Aucun. La déclaration reste intacte dans l'arbre ; rien ne l'encode en autorité |

**[C]** Aucune hiérarchie ni autorité n'est implémentée entre Laurentia et Agent Factory, et aucune n'est requise par les contrats. La relation est **fonctionnelle et contractuelle** : D-025, le code d'Agent Factory, et Kiltikonet les 20-25 sept.

---

## 4. Violations de souveraineté et risques sur les mémoires

### 4.1 Violations de souveraineté (inférence, données cognitives)

| # | Dépôt | Chemin d'exécution | Fournisseur | Données de Laurent concernées | Preuve |
|---|---|---|---|---|---|
| V1 | Laurent.ia **production** | `services/cvl_brain.py` ← `POST /api/laurentia/query`, `/api/brain/chat-enriched`, **`POST /api/brain/briefing`** (appelé par Meta et Kiltikonet Code), `/api/omega/*`, `/api/laurentia/echo`, `jobs/social_agent.py` (cron) | Emergent → Anthropic | **Oui** : prompts, 50 derniers échanges, pièces jointes | `cvl_brain.py:16-28` |
| V2 | Laurent.ia **production** | Front : enregistrement de session **PostHog** (US) + script `assets.emergent.sh` | PostHog, Emergent | **Oui** : tout ce qui est tapé et affiché | `public:frontend/public/index.html` (corrigé **uniquement** sur la branche de cette session) |
| V3 | Laurent.ia production | Reconnaissance vocale du navigateur | Google (Chrome) | **Oui** : la voix | `useLaurentIA.js:130` |
| V4 | Laurent.ia production | Authentification Emergent | Emergent | Identité | `AuthContext.jsx:70`, `auth.py:22` |
| V5 | Laurent.ia **PR #1** (non fusionnée) | `cvln_model_router.py` → `POST /api/providers/route` d'Agent Factory ; repli local = V1 | Via Agent Factory → externes | Oui, si fusionnée | `cvln_model_router.py`, `cvl_brain.py` (PR) |
| V6 | Agent Factory | `provider_layer.routed_generate` ← `/api/cognitive/chat` (**conversations avec Laurent**) ; stratégie par défaut `quality` | Emergent → Anthropic / OpenAI / Gemini ; le repli « sovereign » est déterministe, pas un LLM | **Oui** | `provider_layer.py:17-25, 42-81` |
| V7 | Agent Factory | Front : PostHog + script Emergent | PostHog, Emergent | Oui (console d'administration de Laurent) | `frontend/public/index.html` |
| V8 | Meta CVLN | `/api/brain/ask` (historique `brain_messages`) | Emergent → Anthropic | **Oui** : questions de Laurent et contexte de gouvernance | `server.py:1478-1530` |
| V9 | Meta CVLN | Front : PostHog + script Emergent | PostHog, Emergent | Oui | `frontend/public/index.html` |
| V10 | Kiltikonet | `services/brain_llm.py` (client unique), 9 sites d'appel : `cvl_brain.py`, `server.py` ×2, `routes/brain.py`, `omega.py` ×2, `kiltikonet_code.py`, `kiltikonet_sites.py`, `ghost_profiles.py` | Anthropic direct ou via Emergent | Données métier et de membres ; code source (Kiltikonet Code) | `brain_llm.py:1-25` |
| — | KORA | **Aucun appel LLM** dans le code (`openai` / `emergentintegrations` non importés) | — | — | `grep` des imports |

**[F]** Aucun moteur souverain n'existe dans aucun dépôt : pas de poids, pas de serveur d'inférence, pas de configuration (Q-001 iOS confirmé). **L'exigence D8 n'est donc satisfaite nulle part aujourd'hui.**

### 4.2 Risques sur les mémoires

| # | Risque | Mémoires concernées | Preuve |
|---|---|---|---|
| M1 | **Mémoire personnelle dispersée** : les conversations de Laurent vivent dans trois systèmes (Laurent.ia `laurentia_memory`, Agent Factory `cognitive_conversations`, Meta `brain_messages`), et sont toutes envoyées à des LLM externes | Personnelle | V1, V6, V8 |
| M2 | **Perte silencieuse** : Laurent.ia ne garde que les 50 derniers échanges (`$slice: -50`) | Personnelle | `laurentia_gateway.py:482-499` |
| M3 | **Données métier dans le contexte de l'IA** : Laurent.ia importe identité et profil culturel des membres Kiltikonet (I4) et les injecte dans ses prompts | Métier → cognitive | `kiltikonet_bridge.py:84,122` |
| M4 | **Copie potentielle** : le pipeline corpus de Laurent.ia exporte des conversations (S3 OVH ou local) s'il est actif ; à vérifier en mode opérateur | Personnelle → externe | `jobs/corpus_pipeline.py` |
| M5 | **Interface publique** : le briefing ne lit aucune mémoire aujourd'hui (sûr), mais aucun test ne l'empêchera demain | Personnelle | `routes/brain.py:54-73` |
| M6 | **Trois mémoires sans frontière codée** : mémoire en couches validée (Agent Factory), mémoire chiffrée (Laurent.ia), preuves et doctrine (Meta) ; aucun identifiant ni contrat commun | Toutes | iOS `architecture/MEMORY.md` |

### 4.3 Tests nécessaires pour éliminer violations et risques

| Test | Garantit | Couvre |
|---|---|---|
| T1 — aucun SDK de LLM externe importé par un module de production | Aucun appel direct à un fournisseur | V1, V5 |
| T2 — liste blanche des hôtes d'inférence ; refus de démarrer en production si un fournisseur externe est configuré | Le moteur est forcément souverain | V1, V5, V6 |
| T3 — test de bout en bout avec garde réseau (sockets interdits hors liste blanche) sur `/query` et `/briefing` | Zéro sortie réseau pendant l'inférence | V1, V5 |
| T4 — front sans script tiers (modèle : `backendBoundary.test.js` de Kiltikonet) | Aucune fuite par le navigateur | V2, V7, V9 |
| T5 — l'interface publique (`/api/brain/briefing`, `/api/capabilities`) ne peut lire aucun objet de mémoire personnelle | Séparation des mémoires | M5 |
| T6 — aucune écriture en mémoire sans provenance ; aucun export de corpus en mode opérateur | Pas de copie silencieuse | M2, M4 |
| T7 — test de contrat sur chaque interface inter-systèmes (schéma et authentification par clé de service) | Pas d'accès implicite | M3, I1–I8 |

---

## 5. Architecture voulue ou architecture exécutée

| Élément | Voulu | Exécuté | Écart |
|---|---|---|---|
| Moteur LLM | Souverain, sur l'infrastructure de Laurent (D8, D9) | Externe partout ; aucun moteur souverain | Total |
| CVLN Brain | Cœur silencieux, « Intelligence · LLM », une seule frontière fournisseur (cible iOS) | Fragments dans Kiltikonet, Laurent.ia, Meta, Agent Factory ; pas de service | Total |
| Laurent.ia, rôle personnel | IA personnelle souveraine, mémoire personnelle structurée | SaaS multi-locataire, 50 échanges, persona de dissimulation | Majeur |
| Laurentia, rôle opérateur | Fait circuler intelligence et action par contrats | Briefing via Meta et Kiltikonet ; rien vers Agent Factory | Partiel |
| Agent Factory | Exécution technique | Exécution + « OS cognitif » avec mémoire et chat avec Laurent | Débordement (C6) |
| Meta CVLN | Gouvernance | Gouvernance + assistant LLM `/brain/ask` | Débordement sur la cognition |
| CVLN iOS | Référentiel documentaire | Référentiel + application de gel testée | Conforme |
| Contrats | `Capability`, `Event`, `ExecutionPlan`… ; `/api/capabilities` partout | Définis dans Meta ; implémentés côté Laurentia **dans une PR non fusionnée** | Partiel |

---

## 6. Arbitrages réellement impossibles à résoudre par les preuves

**Résolus par les preuves (je ne te les redemande pas)**
- Laurent.ia / Laurentia : un système, deux rôles (§2).
- Relations fonctionnelles et contractuelles, sans hiérarchie (§3).
- « Pense » = gouvernance ; « organise » = référentiel documentaire.
- La PR #1 est conservée ; seule sa délégation d'inférence est contraire à D8, qui n'est pas négociable.
- **Ne pas renommer `services/cvl_brain.py`** : décision du 30 mai, qui contredit ma proposition antérieure.
- CVLN iOS n'est pas une autorité d'implémentation.

> **Mise à jour E1 (11 oct. 2026).** A1 → **LIA-D19**, A2 → **LIA-D20**, A3 → **LIA-D21** : tranchés par Laurent, statut [RC]. A4 reste ouvert et non bloquant (arbre fondateur inchangé).

**Étaient ouverts au moment de l'audit : aucune preuve ne permettait de trancher**

| # | Arbitrage | Pourquoi il est ouvert | Ce que les preuves établissent déjà |
|---|---|---|---|
| A1 | **Propriétaire de la doctrine de référence** : Brain (Meta ratifie) ou Meta | FD-001 / C-002 ouverts ; trois doctrines coexistent (Meta, Agent Factory, persona Laurent.ia) | La cible iOS **propose** « Brain détient, Meta ratifie » (PROPOSED) ; Agent Factory classe la doctrine dans « CVLN Brain » |
| A2 | **Emplacement physique de Brain** | Aucune décision ; FD-001 ouvert | La **frontière** est de forme service : Foundation type SERVICE ; cible iOS « service adressable » ; « cœur silencieux » ; frontière fournisseur unique. Seul l'emplacement du code et du déploiement reste ouvert (§7) |
| A3 | **Où vivent les conversations de Laurent** avec l'assistant d'Agent Factory (`/cognitive/chat`) et celui de Meta (`/brain/ask`) | Aucune décision ; existant dans les deux | Elles relèvent de la mémoire personnelle (M1), aujourd'hui dispersée |
| A4 | **Statut de `PART_OF` (Laurentia sous Agent Factory)** dans l'arbre fondateur | Seule une décision fondatrice peut modifier l'arbre | Non implémenté, non nécessaire aux contrats. **Peut rester tel quel** sans bloquer quoi que ce soit |

---

## 7. CVLN Brain — options au regard de l'architecture cible

**Composants existants** : `brain_llm.py` (Kiltikonet, client unique) ; `cvl_brain*.py` (Laurent.ia : client, persona, registre d'agents) ; `/brain/ask` (Meta) ; `provider_layer.py` (Agent Factory : routeur, stratégies, journal des appels, repli déterministe) ; mémoire en couches validée par l'humain et registre de doctrine (Agent Factory).
**Flux d'inférence actuels** : tous externes (§4.1).
**Contraintes cibles** : cœur silencieux sans interface ; « Intelligence · LLM » ; frontière fournisseur unique ; moteur souverain sur l'infrastructure de Laurent ; mémoire institutionnelle distincte de la mémoire personnelle ; Laurent.ia est sa réalisation.

| Critère cible | (a) Module dans le dépôt Laurent.ia | (b) Service dédié | (c) Distribué avec contrat commun |
|---|---|---|---|
| Cœur silencieux, sans interface | Possible si processus séparé ; risque de couplage avec l'interface | **Naturel** | Non : quatre embarquements |
| Frontière fournisseur unique (souveraineté vérifiable) | Oui pour Laurent.ia ; les autres systèmes devraient passer par Laurent.ia | **Oui pour tout le groupe** | **Non** : quatre frontières à surveiller |
| Séparation mémoire institutionnelle / personnelle | Risque : même dépôt, même équipe, même base possible | **Forte** (processus et base distincts) | Faible |
| Fidélité historique (30 mai : « nom technique interne CVL Brain » de Laurent.ia) | **Forte** | Moyenne : extraction prévue par la cible iOS (étape 4) | Faible |
| Cohérence Foundation (Brain = SERVICE) et cible iOS | Moyenne | **Forte** | Faible |
| Coût initial | Faible | Moyen (déploiement, D9) | Faible au départ, élevé à terme |

**[C]** La cible favorise une **frontière de forme service**. L'option (a) n'est compatible que comme **étape transitoire**, à condition que Brain soit un module isolé, avec sa propre API et son propre processus, extractible sans réécriture. L'option (c) contredit l'invariant de frontière fournisseur unique et la vérifiabilité de D8. **Le choix de l'emplacement reste à toi (A2).**

---

## 8. Audit de `SEPARATIONS.md`, du Product Contract et du commit `cef8203`

### 8.1 Affirmations non prouvées ou contraires aux décisions historiques

| Ligne | Affirmation | Problème |
|---|---|---|
| 5-9 | « Sources, par ordre d'autorité : Foundation > règles de Laurent > Meta > iOS » | Ordre inventé ; iOS est un référentiel, pas une autorité (9-10 sept.) |
| 18, 85-90 | « Laurentia **commande** (`SUPERVISES`/`OPERATES`) les agents de la Factory » | Transforme une relation fonctionnelle en autorité ; contraire à D-025 et au code d'Agent Factory |
| 47 | Brain « possède le LLM souverain et son routage, la doctrine de référence » | Doctrine : ouvert (A1). Routage : aujourd'hui dans Agent Factory |
| 48 | « Laurent.ia (Laurentia) », « l'agent et l'interface de Brain » | Fusion des deux rôles sans distinction |
| 49 | Agent Factory « ne possède jamais… une conversation propre avec Laurent » | Contraire à l'existant (`/api/cognitive/chat`) ; c'est l'arbitrage ouvert A3 |
| 50 | Intelligence OS = « conteneur » | Terme inventé ; Foundation : « système commun d'intelligence » ; 9-10 sept. : référentiel |
| 53 | Les entités « consomment les capacités publiques de Laurent.ia » | Vrai pour Kiltikonet (briefing), faux pour KORA (aucune intégration) |
| 79-81 | « Brain porte le modèle » ; « Agent Factory et les autres systèmes n'ont pas leur propre LLM » | Proposition présentée comme fait ; Agent Factory, Meta et Kiltikonet ont leurs appels propres (V6, V8, V10) |
| 99 | « Laurent.ia / Laurentia : le même système » | Présomption ; voir §2 |
| 100 | « `services/cvl_brain.py` n'est pas CVLN Brain, à renommer `llm/` » | **Contraire au 30 mai** (« ne pas renommer dans le code ») |
| 101 | « CVL Brain » de Kiltikonet = « assistant local, pas CVLN Brain » | Kiltikonet est **l'origine** historique de CVL Brain (avril) |
| 102 | « Laurentia » de KORA = « capacité publique de Laurent.ia » | Non prouvé ; aucune intégration |
| 112 | « Renommer `services/cvl_brain.py` » | Même conflit avec le 30 mai |
| 118-119 | Q2 propose de modifier l'arbre ; Q3 réduit Brain à un choix de dépôt | Hors de la méthode demandée |

### 8.2 Références qui leur donnent une autorité excessive
- **Product Contract** (`cef8203`) : « Qui est quoi dans l'écosystème : voir `SEPARATIONS.md` », ce qui en fait une référence canonique.
- **Audit §9** : « Laurent.ia = Learning Plane » posé comme rôle, à partir de la seule fiche Meta.
- **Audit §10** : rôles du registre iOS pris comme définitions (« ce qui change »).
- **PR #1** : `cvln_identity.py` déclare `Layer 3` / « Cultural industry operator » d'après le registre iOS. C'est hors de cette session, mais à signaler au moment de la reprise.

### 8.3 Correctif minimal proposé (appliqué par E1, voir le registre)
1. `SEPARATIONS.md` : statut → « **PROPOSITION NON CANONIQUE — remplacée par le rapport de réconciliation** » ; retirer l'ordre d'autorité ; supprimer §3.5 et la relation « commande » ; supprimer §4 lignes 99-102 et §5 point 3 (renommage) ; requalifier §3.4 en « cible » ; renvoyer vers le rapport de réconciliation.
2. Product Contract : remplacer le renvoi à `SEPARATIONS.md` par un renvoi au rapport de réconciliation, en précisant « référence en cours de validation ».
3. Audit §9 et §10 : ajouter un encadré « Lecture corrigée » qui requalifie les rôles du registre Meta et du registre iOS en **déclarations**, avec renvoi à la règle du 9-10 sept.
4. Renommer les décisions de Laurent.ia `D1…D18` en `LIA-D1…` pour éviter la collision avec D-001…D-031.

---

## 9. Plan de correction ordonné

Aucune étape ne démarre sans ton accord. Toutes les écritures se font dans **Laurent.ia uniquement**, sur une branche, sauf mention contraire.

| Étape | Contenu | Dépend de | Critères d'acceptation | Tests et preuves |
|---|---|---|---|---|
| **E1 — Correctif documentaire** | Appliquer §8.3 ; verser ce rapport dans `docs/audit/` | Ton accord | Chaque affirmation sur les rôles porte un statut F/DH/DL/C/H/P et une source ; aucune identité fusionnée, aucune hiérarchie ajoutée, aucun renommage contraire au 30 mai | Relecture ; `grep` des formulations retirées |
| **E2 — Contrat V1 réconcilié** | Product Contract aligné : deux rôles, cinq fonctions, relations du §3.2, garanties §4.3 | E1 ; A1-A3 tranchés ou explicitement reportés | Le contrat ne cite aucun rôle sans source ; les arbitrages ouverts sont listés comme tels | Matrice de traçabilité contrat → preuves |
| **E3 — Lot 0a : base runtime** | Reprendre la PR #1 sur `public` : conserver identité, capacités, état, événements, traçage ; **retirer la délégation à des LLM externes** et la remplacer par l'interface du moteur Brain (adaptateur factice en test) ; déclarer les deux rôles dans l'identité | E2 | Tests de la PR #1 verts ; aucun chemin vers un fournisseur externe | Tests de la PR + T1, T2 |
| **E4 — Lot 0b : verrous de souveraineté** | Retrait de PostHog, du script Emergent et de la reconnaissance vocale cloud sur `public` ; gel des modules B2C ; désactivation du pipeline corpus en mode opérateur | E3 | Zéro script tiers ; zéro sortie réseau pendant une requête ; aucun export de corpus | T3, T4, T6 |
| **E5 — Séparation des interfaces et des mémoires** | Interface interne et interface publique séparées ; I4 désactivé en mode opérateur ; fin de la perte à 50 échanges | E4 | L'interface publique ne lit jamais la mémoire personnelle ; aucune donnée de membre injectée | T5, T6, T7 |
| **E6 — Moteur souverain et frontière Brain** | Infrastructure (D9), benchmark (D8), serveur d'inférence, API Brain minimale (`reason`, `route`, `memory`), selon l'emplacement choisi (A2) | A2 ; E3 | Une conversation complète sans aucun appel externe sur l'infrastructure de Laurent | Capture réseau ; rapport de benchmark |
| **E7 — Raccordement des autres systèmes** (sessions séparées, par dépôt) | Agent Factory : `provider_layer` → API Brain, `/api/providers/route` retiré du chemin d'inférence de Laurentia ; Meta : `/brain/ask` → Brain ; Kiltikonet : `brain_llm.py` → Brain ; retrait de PostHog et du script Emergent de Meta et Agent Factory ; widget Kiltikonet (I3) corrigé ; Laurentia → Agent Factory par `ExecutionPlan` | E6 ; A1 ; A3 | Chaque système n'appelle plus que Brain ; tests de contrat des deux côtés | T1-T4 dans chaque dépôt ; tests de contrat |

**Prérequis bloquant pour E3 et la suite : ton accord sur E1 et E2.**
