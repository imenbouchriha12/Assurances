import re
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from ..inferences import materialiser
from ..ontologie import (exiger, existe, id_libre, prochain_numero, remplacer, statuts_sinistre,
                         supprimer_ressource, verifier_sous_type)
from ..schemas import IndemnisationIn, SinistreIn, StatutIn
from ..sparql import ask, booleen, iri, jour, nombre, select, texte, update

router = APIRouter(prefix="/sinistres", tags=["Sinistres"])


def lister_sinistres(id_=None, statut=None, type_=None, grave=None, couvert=None, assure=None,
                     contrat=None, depuis=None, jusqua=None, montant_min=None):
    filtres = []
    if id_:
        filtres.append(f"FILTER(?id = {iri(id_)})")
    if statut:
        filtres.append(f"FILTER(?statut = {texte(statut)})")
    if type_:
        filtres.append(f"FILTER(?type = {iri(type_)})")
    if grave is not None:
        filtres.append(f"FILTER(?grave = {booleen(grave)})")
    if couvert is not None:
        filtres.append(f"FILTER(?couvert = {booleen(couvert)})")
    if assure:
        filtres.append(f"FILTER(?assure = {iri(assure)})")
    if contrat:
        filtres.append(f"FILTER(?contrat = {iri(contrat)})")
    if depuis:
        filtres.append(f"FILTER(?date >= {jour(depuis)})")
    if jusqua:
        filtres.append(f"FILTER(?date <= {jour(jusqua)})")
    having = f"HAVING (SUM(?montant) >= {nombre(montant_min)})" if montant_min is not None else ""
    return select(f"""
SELECT ?id ?type ?typeLabel ?date ?description ?lieu ?statut ?assure ?assureNom ?contrat ?numeroContrat
       ?assureur ?assureurNom ?grave ?couvert (SUM(?montant) AS ?totalEstime) (SAMPLE(?indemnise) AS ?montantIndemnise) WHERE {{
  ?id a :Sinistre , ?type ; :dateSinistre ?date ; :statutSinistre ?statut .
  ?type rdfs:subClassOf :Sinistre ; rdfs:label ?typeLabel .
  FILTER NOT EXISTS {{ ?type owl:equivalentClass ?definition }}
  FILTER NOT EXISTS {{ ?regle swrl:head/rdf:rest*/rdf:first/swrl:classPredicate ?type }}
  OPTIONAL {{ ?id :descriptionSinistre ?description }}
  OPTIONAL {{ ?id :lieuSinistre ?lieu }}
  OPTIONAL {{ ?assure :declareSinistre ?id ; :prenom ?p ; :nom ?n BIND(CONCAT(?p, " ", ?n) AS ?assureNom) }}
  OPTIONAL {{ ?id :concerneContrat ?contrat . ?contrat :numeroContrat ?numeroContrat .
             OPTIONAL {{ ?contrat :assurePar ?assureur . ?assureur :raisonSociale ?assureurNom }} }}
  OPTIONAL {{ ?id :causeDommage/:montantEstime ?montant }}
  OPTIONAL {{ ?id :estIndemnisePar/:montantIndemnisation ?indemnise }}
  BIND(EXISTS {{ ?id a :SinistreGrave }} AS ?grave)
  BIND(EXISTS {{ ?id a :SinistreCouvert }} AS ?couvert)
  {" ".join(filtres)}
}}
GROUP BY ?id ?type ?typeLabel ?date ?description ?lieu ?statut ?assure ?assureNom ?contrat ?numeroContrat
         ?assureur ?assureurNom ?grave ?couvert
{having}
ORDER BY DESC(?date)""")


@router.get("", summary="Lister les sinistres avec filtres")
def lister(statut: str | None = Query(None, description="Declare, EnExpertise, Indemnise, Refuse, Cloture"),
           type: str | None = Query(None, description="SinistreAutomobile, SinistreHabitation, SinistreSante"),
           grave: bool | None = Query(None, description="Déduit par la règle SWRL"),
           couvert: bool | None = Query(None, description="Déduit de la classe définie SinistreCouvert"),
           assure: str | None = None, contrat: str | None = None,
           depuis: date | None = None, jusqua: date | None = None,
           montantMin: float | None = Query(None, description="Total estimé minimum des dommages")):
    return lister_sinistres(statut=statut, type_=type, grave=grave, couvert=couvert, assure=assure,
                            contrat=contrat, depuis=depuis, jusqua=jusqua, montant_min=montantMin)


@router.get("/{id}", summary="Détail d'un sinistre (dommages, garanties, expert, indemnisation)")
def detail(id: str):
    exiger(id, "Sinistre", "Sinistre")
    sinistre = lister_sinistres(id_=id)[0]
    s = iri(id)
    sinistre["dommages"] = select(f"""
SELECT ?id ?type ?typeLabel ?montantEstime ?description WHERE {{
  {s} :causeDommage ?id . ?id a ?type ; :montantEstime ?montantEstime .
  ?type rdfs:subClassOf :Dommage ; rdfs:label ?typeLabel .
  OPTIONAL {{ ?id :descriptionDommage ?description }}
}}""")
    sinistre["garanties"] = select(f"""
SELECT ?id ?libelle ?plafond WHERE {{ {s} :estCouvertPar ?id . ?id :libelleGarantie ?libelle ; :plafondGarantie ?plafond }}""")
    experts = select(f"""
SELECT ?id ?nom ?prenom ?specialite WHERE {{
  {s} :estExpertisePar ?id . ?id :nom ?nom ; :prenom ?prenom . OPTIONAL {{ ?id :specialite ?specialite }}
}}""")
    sinistre["expert"] = experts[0] if experts else None
    indemnisations = select(f"""
SELECT ?id ?montant ?date ?bareme ?baremeLibelle ?taux WHERE {{
  {s} :estIndemnisePar ?id . ?id :montantIndemnisation ?montant ; :suitBareme ?bareme .
  ?bareme :libelleBareme ?baremeLibelle ; :tauxIndemnisation ?taux .
  OPTIONAL {{ ?id :dateIndemnisation ?date }}
}}""")
    sinistre["indemnisation"] = indemnisations[0] if indemnisations else None
    return sinistre


@router.post("", status_code=201, summary="Déclarer un sinistre (statut initial : Declare)")
def declarer(s: SinistreIn):
    verifier_sous_type(s.type, "Sinistre")
    exiger(s.contrat, "Contrat", "Contrat")
    # Correspondance de nommage : SinistreHabitation <-> ContratHabitation, etc.
    type_contrat = "Contrat" + s.type.removeprefix("Sinistre")
    if not existe(s.contrat, type_contrat):
        raise HTTPException(400, f"Un {s.type} doit concerner un {type_contrat}")

    contrat = select(f"""
SELECT ?assure ?debut ?fin WHERE {{
  {iri(s.contrat)} :dateDebutContrat ?debut ; :dateFinContrat ?fin . ?assure :aPourContrat {iri(s.contrat)} .
}}""")[0]
    if not date.fromisoformat(contrat["debut"]) <= s.dateSinistre <= date.fromisoformat(contrat["fin"]):
        raise HTTPException(400, f"Le sinistre du {s.dateSinistre} est hors de la période du contrat "
                                 f"({contrat['debut']} → {contrat['fin']})")
    for g in s.garanties:
        if not ask(f"ASK {{ {iri(s.contrat)} :possedeGarantie {iri(g)} }}"):
            raise HTTPException(400, f"La garantie {g} ne fait pas partie du contrat {s.contrat}")
    for d in s.dommages:
        verifier_sous_type(d.type, "Dommage")

    numero = f"{prochain_numero('Sinistre_'):03d}"
    id_ = f"Sinistre_{s.dateSinistre.year}_{numero}"
    triplets = [f"{iri(id_)} a owl:NamedIndividual , {iri(s.type)} ; :concerneContrat {iri(s.contrat)} ; "
                f":dateSinistre {jour(s.dateSinistre)} ; :descriptionSinistre {texte(s.description)} ; "
                f':statutSinistre "Declare"' + (f" ; :lieuSinistre {texte(s.lieu)}" if s.lieu else "") + " .",
                f"{iri(contrat['assure'])} :declareSinistre {iri(id_)} ."]
    triplets += [f"{iri(id_)} :estCouvertPar {iri(g)} ." for g in s.garanties]
    deja_pris = {}  # deux dommages du même type dans la même déclaration : suffixe _2, _3...
    for d in s.dommages:
        base = f"{d.type.replace('Dommage', 'Dommage_')}_{numero}"
        deja_pris[base] = deja_pris.get(base, 0) + 1
        id_d = id_libre(base if deja_pris[base] == 1 else f"{base}_{deja_pris[base]}")
        triplets.append(f"{iri(id_d)} a owl:NamedIndividual , {iri(d.type)} ; :montantEstime {nombre(d.montantEstime)}"
                        + (f" ; :descriptionDommage {texte(d.description)}" if d.description else "") + " .")
        triplets.append(f"{iri(id_)} :causeDommage {iri(id_d)} .")
    update("INSERT DATA {\n" + "\n".join(triplets) + "\n}")
    materialiser()
    return detail(id_)


@router.patch("/{id}/statut", summary="Changer le statut d'un sinistre et/ou lui affecter un expert")
def changer_statut(id: str, corps: StatutIn):
    exiger(id, "Sinistre", "Sinistre")
    statuts = statuts_sinistre()
    if corps.statut not in statuts:
        raise HTTPException(400, f"Statut inconnu : {corps.statut}. Valeurs possibles : {', '.join(statuts)}")
    if corps.statut == "Indemnise" and not ask(f"ASK {{ {iri(id)} :estIndemnisePar ?i }}"):
        raise HTTPException(400, "Pour indemniser, utilisez POST /sinistres/{id}/indemnisation (calcul du montant)")
    fragments = [remplacer(id, "statutSinistre", [texte(corps.statut)])]
    if corps.expert:
        exiger(corps.expert, "Expert", "Expert")
        if not ask(f"ASK {{ {iri(corps.expert)} :travaillePour ?a . {iri(id)} :concerneContrat/:assurePar ?a }}"):
            raise HTTPException(400, "Cet expert ne travaille pas pour l'assureur du contrat (travaillePour)")
        fragments.append(remplacer(id, "estExpertisePar", [iri(corps.expert)]))
    update(" ;\n".join(fragments))
    return detail(id)


@router.post("/{id}/indemnisation", status_code=201,
             summary="Indemniser : montant = (dommages − franchise) × taux du barème, plafonné par la garantie")
def indemniser(id: str, corps: IndemnisationIn):
    exiger(id, "Sinistre", "Sinistre")
    exiger(corps.bareme, "BaremeIndemnisation", "Barème")
    s, b = iri(id), iri(corps.bareme)
    if ask(f"ASK {{ {s} :estIndemnisePar ?i }}"):
        raise HTTPException(409, "Ce sinistre a déjà été indemnisé")
    if ask(f'ASK {{ {s} :statutSinistre "Refuse" }}'):
        raise HTTPException(409, "Ce sinistre a été refusé")
    plafonds = [g["plafond"] for g in select(f"SELECT ?plafond WHERE {{ {s} :estCouvertPar/:plafondGarantie ?plafond }}")]
    if not plafonds:
        raise HTTPException(409, "Sinistre non couvert : aucune garantie (il n'est pas un SinistreCouvert)")
    if not ask(f"ASK {{ ?a :definitBareme {b} . {s} :concerneContrat/:assurePar ?a }}"):
        raise HTTPException(400, f"Le barème {corps.bareme} n'est pas défini par l'assureur du contrat (definitBareme)")
    if not ask(f"ASK {{ {b} :sAppliqueA ?g . {s} :estCouvertPar ?g }}"):
        raise HTTPException(400, f"Le barème {corps.bareme} ne s'applique à aucune garantie couvrant ce sinistre")

    calcul = select(f"""
SELECT (SUM(?m) AS ?totalDommages) (SAMPLE(?f) AS ?franchise) (SAMPLE(?t) AS ?taux) WHERE {{
  {s} :causeDommage/:montantEstime ?m .
  OPTIONAL {{ {s} :concerneContrat/:appliqueFranchise/:montantFranchise ?f }}
  {b} :tauxIndemnisation ?t .
}}""")[0]
    total, franchise, taux = calcul["totalDommages"], calcul.get("franchise", 0.0), calcul["taux"]
    plafond = max(plafonds)
    montant = round(min(max(total - franchise, 0.0) * taux, plafond), 2)

    numero = re.search(r"(\d+)$", id)
    id_i = id_libre(f"Indemnisation_{numero.group(1) if numero else id}")
    update(f"""INSERT DATA {{
  {iri(id_i)} a owl:NamedIndividual , :Indemnisation ; :suitBareme {b} ;
      :montantIndemnisation {nombre(montant)} ; :dateIndemnisation {jour(date.today())} .
  {s} :estIndemnisePar {iri(id_i)} .
}} ;
{remplacer(id, "statutSinistre", ['"Indemnise"'])}""")
    materialiser()
    return {"calcul": {"totalDommages": total, "franchise": franchise, "taux": taux, "plafond": plafond,
                       "montant": montant, "formule": f"min(({total} - {franchise}) × {taux}, {plafond})"},
            "sinistre": detail(id)}


@router.delete("/{id}", status_code=204, summary="Supprimer un sinistre avec ses dommages et son indemnisation")
def supprimer(id: str):
    exiger(id, "Sinistre", "Sinistre")
    lies = select(f"SELECT ?x WHERE {{ {{ {iri(id)} :causeDommage ?x }} UNION {{ {iri(id)} :estIndemnisePar ?x }} }}")
    for l in lies:
        supprimer_ressource(l["x"])
    supprimer_ressource(id)
    materialiser()
