import os
from pathlib import Path

FUSEKI_URL = os.getenv("FUSEKI_URL", "http://localhost:3030/assurance")
QUERY_ENDPOINT = f"{FUSEKI_URL}/sparql"
UPDATE_ENDPOINT = f"{FUSEKI_URL}/update"
DATA_ENDPOINT = f"{FUSEKI_URL}/data"  # Graph Store Protocol : lecture/écriture du graphe entier

NS = "http://www.semanticweb.org/ontologies/assurance-sinistres#"

# Dossier racine du projet (contient raisonnement.py et les fichiers .owl)
RACINE_PROJET = Path(__file__).resolve().parents[2]
