"""Point d'entrée du module NLP : question -> analyse spaCy -> intention -> SPARQL -> résultats.

Le modèle spaCy est chargé une seule fois. Le lexique (lu dans l'ontologie) et le classifieur sont
reconstruits quand les données ont changé : écriture via l'API ou rechargement extérieur de Fuseki.
"""
import threading
import time

import spacy
from fastapi import HTTPException

from ..config import NS
from ..sparql import convertir_lignes, generation, lecture, select
from .analyse import Analyseur
from .generateur import Incompris, generer
from .intentions import ClassifieurIntention
from .lexique import construire_lexique
from .redaction import Redacteur

MODELE = "fr_core_news_md"
_verrou = threading.Lock()
_etat = {"nlp": None, "analyseur": None, "classifieur": None, "redacteur": None, "signature": None, "lexique": None}


def _signature():
    return generation(), select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")[0]["n"]


def _preparer():
    with _verrou:
        signature = _signature()
        if _etat["analyseur"] is not None and _etat["signature"] == signature:
            return
        if _etat["nlp"] is None:
            _etat["nlp"] = spacy.load(MODELE)
        lexique = construire_lexique()
        analyseur = Analyseur(_etat["nlp"], lexique)
        _etat.update(lexique=lexique, analyseur=analyseur, classifieur=ClassifieurIntention(analyseur),
                     redacteur=Redacteur(_etat["nlp"], lexique), signature=signature)


def prechauffer():
    """Préparation lancée au démarrage de l'API : la première question n'attend pas le chargement de spaCy."""
    try:
        _preparer()
    except HTTPException:
        pass  # Fuseki pas encore lancé : la préparation se fera à la première question


def repondre(question):
    debut = time.perf_counter()
    _preparer()
    analyse = _etat["analyseur"].analyser(question)
    intention, confiance = _etat["classifieur"].predire(analyse)
    try:
        interpretation = generer(_etat["lexique"], analyse, intention)
    except Incompris as e:
        raise HTTPException(422, str(e)) from e

    resultat = lecture(interpretation["sparql"])
    colonnes, lignes = resultat["head"]["vars"], convertir_lignes(resultat)
    return {
        "question": question,
        # Réponse rédigée pour l'utilisateur
        **_etat["redacteur"].rediger(interpretation, colonnes, lignes),
        "corrections": analyse.corrections,
        # Détails techniques (documentation de l'API, démonstration) : non affichés dans l'interface
        "intention": {"predite": intention, "appliquee": interpretation["intention"], "confiance": confiance},
        "explication": interpretation["explication"],
        "interpretation": {k: interpretation[k] for k in ("classe", "attribut", "regroupement", "filtres", "avertissements")},
        "entites": interpretation["entites"],
        "tokens": analyse.tokens,
        "entitesNommees": analyse.entites_nommees,
        "texteDelexicalise": analyse.texte_delexicalise,
        "sparql": f"PREFIX : <{NS}>\n{interpretation['sparql']}",
        "colonnes": colonnes,
        "lignes": lignes,
        "dureeMs": round((time.perf_counter() - debut) * 1000),
    }


def evaluation():
    _preparer()
    moyenne, ecart = _etat["classifieur"].evaluer()
    return {"modele": MODELE, "exemples": len(_etat["classifieur"].textes),
            "phrasesLexique": len(_etat["lexique"].phrases), "exactitudeValidationCroisee": moyenne, "ecartType": ecart}
