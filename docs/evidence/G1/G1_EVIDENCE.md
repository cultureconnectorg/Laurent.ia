# G1 : déploiement souverain sur tes machines, fiche de preuve

> 11 octobre 2026 · Branche isolée `claude/g1-self-hosted` (= S2 + paquet `deploy/`). **Sans fusion, sans déploiement chez toi tant que tu ne l'as pas lancé toi-même.**

## Vérifié ici, sur la pile réelle

Lancée avec `docker compose`, et le moteur de test à la place des poids du modèle, que cet environnement ne peut pas télécharger.

| Garantie | Résultat |
|---|---|
| Les 6 conteneurs démarrent, Laurent.ia en `APP_ENV=production` (verrous S1 et S2 actifs) | **OK** : `engine=sovereign` au démarrage |
| Réseau `core` déclaré `internal` | **OK** (`verify-sovereignty.sh`) |
| Aucune sortie possible depuis le backend | **OK** : sonde active vers 1.1.1.1:443 refusée |
| Aucune sortie possible depuis FREKCORE | **OK** : « Network is unreachable » |
| Aucune clé de fournisseur externe | **OK** |
| Conversation dans un **vrai navigateur** (Chromium), par HTTPS, à travers le proxy | **OK** : réponse affichée ; **11 requêtes, 0 vers un tiers** (`browser_check.png`) |
| Isolation des bases : l'utilisateur Laurent.ia ne lit pas la base FREKCORE | **OK** : refus de MongoDB, code 13 |
| Sauvegarde : `mongodump` chiffrée avec `age` pour la clé du portable | **OK** : déchiffrée avec la clé du portable, **refusée** avec toute autre clé |
| Configurations WireGuard ordinateur / portable | **OK** : générées en mode 600, analysées sans erreur par `wg-quick` |
| En-têtes HTTPS : CSP limitée à la même origine, HSTS ; autorité de certification locale | **OK** |
| Build du frontal sans paquet Emergent | **OK** (`@emergentbase/visual-edits` retiré) |

## Vérifié ailleurs

- **Vraie inférence** sur un modèle open-weight servi par llama.cpp, avec **0 sortie réseau** pendant une conversation réelle : job CI `real-inference` (voir la fiche S2).

## Non vérifié ici [NV]

- **Le moteur conteneurisé avec de vrais poids** (`engine`, image `llama.cpp:server-b5350`) : le téléchargement depuis HuggingFace est bloqué dans cet environnement. La vraie inférence est prouvée par le job CI `real-inference`, avec le même serveur llama.cpp.
- **Ta machine** : système, RAM et GPU inconnus. Le guide couvre macOS, Linux et Windows (WSL2).
- **Tunnel WireGuard réel** entre tes deux machines : il dépend de ta box (redirection UDP 51820).

## Écarts connus, à traiter

| # | Écart | Lot |
|---|---|---|
| 1 | Le pont FREKCORE de Laurent.ia appelle des routes qui n'existent pas dans FREKCORE (`/api/frek/validate`, `/api/frek/{id}/profile`) | **C1** |
| 2 | Pas encore de connexion par passkey : l'OAuth Emergent ne fonctionne pas ici, et c'est voulu | **C1** |
| 3 | Fonctions de FREKCORE qui sortaient vers Internet (OpenTimestamps, Baserow, OSM, e-mail) : **bloquées** ; réactivation = décision explicite | Décision |
| 4 | Une seule identité MongoDB par système (frontière publique / personnelle pas encore séparée) | **S3** |
| 5 | Portable autonome : sa mémoire n'est pas synchronisée avec celle de l'ordinateur | **F** |
| 6 | Moteur processeur seulement ; accélération Metal ou CUDA à ajouter | **S5** |
