# Registre des décisions — Laurent.ia

> Créé le 11 octobre 2026 (correctif E1). Seul registre de référence des décisions **propres à Laurent.ia**.
> Préfixe `LIA-` : évite la collision avec les décisions de l'écosystème `D-001…D-031` (corpus `cultureconnectorg/Cvln-ios-v.1`). Les anciens numéros `D1…D18` des documents de ce dépôt restent valables **comme alias**.

## Légende des statuts

| Marque | Sens |
|---|---|
| **[RC]** | Règle canonique : décidée par Laurent et applicable |
| **[AR]** | **Arbitrage récent** (octobre 2026) de Laurent. Il fait foi comme décision, **pas comme preuve historique** : il ne démontre pas ce qui avait été décidé avant lui |
| **[DH]** | Décision historique écrite, antérieure à octobre 2026, dont la source est vérifiée dans un dépôt |
| **[DL]** | Décision ou formulation antérieure rapportée par Laurent (ses archives), **absente des dépôts audités** |
| **[H]** | Hypothèse de travail, non décidée |
| **[NV]** | Élément non vérifié dans le code ou dans les dépôts |
| **[OUVERT]** | Décision à prendre |
| **[CADUQUE]** | Remplacée, ou contraire à une décision historique |

**Règle de lecture des sources.** La colonne « Décidée par » donne l'acte qui fait foi. La colonne « Antécédents » liste des documents antérieurs **convergents** : ils situent la décision dans l'histoire, mais **ne la prouvent pas**. Un document au statut `PROPOSED`, `TARGET` ou `UNVERIFIED` reste une proposition ou une déclaration.

## Ordre de lecture chronologique [RC][AR] (Laurent, 11 oct. 2026)

1. **Socle du 20 août 2026.** Traces vérifiables les plus proches : les états de référence du 19 août (UTC) audités par CVLN iOS v1.0 — Laurent.ia `c097637`, Meta CVLN `b36a893`, premier commit de `Cvln-ios-v.1`. **[NV]** : le contenu exact des décisions du 20 août n'est pas archivé dans les dépôts audités.
2. **Septembre 2026** : précisions sur les relations opérationnelles — formulation du 8 septembre **[DL]**, règle CVLN iOS des 9-10 septembre **[DH]**, PATCH-007 du 15 septembre **[DH, statut PROPOSED dans iOS]**, gel de l'architecture Kiltikonet des 20-25 septembre **[DH]**.
3. **Octobre 2026** : renforcement de la souveraineté et de la séparation de l'instance personnelle **[AR]**.

En cas de conflit, une décision plus récente ne prévaut que si elle porte explicitement sur le même point. Sinon, les deux s'appliquent.

## Décisions

| ID | Alias | Décision | Statut | Décidée par (date) | Antécédents convergents (non probants) |
|---|---|---|---|---|---|
| LIA-D1 | D1 | V1 personnelle : Laurent est l'unique principal | [RC][AR] | Laurent, 6 oct. 2026 | 30 mai, « usage personnel intime » (Laurent.ia `memory/PRD.md` v0.1) [DH] |
| LIA-D2 | D2 | B2C, paywall et mécaniques virales désactivés, sans suppression inutile | [RC][AR] | Laurent, 6 oct. 2026 | — |
| LIA-D3 | D3 | Inférence par moteur souverain uniquement en production | [RC][AR], précisée par LIA-D8 | Laurent, 6 oct. 2026 | — |
| LIA-D4 | D4 | MongoDB conservé pour la mémoire structurée de Laurent.ia, sous condition de preuve | [H] ; à revoir avec LIA-D20 et LIA-D21 (la mémoire cognitive relève de Brain) | Cadrage §3.5 (proposition) | — |
| LIA-D5 | D5 | Renommer les modules `cvl_brain*` de Laurent.ia | **[CADUQUE]** : contraire à la décision historique du 30 mai | — | **[DH]** 30 mai : « Nom technique interne : CVL Brain (héritage kiltikonet — ne pas renommer dans le code) », Kiltikonet `memory/LAURENTIA_SYSTEM_PROMPT_EMERGENT_FINAL.md` (`8f8a82ea`) |
| LIA-D6 | D6 | Transparence totale envers Laurent, confidentialité stricte envers les tiers, pas de persona | [RC][AR] | Laurent, 6 oct. 2026 | — |
| LIA-D7 | D7 | Aucune responsabilité d'un autre système n'est supposée ; contrats établis avant intégration | [RC][AR] | Laurent, 6 oct. 2026 | D-025 (iOS, 31 août) [DH] |
| LIA-D8 | D8 | **Sovereign Local Intelligence** : aucun LLM externe ne reçoit de données cognitives de production | [RC][AR] — exigence d'architecture, non négociable | Laurent, 6 oct. 2026 (`D8-sovereign-local-intelligence.md`) | — |
| LIA-D9 | D9 | Inférence, mémoire et runtime sur une infrastructure contrôlée par Laurent, une ou plusieurs machines | [RC][AR] | Laurent, 6 et 11 oct. 2026 | — |
| LIA-D10 | D10 | Licence du dépôt (BSL 1.1 orientée B2C) à revoir | [OUVERT], non bloquant | — | Cadrage §10 |
| LIA-D11 | D11 | Modèles open-weight de toutes origines autorisés s'ils tournent localement | [RC][AR] | Laurent, 6 oct. 2026 | — |
| LIA-D12 | D12 | Recherche web : approbation de chaque requête au départ, puis échelle de confiance | [RC][AR] | Laurent, 11 oct. 2026 | — |
| LIA-D13 | D13 | Interfaces existantes I1–I9 : rien n'est retiré ; décision interface par interface | [RC][AR] (méthode) ; décisions par interface [OUVERT] | Laurent, 11 oct. 2026 | — |
| LIA-D14 | D14 | Pas de duplication arbitraire ; chaque système garde ses données | [RC][AR], **précisée par LIA-D21** (la mémoire personnelle n'est plus « possédée par Laurent.ia ») | Laurent, 11 oct. 2026 | Kiltikonet `ARCHITECTURE.md` v1.3.0 : « consommer un service ne transfère pas sa propriété » [DH] |
| LIA-D15 | D15 | Le Product Contract devient la spécification V1 canonique | [OUVERT] : après E2 | — | — |
| LIA-D16 | D16 | « Laurentia » dans l'architecture de KORA (assistant des abonnés) | [OUVERT] ; hors V1 ; **[NV]** aucune intégration KORA ↔ Laurentia dans le code | — | KORA `memory/KORA_Master_Prompt_Architecture.md` §11 (déclaration) |
| LIA-D17 | D17 | Où vivent les conversations de Laurent avec les assistants des autres systèmes | **Tranchée par LIA-D21** | Laurent, 11 oct. 2026 | — |
| LIA-D18 | D18 | Partage des rôles Laurent.ia ↔ Agent Factory | **Tranchée par LIA-D19 à LIA-D22** | Laurent, 11 oct. 2026 | — |
| **LIA-D19** | A1 | **Doctrine** : CVLN Brain détient et applique la doctrine de référence. Meta CVLN gouverne les changements officiels, l'identité institutionnelle, les contrats et les registres. Cognition et gouvernance restent distinctes | [RC][AR] | **Arbitrage de Laurent, 11 oct. 2026** | Cible CVLN iOS « Brain owns doctrine, META ratifies » (**PROPOSED**, non décidée) ; entité « CVLN Brain — Doctrine » dans le code d'Agent Factory [F]. Avant le 11 oct., la question était **ouverte** (FD-001, C-002) |
| **LIA-D20** | A2 | **Brain** : la cible est un service cognitif souverain indépendant, déployable séparément, avec son propre moteur souverain. Les modules historiques et chemins existants sont préservés pendant la transition ; rien n'est extrait, renommé ou supprimé avant documentation des dépendances et définition des tests de migration | [RC][AR] | **Arbitrage de Laurent, 11 oct. 2026** | Foundation `ENT-CVLN-BRAIN`, type SERVICE (31 août, **`UNVERIFIED`**) ; cible CVLN iOS étape 4 (**PROPOSED**). Avant le 11 oct., l'emplacement de Brain était **ouvert** (FD-001) |
| **LIA-D21** | A3 | **Mémoire** : la mémoire cognitive et les conversations personnelles relèvent de Brain, avec un cloisonnement strict de l'espace personnel de Laurent. Meta CVLN conserve la mémoire de gouvernance ; Agent Factory l'état d'exécution nécessaire ; chaque entité ses données métier. Aucun transfert automatique, aucune copie silencieuse | [RC][AR] | **Arbitrage de Laurent, 11 oct. 2026** | Aucun antécédent écrit ne tranchait ce point. Il **remplace** la formulation antérieure de ce dépôt « Laurent.ia propriétaire unique de la mémoire personnelle » (Product Contract, 11 oct.) |
| **LIA-D22** | — | **Relations** : fonctionnelles et contractuelles, sans hiérarchie ni autorité implicite. Meta CVLN **pense** (gouvernance), CVLN iOS **organise** (référentiel documentaire), Agent Factory **exécute** (exécution technique), Laurentia **fait circuler** l'intelligence et l'action (orchestration métier), CVLN Brain porte la **cognition** | [RC][AR] | **Arbitrage de Laurent, 11 oct. 2026**, qui reprend la formulation du 8 sept. et y ajoute la fonction de cognition de Brain | Formulation du 8 sept. **[DL]**, sans « Brain » ; D-025 « par contrats, jamais par absorption » [DH] ; règle CVLN iOS des 9-10 sept. [DH] ; Kiltikonet `ARCHITECTURE.md` v1.3.0 [DH] ; `seed_workforce.py:16` d'Agent Factory [F]. L'arbre `Foundation-Cvln` déclare au contraire `PART_OF` (`UNVERIFIED`), conservé tel quel |
| **LIA-D23** | — | **Identifiants historiques conservés** : nom produit **Laurent.ia** ; identifiant technique **`laurentia`** ; nom technique interne du moteur **CVL Brain** (non renommé dans le code). Un seul système porte deux rôles documentés — instance personnelle de Laurent et Laurentia opérateur métier — sans second système artificiel ni fusion de leurs périmètres de mémoire | [RC][AR] pour « un système, deux rôles » ; [DH] pour les noms | **Arbitrage de Laurent, 11 oct. 2026** (deux rôles) ; **30 mai** (noms) | 30 mai, `8f8a82ea` : « Nom affiché : Laurent.ia · Nom technique interne : CVL Brain » [DH] ; identifiant `laurentia` dans le code et dans Meta [F] |
