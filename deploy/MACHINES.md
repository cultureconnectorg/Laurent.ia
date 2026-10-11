# Ordinateur et portable — ressources, sauvegardes, perte d'un appareil

> Chiffres **mesurés** sur la pile réelle (11 oct. 2026), sauf mention [estimé].

## 1. Ressources nécessaires

| Élément | Mémoire vive | Disque | Source |
|---|---|---|---|
| MongoDB | ~200 Mio | image 1,2 Go + données | mesuré (`docker stats`) |
| Laurent.ia (backend) | ~90 Mio | image 1,15 Go | mesuré |
| FREKCORE | ~105 Mio | image 1,1 Go | mesuré |
| Proxy + interface web | ~17 Mio | image 72 Mo | mesuré |
| **Total hors moteur** | **~410 Mio** | **~3,5 Go** | mesuré |
| Moteur, Qwen2.5-1.5B (Q4_K_M) | ~1,5 à 2 Go | fichier 1,1 Go | fichier mesuré ; mémoire [estimé] |
| Moteur, Qwen2.5-7B (Q4_K_M) | ~6 Go | fichier 4,7 Go | [estimé] |

**Recommandation**

| Machine | Rôle | Minimum | Confortable |
|---|---|---|---|
| **Ordinateur** | Serveur permanent | 8 Go de RAM, modèle 1,5B | 16 Go de RAM ou plus, modèle 7B ; carte graphique NVIDIA ou Mac Apple Silicon (accélération : S5) |
| **Portable** | Client par WireGuard ; reçoit les sauvegardes chiffrées | n'importe quel portable récent | — |

**Vitesse mesurée** : sur un processeur sans carte graphique (runner GitHub, 4 cœurs), le modèle 1,5B répond correctement mais une première réponse avec le long prompt système peut dépasser 60 s. Pour un usage quotidien, il faut une carte graphique ou une puce Apple Silicon (S5).

## 2. Sauvegardes

| Quoi | Où | Comment |
|---|---|---|
| Bases (Laurent.ia + FREKCORE) | Portable | `scripts/backup.sh <clé age publique du portable> <cible>` : archive chiffrée **pour le portable seul**. Fréquence conseillée : quotidienne (tâche planifiée) |
| `deploy/.env` (clé de chiffrement de la mémoire, mots de passe) | **Hors ligne** : clé USB chiffrée **et** copie papier dans un lieu sûr | Une fois, puis à chaque changement |
| Clé privée `age` du portable | Portable + copie hors ligne | Sans elle, les sauvegardes sont illisibles |
| Poids du modèle | Rien à sauvegarder | Re-téléchargeables (fichiers publics, vérifiés par empreinte) |

**Testé** : une sauvegarde chiffrée pour une clé ne se déchiffre avec aucune autre clé.

## 3. Perte d'un appareil — procédures

### Perte ou panne de l'ordinateur

**Restauration testée réellement** : sauvegarde, suppression complète des volumes, puis restauration. Résultat : 17 et 70 documents avant comme après ; mémoire chiffrée relue à l'identique ; état FREKCORE conservé.

1. Nouvelle machine : installer Docker, cloner les deux dépôts.
2. Remettre **le même** `deploy/.env` depuis la copie hors ligne.
3. Récupérer la dernière sauvegarde depuis le portable.
4. `scripts/restore.sh <sauvegarde> <clé age privée du portable>`. Le script refuse d'écraser une base non vide.
5. `scripts/fetch-model.sh desktop`, puis `docker compose up -d`, puis `scripts/verify-sovereignty.sh`.

**Sans le `.env` d'origine, la mémoire est perdue** : testé, une autre clé ne déchiffre rien. C'est voulu, et c'est la raison de la copie hors ligne.

### Perte ou vol du portable

1. **Couper son accès** : sur l'ordinateur, retirer le bloc `[Peer]` du portable dans `wg/computer.conf`, puis redémarrer WireGuard. Le portable ne peut plus joindre Laurent.ia.
2. Si la **passkey** était sur le portable : la considérer comme compromise. FREKCORE peut **révoquer** le FREK-ID. C'est testé en C1 : la session ouverte est fermée en quelques secondes et la reconnexion est refusée. Ensuite, réenregistrer une passkey par le parcours de récupération de FREKCORE (voir §4).
3. Les sauvegardes présentes sur le portable sont chiffrées : sans la clé `age` (protégée par la session du portable), elles sont illisibles. Générer une **nouvelle** paire `age` pour le portable de remplacement.

### Perte des deux appareils

La copie hors ligne de `.env`, la clé `age` hors ligne et une sauvegarde suffisent à tout reconstruire sur une nouvelle machine (§3, ordinateur).

## 4. Passkey : où la garder

| Option | Souveraineté | Récupération |
|---|---|---|
| **Clé de sécurité FIDO2 physique** (recommandé) | Totale : la clé privée ne quitte jamais la clé physique | Prévoir **deux** clés. FREKCORE n'accepte qu'une credential sans preuve du titulaire, la seconde passe par son parcours de récupération ; **à tester en C1-bis** |
| Passkey intégrée à l'appareil (Touch ID, Windows Hello) | Totale tant qu'elle n'est pas synchronisée | Perdue avec l'appareil |
| Passkey synchronisée (iCloud, Google) | **Réduite** : la clé circule par le cloud d'Apple ou de Google (chiffrée de bout en bout, mais chez un tiers) | Simple |

## 5. Synchronisation entre les deux machines

| Mode | Synchronisation | État |
|---|---|---|
| **Portable client** de l'ordinateur (recommandé) | Inutile : une seule mémoire, sur l'ordinateur | Prêt (G1) |
| Portable autonome, hors ligne | Deux mémoires distinctes, **non synchronisées** | Limite connue : la synchronisation avec gestion des conflits relève de la voie F |
