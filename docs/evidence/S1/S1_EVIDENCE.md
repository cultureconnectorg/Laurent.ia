# S1 : fiabilité de la base et premiers verrous, fiche de preuve

> 11 octobre 2026 · Branche isolée `claude/s1-reliability-guards`, créée depuis `claude/s0-test-baseline` (code = `b898e19`).
> **Sans fusion, sans déploiement, sans changement de production.** Ce lot **ne doit pas être déployé avant S2** : le verrou S1.4 refuserait de démarrer la configuration de production actuelle, qui utilise `EMERGENT_LLM_KEY`.

## 1. Résultat global

| Mesure | S0 (`b898e19`) | S1 (fin de lot) |
|---|---|---|
| Tests collectés | 131 | **169** (+38 nouveaux) |
| Réussis | 121 | **160** |
| Échoués | 10 | **9**, tous B1 : ils exigent un moteur d'inférence et relèvent de S2 |
| Tentatives de sortie réseau pendant l'exécution | 9 (tests) + 6 (serveur) | **0** |
| Régressions par rapport à S0 | — | **0** : `compare_baseline.py` sort en code 0 ; les 121 tests qui passaient passent toujours |
| Reproductibilité | 3 exécutions identiques | 2 exécutions finales identiques (`raw/final/`) |

Le test PDF n° 10 (B2) passe désormais. **L'hypothèse B2 est confirmée** : l'échec venait des polices Google bloquées. Avec les polices locales, le rendu est correct.

## 2. Sous-lots : preuve rouge, puis verte

| Lot | Commit | Rouge sur la base | Vert après le lot |
|---|---|---|---|
| **S1.1** Hygiène de la suite | `8665233` | 9 tentatives vers l'hôte Emergent (S0, `raw/runA/egress.jsonl`) ; 2 tests asynchrones non exécutables | 0 tentative ; `pytest-asyncio` déclaré dans `requirements-test.txt` |
| **S1.3** Garde réseau | `3bd0000`, `e86cba7` | Sur S0, la garde n'existait que dans le harnais externe | `test_s1_network_guard.py` (4 tests). Un test qui avale l'erreur de sortie échoue quand même (`raw/guard-fixture-proof.txt`). Toute sortie du serveur fait échouer l'exécution (`run_suite.sh`) |
| **S1.4** Verrous de démarrage | `8a4eb97` | La base démarre en `APP_ENV=production` avec `EMERGENT_LLM_KEY` et CORS `*` (`raw/startup-red-base.txt`) | `test_s1_startup_checks.py` (23 tests, dont 4 démarrages réels en sous-processus). Refus si : clé de fournisseur externe ; URL de modèle hors liste blanche ; CORS `*` ou vide ; clé de chiffrement ou sel absents ou égaux aux valeurs par défaut. **`APP_ENV` absent = production** (refus par défaut). Seuls les noms des variables sont affichés, jamais leurs valeurs |
| **S1.5** Frontal et PDF | `7f4cc04` | 4 tests T4 sur 5 échouent sur la base (`raw/t4-red-base.txt`) ; 6 appels du serveur à `fonts.googleapis.com` | PostHog et le script Emergent retirés ; polices auto-hébergées (licence OFL, licences jointes) ; le PDF est rendu sans réseau et embarque les polices locales |
| **S1.6** Routes sans authentification | `e03f753` | 4 tests sur 6 échouent sur la base (`raw/s16-red-base.txt`) : un appel anonyme atteint le moteur | Un appel anonyme ou avec un jeton inconnu reçoit **401 avant tout appel au moteur**, vérifié par un espion sur le moteur ; un appel authentifié (vraie session MongoDB) passe. **Rien n'est retiré** |
| **S1.2** CI | `5955ba7` | Pas de CI | `.github/workflows/backend-tests.yml` : MongoDB réelle, garde réseau, suite complète. Le job reste **rouge tant que B1 échoue** ; deux contrôles distincts vérifient l'absence de régression et l'absence de sortie réseau |

## 3. Modifications de tests existants (justifiées ligne par ligne)

| Fichier | Changement | Justification |
|---|---|---|
| `tests/test_laurentia_backend.py:14-15` | URL par défaut : `http://localhost:8001` au lieu de l'hôte d'aperçu Emergent | Empêche l'envoi de données de test vers un tiers. Ne rend aucun test vert à lui seul : les tests visent le serveur local, comme tous les autres tests HTTP |
| `tests/conftest.py` | Ajouts uniquement : installation de la garde, vérification automatique des sorties, `APP_ENV=test` par défaut | Garde réseau (S1.3) ; environnement de test explicite, nécessaire au refus par défaut de S1.4 |

Aucun test n'est supprimé, désactivé, sauté ni marqué « échec attendu ». La liste `tests/_harness/known_failures.txt` ne sert qu'au contrôle de non-régression : **les 9 tests B1 continuent de s'exécuter et d'échouer**.

## 4. Non vérifié, limites

- **[NV] Rendu du frontal dans un navigateur.** Le build React n'a pas été construit dans cette session. Les tests vérifient le HTML, la feuille de polices et la présence des fichiers, pas l'affichage.
- **[NV] Exécution de la CI sur GitHub.** Le workflow est syntaxiquement valide et reproduit localement le même protocole ; son premier passage sur GitHub reste à constater.
- **Hors S1, inchangés** :
  - reconnaissance et synthèse vocales du navigateur (N1, N2) ;
  - authentification Emergent (R6) ;
  - pipeline de corpus (R1) ;
  - inférence externe (P1 à P8).
  Ils relèvent de S2, S3 et de décisions ouvertes.
- **S1.6 exige un utilisateur authentifié, pas encore « Laurent seul ».** Restreindre l'interface interne au seul principal Laurent (LIA-D1) relève de S3, avec la séparation des interfaces.

## 5. Critères d'acceptation de S1

| Critère | État |
|---|---|
| Protocole S0 rejoué sans régression | **Fait** |
| 0 tentative de sortie pendant la suite et dans le serveur | **Fait** |
| T2 (configuration) et T4 au vert | **Fait** |
| Preuve rouge sur la base pour chaque nouvelle garantie | **Fait** (`raw/`) |
| CI qui rejoue le protocole | Workflow ajouté ; **premier passage sur GitHub à constater** |
| Les 9 tests B1 restent rouges jusqu'à S2 | **Conforme** |
