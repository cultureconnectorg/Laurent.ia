# Laurent.ia sur tes machines — guide d'installation (G1)

> **Principe** : tout tourne chez toi, sur ton ordinateur ; ton portable s'y connecte par un tunnel privé.
> Moteur d'IA, mémoire, Laurent.ia et FREKCORE n'ont **aucun accès à Internet**. C'est Docker qui l'impose (réseau `internal`), pas une convention.
> Une seule exception, ponctuelle et volontaire : le **téléchargement initial des poids du modèle**. Ce sont des fichiers publics, vérifiés par empreinte, et aucune donnée te concernant n'est envoyée.

## 1. Architecture

```
               Ton portable ──── WireGuard (tunnel chiffré, 10.77.0.x) ────┐
                                                                            ▼
┌──────────────────────── Ton ordinateur (serveur) ──────────────────────────────┐
│  proxy (Caddy, HTTPS, autorité de certification locale)  ◄── seul port ouvert   │
│     │ /api                    │ page web                                       │
│  ┌──▼───────────── réseau `core` : AUCUNE route vers Internet ───────────────┐ │
│  │ backend Laurent.ia ── engine (llama.cpp + modèle open-weight)             │ │
│  │        │                                                                  │ │
│  │        ├── frekcore (identité FREK-ID, passkeys, preuves)                 │ │
│  │        └── mongo (authentification activée : un utilisateur par système, │ │
│  │                   Laurent.ia et FREKCORE ne voient pas leurs données      │ │
│  │                   mutuelles)                                              │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────┘
```

| Service | Rôle | Accès réseau |
|---|---|---|
| `proxy` | Interface web + HTTPS + relais vers l'API | Écoute seulement sur `BIND_ADDRESS` (127.0.0.1, ou l'adresse WireGuard) |
| `backend` | Laurent.ia (`APP_ENV=production`, verrous S1 et S2 actifs) | Aucune sortie |
| `engine` | Moteur souverain (llama.cpp) | Aucune sortie |
| `frekcore` | FREKCORE, construit depuis son propre dépôt | Aucune sortie |
| `mongo` | Base de données, authentification activée | Aucune sortie |

## 2. Prérequis

| | Ordinateur (serveur) | Portable |
|---|---|---|
| Système | macOS, Linux ou Windows 11 (avec WSL2) | macOS, Linux, Windows |
| Logiciels | Docker (Docker Desktop sur Mac et Windows), `git`, `openssl`, `python3`, `curl` | WireGuard (application officielle) ; `age` pour lire les sauvegardes |
| Mémoire | 16 Go de RAM conseillés (modèle 7B) ; 8 Go minimum (modèle 1,5B) | — |
| Disque | ~10 Go | ~2 Go pour les sauvegardes |

Sous Windows, lance les scripts depuis WSL2 (Ubuntu).

## 3. Installation sur l'ordinateur

```bash
# 1. Les deux dépôts côte à côte
git clone https://github.com/cultureconnectorg/Laurent.ia.git
git clone https://github.com/cultureconnectorg/frekcoreAout2026.git
cd Laurent.ia/deploy

# 2. Secrets générés localement (fichier .env, lisible par toi seul)
scripts/init-secrets.sh                       # accès local : https://localhost:8443

# 3. Modèle open-weight, téléchargé une fois et vérifié par empreinte
scripts/fetch-model.sh desktop                # Qwen2.5-7B (ou « laptop » : 1,5B, plus léger)

# 4. Démarrage
docker compose --profile engine up -d --build

# 5. Contrôle de souveraineté (doit tout afficher en OK)
scripts/verify-sovereignty.sh
```

Ouvre ensuite **https://localhost:8443/laurentia**. Le navigateur signale un certificat inconnu : c'est l'autorité de certification locale de Caddy. Pour supprimer l'avertissement, installe-la sur ta machine comme autorité de confiance :

```bash
docker compose cp proxy:/data/caddy/pki/authorities/local/root.crt ./laurentia-root.crt
```

**Garde une copie hors ligne** de `LAURENTIA_ENCRYPTION_KEY` (dans `.env`). Sans elle, la mémoire ne peut pas être déchiffrée.

## 4. Le portable

### Mode 1 — accès à distance (recommandé)

Le portable utilise le serveur de l'ordinateur à travers un tunnel WireGuard. Ta mémoire reste à un seul endroit, l'ordinateur ; il n'y a donc aucun conflit de synchronisation.

```bash
# Sur l'ordinateur. L'adresse publique est celle de ta box, avec le port UDP 51820
# redirigé vers l'ordinateur.
scripts/wireguard-setup.sh ton-adresse-publique:51820
```

1. Importe `wg/computer.conf` dans WireGuard sur l'ordinateur, et `wg/laptop.conf` sur le portable.
2. Dans `.env`, règle `BIND_ADDRESS=10.77.0.1`, `PUBLIC_ORIGIN=https://10.77.0.1:8443` et `SITE_ADDRESSES="localhost, 10.77.0.1"`, puis lance `docker compose --profile engine up -d`.
3. Sur le portable, ouvre **https://10.77.0.1:8443/laurentia**.

Le tunnel ne transporte que le trafic du portable vers l'ordinateur. Aucun service tiers n'intervient : pas de relais, pas de compte en ligne.

### Mode 2 — portable autonome, hors ligne

Même installation que l'ordinateur, avec `scripts/fetch-model.sh laptop`. **Limite actuelle** : cette instance a sa **propre** mémoire, qui n'est pas synchronisée avec l'ordinateur. La synchronisation entre les deux instances fait partie de la voie F du rail ; elle n'est pas encore faite.

### Sauvegardes chiffrées vers le portable

```bash
# Sur le portable, une fois :  age-keygen -o ~/.laurentia-backup.key  (garde la clé privée)
# Sur l'ordinateur, régulièrement :
scripts/backup.sh age1…(clé publique du portable) laurent@10.77.0.2:~/laurentia-backups
```

L'archive contient Laurent.ia et FREKCORE. Elle est chiffrée **pour le portable seul**.

## 5. FREKCORE

- Construit **depuis son dépôt** (`frekcoreAout2026`), sans modification, et isolé comme les autres services.
- Base séparée (`frekcore`) avec son propre utilisateur : Laurent.ia ne peut pas lire les données de FREKCORE, ni l'inverse.
- Laurent.ia est déclaré comme client FREKCORE `cvl-brain`. Son secret est généré par `init-secrets.sh`, et son origine WebAuthn vaut `PUBLIC_ORIGIN`.
- Fonctions de FREKCORE qui **sortaient vers Internet** et qui sont **bloquées** ici par construction :
  - ancrage OpenTimestamps (qui n'envoyait que des empreintes) ;
  - synchronisation Baserow ;
  - géocodage OpenStreetMap ;
  - envoi d'e-mails.

  Leur réactivation éventuelle sera une décision explicite.
- **Écart connu, à corriger dans le lot C1** : le pont de Laurent.ia appelle `/api/frek/validate/{id}` et `/api/frek/{id}/profile`, routes **absentes** de FREKCORE. FREKCORE expose `/api/frek/verify/{id}` et les passkeys sous `/api/v1/identity-client/passkeys/…`. La connexion par FREK-ID et passkey sera branchée sur ces routes en C1.

## 6. Ce qui est vérifié, et comment

| Garantie | Vérification |
|---|---|
| Aucun service interne ne peut joindre Internet | `verify-sovereignty.sh` : réseau `internal`, plus une sonde active depuis le backend et depuis FREKCORE (« Network is unreachable ») |
| Le moteur qui répond est le moteur local | `/api/health` → `"engine": "sovereign"` |
| Aucune clé de fournisseur externe | `verify-sovereignty.sh` ; le backend **refuse de démarrer** en production sinon (S1.4) |
| L'interface ne charge rien d'un tiers | `verify/browser_check.py` : un vrai navigateur enregistre chaque requête ; toute requête hors de la machine fait échouer le contrôle |
| Secrets générés sur la machine, jamais versionnés | `.env` en mode 600, ignoré par git |

## 7. Limites actuelles (honnêtes)

- **Connexion** : l'authentification Emergent de l'ancien produit ne fonctionne pas ici, et c'est voulu. La connexion par passkey FREKCORE arrive avec **C1**. En attendant, l'interface fonctionne en accès local ou par le tunnel privé.
- **GPU** : le moteur conteneurisé utilise le processeur. Sur un Mac Apple Silicon, un moteur natif (Metal) sera beaucoup plus rapide ; une variante est prévue en S5.
- **Mémoire à deux principaux** (frontière publique / personnelle prouvée par MongoDB) : lot **S3**.
- **Synchronisation entre ordinateur et portable autonome** : voie **F**.
