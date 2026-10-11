# Preuve — nettoyage sécurité et souveraineté (11 octobre 2026)

Suite de l'[audit des frontières](../audit/ECOSYSTEM_BOUNDARIES_AUDIT.md). Aucune valeur secrète n'est reproduite dans ce document.

## État par dépôt

| Dépôt | Problème | Statut | Preuve |
|---|---|---|---|
| **Laurent.ia** | Enregistrement de session PostHog (serveurs US) et script tiers Emergent chargés sur chaque page (fuites S2 et S3 du cadrage §3.1) | ✅ **Corrigé** : les deux scripts sont retirés de `frontend/public/index.html` ; HTML vérifié équilibré ; aucun code du front n'en dépend | `grep -nE "posthog\|emergent" frontend/public/index.html` → aucun résultat |
| **Agent Factory** (`cultureconnectorg/Cvlnagentfactory`, **public**) | Identifiant et mot de passe administrateur, jeton de service `AGT-000` en clair dans `memory/PRD.md`, 13 fichiers de test, `seed_data.py`, `compare_l4.py` et 12 rapports de test de l'archive | ✅ **Corrigé sur la branche `claude/redact-exposed-credentials`** (commit `9e70049`) : archive reconstruite avec les mêmes 267 fichiers, 0 identifiant restant, code Python modifié compilé ; valeurs remplacées par `ADMIN_PASSWORD` et `AGT000_SERVICE_TOKEN` ; README documentant ces variables. **À fusionner** | Vérification par expression régulière sur l'archive extraite ; comparaison des listes de fichiers |
| **KORA** (`kora2024/Kora-app`, **public**) | `memory/test_credentials.md` (identifiants de comptes) ; secret JWT avec valeur par défaut codée en dur dans 7 fichiers de routes ; 22 190 fichiers de cache versionnés. *(Le commit `48a9a4e` du 7 oct. avait déjà sécurisé `server.py` via `backend/config.py`.)* | ✅ **Corrigé sur la branche `claude/security-hygiene`** (commit `72a4394`) : les 7 routes utilisent `config.load_settings()` ; identifiants retirés ; cache exclu du suivi. **À fusionner** | Compilation OK ; les 7 routes importées partagent le secret du serveur ; `APP_ENV=production` sans `JWT_SECRET` → refus de démarrer ; **14/14 tests backend verts** |
| **Meta CVLN** (privé) | Clé PostHog dans le front ; aucune valeur secrète critique identifiée | ❌ Non traité : écriture refusée par le contrôle de sécurité de la session | — |
| **Kiltikonet** (privé) | Valeurs par défaut de mots de passe et jetons dans quelques tests ; documents d'inventaire de secrets à vérifier | Non traité dans cette passe | — |

## Ce qu'aucun nettoyage de fichier ne règle

Les identifiants d'Agent Factory et de KORA sont **déjà publics dans l'historique git** de dépôts publics. Les retirer de la version courante n'efface pas l'historique. **La seule correction réelle est de les renouveler** :
1. changer le mot de passe du compte administrateur d'Agent Factory et des comptes listés dans `memory/test_credentials.md` de KORA ;
2. révoquer et régénérer le jeton de service `AGT-000` d'Agent Factory ;
3. définir `JWT_SECRET`, `ADMIN_SECRET` et `STRIPE_API_KEY` dans l'environnement de chaque déploiement de KORA.
