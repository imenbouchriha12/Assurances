"""Accès à Fuseki : exécution des requêtes SPARQL et construction sûre des termes (IRI, littéraux)."""
import re
from datetime import date
from urllib.error import URLError

from fastapi import HTTPException
from SPARQLWrapper import SPARQLWrapper, JSON, POST
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

from .config import NS, QUERY_ENDPOINT, UPDATE_ENDPOINT

PREFIXES = f"""PREFIX :     <{NS}>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX swrl: <http://www.w3.org/2003/11/swrl#>
"""

XSD = "http://www.w3.org/2001/XMLSchema#"
_DECIMAUX = {XSD + "float", XSD + "double", XSD + "decimal"}
_ENTIERS = {XSD + "integer", XSD + "int", XSD + "long", XSD + "nonNegativeInteger"}
_NOM_LOCAL = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _convertir(valeur):
    """Valeur SPARQL JSON -> valeur Python (IRI de l'ontologie -> nom local, nombres -> float/int)."""
    v = valeur["value"]
    if valeur["type"] == "uri":
        return v[len(NS):] if v.startswith(NS) else v
    datatype = valeur.get("datatype")
    if datatype in _DECIMAUX:
        return float(v)
    if datatype in _ENTIERS:
        return int(v)
    if datatype == XSD + "boolean":
        return v == "true"
    return v


def _executer(endpoint, requete, ecriture=False):
    client = SPARQLWrapper(endpoint)
    client.setQuery(PREFIXES + requete)
    if ecriture:
        client.setMethod(POST)
    else:
        client.setReturnFormat(JSON)
    try:
        resultat = client.query()
        return None if ecriture else resultat.convert()
    except URLError as e:
        raise HTTPException(503, f"Fuseki injoignable ({endpoint}) : lancez demarrer_fuseki.bat") from e
    except SPARQLWrapperException as e:
        raise HTTPException(400, f"Requête SPARQL refusée par Fuseki : {e}") from e


def lecture(requete):
    """Exécute un SELECT ou un ASK et renvoie le résultat brut (JSON SPARQL)."""
    return _executer(QUERY_ENDPOINT, requete)


def select(requete):
    """Exécute un SELECT et renvoie une liste de dictionnaires {variable: valeur}."""
    lignes = lecture(requete)["results"]["bindings"]
    return [{k: _convertir(v) for k, v in ligne.items()} for ligne in lignes]


def ask(requete):
    return lecture(requete)["boolean"]


# Incrémenté à chaque écriture : le module NLP reconstruit son lexique quand les données ont changé
_generation = [0]


def generation():
    return _generation[0]


def signaler_modification():
    _generation[0] += 1


def update(requete):
    _executer(UPDATE_ENDPOINT, requete, ecriture=True)
    signaler_modification()


def convertir_lignes(resultat):
    return [{k: _convertir(v) for k, v in ligne.items()} for ligne in resultat["results"]["bindings"]]


# ---------- Construction des termes : toute valeur venant de l'utilisateur passe par ici ----------

def iri(nom_local):
    """Nom local -> IRI préfixée. Refuse tout caractère qui permettrait une injection SPARQL."""
    if not isinstance(nom_local, str) or not _NOM_LOCAL.match(nom_local):
        raise HTTPException(400, f"Identifiant invalide : {nom_local!r}")
    return f":{nom_local}"


def texte(valeur):
    echappe = (str(valeur).replace("\\", "\\\\").replace('"', '\\"')
               .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))
    return f'"{echappe}"'


def nombre(valeur):
    return f'"{float(valeur)}"^^xsd:float'


def jour(valeur: date):
    return f'"{valeur.isoformat()}"^^xsd:date'


def booleen(valeur):
    return f'"{"true" if valeur else "false"}"^^xsd:boolean'
