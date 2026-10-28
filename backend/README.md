# Back-end — API Assurance et Gestion des Sinistres

API REST en **FastAPI** qui interroge l'ontologie stockée dans **Apache Jena Fuseki** avec **SPARQL** (via SPARQLWrapper).

## Installation (une seule fois)

```
cd backend
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## Lancement

1. `demarrer_fuseki.bat` (à la racine du projet), puis `recharger_donnees.bat` au premier lancement
2. `backend\demarrer_backend.bat`
3. Ouvrir **http://localhost:8000/docs** : chaque route peut y être testée (bouton « Try it out »)

## Organisation

| Fichier | Rôle |
|---|---|
| `app/main.py` | création de l'application, CORS, enregistrement des routes |
| `app/sparql.py` | exécution des requêtes, conversion des résultats, construction sûre des IRI et littéraux (anti-injection) |
| `app/ontologie.py` | règles lues dans l'ontologie : types autorisés, statuts (énumération), garanties obligatoires (axiomes), identifiants |
| `app/inferences.py` | maintien des déductions après chaque écriture (règles SPARQL) et relance complète de Pellet |
| `app/schemas.py` | validation des données envoyées (Pydantic) |
| `app/routers/` | routes : `assures`, `contrats`, `sinistres`, `referentiel`, `recherche` (recherche, statistiques, SPARQL libre, raisonnement), `nlp` |
| `app/nlp/` | module NLP : lexique tiré de l'ontologie, analyse spaCy, intention scikit-learn, génération SPARQL |

## Routes principales

| Méthode | Route | Description |
|---|---|---|
| GET | `/assures`, `/contrats`, `/sinistres` | listes avec filtres (`?q=`, `?type=`, `?valide=`, `?statut=`, `?grave=`, `?couvert=`, `?depuis=`, `?montantMin=`…) |
| GET | `/assures/{id}`, `/contrats/{id}`, `/sinistres/{id}` | détail avec les ressources liées |
| POST / PUT / DELETE | `/assures`, `/contrats` | création, modification, suppression |
| POST / DELETE | `/sinistres` | déclaration, suppression |
| PATCH | `/sinistres/{id}/statut` | changement de statut, affectation d'un expert |
| POST | `/sinistres/{id}/indemnisation` | calcul : min((dommages − franchise) × taux du barème, plafond) |
| GET | `/types`, `/ontologie/classes` | types autorisés et hiérarchie, lus dans l'ontologie |
| GET / POST / PUT / DELETE | `/assureurs`, `/experts`, `/garanties`, `/clauses`, `/baremes`, `/franchises` | référentiel complet (suppression refusée si la ressource est utilisée ; le type d'une garantie ou d'une clause ne change pas après création) |
| GET | `/recherche?q=` | recherche plein texte |
| GET | `/statistiques` | indicateurs du tableau de bord |
| POST | `/sparql` | requête SPARQL libre en lecture |
| POST | `/raisonnement` | relance Pellet : cohérence + déductions |
| POST | `/nlp/question` | question en français → requête SPARQL → résultats (voir `app/nlp/README.md`) |
| GET | `/nlp/exemples`, `/nlp/evaluation` | exemples d'entraînement, exactitude du classifieur d'intention |

## Règles métier contrôlées

- CIN unique (`owl:hasKey` sur Personne), CIN de 8 chiffres
- un contrat automobile / santé / vie doit avoir une garantie RC / frais médicaux / décès (axiomes `∃possedeGarantie`)
- un sinistre doit avoir au moins un dommage, être du même type que son contrat et dater de la période du contrat
- statut parmi l'énumération de l'ontologie ; indemnisation refusée si le sinistre est refusé, non couvert ou déjà indemnisé
- suppression refusée si des données dépendent de la ressource (assuré avec contrats, contrat avec sinistres)
