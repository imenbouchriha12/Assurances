from datetime import date

from fastapi import APIRouter, HTTPException, Query

from ..inferences import materialiser
from ..ontologie import (exiger, garanties_requises, prochain_numero, remplacer, supprimer_ressource,
                         verifier_sous_type)
from ..schemas import ContratIn, ContratMaj
from ..sparql import ask, booleen, iri, jour, nombre, select, texte, update
from .referentiel import lister_clauses, lister_garanties, verifier_catalogue
from .sinistres import lister_sinistres

router = APIRouter(prefix="/contrats", tags=["Contrats"])


def lister_contrats(id_=None, type_=None, assureur=None, assure=None, valide=None):
    filtres = []
    if id_:
        filtres.append(f"FILTER(?id = {iri(id_)})")
    if type_:
        filtres.append(f"FILTER(?type = {iri(type_)})")
    if assureur:
        filtres.append(f"FILTER(?assureur = {iri(assureur)})")
    if assure:
        filtres.append(f"FILTER(?assure = {iri(assure)})")
    if valide is not None:
        filtres.append(f"FILTER(?valide = {booleen(valide)})")
    return select(f"""
SELECT ?id ?numero ?type ?typeLabel ?assure ?assureNom ?assureur ?assureurNom
       ?dateDebut ?dateFin ?prime ?valide WHERE {{
  ?id a :Contrat , ?type ; :numeroContrat ?numero ; :dateDebutContrat ?dateDebut ;
      :dateFinContrat ?dateFin ; :montantPrime ?prime .
  ?type rdfs:subClassOf :Contrat ; rdfs:label ?typeLabel .
  OPTIONAL {{ ?id :assurePar ?assureur . ?assureur :raisonSociale ?assureurNom }}
  OPTIONAL {{ ?assure :aPourContrat ?id ; :prenom ?p ; :nom ?n BIND(CONCAT(?p, " ", ?n) AS ?assureNom) }}
  # Validité calculée à partir de la date du jour (estValide n'est qu'une valeur figée)
  BIND(?dateFin >= xsd:date(NOW()) AS ?valide)
  {" ".join(filtres)}
}} ORDER BY ?numero""")


def verifier_references(type_contrat, assureur=None, garanties=None, clauses=None, franchise=None):
    if assureur:
        exiger(assureur, "Assureur", "Assureur")
    for g in garanties or []:
        exiger(g, "Garantie", "Garantie")
    for c in clauses or []:
        exiger(c, "Clause", "Clause")
    if franchise:
        exiger(franchise, "Franchise", "Franchise")
    if garanties is not None:
        # Axiomes du type  ContratAutomobile ⊑ ∃possedeGarantie.GarantieResponsabiliteCivile
        valeurs = " ".join(iri(g) for g in garanties)
        for classe in garanties_requises(type_contrat):
            if not ask(f"ASK {{ VALUES ?g {{ {valeurs} }} ?g a {iri(classe)} }}"):
                raise HTTPException(400, f"Un {type_contrat} doit posséder une garantie de type {classe} "
                                         "(axiome de l'ontologie)")


@router.get("", summary="Lister les contrats avec filtres")
def lister(type: str | None = Query(None, description="ContratAutomobile, ContratHabitation, ContratSante, ContratVie"),
           assureur: str | None = Query(None, description="ex. Assureur_STAR"),
           assure: str | None = Query(None, description="ex. Assure_Amine"),
           valide: bool | None = Query(None, description="true = en cours aujourd'hui")):
    return lister_contrats(type_=type, assureur=assureur, assure=assure, valide=valide)


@router.get("/{id}", summary="Détail d'un contrat (garanties, clauses, franchise, sinistres)")
def detail(id: str):
    exiger(id, "Contrat", "Contrat")
    contrat = lister_contrats(id_=id)[0]
    contrat["garanties"] = lister_garanties(contrat=id)
    contrat["clauses"] = lister_clauses(contrat=id)
    franchises = select(f"SELECT ?id ?montant WHERE {{ {iri(id)} :appliqueFranchise ?id . ?id :montantFranchise ?montant }}")
    contrat["franchise"] = franchises[0] if franchises else None
    contrat["sinistres"] = lister_sinistres(contrat=id)
    return contrat


@router.post("", status_code=201, summary="Créer un contrat (numéro attribué automatiquement)")
def creer(c: ContratIn):
    verifier_sous_type(c.type, "Contrat")
    exiger(c.assure, "Assure", "Assuré")
    if c.dateFin <= c.dateDebut:
        raise HTTPException(400, "La date de fin doit être postérieure à la date de début")
    verifier_references(c.type, c.assureur, c.garanties, c.clauses, c.franchise)
    verifier_catalogue(c.assureur, c.garanties)

    n = prochain_numero("Contrat_")
    id_ = f"Contrat_{n:03d}"
    proprietes = [f"a owl:NamedIndividual , {iri(c.type)}",
                  f":numeroContrat {texte(f'CT-{c.dateDebut.year}-{n:03d}')}",
                  f":dateDebutContrat {jour(c.dateDebut)}", f":dateFinContrat {jour(c.dateFin)}",
                  f":montantPrime {nombre(c.prime)}", f":estValide {booleen(c.dateFin >= date.today())}",
                  f":assurePar {iri(c.assureur)}",
                  ":possedeGarantie " + ", ".join(iri(g) for g in c.garanties)]
    if c.clauses:
        proprietes.append(":contientClause " + ", ".join(iri(x) for x in c.clauses))
    if c.franchise:
        proprietes.append(f":appliqueFranchise {iri(c.franchise)}")
    corps = " ;\n    ".join(proprietes)
    update(f"INSERT DATA {{\n  {iri(id_)} {corps} .\n  {iri(c.assure)} :aPourContrat {iri(id_)} .\n}}")
    materialiser()
    return detail(id_)


@router.put("/{id}", summary="Modifier un contrat (seuls les champs fournis sont modifiés)")
def modifier(id: str, c: ContratMaj):
    exiger(id, "Contrat", "Contrat")
    actuel = lister_contrats(id_=id)[0]
    debut = c.dateDebut or date.fromisoformat(actuel["dateDebut"])
    fin = c.dateFin or date.fromisoformat(actuel["dateFin"])
    if fin <= debut:
        raise HTTPException(400, "La date de fin doit être postérieure à la date de début")
    verifier_references(actuel["type"], c.assureur, c.garanties, c.clauses, c.franchise)
    if c.assureur or c.garanties is not None:
        # Les garanties (nouvelles ou actuelles) doivent être au catalogue de l'assureur (nouveau ou actuel)
        garanties = c.garanties if c.garanties is not None else [g["id"] for g in lister_garanties(contrat=id)]
        verifier_catalogue(c.assureur or actuel["assureur"], garanties)

    fragments = []
    if c.assureur:
        fragments.append(remplacer(id, "assurePar", [iri(c.assureur)]))
    if c.dateDebut:
        fragments.append(remplacer(id, "dateDebutContrat", [jour(debut)]))
    if c.dateFin:
        fragments.append(remplacer(id, "dateFinContrat", [jour(fin)]))
        fragments.append(remplacer(id, "estValide", [booleen(fin >= date.today())]))
    if c.prime is not None:
        fragments.append(remplacer(id, "montantPrime", [nombre(c.prime)]))
    if c.garanties is not None:
        fragments.append(remplacer(id, "possedeGarantie", [iri(g) for g in c.garanties]))
    if c.clauses is not None:
        fragments.append(remplacer(id, "contientClause", [iri(x) for x in c.clauses]))
    if c.franchise:
        fragments.append(remplacer(id, "appliqueFranchise", [iri(c.franchise)]))
    if fragments:
        update(" ;\n".join(fragments))
        materialiser()
    return detail(id)


@router.delete("/{id}", status_code=204, summary="Supprimer un contrat (refusé s'il a des sinistres)")
def supprimer(id: str):
    exiger(id, "Contrat", "Contrat")
    if ask(f"ASK {{ ?s :concerneContrat {iri(id)} }}"):
        raise HTTPException(409, "Ce contrat a des sinistres : supprimez-les d'abord")
    supprimer_ressource(id)
    materialiser()
