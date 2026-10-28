from fastapi import APIRouter, HTTPException, Query

from ..inferences import materialiser
from ..ontologie import exiger, id_libre, remplacer, slug, supprimer_ressource, verifier_cin_libre
from ..schemas import AssureIn, AssureMaj
from ..sparql import ask, iri, select, texte, update
from .contrats import lister_contrats
from .sinistres import lister_sinistres

router = APIRouter(prefix="/assures", tags=["Assurés"])


def lister_assures(id_=None, q=None):
    filtres = f"FILTER(?id = {iri(id_)})" if id_ else ""
    if q:
        filtres += f' FILTER(CONTAINS(LCASE(CONCAT(?prenom, " ", ?nom, " ", ?cin)), LCASE({texte(q)})))'
    return select(f"""
SELECT ?id ?nom ?prenom ?cin ?adresse (COUNT(DISTINCT ?c) AS ?nbContrats) (COUNT(DISTINCT ?s) AS ?nbSinistres) WHERE {{
  ?id a :Assure ; :nom ?nom ; :prenom ?prenom ; :cin ?cin .
  OPTIONAL {{ ?id :adresse ?adresse }}
  OPTIONAL {{ ?id :aPourContrat ?c }}
  OPTIONAL {{ ?id :declareSinistre ?s }}
  {filtres}
}} GROUP BY ?id ?nom ?prenom ?cin ?adresse ORDER BY ?nom ?prenom""")


@router.get("", summary="Lister les assurés (recherche par nom, prénom ou CIN)")
def lister(q: str | None = Query(None, description="Texte recherché dans le nom, le prénom ou le CIN")):
    return lister_assures(q=q)


@router.get("/{id}", summary="Détail d'un assuré avec ses contrats et ses sinistres")
def detail(id: str):
    exiger(id, "Assure", "Assuré")
    assure = lister_assures(id_=id)[0]
    assure["contrats"] = lister_contrats(assure=id)
    assure["sinistres"] = lister_sinistres(assure=id)
    return assure


@router.post("", status_code=201, summary="Créer un assuré")
def creer(a: AssureIn):
    verifier_cin_libre(a.cin)
    id_ = id_libre("Assure_" + slug(a.prenom))
    adresse = f" ; :adresse {texte(a.adresse)}" if a.adresse else ""
    update(f"""INSERT DATA {{
  {iri(id_)} a owl:NamedIndividual , :Assure ; :nom {texte(a.nom)} ; :prenom {texte(a.prenom)} ;
      :cin {texte(a.cin)}{adresse} .
}}""")
    materialiser()
    return detail(id_)


@router.put("/{id}", summary="Modifier un assuré (seuls les champs fournis sont modifiés)")
def modifier(id: str, a: AssureMaj):
    exiger(id, "Assure", "Assuré")
    if a.cin:
        verifier_cin_libre(a.cin, sauf=id)
    fragments = [remplacer(id, champ, [texte(valeur)])
                 for champ, valeur in a.model_dump(exclude_none=True).items()]
    if fragments:
        update(" ;\n".join(fragments))
    return detail(id)


@router.delete("/{id}", status_code=204, summary="Supprimer un assuré (refusé s'il a des contrats)")
def supprimer(id: str):
    exiger(id, "Assure", "Assuré")
    if ask(f"ASK {{ {iri(id)} :aPourContrat ?c }}"):
        raise HTTPException(409, "Cet assuré a des contrats : supprimez-les d'abord")
    supprimer_ressource(id)
