# Séparations canoniques — Laurent.ia et l'écosystème CVLN

> Statut : **proposition à valider par Laurent** · 11 octobre 2026
> But : une seule réponse, sans ambiguïté, à « qui est quoi, qui possède quoi, qui parle à qui ».
> Sources, par ordre d'autorité :
> 1. **Arbre fondateur** — `kimoune2025-a11y/Foundation-Cvln`, `lib/registry/cvlnRegistry.js` (commit `886ac8c`, gelé, « préservé à l'identique ») ;
> 2. **Règles données par Laurent** le 11 octobre 2026 (§1) ;
> 3. **Meta CVLN** (`Metacvln-Sept2026`, `7673bfc`) pour les contrats et le registre opérationnel ;
> 4. **Doctrine CVLN Intelligence OS** (`Cvln-ios-v.1`, `1cedf8a`) pour les décisions d'architecture déjà prises.

---

## 1. Règles de Laurent (11 octobre 2026)

1. **Laurent.ia est la réalisation de CVLN Brain pour Laurent.**
2. **CVLN Brain est le cœur silencieux du groupe** : il n'a pas d'interface propre.
3. **Laurent doit avoir son propre LLM** : c'est ce qu'est Laurent.ia, avec une **interface publique** et une **interface interne**.
4. **Les agents de CVLN Agent Factory sont les agents du groupe**, et donc aussi **les enfants de Laurentia**.
5. **Meta CVLN dit ce qu'il faut** pour les rôles et les contrats.

---

## 2. Arbre fondateur (inchangé)

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

### 3.1 Tableau de référence

| Système | Ce qu'il est | Interface | Possède | Ne possède jamais | Relation avec Laurent.ia |
|---|---|---|---|---|---|
| **CVLN Brain** | **Le cœur silencieux** de l'intelligence du groupe : modèles de langage, doctrine, mémoire institutionnelle, raisonnement | **Aucune** (service interne, appelé par contrat) | Le LLM souverain et son routage, la doctrine de référence, la mémoire **institutionnelle** du groupe | Une interface utilisateur ; la mémoire personnelle de Laurent ; les données métier des produits | Laurent.ia en est la **réalisation** pour Laurent : il s'appuie sur Brain et lui donne une voix |
| **Laurent.ia** (Laurentia) | **Le LLM de Laurent rendu utilisable** : l'agent et l'interface de Brain | **Interne** (Laurent) **et publique** (usages métier, autres systèmes via contrats) | La **mémoire personnelle** de Laurent, ses décisions personnelles, son contexte, ses conversations ; les sessions, artefacts et rapports | La doctrine de groupe (Brain), l'exécution des agents (Agent Factory), la gouvernance (Meta CVLN), les données métier des produits | — |
| **CVLN Agent Factory** | Le **système nerveux** : fabrique, compose et exécute **les agents du groupe** | Console d'administration | Les définitions d'agents (ADL), leur cycle de vie, leur runtime, leurs portes d'exécution | La doctrine de groupe, la mémoire personnelle de Laurent, une conversation propre avec Laurent | Ses agents sont **les enfants de Laurentia** : Laurent.ia les commande par contrat |
| **CVLN Intelligence OS** | Le **conteneur** commun d'intelligence (Brain, Agent Factory, Laurentia, Command Center) | Aucune propre | L'orchestration commune entre ses membres | Les responsabilités de Meta CVLN (D-027 : jamais fusionnés) | Laurent.ia en fait partie |
| **CVLN Command Center** | La tour de contrôle : supervision et pilotage | Tableau de bord | La supervision | L'exécution | Supervise, ne commande pas |
| **Meta CVLN** | L'**autorité** du groupe : gouvernance, registre, contrats, notariat, validations humaines | Console de gouvernance | Le registre des systèmes, les 5 contrats, les décisions et projets **du groupe** | L'exécution, l'intelligence système | Laurent.ia s'y déclare et y expose ses capacités au format `Capability` v1.0 |
| **KORA, Kiltikonet, Academy, FMS, LabelOS** | Les **entités métier** | Leurs produits | Leurs **données métier** | L'intelligence du groupe | Consomment les capacités publiques de Laurent.ia par contrat, sans accès à la mémoire personnelle |
| **FREKCORE, Proof Layer, Wallet** | Les **infrastructures** : identité, preuve, valeur | Leurs API | Identité, provenance, JCC | — | Fournisseurs de services pour Laurent.ia |

### 3.2 Les trois mémoires — à ne jamais mélanger

| Mémoire | Propriétaire | Contenu | Qui y accède |
|---|---|---|---|
| **Personnelle** | **Laurent.ia** (interface interne) | Identité, préférences, décisions personnelles, conversations de Laurent | **Laurent seul** |
| **Institutionnelle** | **CVLN Brain** | Doctrine, savoirs et apprentissages du groupe | Les systèmes de l'Intelligence OS, par contrat |
| **Métier** | **Chaque entité** (KORA, Kiltikonet…) ; **Meta CVLN** pour la gouvernance | Données des produits ; décisions et projets du groupe | Le propriétaire ; les autres par contrat |

Passage d'une mémoire à l'autre : **jamais par copie silencieuse**. Uniquement par contrat, avec trace, et validation de Laurent quand une donnée personnelle est en jeu.

### 3.3 Les deux interfaces de Laurent.ia

| | Interface interne | Interface publique |
|---|---|---|
| Pour qui | Laurent | Usages métier, utilisateurs des entités, autres systèmes |
| Accès à la mémoire personnelle | **Oui** | **Jamais** |
| Accès à la mémoire institutionnelle (Brain) | Oui | Selon le contrat de la capacité |
| Actions | READ / PROPOSE / EXECUTE sous approbation de Laurent | Capacités déclarées dans Meta CVLN uniquement, avec leurs validations humaines |
| Exemple existant | — | Contrat `laurentia.briefing@1.0` |

### 3.4 Le LLM

- **Il y a un LLM souverain, celui de Laurent** : un modèle open-weight exécuté sur l'infrastructure contrôlée par Laurent (D8), spécialisable puis entraînable (trajectoire N1 → N3).
- **CVLN Brain en est le moteur silencieux** : c'est lui qui porte le modèle, son routage et la doctrine.
- **Laurent.ia en est la voix** : il appelle Brain et donne au modèle ses interfaces, sa mémoire personnelle et ses actions.
- **Agent Factory et les autres systèmes n'ont pas leur propre LLM** : ils passent par Brain. Le routage vers des fournisseurs externes (Anthropic, OpenAI, Gemini) n'est pas autorisé en production pour les données de Laurent (D8).

### 3.5 Agent Factory et Laurentia

Dans l'arbre fondateur, Laurentia est **une partie** d'Agent Factory (`PART_OF`) : c'est un agent, fabriqué par la Factory.
Selon la règle 4 de Laurent, les agents d'Agent Factory sont **les enfants de Laurentia** : c'est Laurentia qui les commande.

Les deux sont compatibles si on distingue **structure** et **commande** :
- **Structure** (inchangée) : Laurentia est un agent de la Factory (`PART_OF`).
- **Commande** (relation ajoutée, sans modifier l'arbre) : Laurentia **commande** (`SUPERVISES`/`OPERATES`) les agents de la Factory, par contrat.

---

## 4. Noms à ne plus confondre

| Nom | Désigne |
|---|---|
| **CVLN Brain** | Le cœur silencieux (service, sans interface) |
| **Laurent.ia** / **Laurentia** | Le même système : l'agent et l'interface, réalisation de Brain pour Laurent. Nom de produit : **Laurent.ia** ; identifiant dans les registres : `ENT-LAURENTIA` / `laurentia` |
| **`services/cvl_brain.py`** (code actuel de Laurent.ia) | **Pas** CVLN Brain : un client LLM local à renommer (`llm/`) |
| **« CVL Brain »** dans Meta CVLN (`/brain/ask`) et dans Kiltikonet (`brain_llm.py`) | Des assistants locaux à ces systèmes, **pas** CVLN Brain ; à brancher sur Brain par contrat |
| **« Laurentia »** dans l'architecture de KORA (assistant des abonnés) | Une capacité **publique** de Laurent.ia, consommée par KORA |
| **Meta CVLN** (entité) / **MetaCVLN** (logiciel) | La même autorité ; le logiciel en est l'implémentation (D-027) |
| **Décisions D1…D18** de ce dépôt / **D-001…D-031** de l'écosystème | Deux registres distincts ; ceux de Laurent.ia seront renommés `LIA-D1…` |

---

## 5. Conséquences pour Laurent.ia

1. **Partir de la PR #1** (contrat runtime : capacités, identité, état, événements, traçage) en remplaçant la délégation aux LLM externes par **CVLN Brain sur le LLM souverain** (D8).
2. **Séparer interface interne et interface publique** dans le code, avec un test qui garantit que l'interface publique n'atteint jamais la mémoire personnelle.
3. **Renommer `services/cvl_brain.py`** en client LLM, pour que « Brain » ne désigne plus que le cœur silencieux.
4. **Déclarer dans Meta CVLN** les capacités publiques de Laurent.ia au format `Capability` v1.0 ; corriger la fiche du registre (plan, capacités).

## 6. Points que Laurent doit confirmer

- **Q1** — Laurent.ia et Laurentia sont-ils bien **le même système** (nom produit / identifiant de registre) ?
- **Q2** — Pour la règle 4, la lecture « structure inchangée + relation de commande ajoutée » (§3.5) te convient-elle, ou veux-tu que **l'arbre fondateur soit modifié** (Agent Factory sous Laurentia) ? L'arbre étant gelé, ce serait une décision fondatrice explicite.
- **Q3** — CVLN Brain, comme service, se développe-t-il **dans le dépôt Laurent.ia** (Brain et sa réalisation au même endroit, séparés par modules) ou dans **un dépôt dédié** ?
