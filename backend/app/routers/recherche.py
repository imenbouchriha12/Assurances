import re

from fastapi import APIRouter, HTTPException, Query

from ..inferences import raisonner_avec_pellet
from ..schemas import RequeteSparql
from ..sparql import convertir_lignes, lecture, select, texte

router = APIRouter(tags=["Recherche et statistiques"])

_ECRITURE = re.compile(r"\b(INSERT|DELETE|LOAD|CLEAR|DROP|CREATE|ADD|MOVE|COPY)\b", re.IGNORECASE)


@router.get("/recherche", summary="Recherche plein texte dans toutes les valeurs des individus")
def rechercher(q: str = Query(min_length=2, description="Mot recherché, ex. incendie, Sousse, Ben Salah")):
    return select(f"""
SELECT ?id ?propriete ?proprieteLabel ?valeur
       (GROUP_CONCAT(DISTINCT ?classeLabel; separator=", ") AS ?types) WHERE {{
  ?id a owl:NamedIndividual ; ?propriete ?valeur .
  FILTER(isLiteral(?valeur) && CONTAINS(LCASE(STR(?valeur)), LCASE({texte(q)})))
  OPTIONAL {{ ?propriete rdfs:label ?proprieteLabel }}
  # On n'affiche que les types les plus précis de l'individu
  ?id a ?classe . ?classe rdfs:label ?classeLabel .
  FILTER NOT EXISTS {{ ?id a ?sous . ?sous rdfs:subClassOf ?classe . FILTER(?sous != ?classe) }}
}}
GROUP BY ?id ?propriete ?proprieteLabel ?valeur
ORDER BY ?id LIMIT 100""")


@router.get("/statistiques", summary="Indicateurs pour le tableau de bord")
def statistiques():
    totaux = select("""
SELECT
  (COUNT(DISTINCT ?c) AS ?nbContrats) (COUNT(DISTINCT ?cv) AS ?nbContratsValides)
  (COUNT(DISTINCT ?a) AS ?nbAssures) (COUNT(DISTINCT ?s) AS ?nbSinistres)
  (COUNT(DISTINCT ?sg) AS ?nbSinistresGraves) WHERE {
  { ?c a :Contrat } UNION
  { ?cv a :Contrat ; :dateFinContrat ?fin FILTER(?fin >= xsd:date(NOW())) } UNION
  { ?a a :Assure } UNION { ?s a :Sinistre } UNION { ?sg a :SinistreGrave }
}""")[0]
    # Deux sous-requêtes : avec un UNION, SUM rencontrerait des valeurs non liées et renverrait une erreur
    montants = select("""
SELECT ?totalPrimes ?totalIndemnise WHERE {
  { SELECT (SUM(?p) AS ?totalPrimes) WHERE { ?c :montantPrime ?p } }
  { SELECT (SUM(?i) AS ?totalIndemnise) WHERE { ?x :montantIndemnisation ?i } }
}""")[0]
    return {
        "totaux": {**totaux, **montants},
        "contratsParType": select("""
SELECT ?type ?label (COUNT(?c) AS ?nombre) WHERE {
  ?c a :Contrat , ?type . ?type rdfs:subClassOf :Contrat ; rdfs:label ?label .
} GROUP BY ?type ?label ORDER BY DESC(?nombre)"""),
        "sinistresParStatut": select("""
SELECT ?statut (COUNT(?s) AS ?nombre) WHERE { ?s :statutSinistre ?statut } GROUP BY ?statut ORDER BY DESC(?nombre)"""),
        "sinistresParType": select("""
SELECT ?type ?label (COUNT(?s) AS ?nombre) WHERE {
  ?s a :Sinistre , ?type . ?type rdfs:subClassOf :Sinistre ; rdfs:label ?label .
  FILTER(?type NOT IN (:SinistreGrave, :SinistreCouvert))
} GROUP BY ?type ?label ORDER BY DESC(?nombre)"""),
        "indemnisationsParAssureur": select("""
SELECT ?assureur ?raisonSociale (COUNT(?i) AS ?nombre) (SUM(?m) AS ?total) WHERE {
  ?s :estIndemnisePar ?i ; :concerneContrat/:assurePar ?assureur .
  ?assureur :raisonSociale ?raisonSociale . ?i :montantIndemnisation ?m .
} GROUP BY ?assureur ?raisonSociale ORDER BY DESC(?total)"""),
    }


@router.post("/sparql", summary="Exécuter une requête SPARQL en lecture (SELECT ou ASK) ; les préfixes usuels sont ajoutés")
def sparql(corps: RequeteSparql):
    if _ECRITURE.search(corps.requete):
        raise HTTPException(400, "Seules les requêtes en lecture (SELECT, ASK) sont autorisées ici")
    resultat = lecture(corps.requete)
    if "boolean" in resultat:
        return {"type": "ASK", "resultat": resultat["boolean"]}
    return {"type": "SELECT", "colonnes": resultat["head"]["vars"], "lignes": convertir_lignes(resultat)}


@router.post("/raisonnement", tags=["Raisonnement"],
             summary="Relancer le raisonneur Pellet sur les données actuelles (cohérence + déductions)")
def raisonnement():
    return raisonner_avec_pellet()
