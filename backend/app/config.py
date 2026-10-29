import os
from pathlib import Path

# 127.0.0.1 et non localhost : Fuseki n'écoute qu'en IPv4, et sous Windows chaque connexion tentée d'abord
# sur ::1 attend ~2 s le refus avant de basculer (SPARQLWrapper ouvre une connexion par requête)
FUSEKI_URL = os.getenv("FUSEKI_URL", "http://127.0.0.1:3030/assurance")
QUERY_ENDPOINT = f"{FUSEKI_URL}/sparql"
UPDATE_ENDPOINT = f"{FUSEKI_URL}/update"
DATA_ENDPOINT = f"{FUSEKI_URL}/data"  # Graph Store Protocol : lecture/écriture du graphe entier

NS = "http://www.semanticweb.org/ontologies/assurance-sinistres#"

# Dossier racine du projet (contient raisonnement.py et les fichiers .owl)
RACINE_PROJET = Path(__file__).resolve().parents[2]
