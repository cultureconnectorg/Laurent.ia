# ECOSYSTEM_CONNECT.md
## Contrats de configuration Render — CVLN / Laurent.ia

> **État : inventaire fondé sur le code consulté le 2026-10-14.**
> Les valeurs secrètes ne sont jamais commitées dans ce dépôt. Les éléments entre
> `<CHEVRONS>` sont à remplacer par les valeurs réelles avant de les enregistrer
> dans Render. Ne collez jamais ces exemples tels quels avec les chevrons.
>
> Ce document sépare les variables **confirmées par le code** des contrats
> **encore à vérifier**. Une URL configurée ne prouve pas qu'un service fonctionne.

## 1. Laurent.ia — Render Web Service

Service actuellement identifié : `https://laurent-ia.onrender.com`.

Dans **Render → Laurent.ia → Environment**, ajouter les variables suivantes.
Les variables de base de données déjà configurées et fonctionnelles ne doivent pas
être remplacées sans vérifier leur valeur actuelle.

### Requises

```dotenv
MONGO_URL=<URI_MONGODB_ATLAS_DU_CLUSTER_LAURENTIA>
DB_NAME=<NOM_DE_LA_BASE_LAURENTIA>
LAURENTIA_LLM_BASE_URL=<URL_DE_L_ENDPOINT_OPENAI_COMPATIBLE_SOUS_CONTROLE_CVLN>
LAURENTIA_CVLN_SERVICE_API_KEY=<SECRET_LONG_ALEATOIRE_PARTAGE_AVEC_LES_CONSOMMATEURS_AUTORISES>
```

- `MONGO_URL` et `DB_NAME` sont lus au démarrage par `backend/server.py`.
  Garder l'URI Atlas actuelle qui fonctionne ; ne pas coller le mot de passe dans
  un ticket, un commit ou un journal.
- `LAURENTIA_LLM_BASE_URL` est **obligatoire** pour l'inférence. Le code appelle
  une API compatible OpenAI et n'a volontairement aucun fallback vers un fournisseur
  public. La valeur doit pointer vers le moteur d'inférence réellement déployé et
  accessible depuis Render ; ne pas inventer une URL ni mettre une URL publique par défaut.
- `LAURENTIA_CVLN_SERVICE_API_KEY` protège `POST /api/brain/briefing`
  (et l'alias `POST /api/briefing`) via l'en-tête `X-API-Key`. Générer une clé
  aléatoire longue dans un gestionnaire de secrets, puis la saisir aussi côté
  consommateur autorisé. Ne jamais réutiliser le mot de passe MongoDB.

### Optionnelles / selon le moteur réellement déployé

```dotenv
LAURENTIA_LLM_MODEL=<IDENTIFIANT_EXACT_DU_MODELE_SERVI>
LAURENTIA_LLM_API_KEY=<CLE_DU_ENDPOINT_PRIVE_SI_REQUISE>
```

- Si le moteur privé n'exige pas de clé, `LAURENTIA_LLM_API_KEY` peut rester
  absent ; l'adaptateur utilise alors une valeur locale non secrète.
- `LAURENTIA_LLM_MODEL` doit correspondre au nom servi par l'endpoint, pas à un
  nom supposé.

### Ponts interservices

Configurer ces paires uniquement avec les URL et clés réellement provisionnées :

```dotenv
KILTIKONET_API_URL=<URL_BASE_REELLE_DE_KILTIKONET_SANS_SLASH_FINAL>
KILTIKONET_API_KEY=<CLE_DE_SERVICE_KILTIKONET>
KILTIKONET_TIMEOUT_SECONDS=5.0
LABELOS_API_URL=<URL_BASE_REELLE_DE_LABEL_OS_SANS_SLASH_FINAL>
LABELOS_API_KEY=<CLE_DE_SERVICE_LABEL_OS>
LABELOS_TIMEOUT_SECONDS=5.0
```

- Kiltikonet : si URL et clé sont configurées, les erreurs amont/timeout peuvent
  rendre la validation FREK-ID indisponible (HTTP 503). Vérifier l'endpoint et
  la clé ensemble avant le déploiement.
- LabelOS : si absent, le code retourne un contexte stub. Une URL seule ou une clé
  seule ne constitue pas une connexion active.
- Ne pas configurer une URL de démonstration ou un hôte privé inaccessible depuis
  Render.

## 2. CVLN Academy — Render Web Service

Source vérifiée : `CVL-ACADEMY/backend/.env.example`.
Utiliser les noms exacts ci-dessous. Remplacer les valeurs d'exemple par les valeurs
de production, jamais par les valeurs locales de développement.

### Socle de production

```dotenv
MONGO_URL=<URI_MONGODB_ATLAS_DEDIEE_A_ACADEMY>
DB_NAME=cvln_academy
ACADEMY_ENV=production
ENVIRONMENT=production
JWT_SECRET=<SECRET_ALEATOIRE_D_AU_MOINS_32_OCTETS>
CORS_ORIGINS=<ORIGINES_HTTPS_EXACTES_AUTORISEES_SEPAREES_PAR_VIRGULE>
```

- Générer un `JWT_SECRET` indépendant et fort.
- `CORS_ORIGINS` doit lister les véritables origines frontend, sans `*` en production.
  Exemple de **format uniquement** : `https://academy.example.org,https://admin.example.org`.
- `ACADEMY_ENV` et `ENVIRONMENT` sont deux paramètres distincts dans le code ;
  ne pas les fusionner.
- Utiliser une base Academy dédiée ou une base dont le cloisonnement a été validé.
  Ne pas partager automatiquement la base de Laurent.ia.

### Identité FREKCORE — uniquement après émission des identifiants de service

```dotenv
FREK_CORE_IDENTITY_AUTHORITY=frekcore
FREK_CORE_BASE_URL=<URL_BASE_REELLE_DE_FREKCORE>
FREK_CORE_CLIENT_ID=cvln-academy
FREK_CORE_CLIENT_SECRET=<SECRET_CLIENT_FREKCORE_EMIS_POUR_ACADEMY>
```

Le mode `local_dev` ne convient pas à l'émission d'identités de production.
Ne passer en mode `frekcore` qu'après vérification de l'URL, des identifiants et
de l'endpoint d'émission d'identité.

### Appels Academy → Agent Factory (contrat d'orchestration de missions)

```dotenv
CVLN_AGENT_FACTORY_URL=<URL_BASE_REELLE_DE_L_AGENT_FACTORY>
CVLN_AGENT_FACTORY_SERVICE_TOKEN=<TOKEN_SERVICE_SVC_EMIS_POUR_ACADEMY>
```

`CVLN_AGENT_FACTORY_API_KEY` est documentée dans l'exemple Academy comme alias
de compatibilité du bearer token ; préférer `CVLN_AGENT_FACTORY_SERVICE_TOKEN`
si le code déployé le prend en charge. Ne pas définir les deux avec des valeurs
différentes.

**Important :** l'exemple Academy distingue l'intégration d'orchestration de missions
du transport IA `ACADEMY_AI_TRANSPORT=agent_factory` et de son endpoint
`/api/cognitive/chat`. Le dépôt consulté précise que la seule présence de
`CVLN_AGENT_FACTORY_URL` ne prouve pas que le transport IA distant est actif.
Ne pas activer ce transport avant d'avoir vérifié le contrat et les tests de la
version réellement déployée.

Pour empêcher un fallback silencieux vers un fournisseur externe pendant la
validation du transport :

```dotenv
ACADEMY_AI_STRICT=true
```

Ne pas ajouter de `ANTHROPIC_API_KEY` pour contourner un endpoint Agent Factory
non fonctionnel. Si le transport souverain n'est pas opérationnel, le comportement
attendu est un échec explicite, pas un basculement externe.

### Autres variables Academy

N'ajouter que si la fonctionnalité correspondante est utilisée :
- `AI_PSEUDONYMIZATION_KEY` : clé de pseudonymisation dédiée recommandée.
- `FREK_CORE_API_KEY` ou `FREK_CORE_ACCESS_TOKEN` : contrats distincts utilisés par
  certains ponts ; ne pas les confondre avec `FREK_CORE_CLIENT_SECRET`.
- `CVLN_COMMAND_CENTER_URL` et `CVLN_COMMAND_CENTER_ACCESS_TOKEN` : l'exemple
  indique que l'accès actuel à Command Center repose sur un token d'accès déjà émis,
  et non encore sur une identité M2M pleinement provisionnée.
- `LAURENTIA_URL` / `LAURENTIA_API_KEY` : noms déclarés dans l'exemple Academy,
  mais confirmer dans le code consommateur qu'ils pilotent bien l'appel visé avant
  de les renseigner.

## 3. Meta CVLN — consommateur de Laurent.ia

Contrat côté fournisseur confirmé dans Laurent.ia :
- URL appelée : `POST https://laurent-ia.onrender.com/api/briefing`
- En-tête : `X-API-Key: <même-secret-que-LAURENTIA_CVLN_SERVICE_API_KEY>`
- Corps JSON : `request` ou `topic`, facultativement `context`, `trace_id`, `issuer`.
- Réponse JSON : `contract`, `version`, `trace_id`, `issuer`, `response`.

La variable **côté Meta qui stocke cette URL et le secret** doit garder le nom déjà
consommé par le code Meta. Le dépôt Meta disponible n'a pas fourni de contrat
d'environnement exploitable lors de cet audit ; ne pas inventer un nom comme
`LAURENTIA_URL` ou `LAURENTIA_API_KEY` côté Meta sans vérifier le code appelant.
Avant mise en production, relever le nom exact de ces variables dans le dépôt Meta
et y saisir la même clé interservices que dans Laurent.ia. La clé reste côté serveur,
jamais dans une variable frontend `REACT_APP_*` ou `NEXT_PUBLIC_*`.

## 4. Agent Factory — service lui-même

Le contrat Academy → Agent Factory confirme des variables **consommées par Academy**,
pas les variables d'environnement internes du serveur Agent Factory. Le fichier
d'environnement de production propre à Agent Factory n'a pas pu être confirmé dans
les sources consultées.

Par conséquent, ne coller aucune variable supposée dans le service Agent Factory.
Avant d'en établir la liste exacte, auditer le dépôt et la branche réellement déployés,
les fichiers de configuration et les routes `/missions/orchestrate`,
`/missions` et `/api/cognitive/chat`. Vérifier aussi le mode d'authentification,
l'identité autorisée à écrire dans le registre (notamment l'identité de service AGT-000
mentionnée par Academy), et les scopes du token. Cette section est volontairement
bloquante plutôt que d'inventer des clés.

## 5. Règles de déploiement et vérification

1. Ouvrir chaque service Render séparément → **Environment** → **Add from .env**,
   ou saisir les clés une par une. Les blocs ci-dessus sont des modèles : remplacer
   tous les marqueurs `<...>` avant de les enregistrer.
2. Les secrets doivent être générés/émis pour le service et stockés uniquement dans
   Render. Ne pas les commiter, les envoyer dans un chat, ni les placer dans le frontend.
3. Ne pas partager une clé interservices entre des services différents sauf si le
   contrat le demande explicitement. Pour Laurent.ia briefing, le consommateur autorisé
   doit recevoir la même clé que celle configurée dans `LAURENTIA_CVLN_SERVICE_API_KEY`.
4. Déployer d'abord un service à la fois. Vérifier les logs et les endpoints de santé,
   puis effectuer un vrai appel authentifié. Une réponse HTTP 200 de santé ne prouve
   pas que l'inférence, l'identité FREKCORE ou la création de mission fonctionnent.
5. Documenter chaque connexion avec l'URL effective, le résultat du test, l'heure UTC
   et l'identifiant de trace — sans enregistrer les secrets.
6. Après changement d'environnement, déclencher un déploiement Render pour que les
   valeurs deviennent actives.

## Sources de code consultées

- `cultureconnectorg/Laurent.ia`, branche `public` :
  `backend/server.py`, `backend/services/cvl_brain.py`,
  `backend/services/kiltikonet_bridge.py`, `backend/services/labelos_bridge.py`,
  `backend/routes/brain.py`.
- `cultureconnectorg/CVL-ACADEMY`, branche `main` :
  `backend/.env.example`.
- Contrat de saisie des variables dans Render :
  [Environment Variables and Secrets](https://render.com/docs/configure-environment-variables).

**Critère de complétion :** aucune variable ne doit être marquée « opérationnelle »
avant qu'un test réel depuis le service consommateur ait confirmé l'authentification
et le comportement métier attendu.
