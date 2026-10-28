from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import FUSEKI_URL
from .routers import assures, contrats, nlp, recherche, referentiel, sinistres
from .sparql import select

app = FastAPI(
    title="API Assurance et Gestion des Sinistres",
    description="Back-end du projet Web Sémantique : interroge l'ontologie stockée dans Apache Jena Fuseki "
                "via SPARQL (lecture, CRUD, filtres, recherche, raisonnement Pellet).",
    version="1.0.0",
)

# Le front-end (autre port) appelle l'API depuis le navigateur
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for module in (assures, contrats, sinistres, referentiel, recherche, nlp):
    app.include_router(module.router)


@app.get("/", tags=["Santé"], summary="État de l'API et de la connexion à Fuseki")
def accueil():
    nb = select("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")[0]["n"]
    return {"api": "ok", "fuseki": FUSEKI_URL, "triplets": nb, "documentation": "/docs"}
