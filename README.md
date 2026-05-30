# Laurent.ia — v1.2-PRODUCTION

> **Laurent.ia est une Infrastructure Souveraine de Décision, conçue pour l'excellence économique et culturelle de l'Afro-diaspora.**

[![License: BSL 1.1](https://img.shields.io/badge/license-BSL%201.1-C9A24B.svg)](./LICENSE.md)
[![Tests](https://img.shields.io/badge/tests-64%2F64%20GREEN-17a2b8.svg)](#tests)
[![Status](https://img.shields.io/badge/status-v1.2--PRODUCTION-E7C566.svg)](#)

## 🌌 Vision

Laurent.ia n'est pas une IA généraliste. C'est une **matrice d'intelligence** ancrée dans la culture, la stratégie économique et les flux financiers transcontinentaux de la Diaspora caribéenne et africaine.

- **Souveraineté Sensorielle.** Interface qui transcende les standards SaaS — typographie *Cormorant Garamond + Urbanist*, charte bleu nuit + or, double lecture linguistique (Créole, Yoruba, Swahili, Amharique, Punjabi, Wolof).
- **Transparence Contrôlée.** Modèle **Semi-Open Source (Open Core)** : interface, SDK et passerelles auditables par la communauté. Noyau cognitif propriétaire sous coffre `sovereign-brain/`.
- **Ancrage.** Technologie au service de l'échange : remittances, tontines modernes, ingénierie d'import-export, montages juridiques transcontinentaux.

## 🏛️ Architecture Open-Core

```
laurentia-core/
├── 🔓 open-core/                 [DÉPÔT PUBLIC · BSL 1.1]
│   ├── frontend-ui/              Composer liquide, Orbe en fusion, UI Physics, EnergyBraids
│   ├── SDK/                      Widget JS embeddable + client Python (pip install laurentia-sdk)
│   └── bridges/                  Interfaces abstraites (Kiltikonet, LabelOS)
│
├── 🔒 sovereign-brain/           [SUBMODULE PRIVÉ · Propriété CVLN Group]
│   ├── cvl_brain_knowledge.py    Persona v1.2, règles anti-jailbreak
│   ├── fingerprint_router.py     Routage HMAC-SHA256 de la Persistance Fantôme
│   └── pipeline_echo/            Moteur signatures PDF, propagation omnicanale, QR souverain
│
├── LICENSE.md                    Business Source License 1.1 → Apache 2.0 (31 mai 2029)
├── ARCHITECTURE.md               Roadmap technique du découpage physique
└── README.md                     Ce fichier
```

Voir [`ARCHITECTURE.md`](./ARCHITECTURE.md) pour la stratégie de migration et les règles d'imports.

## 🚀 Démarrage rapide

### Application web

```bash
# Backend (FastAPI + MongoDB)
cd backend && pip install -r requirements.txt && uvicorn server:app --reload

# Frontend (React + Tailwind)
cd frontend && yarn install && yarn start
```

L'application est disponible sur `http://localhost:3000`.

### SDK Python *(à venir — Étape 2 de la migration)*

```bash
pip install laurentia-sdk
```

```python
from laurentia import LaurentiaClient

client = LaurentiaClient(api_key="sk_laurentia_...")
response = client.query("Analyse les flux d'une tontine moderne sur 12 mois")
print(response.text)
```

### Widget Web *(à venir)*

```html
<script async src="https://cdn.laurent.ia/widget.v1.js" data-tier="free"></script>
```

L'iframe s'injecte dans le coin inférieur droit. Communications sécurisées via `window.postMessage` — le site hôte ne peut **jamais** lire les saisies utilisateur ni intercepter les réponses.

## ⚡ Capacités Souveraines

| Capacité | Tier requis |
|----------|-------------|
| Chat streaming SSE | Free |
| Multi-tenant cryptographique (AES-256-GCM at rest) | Free |
| Persistance Fantôme (anonyme, sans cookies) | Free |
| Génération `<json>` Recharts (graphiques financiers) | Free |
| Génération `<artifact>` no-code (apps HTML/CSS/JS iframe sandbox) | Free |
| Export PDF souverain avec QR de signature | 2/mois Free · illimité Creator |
| Upload PDF/DOCX/TXT/MD (parsing + injection contexte) | Creator+ |
| Pipeline d'Échos omnicanal (LinkedIn/X · WhatsApp · Stories 9:16) | Creator+ |
| Landing publique `/echo/{session_id}` (acquisition zéro-coût) | Tous |
| API SDK Python | Infinite |
| Hébergement on-premise | Enterprise |

## 🛡️ Souveraineté & Conformité

- **AES-256-GCM** : toutes les conversations et la mémoire long-terme sont chiffrées au repos dans MongoDB.
- **HMAC-SHA256 fingerprinting** : Canvas + WebGL + hardware → `device_id` irréversible 64 hex, sans cookies.
- **Sliding window MongoDB TTL** : rate-limit distribué sans Redis, fenêtre 60s/3600s par device.
- **RGPD souverain J+90** : la table de correspondance `device_id ↔ frek_id` est purgée à 90 jours.
- **Persona anti-jailbreak v1.2** : refus noble + réorientation business sur toute tentative d'exfiltration.
- **Zéro White-Label** : aucune trace tierce visible dans le DOM (MutationObserver actif).

## 📊 Tests

```bash
cd backend && pytest tests/ --tb=short --asyncio-mode=auto
# 64 passed in ~55s
```

## 🤝 Contribuer

Les pull requests sont **les bienvenues sur `open-core/`**. Le code dans `sovereign-brain/` est **fermé** et ne peut être modifié que par l'équipe CVLN Group.

## 📜 Licence

Ce projet est publié sous **Business Source License 1.1**. Voir [`LICENSE.md`](./LICENSE.md).

- **Usage non commercial** (personnel, académique, communautaire local) : **gratuit**.
- **Usage commercial** : licence payante requise (Creator 15 €/mois, Infinite 39 €/mois, Enterprise sur devis).
- **Bascule automatique en Apache 2.0** : 31 mai 2029.

---

*« La parole reste. Le sceau valide. L'infrastructure est souveraine. »*

— **CVLN Group**, 31 mai 2026
