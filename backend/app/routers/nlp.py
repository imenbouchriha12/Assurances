from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..nlp import service
from ..nlp.intentions import EXEMPLES

router = APIRouter(prefix="/nlp", tags=["NLP (langage naturel → SPARQL)"])


class QuestionIn(BaseModel):
    question: str = Field(min_length=3, max_length=300, examples=["Quels sont les sinistres graves ?"])


@router.post("/question", summary="Traduire une question en français en requête SPARQL et l'exécuter")
def question(corps: QuestionIn):
    return service.repondre(corps.question)


@router.get("/exemples", summary="Exemples de questions par intention (données d'entraînement du classifieur)")
def exemples():
    return EXEMPLES


@router.get("/evaluation", summary="Exactitude du classifieur d'intention en validation croisée")
def evaluation():
    return service.evaluation()
