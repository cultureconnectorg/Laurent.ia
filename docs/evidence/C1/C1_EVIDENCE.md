# C1 : identité FREK-ID par l'API contrôlée de FREKCORE, fiche de preuve

> 11 octobre 2026 · Branche isolée `claude/c1-frek-identity`, créée depuis `claude/g1-self-hosted`. **Sans fusion, sans déploiement.** **Aucune modification du dépôt FREKCORE.**

## Architecture retenue (ton exigence)

- **Laurent.ia ne touche jamais la base de FREKCORE.** Il est un **client API authentifié** de FREKCORE :
  - identifiant `cvl-brain` ;
  - jeton OAuth2 `client_credentials` ;
  - **permissions explicites** accordées par l'API d'administration de FREKCORE (`deploy/scripts/frekcore-setup.sh`).
- **Garantie par le stockage** : l'utilisateur MongoDB de Laurent.ia ne peut pas lire la base `frekcore` (refus code 13, prouvé en G1).
- **Garantie par le réseau** : les deux services ne se parlent que sur le réseau interne, sans Internet.
- **FREKCORE vérifie** challenge, origine et signature de chaque passkey. Laurent.ia ne fait que relayer la cérémonie WebAuthn et ne voit aucune clé privée.
- **Principal unique** (LIA-D1) : seul `LAURENTIA_PRINCIPAL_FREK_ID` peut s'inscrire ou se connecter.

## Corrections

| # | Constat | Correction |
|---|---|---|
| 1 | Le pont appelait `/api/frek/validate` et `/api/frek/{id}/profile`, **inexistantes** dans FREKCORE | `/api/v1/identity/{id}/status` et `/detail`, via `services/frekcore_client.py` |
| 2 | **Faille** : `POST /api/auth/frek` ouvrait une session **avec le seul FREK-ID**, sans preuve de possession (identifiants `DEMO-*` acceptés même en production) | Fermée en déploiement ; les identifiants `DEMO-*` n'existent pas en déploiement |
| 3 | **Faille** : les routes de conversation, de mémoire et d'export n'exigeaient **aucune session** (le `frek_id` venait du corps de la requête) | `services/principal_gate.py` : **refus par défaut**. Toute route `/api` exige la session du titulaire, sauf une liste publique explicite (santé, passkey, briefing avec clé de service) |
| 4 | Une révocation dans FREKCORE ne fermait pas une session déjà ouverte | La barrière vérifie l'état du FREK-ID auprès de FREKCORE (cache 60 s) ; si FREKCORE révoque ou ne répond pas, la session est **supprimée** |
| 5 | Le frontal redirigeait vers l'OAuth Emergent (tiers) | Remplacé par la connexion par passkey FREK-ID (`frontend/src/lib/passkey.js`, menu) |
| 6 | WebAuthn refuse les adresses IP | Nom privé `laurentia.home.arpa` pour le portable (G1) |

## Preuves

**Tests unitaires `test_c1_access_control.py`** (27 tests). Avant C1 : **18 échecs + 1 erreur** (`raw/red-before-c1.txt`). Suite complète : **212 réussis, 3 sautés (vraie inférence), 0 régression, 0 sortie réseau.**

**Bout en bout, `deploy/verify/passkey_check.py`** : vrai FREKCORE, vrai MongoDB avec authentification, vrai Chromium avec un **authentificateur WebAuthn virtuel**, à travers l'interface (`raw/passkey_e2e_run.txt`) :

| # | Étape | Résultat |
|---|---|---|
| 1 | Un FREK-ID qui n'est pas le titulaire est refusé | OK |
| 2 | Inscription de la passkey (vérifiée par FREKCORE), puis connexion | OK |
| 3 | Route protégée accessible avec la session | OK |
| 4 | **Preuve FREKCORE** de l'identité (bloc notarié, plus vérification de la chaîne) | OK |
| 5 | Déconnexion, puis reconnexion avec la même passkey | OK |
| 6 | **Révocation** du FREK-ID par FREKCORE : la session ouverte est fermée et la reconnexion refusée (« FREK-ID révoqué ») | OK |
| 7 | **Désactivation du client `cvl-brain`** par FREKCORE : Laurent.ia ne peut plus l'appeler (401) | OK |
| 8 | Aucune requête hors de la pile | OK |

## Défaut de FREKCORE trouvé (non corrigé dans son dépôt)

- **Constat** : `identity_engine/client_passkeys.py:422` (`_consume_challenge`) soustrait une date sans fuseau, renvoyée par un **vrai** MongoDB, d'une date avec fuseau. La finalisation de toute passkey plante (500). Les tests de FREKCORE utilisent un MongoDB simulé, qui masque le problème.
- **Contournement de configuration**, sans toucher au code : `tz_aware=true` dans l'URL MongoDB de FREKCORE (`deploy/docker-compose.yml`), vérifié avec les versions exactes de FREKCORE (pymongo 4.5.0, motor 3.3.1).
- **Correctif recommandé dans FREKCORE**, à faire dans son dépôt **avec ton autorisation** : normaliser `created_at` en UTC avant la soustraction, et ajouter un test sur un vrai MongoDB.

## Limites

- La **récupération** d'une passkey perdue suit le parcours de FREKCORE : une deuxième credential exige une preuve du titulaire ou le recovery FREKCORE. Ce parcours n'est pas encore exposé dans Laurent.ia : c'est le prochain point de la préparation des machines.
- La preuve renvoyée par `/api/auth/passkey/proof` est le **premier bloc** du FREK-ID (émission). La notarisation `identity_holder_verified` existe bien dans la chaîne ; il reste à l'exposer de façon ciblée.

## Correctif issu de la revue de sécurité : inscription initiale

**Faille** : `register/begin` et `register/complete` étaient publiques. Une personne qui atteignait le proxy et connaissait le FREK-ID du titulaire pouvait inscrire **sa** passkey la première. FREKCORE ne garde que la première passkey : cette personne aurait obtenu la session du titulaire de façon durable.

**Correctif** (`routes/passkey_auth.py`, sans modifier FREKCORE) :
- l'inscription exige un **code à usage unique**, généré par `frekcore-setup.sh` ;
- seule l'empreinte SHA-256 de ce code est conservée, et la comparaison se fait en temps constant ;
- sans code configuré, l'inscription est **fermée** ;
- après la première liaison, elle est **fermée définitivement**, et cet état est stocké en base ;
- rien n'atteint FREKCORE avant ces contrôles ;
- la connexion par passkey n'est pas modifiée.

| Preuve | Avant le correctif | Après le correctif |
|---|---|---|
| `test_c1_enrollment.py` (6 tests, avec une doublure locale de FREKCORE) | **5 échecs, 1 réussite** : inscription acceptée sans code (200 au lieu de 403) — `raw/enrollment-unit-red-before-fix.txt` | **6 réussites** — `raw/enrollment-unit-green-after-fix.txt` |
| `verify/passkey_check.py` avec le **vrai FREKCORE** et un vrai navigateur | **Échec** : passkey inscrite **sans code** (200) — `raw/enrollment-e2e-red-before-fix.txt` | **14 étapes sur 14** : refus sans code (403) et avec un mauvais code ; inscription avec le bon code ; **fermeture après liaison, même avec le bon code (403)** ; révocation et désactivation toujours OK ; aucune requête hors de la pile — `raw/enrollment-e2e-green-after-fix.txt` |
| Suite complète | — | **218 réussis, 3 sautés (vraie inférence), 0 régression, 0 sortie réseau** |

## Correctif 2 issu de la revue : concurrence de l'inscription

**Faille** (signalée par Laurent) : le contrôle lisait l'état `completed` en base, puis appelait FREKCORE, puis enregistrait la fermeture **après** la réponse. Ces trois opérations n'étaient pas atomiques : deux cérémonies simultanées (double soumission, ou un code intercepté utilisé en même temps) passaient toutes deux le contrôle.

**Mesuré sur le code d'avant** (`e8b4778`, `raw/race-red-before-fix2.txt`) :
- 6 `register/begin` simultanés : **6 acceptés** (attendu : 1) ;
- 6 `register/complete` simultanés : **6 transmis à FREKCORE**. Cette sonde jetable n'est pas versionnée ; sa sortie figure dans le même fichier.

**Correctif** (`routes/passkey_auth.py`, sans modifier FREKCORE) : une réservation exclusive du parcours, prise par une seule opération atomique de la base. L'unicité de `_id` fait échouer toute réservation concurrente. `begin` renvoie un **verrou de cérémonie** ; seul ce verrou peut appeler `complete`, une seule fois, et cette prise est atomique elle aussi. Seule l'empreinte SHA-256 du verrou est stockée.

| État | Sens | Sortie |
|---|---|---|
| `reserved` | une cérémonie détient l'inscription | expire après `LAURENTIA_ENROLLMENT_LOCK_TTL` (300 s par défaut) en cas d'abandon |
| `completing` | FREKCORE est en train d'enregistrer la clé | n'expire jamais (blocage par défaut) |
| `uncertain` | réponse de FREKCORE perdue (5xx, délai dépassé, coupure) : la clé est peut-être enregistrée | reste **fermée** ; une connexion réussie par passkey prouve l'inscription et la clôt |
| `completed` | fermée définitivement | — |

Un refus de FREKCORE (4xx) libère la réservation. Un échec au `begin` la libère aussi, car un défi seul n'enregistre rien chez FREKCORE.

| Preuve | Avant | Après |
|---|---|---|
| `test_c1_enrollment_race.py` (10 tests : `begin` simultanés, `complete` simultanés, double soumission après succès, cérémonie interrompue puis expirée, verrou périmé refusé, refus FREKCORE, échec au `begin`, issue inconnue restant fermée même après expiration, clôture par connexion, verrou jamais stocké en clair) | **9 échecs** | **10 réussites**, 3 répétitions identiques — `raw/race-green-after-fix2.txt` |
| `verify/passkey_check.py` avec le **vrai FREKCORE**, Chromium et une durée de verrou de 3 s | — | **15 étapes sur 15**. Double soumission : `[409, 200]`. Les deux cérémonies abandonnées expirent, puis l'inscription par l'interface réussit, ce qui prouve que le frontal transmet bien le verrou. Le reste des étapes est inchangé — `raw/passkey_e2e_fix2.txt` |
| Suite complète (`run_suite.sh`) | 218 réussis | **228 réussis, 3 sautés (vraie inférence), 0 régression, 0 sortie réseau** — `raw/fix2-suite/` |

**Tests existants modifiés** : dans `test_c1_enrollment.py`, deux tests transmettent désormais le verrou obtenu au `begin` à `complete`, comme le fait le nouveau contrat. Leurs assertions sont inchangées.

**Limite restante.** L'état `uncertain` sans passkey réellement enregistrée bloque l'inscription. Dans ce cas, il faut une action explicite de l'opérateur : supprimer le document `principal_enrollment` (seulement s'il n'est pas `completed`), puis relancer `frekcore-setup.sh` pour obtenir un nouveau code. C'est un choix délibéré : fermer par défaut plutôt que risquer une seconde inscription.
