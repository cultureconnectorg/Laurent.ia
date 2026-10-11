# S2 : moteur souverain derrière `cvl_brain`, fiche de preuve

> 11 octobre 2026 · Branche isolée `claude/s2-sovereign-engine`, créée depuis `claude/s1-reliability-guards`.
> **Sans fusion, sans déploiement, sans changement de production.** S1 et S2 forment un ensemble : S1 seul ne doit pas être déployé.

## 1. Résultat

| Mesure | S0 | S1 | **S2** |
|---|---|---|---|
| Tests collectés | 131 | 169 | **185** (+3 tests de vraie inférence, sautés hors du job dédié) |
| Réussis | 121 | 160 | **185 / 185** |
| Échoués | 10 | 9 (B1) | **0** |
| `emergentintegrations` installé | requis | remplacé par un module qui échoue | **inutile : l'application démarre et passe tous ses tests sans lui** |
| Sorties réseau pendant la suite | 15 | 0 | **0** |
| Reproductibilité | — | — | **3 exécutions identiques** (185/185) |

Les 9 tests B1, qui exigeaient un moteur d'inférence, passent désormais avec le moteur local. La liste de référence des échecs connus est **vide**.

## 2. Ce qui a changé

| Élément | Avant | Après | Preuve |
|---|---|---|---|
| `services/cvl_brain.py` (nom, fonctions et signatures **conservés**, LIA-D23) | SDK Emergent → Anthropic, chargé à l'import du module | Client HTTP simple vers `BRAIN_ENGINE_URL` (protocole compatible OpenAI, **sans SDK de fournisseur**), avec un **vrai flux**. Chemin Emergent **conservé** (LIA-D20), mais seulement si aucun moteur n'est configuré, en développement ou en test, et avec `EMERGENT_LLM_KEY` défini. **Refusé en environnement déployé.** Sans moteur : erreur visible (`BrainEngineError`) | `test_s2_inference_paths.py` |
| Verrous de démarrage | — | Un environnement déployé **exige** `BRAIN_ENGINE_URL` | `test_s1_startup_checks.py` |
| `/api/health`, `/api/brain/health` | Annonçaient `claude-sonnet-4-5…` | Annoncent le moteur qui répond réellement : `engine`, `model` | Tests de santé |
| `routes/billing.py` (B2C gelé) | Import d'Emergent au chargement | Import paresseux, à l'usage seulement | Démarrage sans `emergentintegrations` |
| Dépendances | `litellm` installé depuis un fichier hébergé chez Emergent | Retiré (il n'était importé nulle part) | T1 |
| Harnais de test | Module de remplacement qui échoue (S0, S1) | **Moteur local déterministe** : un vrai serveur HTTP, réponse fixe, journal des prompts reçus | `tests/_harness/fake_engine.py` |

## 3. Tests ajoutés : rouge avant S2, vert après

`test_s2_inference_paths.py`, 15 tests. **Avant S2 : 13 échecs sur 15** (`raw/red-before-s2-with-stub.txt`). Sans Emergent installé, l'ancien code ne se charge même pas (`raw/red-before-s2-no-emergent.txt`).

| Garantie | Test |
|---|---|
| P1 conversation, P2 briefing, P3 `chat-enriched`, P4 omega, P5 écho, P6 agent social : **chaque chemin atteint le moteur local** (vérifié par le journal du moteur), sous garde réseau | `test_p1` à `test_p6` |
| Moteur coupé ou absent : **échec visible** sur chaque chemin, **jamais** de bascule vers un fournisseur | `test_p1/p2/p5_fails_visibly…`, `test_unconfigured…` |
| Chemin Emergent **refusé en déployé**, sans même charger le SDK | `test_legacy_provider_path_is_refused_when_deployed` |
| Les points de santé disent la vérité | `test_health_reports_the_sovereign_engine` |
| **T1** : analyse syntaxique de tout le code de production. Aucun import de SDK de fournisseur, hors deux imports paresseux documentés (chemin historique et paiement gelé). Le démarrage du serveur ne charge **aucun** module de fournisseur | `test_t1_…` (2 tests) |

P7 (génération d'images) n'a pas de test de chemin dédié. Il est couvert par `test_image_generator.py` et par le verrou de démarrage, qui refuse une `SD_API_URL` hors liste blanche.

## 4. Vraie inférence (job CI `real-inference`)

- **Modèle** : Qwen2.5-0.5B-Instruct (open-weight, Apache-2.0), servi par llama.cpp sur le runner, en local (`127.0.0.1`). L'empreinte SHA-256 des poids est archivée.
- **`test_s2_real_engine.py`** (3 tests) :
  1. réponse directe, avec un **contrôle de qualité** (« Paris ») qu'une réponse fixe ne passe pas : vérifié, le moteur déterministe y échoue ;
  2. conversation complète diffusée en flux, puis **stockée chiffrée** ;
  3. contrat de briefing.
- **Conditions de validation** : ces 3 tests verts, et **zéro sortie réseau**.
- Les autres tests de la suite, exécutés contre le modèle de 0,5 milliard de paramètres, sont **rapportés** mais ne bloquent pas : la qualité ou le format d'un si petit modèle n'est pas l'objet du test. Le choix du vrai modèle relève de S5.
- **Résultat du premier passage : voir §6.**

## 5. Modifications de tests existants (justifiées)

| Fichier | Changement | Justification |
|---|---|---|
| `test_laurentia_backend.py`, tests de santé | `model == "claude-sonnet-4-5…"` remplacé par : moteur souverain + modèle configuré + aucun « claude » | L'exigence a changé (LIA-D8). L'ancien test exigeait un modèle externe |
| `test_s1_startup_checks.py` | Cas « `BRAIN_ENGINE_URL` absent » ajouté ; référence au module de remplacement retirée | Nouveau verrou ; module supprimé |
| `test_s1_legacy_routes_auth.py`, `conftest.py` | Client de test partagé pour toute la session | Le client MongoDB de l'application est lié à une seule boucle d'événements |

Aucun test supprimé, désactivé ni marqué « échec attendu ». Les 3 tests de vraie inférence sont **sautés** dans la suite par défaut (il faut un vrai modèle) et **exécutés** dans le job dédié.

## 6. Limites et suites

- **[NV] Matériel de production** : non connu. Le modèle et le serveur d'inférence réels sont choisis en S5.
- **Persona B2C** : le prompt système envoyé au moteur (`cvl_brain_knowledge`) décrit encore le persona grand public « Laurent.ia v0.8 … Diaspora ». C'est contraire à LIA-D6 (pas de persona) et à LIA-D1. **À traiter dans la voie D** (Identity, Context).
- **`emergentintegrations` reste listé** dans `requirements.txt` (transition, LIA-D20). Il n'est plus nécessaire au fonctionnement. Son retrait sera décidé avec le chemin historique.
- **Premier passage de la CI** : *(complété après exécution)*.
