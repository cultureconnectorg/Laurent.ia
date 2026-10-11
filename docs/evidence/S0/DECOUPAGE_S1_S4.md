# Découpage des modifications S1 à S4 — proposition soumise à validation

> 11 octobre 2026 · **[P] Proposition. Rien n'est lancé.** Chaque lot démarre seulement après ta validation explicite.
> **Périmètre** : Laurent.ia uniquement, une branche isolée par lot, créée depuis `public` (`b898e19`) ou depuis le lot précédent. **Ni fusion, ni déploiement, ni production.**
> **Priorités fixées par Laurent** : (1) fiabilité de la base ; (2) souveraineté démontrable ; (3) extraction de Brain.

## Règles communes à tous les lots

1. **Rouge puis vert.**
   - Chaque garantie arrive avec un test.
   - On exécute d'abord ce test sur la base S0 (`b898e19`) et on archive la sortie en échec dans `docs/evidence/Sx/`.
   - Le test et la correction sont fusionnés **dans le même lot**. Aucun test n'est jamais livré désactivé ou marqué « échec attendu ».
2. **Non-régression.**
   - Le protocole S0 (`run_s0.sh`) est rejoué à la fin de chaque lot.
   - Le nombre de tests réussis ne peut que monter.
   - Tout test qui passait (121 sur 131) doit continuer à passer.
   - Toute modification d'un test existant est **signalée et justifiée ligne par ligne** dans la fiche de preuve.
3. **Rien n'est supprimé, extrait ni renommé** avant la carte des dépendances et les tests de migration [RC LIA-D20]. `cvl_brain.py`, `chat_enriched` et `chat_stream` conservent leurs noms [RC LIA-D23].
4. **Une fiche de preuve par lot** : commandes, sorties brutes, critères cochés.

---

## S1 — Fiabilité de la base et premiers verrous (priorité 1)

| Sous-lot | Contenu | Fichiers | Preuve, puis acceptation |
|---|---|---|---|
| **S1.1** Hygiène de la suite | (a) URL par défaut des tests → `http://localhost:8001` au lieu de l'hôte Emergent (D-S0-1). **C'est une modification de test**, justifiée par le fait qu'elle empêche l'envoi de données vers un tiers ; elle ne fait passer aucun test. (b) Déclaration de `pytest-asyncio` (D-S0-2) | `backend/tests/test_laurentia_backend.py:14`, `backend/requirements-test.txt` (nouveau) | Rouge : `egress.jsonl` de l'exécution A (9 tentatives). Vert : 0 tentative ; les 2 tests asynchrones passent |
| **S1.2** CI | Workflow qui rejoue le protocole S0 : service MongoDB, garde réseau active, serveur local, rapport JUnit archivé | `.github/workflows/s0-baseline.yml` (nouveau), `backend/tests/_harness/` (garde reprise de S0) | Une exécution en CI donne le même ensemble d'échecs que S0 (empreinte identique) |
| **S1.3** Garde réseau dans la suite | La garde de S0 devient un module de test (`conftest`), active pour toute la suite, avec un journal des tentatives | `backend/tests/conftest.py` (ajout, sans retrait) | Toute sortie hors liste blanche fait échouer le test qui la provoque |
| **S1.4** Verrous de démarrage (T2, partie configuration) | En `APP_ENV=production`, refus de démarrer si : `EMERGENT_LLM_KEY` est défini ; une URL de modèle (`SD_API_URL`, `CVLN_MODEL_ROUTER_URL`) est hors liste blanche ; `CORS_ORIGINS` vaut `*` (D-S0-8) ; `LAURENTIA_ENCRYPTION_KEY` ou `LAURENTIA_SECRET_SALT` est absent ou égal à sa valeur par défaut (D-S0-3, D-S0-4) | `backend/server.py` (contrôle au démarrage), `backend/services/startup_checks.py` (nouveau) | Test : démarrage réel en sous-processus pour chaque cas → code de sortie ≠ 0. Rouge sur la base : le serveur démarre |
| **S1.5** Frontal (T4) | Test d'inventaire : aucun script tiers dans `public/index.html` ni dans le build. Reprise du retrait de PostHog et d'Emergent déjà fait sur la branche E1 (`f8bf45c`). Polices auto-hébergées (R4, D-S0-5) | `frontend/public/index.html`, `frontend/src/__tests__/noThirdParty.test.js` (nouveau), `backend/routes/pdf_export.py` | Rouge sur `public` ; vert après le retrait. Le test PDF n° 10 (B2) est rejoué avec les polices locales, ce qui **confirmera ou infirmera** l'hypothèse B2 |
| **S1.6** Routes sans authentification (D-S0-7) | **Décision à prendre (LIA-D13)** pour `/api/brain/chat-enriched` et `/api/omega/chat-enriched` : (a) les réserver à l'interface interne avec authentification ; (b) les retirer après la carte des appelants. **Je recommande (a)** : rien n'est retiré | `backend/routes/brain.py`, `backend/routes/omega.py` | Test : un appel anonyme renvoie 401 **et** le moteur n'est jamais atteint (compteur côté moteur de test) |

**Acceptation de S1** : S0 rejoué sans aucune régression ; 0 tentative de sortie pendant la suite ; T2 (configuration) et T4 au vert ; CI au vert sur les tests qui n'exigent pas de moteur. Les 9 échecs B1 restent rouges : ils dépendent de S2.

## S2 — Moteur souverain derrière `cvl_brain` (priorité 2)

| Sous-lot | Contenu | Preuve, puis acceptation |
|---|---|---|
| **S2.1** Port d'inférence | `chat_enriched()` et `chat_stream()` (mêmes noms, mêmes signatures) appellent un moteur local par HTTP simple (protocole compatible OpenAI, **sans SDK de fournisseur**). Configuration : `BRAIN_ENGINE_URL`, `BRAIN_ENGINE_MODEL`, `BRAIN_ENGINE_ALLOWED_HOSTS`. Le chemin Emergent est **conservé** mais refusé en production par S1.4 [RC LIA-D20] | T1 : aucun SDK de LLM importé par un module joignable en production |
| **S2.2** Deux niveaux de moteur de test | (a) **Moteur déterministe** : un vrai serveur HTTP local, avec journal des prompts reçus, pour la suite rapide. (b) **Moteur réel open-weight minuscule**, servi par llama.cpp (modèle de quelques centaines de Mo, à choisir), dans un job CI séparé : **vraie inférence** de bout en bout | Les **9 tests B1 passent** avec (a) et avec (b) |
| **S2.3** Un test par chemin d'inférence | P1 à P7 (`INFERENCE_PATHS.md`) : chaque chemin est exécuté réellement sous garde réseau. On vérifie que le moteur local a reçu l'appel et qu'aucune sortie n'a eu lieu (T3) | 7 tests verts ; `egress.jsonl` vide |
| **S2.4** Repli | Moteur local coupé → erreur visible sur chaque chemin, **aucune bascule** | Test par chemin |
| **S2.5** Santé | `/api/health` et `/api/brain/health` annoncent le moteur réellement configuré (D-S0-6) | Test |
| **S2.6** Dépendances | Retrait de `litellm`, qui n'est importé nulle part. `emergentintegrations` reste tant que `billing.py` l'importe (module B2C gelé) | Le protocole S0 est rejoué sans le remplaçant pour la partie inférence |

**Acceptation de S2** : 131 tests sur 131 au vert si l'hypothèse B2 a été confirmée en S1.5, sinon 130 avec la cause documentée ; T1 et T3 au vert ; un job CI de vraie inférence locale sans aucune sortie réseau.

## S3 — Frontières de mémoire, prouvées par le stockage (priorité 2)

| Sous-lot | Contenu | Preuve, puis acceptation |
|---|---|---|
| **S3.1** `DATA_MAP.md` | Chaque collection avec ses lecteurs, ses écrivains et sa classe (proposition dans `STORAGE_BOUNDARIES.md` §2) | Documentaire ; **validation par toi** |
| **S3.2** Deux principaux MongoDB | Connexions `laurentia_internal` et `laurentia_public`. Les routes publiques ne reçoivent que la connexion publique | **T5** sur MongoDB avec authentification : refus (code 13) dans le journal `mongod` ; le profileur montre zéro accès public aux collections personnelles ; régression volontaire refusée par la base (`STORAGE_BOUNDARIES.md` §4) |
| **S3.3** Fin de l'effacement au-delà de 50 échanges | Échanges stockés en ajout seul ; la fenêtre de contexte est calculée à la lecture | Test : 60 écritures, 60 lectures, N échanges dans le prompt (relevés par le journal du moteur de S2.2) |
| **S3.4** Provenance | Écriture refusée si `source_system`, `trace_id`, `created_at` ou `actor` manque | T6a |
| **S3.5** Aucune copie silencieuse | Pipeline corpus (R1) désactivé en mode opérateur | T6b : le job sous garde ne produit ni sortie réseau ni fichier |
| **S3.6** Données de membres | Profils Kiltikonet et LabelOS absents des prompts en mode personnel et opérateur | Test avec le journal du moteur de S2.2 |
| **S3.7** Format d'export vers Brain | JSONL + manifeste + empreintes. **Aucun transfert exécuté** [RC LIA-D21] | Test aller-retour dans une base jetable |

## S4 — Contrats entre systèmes (priorité 2, puis 3)

| Sous-lot | Contenu | Preuve, puis acceptation |
|---|---|---|
| **S4.1** Reprise de la PR #1 | Identité, `GET /api/capabilities`, `SystemState`, `Event`, `X-CVLN-Trace-Id`. **Sans** `cvln_model_router.py` (P8) | Tests de la PR #1 repris et verts. Ceux du routeur sont retirés **avec leur code** et listés dans la fiche |
| **S4.2** Identité | Un système, deux rôles [RC LIA-D23] ; correction de la déclaration `Layer 3 / Cultural industry operator` | Test |
| **S4.3** Schémas épinglés | Contrats Meta v1.0 copiés dans le dépôt, avec la source `7673bfc` et leur empreinte | T7a : les réponses réelles sont validées contre ces schémas |
| **S4.4** Clés de service | Sans clé → 401 ; clé valide → capacités déclarées seulement ; jamais d'accès à l'interface interne | T7b |
| **S4.5** Laurentia → Agent Factory | **Spécification seulement**. L'implémentation touche Agent Factory : autre dépôt, autorisation séparée | Revue |

## Après S4 (priorité 3, à valider séparément)

- **S5** : moteur réel sur ton infrastructure (matériel [NV], benchmark, choix du modèle) ; service Brain indépendant (emplacement [OUVERT]).
- **S6** : bascule de production, avec validation explicite.
- **E7** : les autres dépôts.

## Décisions attendues de ta part avant S1

1. Valider ce découpage et l'ordre S1 → S2 → S3 → S4.
2. Trancher **S1.6** (routes sans authentification) : (a), recommandée, ou (b).
3. Autoriser l'ajout d'une CI (`.github/workflows/`) sur les branches isolées, sans déploiement.
