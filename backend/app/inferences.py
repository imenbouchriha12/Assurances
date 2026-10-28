"""Maintien des faits déduits dans Fuseki (qui ne raisonne pas lui-même).

- materialiser() : après chaque écriture, recalcule en SPARQL les déductions de l'ontologie
  (quelques millisecondes). Les règles reproduisent exactement les axiomes OWL et la règle SWRL.
- raisonner_avec_pellet() : relance le vrai raisonneur Pellet sur toutes les données de Fuseki
  (quelques secondes), vérifie la cohérence et recharge le résultat.
"""
import sys

import httpx
from fastapi import HTTPException
from rdflib import Graph, Namespace, RDF

from .config import DATA_ENDPOINT, NS, RACINE_PROJET
from .sparql import signaler_modification, update

sys.path.insert(0, str(RACINE_PROJET))
from raisonnement import OntologieIncoherente, raisonner_graphe  # noqa: E402  (raisonnement.py à la racine)

_SUPER_CLASSES = """
INSERT { ?i a ?sup } WHERE {
  ?i a owl:NamedIndividual , ?t .
  ?t rdfs:subClassOf+ ?sup .
  FILTER(isIRI(?sup))
}"""

REGLES = f"""
# Super-classes nommées de chaque individu (ex. un SinistreAutomobile est aussi un Sinistre)
{_SUPER_CLASSES} ;

# Propriétés inverses (owl:inverseOf)
DELETE WHERE {{ ?a :estAssureDe ?c }} ;
INSERT {{ ?a :estAssureDe ?c }} WHERE {{ ?c :assurePar ?a }} ;
DELETE WHERE {{ ?g :estGarantieDe ?c }} ;
INSERT {{ ?g :estGarantieDe ?c }} WHERE {{ ?c :possedeGarantie ?g }} ;

# Classe définie : SinistreCouvert ≡ Sinistre ⊓ ∃estCouvertPar.Garantie
DELETE {{ ?s a :SinistreCouvert }} WHERE {{ ?s a :SinistreCouvert , owl:NamedIndividual }} ;
INSERT {{ ?s a :SinistreCouvert }} WHERE {{ ?s a :Sinistre ; :estCouvertPar ?g }} ;

# Règle SWRL : Sinistre(?s) ∧ causeDommage(?s, ?d) ∧ DommageCorporel(?d) → SinistreGrave(?s)
DELETE {{ ?s a :SinistreGrave }} WHERE {{ ?s a :SinistreGrave , owl:NamedIndividual }} ;
INSERT {{ ?s a :SinistreGrave }} WHERE {{ ?s a :Sinistre ; :causeDommage ?d . ?d a :DommageCorporel }} ;

# Une seconde fois pour les classes déduites ci-dessus
# (et SinistreAutomobile ⊑ SinistreCouvert, subsomption déduite par Pellet)
{_SUPER_CLASSES}
"""


def materialiser():
    update(REGLES)


def raisonner_avec_pellet():
    try:
        reponse = httpx.get(f"{DATA_ENDPOINT}?default", headers={"Accept": "text/turtle"}, timeout=30)
        reponse.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(503, f"Fuseki injoignable : {e}") from e

    graphe = Graph().parse(data=reponse.text, format="turtle")
    nb_avant = len(graphe)

    # On retire les faits dérivés pour que Pellet les recalcule depuis les seules assertions
    ns = Namespace(NS)
    for classe in (ns.SinistreGrave, ns.SinistreCouvert):
        for s in list(graphe.subjects(RDF.type, classe)):
            graphe.remove((s, RDF.type, classe))
    for prop in (ns.estAssureDe, ns.estGarantieDe):
        graphe.remove((None, prop, None))

    try:
        raisonner_graphe(graphe)
    except OntologieIncoherente as e:
        raise HTTPException(409, f"Les données actuelles rendent l'ontologie incohérente, rien n'a été modifié : {e}") from e

    reponse = httpx.put(f"{DATA_ENDPOINT}?default", content=graphe.serialize(format="turtle"),
                        headers={"Content-Type": "text/turtle"}, timeout=60)
    reponse.raise_for_status()
    signaler_modification()
    return {"coherente": True, "tripletsAvant": nb_avant, "tripletsApres": len(graphe)}
