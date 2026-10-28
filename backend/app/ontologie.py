"""Fonctions utilitaires qui lisent l'ontologie elle-même (types autorisés, contraintes, identifiants)."""
import re
import unicodedata

from fastapi import HTTPException

from .config import NS
from .sparql import ask, iri, select, texte, update


def sous_types(classe):
    """Sous-classes "saisissables" d'une classe : on exclut les classes déduites par le raisonneur
    (classes définies par owl:equivalentClass et conclusions de règles SWRL)."""
    return select(f"""
SELECT ?id ?label WHERE {{
  ?id rdfs:subClassOf {iri(classe)} ; rdfs:label ?label .
  FILTER NOT EXISTS {{ ?id owl:equivalentClass ?definition }}
  FILTER NOT EXISTS {{ ?regle swrl:head/rdf:rest*/rdf:first/swrl:classPredicate ?id }}
}} ORDER BY ?label""")


def verifier_sous_type(type_, classe):
    autorises = [t["id"] for t in sous_types(classe)]
    if type_ not in autorises:
        raise HTTPException(400, f"Type inconnu : {type_}. Valeurs possibles : {', '.join(autorises)}")


def statuts_sinistre():
    """Valeurs de l'énumération déclarée comme range de :statutSinistre."""
    return [r["v"] for r in select("SELECT ?v WHERE { :statutSinistre rdfs:range/owl:oneOf/rdf:rest*/rdf:first ?v }")]


def existe(id_, classe):
    return ask(f"ASK {{ {iri(id_)} a {iri(classe)} }}")


def exiger(id_, classe, libelle):
    if not existe(id_, classe):
        raise HTTPException(404, f"{libelle} introuvable : {id_}")


def garanties_requises(type_contrat):
    """Classes de garantie imposées par un axiome  TypeContrat ⊑ ∃possedeGarantie.ClasseGarantie."""
    return [r["g"] for r in select(f"""
SELECT ?g WHERE {{
  {iri(type_contrat)} rdfs:subClassOf ?r .
  ?r owl:onProperty :possedeGarantie ; owl:someValuesFrom ?g .
}}""")]


def prochain_numero(prefixe):
    """Plus grand suffixe numérique des individus dont l'identifiant commence par `prefixe`, plus 1."""
    lignes = select(f'SELECT ?id WHERE {{ ?id a owl:NamedIndividual FILTER(STRSTARTS(STR(?id), "{NS}{prefixe}")) }}')
    numeros = [int(m.group(1)) for l in lignes if (m := re.search(r"(\d+)$", l["id"]))]
    return max(numeros, default=0) + 1


def slug(valeur):
    ascii_ = unicodedata.normalize("NFKD", valeur).encode("ascii", "ignore").decode()
    mot = re.sub(r"[^A-Za-z0-9]", "", ascii_)
    return mot[:1].upper() + mot[1:] if mot else "X"


def slug_mots(valeur, max_mots=4):
    """"Vol du véhicule" -> "VolDuVehicule" (identifiant lisible à partir d'un libellé)."""
    ascii_ = unicodedata.normalize("NFKD", valeur).encode("ascii", "ignore").decode()
    mots = [m for m in re.split(r"[^A-Za-z0-9]+", ascii_) if m][:max_mots]
    return "".join(m[:1].upper() + m[1:] for m in mots) or "X"


def id_libre(base):
    """`base`, ou `base2`, `base3`... si l'identifiant est déjà utilisé."""
    candidat, n = base, 2
    while ask(f"ASK {{ {{ {iri(candidat)} ?p ?o }} UNION {{ ?s ?p {iri(candidat)} }} }}"):
        candidat, n = f"{base}{n}", n + 1
    return candidat


def verifier_cin_libre(cin, sauf=None):
    # Personne a pour clé (owl:hasKey) le CIN : deux personnes ne peuvent pas le partager
    exclusion = f"FILTER(?p != {iri(sauf)})" if sauf else ""
    if ask(f"ASK {{ ?p :cin {texte(cin)} {exclusion} }}"):
        raise HTTPException(409, f"Le CIN {cin} est déjà utilisé par une autre personne")


def supprimer_si_inutilise(id_, classe, libelle, ignorer=()):
    """Refuse la suppression si une autre ressource pointe vers celle-ci (contrat, sinistre, barème...).
    Les liens listés dans `ignorer` ne bloquent pas : ils disparaissent avec la ressource."""
    exiger(id_, classe, libelle)
    exclus = f"FILTER(?p NOT IN ({', '.join(iri(p) for p in ignorer)}))" if ignorer else ""
    references = [r["s"] for r in select(f"SELECT DISTINCT ?s WHERE {{ ?s ?p {iri(id_)} {exclus} }} ORDER BY ?s LIMIT 6")]
    if references:
        raise HTTPException(409, f"{libelle} utilisé par : {', '.join(references[:5])}"
                                 f"{'…' if len(references) > 5 else ''}. Modifiez ou supprimez d'abord ces ressources.")
    supprimer_ressource(id_)


def remplacer(sujet, propriete, valeurs):
    """Fragment SPARQL Update qui remplace toutes les valeurs d'une propriété."""
    fragment = f"DELETE WHERE {{ {iri(sujet)} {iri(propriete)} ?ancien }}"
    if valeurs:
        fragment += f" ;\nINSERT DATA {{ {iri(sujet)} {iri(propriete)} {', '.join(valeurs)} }}"
    return fragment


def supprimer_ressource(id_):
    """Supprime tous les triplets où l'individu apparaît (comme sujet ou comme objet)."""
    update(f"DELETE WHERE {{ {iri(id_)} ?p ?o }} ;\nDELETE WHERE {{ ?s ?p {iri(id_)} }}")
