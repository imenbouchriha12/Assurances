# Module NLP : question en français → requête SPARQL

Aucune API de LLM n'est utilisée. La traduction repose sur **spaCy** (analyse linguistique),
**scikit-learn** (classification de l'intention) et sur l'**ontologie elle-même** (lexique et chemins entre concepts).

> Explication détaillée, pas à pas, avec exemples réels et guide d'extension :
> [FONCTIONNEMENT.md](FONCTIONNEMENT.md).

## Outils

| Outil | Rôle |
|---|---|
| **spaCy 3.8** + modèle **fr_core_news_md** | tokenisation, lemmatisation, étiquetage morpho-syntaxique (POS), entités nommées |
| **spaCy `Matcher`** | reconnaissance des concepts de l'ontologie (motifs sur le lemme ou la forme, sans accents) et des comparaisons (« plus de 5000 », « supérieure à 500 », « entre 1000 et 3000 ») |
| **scikit-learn** (`TfidfVectorizer` + `LogisticRegression`) | classification de l'intention : lister, compter, somme, moyenne, maximum, minimum |
| **SPARQL / Fuseki** | lecture de l'ontologie pour construire le lexique, exécution de la requête générée |

## Étapes (exemple : « Quel est le montant total indemnisé par STAR ? »)

1. **Lexique** (`lexique.py`) — construit depuis l'ontologie : `rdfs:label` et `skos:altLabel` des classes,
   valeurs des individus (noms, raisons sociales, libellés, numéros de contrat), villes, énumération des statuts,
   plus les synonymes métier de `synonymes.py`. Il contient aussi le graphe des propriétés objet (domaine → portée).
2. **Analyse spaCy** (`analyse.py`) — lemmes : *indemnisé → indemnisé*, *STAR → STAR* ; le `Matcher` reconnaît
   *indemnisé* = attribut `montantIndemnisation` et *STAR* = individu `Assureur_STAR`.
3. **Intention** (`intentions.py`) — le classifieur voit le texte délexicalisé
   `quel etre le montant total CONCEPT par CONCEPT` → **somme** (confiance 0,90).
4. **Génération** (`generateur.py`) — classe principale = domaine de l'attribut (`Indemnisation`) ;
   le lien vers `Assureur_STAR` est le **plus court chemin** de propriétés dans l'ontologie :
   `:suitBareme/^:definitBareme` (l'indemnisation suit un barème que STAR définit).
   Avant l'ajout de `definitBareme`, le plus court chemin passait par le contrat :
   `^:estIndemnisePar/:concerneContrat/:assurePar` ; les deux donnent le même résultat, car l'API
   impose que le barème d'une indemnisation soit défini par l'assureur du contrat.
5. **Requête produite et exécutée** :

```sparql
SELECT (SUM(?val) AS ?total) WHERE {
  SELECT DISTINCT ?indemnisation ?val WHERE {
    ?indemnisation a :Indemnisation .
    ?indemnisation :suitBareme/^:definitBareme ?x1 . FILTER(?x1 = :Assureur_STAR)
    ?indemnisation :montantIndemnisation ?val .
  }
}
```

6. **Rédaction de la réponse** (`redaction.py`) — génération par gabarits à partir des résultats :
   « Le montant total indemnisé est de 23 030 DT. » L'accord en nombre et en genre utilise l'analyse
   spaCy des labels (« 2 sinistres graves », « aucune garantie »). L'interface affiche cette phrase,
   les critères compris et les résultats ; la requête SPARQL reste disponible dans la réponse de l'API.

## Ce qui est reconnu

- **concepts** : classes (« sinistres », « contrats auto », « accidents de voiture »), qualificatifs (« graves », « habitation »),
  individus (« STAR », « Sarra », « CT-2025-003 », « garantie vol »), villes, statuts (« refusés », « en expertise »)
- **filtres** : comparaisons de montants, années et intervalles de dates (« en 2025 », « après 2024 », « entre 2024 et 2025 »),
  validité des contrats (« en cours », « expirés »), négations (« non couverts », « sans expert »)
- **regroupements** : « par statut », « par type », « par ville », « par année », « par assureur »
- **déductions du raisonneur** : « sinistres graves » (règle SWRL), « couverts » (classe définie)
- **fautes de frappe** : un mot inconnu du modèle spaCy est remplacé par le mot du lexique le plus proche
  (similarité ≥ 0,8 avec `difflib`) : « expprt » → « expert », « contart » → « contrat ». Les mots français
  corrects ne sont jamais modifiés ; les corrections sont renvoyées dans `corrections` et affichées.
- **ressources liées affichées** : « les experts et leur assureur », « donne le nom des experts et où ils
  travaillent » (verbes de `synonymes.RELATIONS` → propriété `travaillePour`) ajoutent une colonne au résultat
  (« Karim Haddad · Assureur : GAT Assurances, STAR Assurances »)

## Évaluation

- `GET /nlp/evaluation` : exactitude du classifieur d'intention en validation croisée à 5 plis (~86 % sur 98 exemples).
- Batterie de 35 questions avec résultat attendu : 35/35 correctes (intention et résultats).

## Limites connues

- Le vocabulaire est celui de l'ontologie et de `synonymes.py` (registre familier compris : « bagnole »,
  « réclamations », « adhérents », « bossent », « périmé »…) ; un synonyme absent des deux n'est pas reconnu.
- Une seule classe principale par question ; pas de questions imbriquées (« les assurés dont tous les sinistres… »).
- Les mois (« en mars ») ne sont pas gérés, seulement les années et les dates complètes (JJ/MM/AAAA).
