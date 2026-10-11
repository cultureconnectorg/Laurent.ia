# S0 : base de tests reproductible

> 11 octobre 2026 · Branche isolée `claude/s0-test-baseline`, créée depuis `public` = `b898e19` (production).
> **Aucun fichier de test ni de code applicatif n'a été modifié, désactivé ou contourné.** Ce commit n'ajoute que de la documentation, les résultats bruts et le harnais d'exécution sous `docs/evidence/S0/`.
> Statuts : **[F]** fait mesuré · **[H]** hypothèse · **[NV]** non vérifié.

## 1. Environnement

| Élément | Valeur |
|---|---|
| Code testé | `b898e19` (`public`), sans modification |
| Python | 3.13.16, environnement virtuel dédié, dépendances de `backend/requirements.txt` (versions exactes dans `raw/pip-freeze.txt`) |
| Dépendances absentes | `emergentintegrations==0.1.2` (absente de PyPI) ; `litellm` (fichier hébergé chez Emergent) |
| Ajout d'outillage | `pytest-asyncio==0.23.8` : les tests utilisent `@pytest.mark.asyncio` (`test_phase4_echo_rgpd.py:140,168`), mais le plugin n'est pas déclaré dans `requirements.txt` |
| Base de données | MongoDB 7.0 réelle et locale (Docker, condensat de l'image dans `raw/env.txt`) ; **une base neuve par exécution** |
| Serveur API | `uvicorn server:app` en local (`127.0.0.1:8001`), lancé à chaque exécution |
| Secrets | Valeurs fictives propres au test (`s0-test-only-*`), aucune donnée réelle |
| Planificateurs | Désactivés par les drapeaux du code : `CHANTIER7_SCHEDULERS_DISABLED`, `CHANTIER10_REPORTS_DISABLED`, `ORCHESTRATOR_DISABLED` |

### Harnais (hors du code applicatif, dans `harness/`)

1. **Garde réseau** (`guard/sitecustomize.py`), active dans le processus de test **et** dans le serveur.
   - Seuls MongoDB local (27017) et l'API locale (8001) sont joignables.
   - Toute autre connexion ou résolution DNS est refusée immédiatement et journalisée (`egress.jsonl`), avec la ligne du dépôt qui l'a déclenchée.
   - Les variables de proxy sont retirées.
   - **But** : aucune donnée de test ne sort, et chaque tentative de sortie est mesurée.
2. **Remplaçant d'`emergentintegrations`** (`stub/`), utilisé seulement pour le protocole P.
   - Il rend le paquet importable afin que l'application démarre.
   - **Tout appel lève une erreur** (`S0StubError`) : aucun test ne peut réussir grâce à une fausse réponse du modèle. C'est un échec visible, pas un contournement.
3. **`run_s0.sh`**
   - Déroulé : base neuve, démarrage de l'API sous garde, suite complète, arrêt.
   - `classify.py` classe les résultats JUnit.

## 2. Résultats

### Exécution A : stricte (sans serveur, sans remplaçant, avec garde)

[F] **120 éléments** : 81 réussis, 37 échoués, **2 fichiers non collectés** (`raw/runA/`).

| Cause | Tests | Détail |
|---|---|---|
| A1 : `emergentintegrations` non installable | 2 fichiers (13 tests) | `test_briefing_contract.py`, `test_social_agent.py` : `ModuleNotFoundError` à la collecte |
| A2 : serveur API absent | 25 | Tests HTTP vers `localhost:8001` : `Connection refused` |
| A3 : **hôte externe Emergent par défaut** | 9 | `test_laurentia_backend.py:14` vise par défaut `https://emergent-ai-238.preview.emergentagent.com`. **Sans la garde, ces tests enverraient des requêtes, dont des créations d'instances et des requêtes cognitives, vers un hôte tiers.** La garde les a bloqués au DNS (`raw/runA/egress.jsonl`) |
| A4 : `pytest-asyncio` non déclaré | 2 | `async def functions are not natively supported` |
| A5 : index TTL créé au démarrage du serveur | 1 | `test_ttl_index_present` dépend du démarrage préalable de l'API |

L'ancien constat « 69 non exécutés » (6 oct.) venait des délais de 30 s par test sans serveur. Avec la garde, les échecs sont immédiats : **aucun test n'est plus « non exécuté »**.

### Protocole P : base de référence (serveur local, remplaçant qui échoue, garde)

[F] **131 tests collectés : 121 réussis, 10 échoués, 0 non collecté, 0 non exécuté.**

[F] **Reproductible** : trois exécutions indépendantes (P1, P2, P3), chacune sur une base neuve et un serveur neuf. Ensemble des échecs **identique** (empreinte md5 de la liste : `c6d2466b…` pour les trois). Durée : environ 13 s.

| # | Test | Cause | Preuve |
|---|---|---|---|
| 1 | `test_laurentia_backend::TestQuerySSE::test_sse_query_sayd` | **B1 : inférence externe requise** | Trace serveur : `laurentia_gateway.py:396` → `cvl_brain.chat_stream` → `S0StubError` |
| 2 | `test_laurentia_backend::TestPersistencePrivacy::test_query_persists_and_anonymizes` | B1 : l'échange n'est enregistré qu'après une réponse du modèle | idem |
| 3 | `test_phase1_integration_http::test_memory_sessions_are_encrypted_at_rest` | B1 | idem |
| 4 | `test_phase1_integration_http::test_get_session_decrypts_blobs` | B1 | idem |
| 5 | `test_phase1_integration_http::test_query_multipart_pdf` | B1 (`rec` vaut `None` : rien n'est enregistré) | idem |
| 6 | `test_phase1_integration_http::test_query_multipart_docx` | B1 | idem |
| 7 | `test_phase1_security_uploads::test_query_multipart_creator_ok_and_encrypted_at_rest` | B1 (`event: error` au lieu de `done`) | idem |
| 8 | `test_phase1_security_uploads::test_query_json_path_still_works` | B1 | idem |
| 9 | `test_phase4_echo_rgpd::test_echo_generate_with_raw_text_and_public_get` | B1 : `echo.py:123` → `cvl_brain.chat_stream` → 502 | idem |
| 10 | `test_phase3_ghost_signature::test_pdf_pages_includes_signature_for_free` | **B2 : mise en page du PDF**. Le texte attendu est coupé par un retour à la ligne (« Certifié par\nl'Infrastructure ») | [H] Cause probable : `pdf_export.py` charge ses polices depuis `fonts.googleapis.com` ; bloqué par la garde (6 tentatives journalisées), le moteur de rendu se rabat sur une autre police. Non confirmé : il faudrait laisser sortir la requête vers Google, ce que je n'ai pas fait |

Les 11 traces de `S0StubError` du serveur passent toutes par l'un des deux sites d'appel observés : `laurentia_gateway.py:396` (10) et `echo.py:123` (1).

### Ce que ces résultats établissent

- **[F]** La suite est **exécutable de façon autonome et reproductible** sur une MongoDB réelle, sans aucune sortie réseau.
- **[F]** **9 des 10 échecs exigent un moteur d'inférence.** Ils ne peuvent passer légitimement ni avec un LLM externe (interdit par LIA-D8) ni avec une fausse réponse (ce serait un contournement). Ils deviendront le **critère d'acceptation de S2** : un moteur local réel derrière `cvl_brain`.
- **[F]** Les tests `test_briefing_contract` (3) et `test_social_agent` (10) réussissent en **remplaçant `cvl_brain` par un simulacre** (`patch`). Ils vérifient le contrat et la logique de reprise, **pas l'inférence**.
- **[F]** Les badges « 64/64 » (README) et « 128/128 » (PRD) ne correspondent pas à la suite actuelle (131 tests).

## 3. Défauts découverts (non corrigés : hors périmètre de S0)

| # | Constat | Lieu | Traitement proposé |
|---|---|---|---|
| D-S0-1 | Un test vise par défaut un hôte tiers (aperçu Emergent) et y écrirait des données | `tests/test_laurentia_backend.py:14` | S1 : valeur par défaut locale, et test de garde réseau en CI |
| D-S0-2 | `pytest-asyncio` n'est pas déclaré | `requirements.txt` | S1 : déclarer la dépendance de test |
| D-S0-3 | Clé de chiffrement de la mémoire : repli sur une **valeur par défaut publique** si la variable est absente (un journal d'erreur, mais pas de refus de démarrer) | `services/crypto.py:28-33` | S3 : refus de démarrer en production sans clé |
| D-S0-4 | Sel des empreintes et des `tenant_id` : même repli sur une valeur publique | `services/fingerprint.py:20-24` | S3 : même traitement |
| D-S0-5 | Export PDF : appel à `fonts.googleapis.com` pendant la génération | `routes/pdf_export.py:360,501` | S1 : polices embarquées localement |
| D-S0-6 | `/api/health` et `/api/brain/health` annoncent le modèle externe `claude-sonnet-4-5-…` | `server.py:54`, `routes/brain.py:36` | S2 : annoncer le moteur réellement configuré |
| D-S0-7 | `POST /api/brain/chat-enriched` et `POST /api/omega/chat-enriched` déclenchent l'inférence **sans aucune authentification**. [F] Démontré par une requête anonyme qui atteint `cvl_brain` | `routes/brain.py:47-51`, `routes/omega.py:26-36` | S1 (sécurité), puis décision LIA-D13 : maintenir, adapter ou retirer |
| D-S0-8 | CORS par défaut (`CORS_ORIGINS` absent ou `*`) : toute origine est acceptée **avec identifiants** (`allow_origin_regex=".*"`) | `server.py:137-145` | S1 : refus de démarrer en production sans liste explicite |

## 4. Reproduire

```bash
python3 -m venv venv && grep -vE '^(emergentintegrations|litellm)' backend/requirements.txt > req.txt
venv/bin/pip install -r req.txt pytest-asyncio==0.23.8
docker run -d --name s0-mongo --network host mongo:7.0 --bind_ip 127.0.0.1 --port 27017
# copier harness/ dans un dossier, y placer venv/, adapter envB.sh (S0_HARNESS_DIR), puis :
./run_s0.sh p1    # résultats dans proto/p1/{junit.xml,pytest.log,server.log,egress.jsonl}
```

## 5. Critères d'acceptation de S0

| Critère | État |
|---|---|
| Suite exécutée sur une base connue (`b898e19`) | **Fait** |
| Résultats initiaux conservés (JUnit, journaux, sorties réseau, environnement) | **Fait** (`raw/`) |
| Cause documentée pour chaque échec et chaque test non exécuté | **Fait** (§2) ; une cause reste [H] (B2) |
| Aucun test supprimé, désactivé ou contourné | **Fait** (`git diff b898e19 -- backend frontend` est vide) |
| Reproductibilité démontrée | **Fait** (3 exécutions identiques) |
| CI | **Non fait** : à proposer en S1 (ajout de `.github/workflows/`, à valider) |
