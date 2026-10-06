# D8 — Sovereign Local Intelligence

- **Statut** : validée par Laurent · Octobre 2026
- **Remplace** : la v1 de D3 (accès direct à un fournisseur de LLM externe)
- **Référence** : [`docs/product/LAURENTIA_V1_CADRAGE.md`](../product/LAURENTIA_V1_CADRAGE.md) §2, §6, §7.3, §8

## Décision

Laurent.ia ne dépend d'aucun service LLM externe pour son fonctionnement cognitif en production.
La chaîne cognitive est entièrement locale :

```
modèle local → mémoire locale → connaissances locales → outils → agents → orchestration → action
```

## Définitions

- **Production** : tout système qui traite des données réelles de Laurent ou qui a une capacité d'action réelle sur son environnement.
- **Données cognitives** : prompts, mémoire, documents, contexte, voix, transcriptions, sorties du modèle.
- **LLM externe** : tout service hors de l'infrastructure de Laurent qui reçoit des données cognitives — API de LLM, intermédiaires (Emergent), reconnaissance vocale cloud, analytics avec enregistrement de session, scripts tiers capables de lire la page.
- **R&D isolée** : usage de services externes avec des données uniquement synthétiques ou publiques, sans dépendance opérationnelle de la production.

## Règles

1. Aucun LLM externe ne reçoit de données cognitives de production.
2. La production ne démarre pas si un adaptateur de LLM externe est configuré.
3. Aucun SDK de LLM externe n'est importé par un module de production (vérifié par test).
4. Les hôtes d'inférence autorisés sont déclarés explicitement ; tout autre hôte est refusé.
5. Aucune donnée réelle de Laurent n'est versionnée dans le dépôt ni transmise à un outil de développement.
6. Le choix du modèle local est fait sur benchmark (critères ci-dessous) et tracé ; il est révisable.

## Critères du benchmark

Qualité de raisonnement · français · contexte long · tool calling · latence · consommation mémoire · coût d'inférence · confidentialité · possibilité de fine-tuning · licence · possibilité d'évolution vers un modèle propriétaire.

Éliminatoires : licence interdisant la modification ou l'usage commercial des dérivés ; impossibilité d'exécution hors ligne.

## Trajectoire

N1 open-weight local (V1) → N2 spécialisation par fine-tuning sur les données de Laurent → N2+ pré-entraînement continu sur corpus de domaine → N3 modèle propre from scratch (décision de groupe, horizon long). Les trois niveaux sont distincts et ne doivent pas être confondus.

## Conséquences sur l'existant (preuves dans le cadrage §3.1)

- `services/cvl_brain.py` (Emergent → Anthropic) est retiré du chemin de production.
- PostHog avec enregistrement de session et le script `emergent-main.js` sont retirés du front.
- La reconnaissance vocale du navigateur est désactivée en production jusqu'à disposer d'une transcription locale.
- L'authentification Emergent est remplacée par une authentification locale.
- L'index vectoriel cloud proposé en v1 (MongoDB Atlas) est abandonné au profit d'un moteur local.
