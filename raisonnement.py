"""
Exécute le raisonneur Pellet sur l'ontologie et produit une version "matérialisée"
(assurance_sinistres_inferred.owl) à charger dans Fuseki, qui ne raisonne pas lui-même.

Faits ajoutés :
  - types déduits par Pellet (règle SWRL -> SinistreGrave, classe définie -> SinistreCouvert)
  - relations déduites (propriétés inverses : estAssureDe, estGarantieDe)
  - toutes les super-classes de chaque individu (pour que "?s a :Sinistre" suffise en SPARQL)

La fonction raisonner_graphe() est aussi utilisée par le back-end (POST /raisonnement).

Dépendances : owlready2==0.46 (car Java 17) et rdflib, installés dans backend/.venv
Usage       : backend\.venv\Scripts\python raisonnement.py [entree.owl] [sortie.owl]
"""
import os
import sys
import tempfile

from owlready2 import World, sync_reasoner_pellet, OwlReadyInconsistentOntologyError
from rdflib import Graph, Namespace, URIRef, RDF, RDFS, OWL

ONTO_IRI = "http://www.semanticweb.org/ontologies/assurance-sinistres"
NS = Namespace(ONTO_IRI + "#")
ICI = os.path.dirname(os.path.abspath(__file__))


class OntologieIncoherente(Exception):
    pass


def raisonner_graphe(graphe):
    """Ajoute à `graphe` (rdflib) les faits déduits par Pellet et renvoie le nombre de triplets ajoutés."""
    # 1. Pellet via owlready2 (copie temporaire : owlready2 gère mal les chemins accentués)
    with tempfile.NamedTemporaryFile(suffix=".owl", delete=False) as tmp:
        tmp.write(graphe.serialize(format="xml", encoding="utf-8"))
    monde = World()
    try:
        with open(tmp.name, "rb") as f:
            onto = monde.get_ontology(ONTO_IRI).load(fileobj=f)
        with onto:
            sync_reasoner_pellet(monde, infer_property_values=True, infer_data_property_values=True, debug=0)
    except OwlReadyInconsistentOntologyError as e:
        raise OntologieIncoherente(str(e)) from e
    finally:
        os.unlink(tmp.name)

    individus = set(graphe.subjects(RDF.type, OWL.NamedIndividual))
    classes = {c for c in graphe.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}
    props_objet = set(graphe.subjects(RDF.type, OWL.ObjectProperty))

    # On ne reprend de Pellet que les faits sur les individus (types et relations objet),
    # pour ne pas dupliquer les axiomes ni modifier les littéraux de la source.
    # On garde aussi la hiérarchie de classes déduite (ex. SinistreAutomobile ⊑ SinistreCouvert).
    deduits = Graph()
    for s, p, o in monde.as_rdflib_graph():
        if not isinstance(o, URIRef):
            continue
        if p == RDFS.subClassOf and s in classes and o in classes and s != o:
            deduits.add((s, p, o))
        elif s in individus and ((p == RDF.type and o in classes) or (p in props_objet and o in individus)):
            deduits.add((s, p, o))

    # 2. Propriétés inverses (owlready2 les calcule à la volée mais ne les stocke pas).
    #    Seulement entre propriétés nommées : "inverse de definitBareme" utilisé dans une restriction est anonyme.
    for p, q in graphe.subject_objects(OWL.inverseOf):
        if not (isinstance(p, URIRef) and isinstance(q, URIRef)):
            continue
        for s, o in list(deduits.subject_objects(p)) + list(graphe.subject_objects(p)):
            deduits.add((o, q, s))
        for s, o in list(deduits.subject_objects(q)) + list(graphe.subject_objects(q)):
            deduits.add((o, p, s))

    # 3. Fermeture des super-classes nommées pour chaque individu (hiérarchie source + déduite)
    hierarchie = Graph()
    for t in graphe.triples((None, RDFS.subClassOf, None)):
        hierarchie.add(t)
    for t in deduits.triples((None, RDFS.subClassOf, None)):
        hierarchie.add(t)

    def super_classes(c):
        return {x for x in hierarchie.transitive_objects(c, RDFS.subClassOf) if x in classes}

    for ind in individus:
        types = {t for t in graphe.objects(ind, RDF.type) if t in classes}
        types |= {t for t in deduits.objects(ind, RDF.type)}
        for t in types:
            for sc in super_classes(t):
                deduits.add((ind, RDF.type, sc))

    nouveaux = [t for t in deduits if t not in graphe]
    for t in nouveaux:
        graphe.add(t)
    return len(nouveaux)


def raisonner(entree, sortie):
    # Ontologie source : on garde ses triplets tels quels (labels, axiomes, règle SWRL)
    graphe = Graph()
    graphe.parse(entree, format="xml")
    graphe.bind("", NS)
    graphe.bind("skos", "http://www.w3.org/2004/02/skos/core#")
    nb_source = len(graphe)

    try:
        nb_ajoutes = raisonner_graphe(graphe)
    except OntologieIncoherente as e:
        sys.exit(f"Ontologie incohérente : {e}")

    # "xml" et non "pretty-xml" : ce dernier perd des triplets dans les listes (règle SWRL, énumérations)
    graphe.serialize(sortie, format="xml", encoding="utf-8")
    print(f"Source : {nb_source} triplets | ajoutés : {nb_ajoutes} | total : {len(graphe)}")
    print(f"Fichier écrit : {sortie}")
    return graphe


if __name__ == "__main__":
    entree = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ICI, "assurance_sinistres.owl")
    sortie = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ICI, "assurance_sinistres_inferred.owl")
    raisonner(entree, sortie)
