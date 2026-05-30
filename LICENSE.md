# Business Source License 1.1 (BSL) — Laurent.ia

Copyright © 2026 CVLN Group. All rights reserved.

---

## 1. Paramètres de la Licence

- **Usage Licencié :** Utilisation **non commerciale, académique, personnelle et déploiements communautaires locaux** (tontines, micro-crédits associatifs, coopératives à but non lucratif) **autorisée**.
- **Usage Commercial Interdit :** Toute exploitation de cette infrastructure, de son UI Physics, de ses connecteurs ou de son moteur d'échos pour générer des revenus, dans un cadre professionnel ou au sein d'une entreprise, **nécessite une licence commerciale payante** auprès de CVLN Group (Rang Creator/Infinite).
- **Change Date :** **31 mai 2029** (36 mois après la publication initiale du 31 mai 2026).
- **Change License :** Après la Change Date, le code bascule **automatiquement sous licence Apache 2.0**.

---

## 2. Définitions

- **« Le Logiciel »** désigne l'ensemble du code source, des artefacts compilés, de la documentation et des composants visuels publiés sous la racine `open-core/` du dépôt Laurent.ia.
- **« Le Concédant »** désigne CVLN Group, propriétaire exclusif des droits sur Laurent.ia.
- **« Usage Commercial »** désigne toute utilisation du Logiciel destinée, directement ou indirectement, à générer un revenu, un profit ou un avantage économique pour une entreprise, une organisation à but lucratif, ou un prestataire de service. Cela inclut, sans s'y limiter : la vente, la sous-licence, l'hébergement payant, l'intégration dans un produit commercial, ou l'utilisation au sein d'une organisation employant plus de cinq (5) personnes.
- **« Usage Non Commercial »** désigne toute utilisation à des fins personnelles, académiques, de recherche, d'apprentissage, ou par des structures communautaires à but non lucratif (tontines, associations, coopératives, ONG) sans génération de revenu direct ni indirect.

---

## 3. Octroi de Licence (Usage Non Commercial)

Sous réserve du respect intégral des présentes conditions, le Concédant accorde à toute personne physique ou morale qualifiée d'**Usager Non Commercial** une licence mondiale, non exclusive, non transférable et révocable pour :

- a) **Utiliser** le Logiciel dans son contexte d'origine.
- b) **Étudier** son fonctionnement et adapter le code à ses besoins personnels.
- c) **Modifier** et **redistribuer** ses propres modifications, à condition de conserver la présente licence et la mention du Concédant.
- d) **Contribuer** au code public via des pull requests soumises au dépôt officiel.

---

## 4. Restrictions

L'Usager s'engage formellement à :

- a) **Ne pas exploiter commercialement** le Logiciel, ni directement ni indirectement, sans avoir préalablement souscrit une **Licence Commerciale Laurent.ia** auprès de CVLN Group (tier Creator à 15 €/mois, ou tier Infinite à 39 €/mois, ou contrat enterprise sur mesure).
- b) **Ne pas retirer** ni altérer les mentions de copyright, les sceaux d'authenticité, le manifeste « Certifié par l'Infrastructure Laurent.ia » ni les QR codes de signature présents dans les exports PDF du tier Free.
- c) **Ne pas reverse-engineer**, extraire ou répliquer les composants confidentiels stockés dans `sovereign-brain/` (Persona, routage cryptographique, pipeline d'échos, clés HMAC/AES). Toute tentative constitue une violation du secret défense de l'infrastructure.
- d) **Ne pas utiliser** les marques « Laurent.ia », « CVLN Group », « Intelligence Souveraine », ni les éléments graphiques associés (orbe, sceau or, charte bleu nuit) pour promouvoir un produit ou service concurrent.

---

## 5. Licence Commerciale

Pour tout usage commercial du Logiciel, l'Usager doit acquérir une licence payante au tarif en vigueur. Les paliers actuels :

| Plan | Usage autorisé | Tarif |
|------|---------------|-------|
| **Free** | Non commercial, personnel, académique, communautaire local | 0 € |
| **Creator** | Commercial petit volume (≤ 5 utilisateurs), exports illimités, pas de signature finale | 15 €/mois |
| **Infinite** | Commercial sans limite, multi-utilisateurs, API illimitée, support prioritaire | 39 €/mois |
| **Enterprise** | Hébergement on-premise, audit, SLA, fingerprinting custom | Sur devis |

Pour souscrire : `https://laurent.ia/pricing`

---

## 6. Avertissement Cryptographique

Les composants suivants relèvent du **Secret Défense de l'Infrastructure** et ne sont **jamais publiés** dans le dépôt open-core :

- La Persona Souveraine v1.2 (système prompt) et toutes ses évolutions.
- Le sel `LAURENTIA_SECRET_SALT` utilisé pour le hash HMAC-SHA256 du device_id.
- La clé `LAURENTIA_ENCRYPTION_KEY` utilisée pour le chiffrement AES-256-GCM at rest.
- Les bridges propriétaires vers Kiltikonet, LabelOS et autres infrastructures partenaires.
- Le pipeline d'échos omnicanal (génération de la signature de la constellation).

Toute personne ayant accédé à ces composants par une voie autre que la souscription d'une licence enterprise est tenue à la **confidentialité absolue**.

---

## 7. Limitation de Responsabilité

LE LOGICIEL EST FOURNI « EN L'ÉTAT », SANS GARANTIE D'AUCUNE SORTE, EXPRESSE OU IMPLICITE. EN AUCUN CAS LE CONCÉDANT NE POURRA ÊTRE TENU RESPONSABLE D'UN QUELCONQUE DOMMAGE DIRECT, INDIRECT, INCIDENT OU CONSÉCUTIF DÉCOULANT DE L'UTILISATION DU LOGICIEL.

---

## 8. Loi Applicable

La présente licence est régie par la loi française. Tout litige relèvera de la compétence exclusive des tribunaux de Paris.

---

## 9. Conversion Apache 2.0

Le **31 mai 2029**, le présent Logiciel basculera automatiquement sous **licence Apache 2.0**, ouvrant alors l'usage commercial libre à toute la communauté. Le fichier `LICENSE.md` sera mis à jour à cette date pour refléter le nouveau régime juridique.

---

*« La parole reste. Le sceau valide. L'infrastructure est souveraine. »*

— **CVLN Group**, mai 2026
