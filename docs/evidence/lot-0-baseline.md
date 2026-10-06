# Preuve — état de référence des tests existants (avant toute modification)

- **Date** : 6 octobre 2026
- **Commit testé** : `48f69d9` (code applicatif inchangé depuis `b898e19`)
- **Environnement** : conteneur de développement isolé, Python 3.13, dépendances de `backend/requirements.txt` installées depuis PyPI, **sans MongoDB et sans serveur API en ligne**, données factices uniquement.

## Commandes

```bash
pip install -r requirements.txt   # sans litellm (URL Emergent) ni emergentintegrations
pip install emergentintegrations==0.1.2
#  → ERROR: No matching distribution found for emergentintegrations==0.1.2

cd backend
MONGO_URL=mongodb://localhost:27017 DB_NAME=test LAURENTIA_ENCRYPTION_KEY=x LAURENTIA_SECRET_SALT=x \
  timeout 900 python -m pytest tests -q -p no:cacheprovider --continue-on-collection-errors
```

## Résultats

| Mesure | Valeur |
|---|---|
| Tests collectés | **118** (le PRD en annonce 128) |
| Fichiers non importables | **2** : `test_briefing_contract.py`, `test_social_agent.py` — `ModuleNotFoundError: emergentintegrations` |
| Tests exécutés avant la limite de 15 min | 49 |
| Réussis | 26 |
| Échoués | 23 (attente d'une base MongoDB ou d'un serveur API, environ 30 s chacun) |
| Non exécutés | 69 (limite de temps atteinte) |

## Constats

1. **Le projet ne s'installe pas hors de la plateforme Emergent** : `emergentintegrations` n'est pas publié sur PyPI et `litellm` pointe vers un fichier hébergé par Emergent. Toute la chaîne cognitive, l'application (`server.py` importe la passerelle qui importe `services/cvl_brain.py`) et le contrat `laurentia.briefing` en dépendent.
2. **La suite n'est pas autonome** : une partie des tests exige une base MongoDB réelle et un serveur API démarré. Le badge « 64/64 GREEN » du README et les « 128/128 » du PRD ne sont **pas reproductibles** en l'état.
3. **Conséquence pour le Lot 0** : rendre la suite exécutable de façon autonome (base de test locale ou simulée, modèle factice) est un prérequis avant toute transformation, pour pouvoir prouver la non-régression.
