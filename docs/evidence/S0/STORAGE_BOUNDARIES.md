# Frontières de mémoire au niveau du stockage — état actuel et faisabilité

> 11 octobre 2026 · Règle visée : **LIA-D21** [RC][AR]. La preuve d'une frontière doit venir **du système de stockage lui-même**, pas d'une convention dans le code.
> **[F]** fait vérifié dans le code · **[D]** observé à l'exécution · **[P]** proposition · **[NV]** non vérifié.

## 1. État actuel : aucune frontière n'existe au niveau du stockage

- **[F]** Un seul client MongoDB pour toute l'application : `server.py:23` (`AsyncIOMotorClient(mongo_url)`), partagé via `app.state.db` (`server.py:27`) par les **11 modules de routes**, y compris l'interface publique `POST /api/brain/briefing`.
- **[F]** Une seule chaîne de connexion (`MONGO_URL`), donc **un seul principal de base de données**. Toute route, publique ou interne, a techniquement accès à toutes les collections, notamment la mémoire personnelle.
- **[NV]** La configuration de production (authentification MongoDB activée ou non, rôle du compte applicatif) n'est pas vérifiable depuis le dépôt.
- **Conséquence** : aujourd'hui, l'interface publique ne lit pas la mémoire personnelle **uniquement parce que son code ne le fait pas** (`routes/brain.py:54-73`). Rien ne l'en empêche.

## 2. Collections utilisées par le code — classement [P] à valider en S3a

| Classe proposée | Collections |
|---|---|
| **Personnelle** (cible : espace personnel cloisonné de Brain, LIA-D21) | `laurentia_memory`, `laurentia_interactions`, `laurentia_echoes`, `laurentia_pdf_exports`, `laurentia_instances` (profil) |
| Identité et sessions | `users`, `user_sessions`, `laurentia_api_keys` |
| Opérationnelle | `laurentia_rate_limits`, `laurentia_usage`, `laurentia_activity_log`, `laurentia_guardrail_logs`, `laurentia_orchestrator_incidents`, `agent_logs`, `cvl_brain_agent_status`, `status_checks`, `laurentia_settings`, `laurentia_reports_daily`, `laurentia_reports_weekly`, `laurentia_corpus_reports` |
| B2C gelé (LIA-D2) | `payment_transactions`, `laurentia_echo_attributions`, `laurentia_social_posts`, `laurentia_social_analytics` |

Ce classement est une **proposition**. Les lecteurs et écrivains de chaque collection seront cartographiés en S3a (`DATA_MAP.md`) avant toute séparation [RC LIA-D20].

## 3. Faisabilité démontrée sur MongoDB (prototype hors application)

**Montage** : MongoDB 7.0 avec authentification activée (conteneur jetable, base `probe`), deux principaux.

| Principal | Droits |
|---|---|
| `laurentia_public` | Rôle `laurentia_public_role` : `find` sur `laurentia_instances` **uniquement** (`raw/storage-probe/role-public.txt`) |
| `laurentia_internal` | `readWrite` sur la base |

**Résultats [D]**

| Principal | `laurentia_instances` | `laurentia_memory` (personnelle) |
|---|---|---|
| `laurentia_public` | Autorisé | **Refusé par MongoDB** : code 13 `Unauthorized` |
| `laurentia_internal` | Autorisé | Autorisé |

**Preuves produites par le stockage lui-même**
1. **Journal de `mongod`** : entrée `id 20436`, « Checking authorization failed », code 13, sur `find: "laurentia_memory"` (`raw/storage-probe/mongod-authz-denied.jsonl`).
2. **Profileur de MongoDB** (niveau 2) : la seule opération réussie du principal public porte sur `probe.laurentia_instances` (`raw/storage-probe/profiler.jsonl`).

Ce prototype **démontre le mécanisme**. Il **ne démontre pas encore la séparation dans l'application**, qui relève de S3.

## 4. Critères d'acceptation de la frontière en S3 [P]

1. L'application utilise **deux connexions distinctes** : publique et interne. Les routes publiques ne reçoivent que la connexion publique.
2. **T5** est exécuté contre une MongoDB **avec authentification**, alimentée de données personnelles marquées :
   - chaque route publique est appelée réellement ;
   - aucune réponse ne contient de marqueur personnel ;
   - le **profileur** montre que le principal public n'a touché **aucune** collection personnelle ;
   - toute tentative est refusée par MongoDB (code 13), et cette tentative est visible dans le journal `mongod`.
3. Un test de **régression volontaire** : on fait lire la mémoire personnelle à une route publique, sur une branche de test. Le refus doit venir de MongoDB, pas du code. Cela prouve que la garde ne dépend pas de la discipline du code.
4. L'application **refuse de démarrer en production** si les deux principaux sont identiques ou si l'authentification MongoDB est désactivée.
