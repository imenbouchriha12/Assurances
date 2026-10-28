# Comment fonctionne le module NLP

Ce document explique pas à pas comment une question en français devient une requête SPARQL,
comment le résultat est mis en forme, et où intervenir pour étendre le module.

> En résumé : **aucun LLM**. La compréhension repose sur trois piliers —
> **spaCy** (analyse linguistique), **scikit-learn** (classification de l'intention)
> et **l'ontologie elle-même** (vocabulaire et chemins entre concepts).
> Le module ne « devine » donc rien qui ne soit dans les données : il relie des mots
> à des concepts, puis construit la requête avec un gabarit.

---

## 1. Vue d'ensemble

```
Question en français
        │
        ▼
[1] Pré-traitement                     analyse.py
    apostrophes, « 5 000 » → 5000, JJ/MM/AAAA → AAAA-MM-JJ
        │
        ▼
[2] Analyse spaCy                      analyse.py
    tokenisation, POS, lemmes, entités nommées
        │
        ├─── [3] Lexique de l'ontologie (lu dans Fuseki)      lexique.py
        │        labels, altLabels, individus, villes, statuts, synonymes
        │        + graphe des propriétés objet (domaine → portée)
        │
        ├─── [4] Matcher de concepts + comparaisons + dates    analyse.py
        │        « sinistres graves » → classe SinistreGrave
        │        « plus de 5000 »    → comparaison >
        │
        ▼
[5] Texte délexicalisé                 analyse.py
    « quel etre le CONCEPT », « combien de CONCEPT par CONCEPT »
        │
        ▼
[6] Intention                          intentions.py
    TF-IDF + régression logistique → lister | compter | somme | moyenne | maximum | minimum
        │
        ▼
[7] Génération SPARQL                  generateur.py
    classe principale, filtres, plus court chemin de propriétés, gabarit d'agrégat
        │
        ▼
[8] Exécution                          Fuseki http://localhost:3030/assurance/sparql
        │
        ▼
[9] Rédaction de la réponse            redaction.py
    gabarits, accords en nombre/genre, formats français
        │
        ▼
Réponse JSON → interface /question
```

Le point d'entrée est `service.repondre()` (`service.py`) ; l'API l'expose via
`POST /nlp/question` (`routers/nlp.py`).

---

## 2. Les fichiers du module

| Fichier | Rôle |
|---|---|
| `service.py` | Orchestration : préparation (cache), analyse → intention → génération → exécution → rédaction |
| `lexique.py` | Construit depuis l'ontologie le vocabulaire et le graphe de propriétés ; fournit `chemin()` (BFS) |
| `analyse.py` | Pré-traitement, pipeline spaCy, `Matcher` de concepts/comparaisons, dates, négations, texte délexicalisé |
| `intentions.py` | Exemples d'entraînement, classifieur TF-IDF + régression logistique, seuil de confiance, évaluation |
| `generateur.py` | Interprétation (classe principale, filtres) et génération de la requête SPARQL |
| `redaction.py` | Phrase de réponse en français, éléments affichables, accords grammaticaux |
| `synonymes.py` | Vocabulaire métier qui complète les labels de l'ontologie (statuts, attributs, dimensions, négations…) |
| `routers/nlp.py` | Routes `/nlp/question`, `/nlp/exemples`, `/nlp/evaluation` |

---

## 3. Étape 1 — Le lexique vient de l'ontologie (`lexique.py`)

Rien n'est codé en dur sur les données : le lexique est construit **par requêtes SPARQL**
au démarrage (et à chaque changement de données). `construire_lexique()` récupère :

| Source dans l'ontologie | Ce qu'on en fait |
|---|---|
| `rdfs:label` des classes | libellé + phrase reconnue (« Sinistre grave ») |
| `skos:altLabel` des classes | variantes de libellé |
| `rdfs:subClassOf` | hiérarchie (utilisée pour les ancêtres et les qualificatifs) |
| propriétés objet (`rdfs:domain`/`rdfs:range`) | graphe des relations entre concepts |
| propriétés de données + `xsd:float` | attributs numériques (prime, indemnisation, plafond…) |
| individus (`prenom`, `nom`, `raisonSociale`, `numeroContrat`, `libelleGarantie`…) | noms propres reconnus (« STAR », « Sarra », « CT-2025-003 ») |
| valeurs de `:adresse` et `:lieuSinistre` | villes |
| énumération de `:statutSinistre` (`owl:oneOf`) | statuts (« Déclaré », « EnExpertise »…) |
| `synonymes.py` | formulations courantes, négations, dimensions de regroupement |

Chaque entrée du lexique est un `Entree(type, valeur, classe, libelle)` où `type` vaut :

- `classe` — une classe de l'ontologie ;
- `qualificatif` — un mot qui précise un type (« auto », « grave », « habitation ») ;
  il est **déduit des labels** : `Contrat automobile` sous `Contrat d'assurance` donne le qualificatif `automobile` ;
- `individu` — une ressource nommée (assureur, assuré, contrat, garantie…) ;
- `statut`, `valeur` (ville), `attribut` (propriété numérique), `dimension`, `validite`.

Deux structures importantes :

- **`qualificatifs`** : `"grave" → {SinistreGrave}`, `"auto" → {ContratAutomobile, SinistreAutomobile}`…
  Le sens final dépend de la classe principale de la question.
- **`aretes` / `chemin()`** : le graphe des propriétés objet. `chemin(depart, arrivee)` fait un
  **parcours en largeur** et renvoie le plus court chemin de propriétés, avec un sens par étape
  (`^` = propriété inverse). Une propriété d'un parent s'applique aussi à ses sous-classes.

Exemple : pour relier une `Indemnisation` à l'assureur `STAR`, le chemin trouvé est
`:suitBareme/^:definitBareme` (« l'indemnisation suit un barème que STAR définit »).
Ce chemin est calculé à l'exécution : si l'ontologie change, la requête s'adapte.

---

## 4. Étape 2 — Analyse linguistique (`analyse.py`)

### 4.1 Pré-traitement

- apostrophes typographiques `’` → `'` ;
- séparateurs de milliers supprimés (« 5 000 » → « 5000 ») ;
- dates complètes normalisées : `22/09/2025` → `2025-09-22`.

### 4.2 Pipeline spaCy

Modèle **`fr_core_news_md`** : tokenisation, étiquetage morpho-syntaxique, lemmatisation,
entités nommées. Le modèle est chargé **une seule fois** par `service.py`.

Chaque token reçoit une extension `_.cles` : l'ensemble **forme + lemme**, en minuscules et
**sans accents**. C'est ce qui permet de reconnaître « contrats automobiles » comme
« contrat automobile ».

### 4.3 Reconnaissance des concepts (`spacy.Matcher`)

Au démarrage de l'`Analyseur`, **toutes les phrases du lexique** passent par le même pipeline
spaCy. Les phrases qui se réduisent aux mêmes clés sont regroupées en un seul motif.
Pour une question, on garde les correspondances **les plus longues d'abord**, sans chevauchement.

Autour de chaque mention :

- **négation** si l'un des deux mots précédents est dans `synonymes.NEGATIONS`
  (« non couverts », « sans expert ») ;
- **regroupement** si le mot précédent est `par`, `chaque` ou `selon`
  (« par statut ») — mais « par la garantie vol » reste une relation.

### 4.4 Comparaisons et dates

Un second `Matcher` reconnaît les comparaisons (`plus de`, `au moins`, `inférieur à`,
`entre … et …`) avec la priorité la plus haute, pour que « plus de 5000 » ne soit pas lu
comme un superlatif.

Les dates sont traitées ensuite : années seules (« en 2025 », « après 2024 », « depuis 2024 »,
« entre 2024 et 2025 ») et dates complètes, avec un opérateur (`annee`, `>=`, `<`, `=`, `entre`).

### 4.5 Texte délexicalisé

Enfin, chaque mention est remplacée par une **étiquette générique** :

| Élément reconnu | Étiquette |
|---|---|
| concept (classe, individu, statut, ville…) | `CONCEPT` |
| attribut numérique seul (« indemnisation », « prime ») | `ATTRIBUT` |
| comparaison | `COMPARAISON` |
| date | `DATE` |
| nombre | `NOMBRE` |
| autres mots | lemme sans accents |

Exemple réel :

```
« Quels sont les sinistres graves ? »          → « quel etre le CONCEPT »
« Quel est le montant total indemnisé par STAR ? » → « quel etre le montant total CONCEPT par CONCEPT »
« Combien de sinistres par statut ? »           → « combien de CONCEPT par CONCEPT »
```

C'est cette phrase **sans vocabulaire métier** qui est donnée au classifieur.

---

## 5. Étape 3 — Intention de la question (`intentions.py`)

Le classifieur est un pipeline scikit-learn :

```
TfidfVectorizer(ngram_range=(1, 3), token_pattern=r"\S+", sublinear_tf=True)
LogisticRegression(max_iter=2000, C=20)
```

- **6 classes** : `lister`, `compter`, `somme`, `moyenne`, `maximum`, `minimum` ;
- environ **95 phrases d'exemple** (dans `EXEMPLES`), délexicalisées **avec le lexique courant**
  avant l'entraînement ;
- comme le texte est délexicalisé, le modèle apprend la **forme** de la question
  (« combien de CONCEPT », « le CONCEPT le plus ATTRIBUT »), pas les mots du domaine.
  Ajouter des données ne demande donc pas de ré-entraîner un modèle sur disque : le classifieur
  est reconstruit en mémoire à chaque rechargement du lexique ;
- si la confiance est inférieure à `SEUIL_CONFIANCE = 0.35`, on retombe sur `lister` ;
- `GET /nlp/evaluation` donne l'exactitude en validation croisée à 5 plis (~85 %).

---

## 6. Étape 4 — Interprétation et génération SPARQL (`generateur.py`)

### 6.1 Classe principale

`choisir_principale()` essaie, dans cet ordre :

1. la première mention de type `classe` non niée (« sinistres », « contrats », « garanties ») ;
2. à défaut, le **domaine de l'attribut** si l'intention est un agrégat ou un superlatif
   (« montant total indemnisé » → `Indemnisation`) ;
3. un qualificatif convertible en classe (« graves » → `SinistreGrave`) ;
4. la classe d'un individu cité seul ;
5. sinon : erreur `Incompris` → **HTTP 422** avec un message explicite.

La classe est ensuite normalisée en **famille d'affichage** (`lexique.affichage`) :
`SinistreGrave`, `SinistreSante`… ont pour famille `Sinistre`. C'est la famille qui
détermine les colonnes affichées, l'attribut par défaut et les propriétés de date.

### 6.2 Filtres

Chaque autre mention devient un filtre, dans cet ordre de priorité :

| Mention | Traitement |
|---|---|
| regroupement (« par statut ») | `GROUP BY` (voir 6.5) |
| attribut (« prime », « plafond ») | attribut utilisé pour les comparaisons/agrégats |
| validité (« en cours », « expirés ») | filtre sur `dateFinContrat` vs `NOW()` (ou statut pour un sinistre) |
| statut (« refusés », « en expertise ») | `:statutSinistre` (ignoré pour « déclarés en 2025 » : le verbe porte sur la date) |
| individu (« STAR », « Sarra », « CT-2025-003 ») | égalité si même famille, sinon lien vers l'individu |
| classe (« garanties ») | `a :Classe` si même famille, sinon lien via l'ontologie |
| qualificatif (« grave », « auto ») | converti en classe de la famille courante |
| ville (« Sousse ») | filtre sur `:lieuSinistre` ou `:adresse` |

Pour relier deux concepts de familles différentes, le générateur utilise
`lexique.chemin()` : par exemple « sinistres de STAR » →
`:concerneContrat/:assurePar`, « contrats de STAR » → `:assurePar`.
Une négation transforme le bloc en `FILTER NOT EXISTS { … }`.

Les comparaisons utilisent l'attribut nommé, sinon l'attribut par défaut de la famille
(`ATTRIBUT_PAR_DEFAUT` : prime pour un contrat, montant estimé pour un sinistre…).
Cas particulier : pour un sinistre, le montant des dommages est la somme des dommages
(`:causeDommage/:montantEstime`), calculée par une sous-requête.

### 6.3 Dates

La propriété dépend de la famille : `:dateSinistre`, `:dateDebutContrat`,
`:dateIndemnisation`… Pour un contrat, les mots « expire(nt) », « fin », « échéance »
(`synonymes.DATE_FIN`) font porter le filtre sur `:dateFinContrat`.

### 6.4 Gabarits de requête

Selon l'intention :

| Intention | Forme SELECT |
|---|---|
| `lister` | `SELECT DISTINCT ?x … ORDER BY ?x LIMIT 200` |
| `compter` | `COUNT(DISTINCT ?x)` (+ `GROUP BY` si regroupement) |
| `somme` / `moyenne` | `SUM` / `AVG` sur une sous-requête `SELECT DISTINCT` |
| `maximum` / `minimum` | `ORDER BY DESC/ASC(?val) LIMIT 1` |

Si un agrégat est demandé mais qu'aucun attribut numérique ne peut être relié,
on retombe proprement sur `lister` (`interpretation.intention` vaut alors `lister`).

### 6.5 Regroupements

- `par type` : `?x a ?groupe . ?groupe rdfs:subClassOf :Famille ; rdfs:label ?libelle`
  en excluant les classes définies (`owl:equivalentClass`) et les classes SWRL pour éviter
  les doublons (`SinistreGrave` est une classe déduite) ;
- `par statut`, `par ville`, `par année` : `BIND` sur `:statutSinistre`, `:lieuSinistre`/`:adresse`
  ou `YEAR(:date…)`.

---

## 7. Étape 5 — Exécution et cache (`service.py`)

- Un **verrou** (`threading.Lock`) sérialise la préparation.
- Une **signature** = compteur d'écritures (`sparql.generation()`) + nombre de triplets.
  Si elle change (écriture via l'API ou rechargement de Fuseki), le lexique, l'analyseur,
  le classifieur et le rédacteur sont reconstruits. Sinon, ils sont réutilisés.
- Le modèle spaCy n'est chargé qu'une fois.
- La requête est exécutée sur Fuseki (`sparql.lecture`) ; les valeurs sont converties en Python.
- Toutes les valeurs venant de l'utilisateur passent par `iri()`, `texte()` ou `nombre()`
  (`sparql.py`), qui échappent/refusent les caractères dangereux (anti-injection).

Erreurs possibles :

| Cas | Réponse |
|---|---|
| aucun concept reconnu | **422** avec le message de `Incompris` |
| Fuseki arrêté | **503** « lancez demarrer_fuseki.bat » |
| requête refusée par Fuseki | **400** |

---

## 8. Étape 6 — Rédaction de la réponse (`redaction.py`)

Pas de génération libre : des **gabarits** remplis avec les résultats.

- **Accords** : le premier mot du label et les adjectifs suivants passent au pluriel selon
  l'analyse spaCy ; « sinistre grave » → « sinistres graves », mais « contrat santé » →
  « contrats santé » (santé est un nom, pas un adjectif) ;
- **genre** : le trait `Gender=Fem` du premier mot choisit « aucun » / « aucune » ;
- **formats** : montants `3 500 DT`, taux `75 %`, dates `22/09/2025` ;
- **éléments** : pour chaque famille (sinistre, contrat, assuré, garantie…), un titre et des
  détails lisibles (`redaction.element`), plus la valeur de l'agrégat éventuel ;
- **critères** : les filtres compris, affichés sous forme de puces dans l'interface.

---

## 9. Trois exemples réels (sortie de l'API)

### 9.1 « Quels sont les sinistres graves ? »

Analyse : mention `sinistres graves` → classe `SinistreGrave` ; texte délexicalisé
`quel etre le CONCEPT` ; intention `lister` (confiance 0.94).

```sparql
SELECT DISTINCT ?sinistre ?type ?date ?description ?statut ?lieu WHERE {
  ?sinistre a :SinistreGrave .
  OPTIONAL { ?sinistre :dateSinistre ?date }
  OPTIONAL { ?sinistre :descriptionSinistre ?description }
  OPTIONAL { ?sinistre :statutSinistre ?statut }
  OPTIONAL { ?sinistre :lieuSinistre ?lieu }
  OPTIONAL { ?sinistre a ?classe_ . ?classe_ rdfs:subClassOf :Sinistre ; rdfs:label ?type .
             FILTER NOT EXISTS { ?classe_ owl:equivalentClass ?def_ }
             FILTER NOT EXISTS { ?regle_ swrl:head/rdf:rest*/rdf:first/swrl:classPredicate ?classe_ } }
}
ORDER BY ?sinistre LIMIT 200
```

Réponse : « J'ai trouvé 2 sinistres graves : » (le raisonneur Pellet a déduit
les instances de `SinistreGrave` à partir des règles SWRL ; c'est le fichier
`assurance_sinistres_inferred.owl` qui est chargé dans Fuseki).

### 9.2 « Quel est le montant total indemnisé par STAR ? »

Analyse : `indemnisé` → attribut `montantIndemnisation` ; `STAR` → individu `Assureur_STAR` ;
texte délexicalisé `quel etre le montant total CONCEPT par CONCEPT` ;
intention `somme` (confiance 0.90). Classe principale = domaine de l'attribut (`Indemnisation`).
Le lien vers STAR est `:suitBareme/^:definitBareme`.

```sparql
SELECT (SUM(?val) AS ?total) WHERE {
  SELECT DISTINCT ?indemnisation ?val WHERE {
    ?indemnisation a :Indemnisation .
    ?indemnisation :suitBareme/^:definitBareme ?x1 . FILTER(?x1 = :Assureur_STAR)
    ?indemnisation :montantIndemnisation ?val .
  }
}
```

Réponse : « Le montant total indemnisé est de 3 500 DT. » — critère : `assureur : STAR`.

### 9.3 « Combien de sinistres par statut ? »

Intention `compter`, regroupement `statut` :

```sparql
SELECT ?groupe ?libelle (COUNT(DISTINCT ?sinistre) AS ?nombre) WHERE {
  ?sinistre a :Sinistre .
  ?sinistre :statutSinistre ?groupe . BIND(?groupe AS ?libelle)
}
GROUP BY ?groupe ?libelle ORDER BY DESC(?nombre)
```

Réponse : « Voici le nombre de sinistres par statut : » suivi des comptes par statut.

---

## 10. L'API et l'interface

| Route | Description |
|---|---|
| `POST /nlp/question` | corps `{"question": "…"}` ; renvoie la réponse rédigée + tous les détails |
| `GET /nlp/exemples` | exemples d'entraînement par intention |
| `GET /nlp/evaluation` | exactitude du classifieur en validation croisée |

Champs principaux de la réponse :

| Champ | Contenu |
|---|---|
| `reponse` | phrase rédigée |
| `criteres` | filtres compris (« assureur : STAR », « par statut ») |
| `elements` | résultats lisibles `{id, titre, details, valeur}` |
| `intention` | `{predite, appliquee, confiance}` |
| `explication` | résumé de l'interprétation |
| `interpretation` | `{classe, attribut, regroupement, filtres, avertissements}` |
| `entites` | chaque mention reconnue (type, valeur, négation, regroupement) |
| `tokens`, `entitesNommees` | sortie spaCy |
| `texteDelexicalise` | entrée du classifieur |
| `sparql` | requête exacte exécutée |
| `colonnes`, `lignes` | résultat brut |
| `dureeMs` | durée de traitement |

Côté interface (`frontend/src/pages/Question.jsx`) : la page `/question` envoie la question
à `POST /nlp/question`, affiche `reponse`, les `criteres`, puis les `elements` (8 premiers,
avec un bouton pour les autres). Les identifiants `Assure_…`, `Contrat_…`, `Sinistre_…`
deviennent des liens vers les fiches correspondantes. La barre de recherche du haut
navigue vers `/question?q=…`. En cas d'erreur, l'interface propose un exemple.

---

## 11. Comment étendre le module

| Besoin | Où intervenir |
|---|---|
| Reconnaître un mot courant en plus (« bagnole ») | ajouter le mot dans `synonymes.py` (`QUALIFICATIFS`, `CLASSES`…) |
| Reconnaître une nouvelle formulation d'une classe | ajouter un `skos:altLabel` dans l'ontologie (relancer `raisonnement.py` + `recharger_donnees.bat`) |
| Ajouter un statut, une dimension, un attribut | compléter `synonymes.py` (et éventuellement l'ontologie) |
| Améliorer la classification d'intention | ajouter des phrases dans `intentions.py` → `EXEMPLES` ; l'évaluation (`/nlp/evaluation`) mesure le gain |
| Changer le seuil de confiance | `intentions.py` → `SEUIL_CONFIANCE` |
| Ajouter une famille affichable | `synonymes.AFFICHAGE` (+ `VARIABLES`, `ATTRIBUT_PAR_DEFAUT` si pertinent) |
| Ajuster un gabarit de phrase | `redaction.py` → `FORMULES` / `rediger()` |

Après une modification du code, uvicorn `--reload` redémarre l'API : le lexique et le
classifieur sont reconstruits au prochain appel.

---

## 12. Limites connues

- **Vocabulaire fermé** : un mot absent de l'ontologie et de `synonymes.py` n'est pas reconnu.
- **Une seule classe principale** par question ; pas de questions imbriquées
  (« les assurés dont tous les sinistres… »).
- **Pas de mois** (« en mars ») : seules les années et les dates complètes sont gérées.
- Les paraphrases très éloignées des exemples d'entraînement peuvent être mal classées ;
  le seuil de 0.35 évite alors de produire un agrégat faux (on liste).
- Les chemins entre concepts sont les plus courts : si l'ontologie offre plusieurs liens,
  un seul est utilisé (celui que le BFS rencontre en premier).

---

## 13. Aide au diagnostic

La réponse de l'API contient tout ce qu'il faut pour comprendre un échec :

1. **`entites`** — le mot a-t-il été reconnu, et comme quoi ?
   S'il est absent : le problème est dans le lexique (`synonymes.py` ou ontologie).
2. **`texteDelexicalise`** — la question a-t-elle la forme attendue ?
3. **`intention`** — `predite` et `confiance` : une confiance faible explique un résultat inattendu.
4. **`interpretation.avertissements`** — par exemple « Aucun lien entre X et Y dans l'ontologie ».
5. **`sparql`** — la requête exacte, à coller dans Fuseki (`http://localhost:3030`) pour vérifier
   si le problème vient de la génération ou des données.

`GET /nlp/evaluation` permet de vérifier que le classifieur est toujours performant après
l'ajout d'exemples ou de synonymes.
