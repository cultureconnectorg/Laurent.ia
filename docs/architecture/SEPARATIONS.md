# Séparations — Laurent.ia et l'écosystème CVLN

> Statut : **document de travail, non canonique**. Corrigé le 11 octobre 2026 (correctif E1) après l'[audit de réconciliation](../audit/RECONCILIATION_2026-10-11.md).
> Les règles canoniques sont dans le [registre des décisions](../decisions/REGISTER.md) (LIA-D19 à LIA-D23). En cas d'écart, **le registre prévaut** sur ce document.
>
> Statuts : **[RC]** règle canonique · **[AR]** arbitrage récent (oct. 2026), qui fait foi comme décision mais pas comme preuve historique · **[DH]** décision historique écrite · **[DL]** formulation antérieure rapportée par Laurent, absente des dépôts · **[F]** fait vérifié dans le code · **[H]** hypothèse · **[NV]** non vérifié.
>
> Sources, **sans ordre d'autorité implicite** : arbre fondateur `Foundation-Cvln` (`886ac8c`, déclaré `DECIDED` / `UNVERIFIED`) ; Meta CVLN (`7673bfc`) ; corpus CVLN iOS (`1cedf8a`), **référentiel de cohérence et de preuves, pas une autorité d'implémentation** [DH, Kiltikonet 9-10 sept.] ; code des dépôts audités ; décisions de Laurent.

---

## 1. Règles de Laurent (11 octobre 2026) [AR]

1. **Laurent.ia est la réalisation de CVLN Brain pour Laurent.** [RC][AR] — cohérent avec, mais **non établi par**, la décision du 30 mai, qui ne porte que sur le nom du moteur : « Nom technique interne : CVL Brain » [DH].
2. **CVLN Brain est le cœur silencieux du groupe** : il n'a pas d'interface propre. [RC]
3. **Laurent doit avoir son propre LLM**, avec une interface publique et une interface interne. [RC] — précisé par LIA-D20 : le moteur souverain est celui du service Brain.
4. **Les agents de CVLN Agent Factory sont les agents du groupe, et donc aussi les enfants de Laurentia.** [RC] — **interprétée fonctionnellement** par LIA-D22 [AR], qui reprend la formulation du 8 sept. [DL] : Laurentia fait circuler l'intelligence et l'action vers ces agents. **Aucune relation d'autorité ni hiérarchie n'en découle.**
5. **Meta CVLN dit ce qu'il faut** pour les rôles institutionnels, les contrats et les registres. [RC] — précisé par LIA-D19 : Meta gouverne, Brain détient la doctrine.

---

## 2. Arbre fondateur (inchangé)

[DH] Déclaré `DECIDED` / `UNVERIFIED` dans `Foundation-Cvln`. **Non modifié.** Les relations `PART_OF` sont des déclarations structurelles. Le `PART_OF` Laurentia → Agent Factory **n'est pas implémenté** [F] : Agent Factory traite Laurent.ia comme « système IA applicatif indépendant — communication par contrats API uniquement » (`seed_workforce.py:16`).

```
CVLN Foundation ─ gouvernance · vision · racine
└─ CVLN Group ─ écosystème global · portefeuille
   ├─ Meta CVLN ─ gouvernance groupe · portefeuille
   │  ├─ Infrastructures CVLN ─ FREKCORE (FREK-ID, FREK-CHAIN, formats .FK), Proof Layer, CVLN Wallet
   │  └─ Entités Métier CVLN ─ KORA (LabelOS, Factory Maker Studio), Kiltikonet, CVLN Academy
   ├─ CVLN Intelligence OS ─ système commun d'intelligence
   │  ├─ CVLN Brain ─ « Intelligence · LLM »
   │  │  └─ CVLN Agent Factory ─ « Système nerveux · agents »
   │  │     └─ Laurentia ─ « Agent · interface métier »
   │  └─ CVLN Command Center ─ supervision · pilotage
   └─ Structures & Entités ─ Culture Connect, Good Mood, Good Mood Fest, Gala Cook & Food, Academies
```

---

## 3. Les séparations

### 3.1 Fonctions et responsabilités

| Système | Fonction (LIA-D22 [AR]) | Détient (cible) | Ne détient pas | État réel |
|---|---|---|---|---|
| **CVLN Brain** | **Cognition** : cœur silencieux, sans interface | Doctrine de référence [RC LIA-D19] ; moteur souverain [RC LIA-D20] ; mémoire cognitive et conversations personnelles, avec un **espace personnel de Laurent strictement cloisonné** [RC LIA-D21] | Interface utilisateur ; gouvernance ; données métier ; état d'exécution des agents | [F] Aucun service Brain. Fragments dans Kiltikonet (origine, avril), Laurent.ia (`cvl_brain*.py`), Meta (`/brain/ask`), Agent Factory (entité « CVLN Brain », `provider_layer.py`) |
| **Laurent.ia / `laurentia`** | **Un système, deux rôles** [RC LIA-D23] : (1) instance personnelle de Laurent, par l'interface interne ; (2) **Laurentia, opérateur métier** : fait circuler l'intelligence et l'action | Interfaces interne et publique ; sessions, artefacts, rapports ; capacités publiques déclarées dans Meta | La mémoire cognitive (relève de Brain) ; la doctrine ; l'exécution des agents ; la gouvernance ; les données métier | [F] Un seul code (branche `public`) ; inférence externe ; mémoire limitée à 50 échanges |
| **CVLN Agent Factory** | **Exécution technique** | Définitions d'agents, cycle de vie, runtime, portes d'exécution ; **état d'exécution nécessaire** [RC LIA-D21] | La doctrine de référence ; la mémoire cognitive ; les conversations personnelles de Laurent (cible) | [F] Possède aujourd'hui une mémoire en couches et un chat avec Laurent (`/api/cognitive/chat`) ; à migrer selon LIA-D20 (rien n'est supprimé avant les tests) |
| **Meta CVLN** | **Gouvernance** (« pense ») | Changements officiels, identité institutionnelle, contrats, registres ; **mémoire de gouvernance** [RC LIA-D19, LIA-D21] | La cognition | [F] Gouvernance implémentée ; possède aussi un assistant LLM `/brain/ask` (débordement sur la cognition) |
| **CVLN Intelligence OS / CVLN iOS** | **Organisation documentaire** (« organise ») : référentiel de cohérence, preuves, responsabilités, contradictions [DH 9-10 sept.] | Le corpus et ses registres | L'autorité d'implémentation ; l'exécution | [F] Corpus et tests de gel ; aucun runtime d'orchestration (CONN-011) |
| **CVLN Command Center** | Supervision | La supervision | L'exécution | [NV] Distinction avec les « Command Center » de Meta et de Kiltikonet non établie (CG-C-005) |
| **KORA, Kiltikonet, Academy, FMS, LabelOS** | Entités métier | Leurs **données métier** [RC LIA-D21] | La cognition du groupe | [F] Kiltikonet consomme le briefing ; [NV] KORA n'a aucune intégration |
| **FREKCORE, Proof Layer, Wallet** | Infrastructures | Identité, provenance, JCC | — | Hors V1 |

### 3.2 Les mémoires — frontières [RC LIA-D21, AR 11 oct.]

| Mémoire | Détenteur | Contenu | Accès |
|---|---|---|---|
| **Personnelle** | **CVLN Brain**, espace personnel **cloisonné** | Conversations, préférences, décisions personnelles de Laurent | **Laurent seul**, par l'interface interne de Laurent.ia |
| **Cognitive / institutionnelle** | **CVLN Brain** | Doctrine, savoirs et apprentissages du groupe | Par contrat, selon la doctrine |
| **De gouvernance** | **Meta CVLN** | Décisions officielles, registres, preuves, historique de doctrine | Par contrat |
| **D'exécution** | **Agent Factory** | État nécessaire à l'exécution des agents | Par contrat |
| **Métier** | **Chaque entité** | Données des produits | Le propriétaire ; les autres par contrat |

**Aucun transfert automatique ni aucune copie silencieuse** entre ces mémoires [RC]. **[F]** Aujourd'hui, les conversations de Laurent sont dispersées dans Laurent.ia, Agent Factory et Meta, et aucune frontière n'est codée.

### 3.3 Les deux interfaces de Laurent.ia

| | Interface interne (instance personnelle) | Interface publique (Laurentia, opérateur métier) |
|---|---|---|
| Pour qui | Laurent | Usages métier, autres systèmes |
| Accès à l'espace personnel de Brain | **Oui** | **Jamais** |
| Actions | READ / PROPOSE / EXECUTE sous approbation de Laurent | Capacités déclarées dans Meta, avec leurs validations |
| Existant | — | `laurentia.briefing@1.0` [F], sans accès mémoire aujourd'hui |

### 3.4 Le LLM

- **Cible** [RC LIA-D8, LIA-D20] : un moteur souverain, celui du service Brain, sur l'infrastructure contrôlée par Laurent. Aucun fournisseur externe pour l'inférence de production.
- **État réel** [F] : aucun moteur souverain dans aucun dépôt. Laurent.ia, Meta, Kiltikonet et Agent Factory appellent chacun des fournisseurs externes (Emergent, Anthropic, OpenAI, Gemini). Voir le rapport de réconciliation §4.

### 3.5 Relations entre systèmes [RC LIA-D22, AR 11 oct.]

Relations **fonctionnelles et contractuelles**, sans hiérarchie ni autorité implicite :
- Laurentia → Brain : demandes de cognition ;
- Laurentia → Agent Factory : demandes d'exécution (`ExecutionPlan`, `Capability`) ;
- Agent Factory → Laurentia : résultats et événements (`Event`) ;
- Meta CVLN → tous : gouvernance, registres, validations ;
- CVLN iOS : référentiel, sans rôle d'exécution.

[F] Seules sont implémentées : Meta → Laurentia (briefing), Meta → Agent Factory (orchestration gouvernée), Kiltikonet → Laurentia (briefing). Laurentia ↔ Agent Factory : **aucune liaison** (CONN-003).

---

## 4. Noms à ne plus confondre

| Nom | Désigne |
|---|---|
| **CVLN Brain** | Le service cognitif souverain cible, cœur silencieux [RC LIA-D20] ; pas encore implémenté [F] |
| **Laurent.ia** / **`laurentia`** / **Laurentia** | Un seul système [RC LIA-D23] : **Laurent.ia** = nom produit ; **`laurentia`** = identifiant technique (base, routes, registres) ; **Laurentia** = son rôle d'opérateur métier dans les registres du groupe. Les périmètres de mémoire des deux rôles ne sont pas fusionnés |
| **`services/cvl_brain.py`** dans Laurent.ia | Le **nom technique historique** du moteur de Laurent.ia, **à ne pas renommer** [DH 30 mai]. Ce n'est pas encore le service CVLN Brain cible |
| **`cvl_brain*.py` / `brain_llm.py`** dans Kiltikonet | L'**origine historique** de CVL Brain (avril 2026) [F] |
| **`/brain/ask`** dans Meta CVLN | Assistant de Meta ; en cible, la cognition passe par Brain [RC LIA-D19, LIA-D20] |
| **« Laurentia »** dans l'architecture de KORA | [NV] Aucune intégration ; statut ouvert (LIA-D16) |
| **Meta CVLN** / **MetaCVLN** | La même autorité ; le logiciel en est l'implémentation [DH D-027] |
| **LIA-D1…LIA-D23** / **D-001…D-031** | Registre de Laurent.ia / registre de l'écosystème |

---

## 5. Conséquences pour Laurent.ia

1. **Reprendre la PR #1** (identité, capacités, état, événements, traçage) en remplaçant la délégation de l'inférence par l'interface du service Brain souverain [RC LIA-D8, LIA-D20].
2. **Séparer interface interne et interface publique**, avec un test qui prouve que l'interface publique n'atteint jamais l'espace personnel [RC LIA-D21].
3. **Conserver les identifiants et les modules historiques** pendant la transition ; documenter leurs dépendances avant toute extraction [RC LIA-D20, LIA-D23].
4. **Déclarer dans Meta CVLN** les capacités publiques de Laurentia au format `Capability` v1.0.

## 6. Questions précédentes — état

| Question | État |
|---|---|
| Laurent.ia et Laurentia : même système ? | Tranché par LIA-D23 |
| Modifier l'arbre fondateur ? | Non : arbre inchangé ; relation fonctionnelle (LIA-D22) |
| Emplacement de Brain | Tranché par LIA-D20 : service indépendant cible ; transition sans extraction préalable non testée |
