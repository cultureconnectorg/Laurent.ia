# Architecture de Découpage — Roadmap Technique Laurent.ia

> Ce document définit la **séparation physique** entre les couches **open** et **privées** de la plateforme Laurent.ia. Toute contribution au dépôt doit s'y conformer.

---

## 1. Modèle Open-Core

Laurent.ia adopte le modèle **Semi-Open Source Contrôlé** : ce qui peut être audité par la communauté l'est, ce qui constitue l'avantage compétitif souverain (Persona, routage cryptographique, signature) reste sous coffre.

```
laurentia-core/
├── 🔓 open-core/                 # BSL 1.1 → Apache 2.0 (31 mai 2029)
│   ├── frontend-ui/              # React, Tailwind, OrbeLaurentIA, Composer, EnergyBraids
│   ├── SDK/                      # Widget JS + Client Python
│   └── bridges/                  # Interfaces Python abstraites (Kiltikonet, LabelOS, etc.)
│
└── 🔒 sovereign-brain/           # Propriétaire CVLN Group (submodule privé)
    ├── cvl_brain_knowledge.py    # Persona v1.2, règles anti-jailbreak
    ├── fingerprint_router.py     # HMAC-SHA256, persistance fantôme cryptographique
    └── pipeline_echo/            # Génération PDF souverain, QR de signature, propagation
```

---

## 2. Stratégie de Découplage

### 2.1 Alias d'Import (Module Façade)

**Règle stricte :** toute importation `open-core` → `sovereign-brain` passe par un module de façade local et stable.

```python
# open-core/backend/app/core/__init__.py
"""
Façade d'accès au noyau souverain.

Si `sovereign-brain` est présent (déploiement officiel), les implémentations
réelles sont exposées. Sinon (fork public), des fallbacks mockés ou une
exception explicite sont retournés.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

try:
    # Tentative d'import du noyau privé
    from sovereign_brain import (
        cvl_brain_knowledge as _brain,
        fingerprint_router as _fp,
    )
    from sovereign_brain.pipeline_echo import (
        signature as _signature,
        echo_generator as _echo,
    )
    _SOVEREIGN_AVAILABLE = True
except ImportError:
    logger.warning(
        "sovereign-brain non disponible — basculement en mode démo. "
        "Les fonctions Persona, signature et fingerprint utilisent des stubs."
    )
    _SOVEREIGN_AVAILABLE = False
    from .stubs import (  # noqa: F401
        cvl_brain_knowledge as _brain,
        fingerprint_router as _fp,
        signature as _signature,
        echo_generator as _echo,
    )


# Interfaces stables exposées au reste de l'open-core
def build_system_prompt(*args, **kwargs) -> str:
    return _brain.build_system_prompt(*args, **kwargs)


def device_id_from_fingerprint(fp: str | None) -> str | None:
    return _fp.device_id_from_fingerprint(fp)


def build_signature_section(session_id: str | None) -> str:
    return _signature.build_signature_section(session_id)


def generate_echo(session_id: str, source: str) -> dict:
    return _echo.generate(session_id, source)


SOVEREIGN_AVAILABLE = _SOVEREIGN_AVAILABLE
```

**Conséquence :** un développeur tiers qui clone le dépôt public peut faire tourner la stack avec des stubs (chat dégradé, pas de signature PDF, pas de pipeline echo). L'équipe CVLN active le coffre via le submodule au déploiement.

### 2.2 Injection de Secrets

**AUCUN secret** ne doit figurer dans le code source `open-core`. Sources autorisées exclusivement :

```python
import os
LAURENTIA_SECRET_SALT = os.environ["LAURENTIA_SECRET_SALT"]
LAURENTIA_ENCRYPTION_KEY = os.environ["LAURENTIA_ENCRYPTION_KEY"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]
```

Les fichiers `.env` sont **gitignorés**. Aucun fork public ne dispose des secrets de production.

### 2.3 Séparation Physique GitHub

- **`open-core/`** → Dépôt public `cvlngroup/laurentia-core` (BSL 1.1)
- **`sovereign-brain/`** → Dépôt privé `cvlngroup/laurentia-sovereign-brain` (propriétaire)
- **Submodule** : `open-core/` référence `sovereign-brain/` via `.gitmodules` (clone ssh restreint à l'organisation CVLN Group).

---

## 3. Mapping des Fichiers (à la migration physique)

| Fichier actuel | Destination | Niveau |
|---|---|---|
| `frontend/src/**` | `open-core/frontend-ui/` | 🔓 Public |
| `backend/routes/laurentia_gateway.py` | `open-core/backend/routes/` | 🔓 Public |
| `backend/routes/billing.py` | `open-core/backend/routes/` | 🔓 Public |
| `backend/routes/auth.py` | `open-core/backend/routes/` | 🔓 Public |
| `backend/routes/rgpd_purge.py` | `open-core/backend/routes/` | 🔓 Public |
| `backend/services/crypto.py` | `open-core/backend/services/` | 🔓 Public *(algo standard)* |
| `backend/services/file_parser.py` | `open-core/backend/services/` | 🔓 Public |
| `backend/services/rate_limit_mongo.py` | `open-core/backend/services/` | 🔓 Public |
| `backend/services/cvl_brain_knowledge.py` | `sovereign-brain/` | 🔒 Privé |
| `backend/services/fingerprint.py` | `sovereign-brain/fingerprint_router.py` | 🔒 Privé |
| `backend/services/kiltikonet_bridge.py` | `sovereign-brain/bridges/` | 🔒 Privé *(secrets API)* |
| `backend/services/labelos_bridge.py` | `sovereign-brain/bridges/` | 🔒 Privé |
| `backend/routes/echo.py` | `sovereign-brain/pipeline_echo/` | 🔒 Privé |
| `backend/routes/pdf_export.py` (signature) | `sovereign-brain/pipeline_echo/signature.py` | 🔒 Privé |

**Bridges abstraits dans open-core :** les interfaces (classes abstraites, schémas Pydantic) sont publiques. Les implémentations concrètes (clés, URLs, signatures) restent privées.

```python
# open-core/bridges/kiltikonet_interface.py
from abc import ABC, abstractmethod
from pydantic import BaseModel

class FrekProfile(BaseModel):
    first_name: str
    wallet: dict
    cultural_profile: dict

class KiltikonetBridgeInterface(ABC):
    @abstractmethod
    async def validate_frek_id(self, frek_id: str) -> dict: ...
    @abstractmethod
    async def get_frek_profile(self, frek_id: str) -> FrekProfile: ...
```

---

## 4. Roadmap de Migration

### Étape 1 — **Préparation documentaire** *(✅ FAIT — 31 mai 2026)*
- `LICENSE.md` (BSL 1.1)
- `README.md` (manifeste v1.2)
- `ARCHITECTURE.md` (ce fichier)
- Code monolithique sous `/app/backend` et `/app/frontend` inchangé. Runtime stable à 64/64 GREEN.

### Étape 2 — **Formalisation des imports via façades**
- Créer `backend/app/core/__init__.py` (façade décrite en §2.1)
- Remplacer dans tous les fichiers `from services.cvl_brain_knowledge import X` par `from app.core import X`
- Ajouter `backend/app/core/stubs/` (fallbacks pour fork public)
- Continuer le runtime monolithique mais via interface stable.

### Étape 3 — **Migration physique des fichiers**
- Créer `/app/open-core/` et `/app/sovereign-brain/`
- Déplacer les fichiers selon le mapping §3
- Mettre à jour `requirements.txt`, `package.json`, `tsconfig.json` pour pointer sur les nouveaux chemins
- Vérifier 64/64 tests toujours GREEN après migration

### Étape 4 — **Configuration GitHub Open-Core**
- Push de `/app/open-core/` vers `github.com/cvlngroup/laurentia-core` (public, BSL 1.1)
- Push de `/app/sovereign-brain/` vers `github.com/cvlngroup/laurentia-sovereign-brain` (privé)
- Lier les deux via `.gitmodules` (submodule SSH)
- Configurer CI/CD : tests publics dans le repo open, tests souverains dans le repo privé

### Étape 5 — **SDK & Widget**
- Publier `open-core/SDK/python/` sur PyPI : `pip install laurentia-sdk`
- Builder `open-core/SDK/js/widget.js` et le servir sur `cdn.laurent.ia/widget.v1.js`
- Documentation publique sur `docs.laurent.ia`

---

## 5. Règles d'Or pour les Contributeurs

| ✅ DO | ❌ DON'T |
|---|---|
| Importer depuis `app.core` ou `app.bridges` | Importer directement depuis `sovereign_brain.*` |
| Utiliser `os.environ[...]` pour les secrets | Hardcoder une clé, sel, URL prod dans le code |
| Ajouter un fallback dans `app.core.stubs/` pour chaque nouvelle fonction privée | Casser le runtime quand `sovereign-brain` est absent |
| Documenter les interfaces publiques avec docstrings + types Pydantic | Exposer accidentellement la Persona ou le sel HMAC |
| Soumettre les pull requests sur `open-core/` | Tenter de modifier `sovereign-brain/` sans contrat Enterprise |

---

## 6. Convergence Conformité

Le découpage Open-Core protège **trois actifs simultanément** :

1. **Sécurité cryptographique** — clés, sel, persona jamais publiés
2. **Avantage stratégique** — pipeline echo, signature, routing restent secrets défense
3. **Conformité RGPD** — la table de liaison `device_id ↔ frek_id` est purgée à J+90 par `rgpd_purge.py` (public, auditable)

La transparence des composants publics renforce la confiance ; la fermeture du noyau préserve la souveraineté.

---

*« Open-core. Souveraineté. Confiance. »*

— **CVLN Group**, 31 mai 2026
