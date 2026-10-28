"""Données de référence : types, assureurs, experts, garanties, clauses, barèmes, franchises (lecture et CRUD)."""
from fastapi import APIRouter, HTTPException, Query

from ..inferences import materialiser
from ..ontologie import (exiger, existe, id_libre, prochain_numero, remplacer, slug, slug_mots, sous_types,
                         statuts_sinistre, supprimer_si_inutilise, verifier_cin_libre, verifier_sous_type)
from ..schemas import AssureurIn, BaremeIn, ClauseIn, ExpertIn, FranchiseIn, GarantieIn
from ..sparql import ask, iri, nombre, select, texte, update

router = APIRouter(tags=["Référentiel"])


def lister_garanties(contrat=None, id_=None):
    filtre = f"{iri(contrat)} :possedeGarantie ?id ." if contrat else ""
    filtre += f" FILTER(?id = {iri(id_)})" if id_ else ""
    return select(f"""
SELECT ?id ?type ?typeLabel ?libelle ?plafond (COUNT(DISTINCT ?c) AS ?nbContrats) WHERE {{
  {filtre}
  ?id a :Garantie , ?type ; :libelleGarantie ?libelle ; :plafondGarantie ?plafond .
  ?type rdfs:subClassOf :Garantie ; rdfs:label ?typeLabel .
  OPTIONAL {{ ?c :possedeGarantie ?id }}
}} GROUP BY ?id ?type ?typeLabel ?libelle ?plafond ORDER BY ?typeLabel ?libelle""")


def lister_clauses(contrat=None, type_=None, id_=None):
    filtres = f"{iri(contrat)} :contientClause ?id ." if contrat else ""
    if type_:
        filtres += f" FILTER(?type = {iri(type_)})"
    if id_:
        filtres += f" FILTER(?id = {iri(id_)})"
    return select(f"""
SELECT ?id ?type ?typeLabel ?libelle ?texte ?reference
       (GROUP_CONCAT(DISTINCT ?garantie; separator=", ") AS ?garantiesExclues)
       (GROUP_CONCAT(DISTINCT STRAFTER(STR(?g), "#"); separator=",") AS ?garanties) WHERE {{
  ?id a :Clause , ?type ; :libelleClause ?libelle ; :texteClause ?texte ; :referenceLegale ?reference .
  ?type rdfs:subClassOf :Clause ; rdfs:label ?typeLabel .
  OPTIONAL {{ ?id :exclut ?g . ?g :libelleGarantie ?garantie }}
  {filtres}
}}
GROUP BY ?id ?type ?typeLabel ?libelle ?texte ?reference
ORDER BY ?typeLabel ?libelle""")


def _creer(id_, classe, proprietes):
    """INSERT DATA d'un individu, puis recalcul des déductions (super-classes, inverses)."""
    corps = " ;\n    ".join([f"a owl:NamedIndividual , {iri(classe)}"] + [p for p in proprietes if p])
    update(f"INSERT DATA {{\n  {iri(id_)} {corps} .\n}}")
    materialiser()


def _mettre_a_jour(id_, valeurs):
    """valeurs : {propriété: [termes SPARQL]} ; une liste vide supprime la propriété."""
    update(" ;\n".join(remplacer(id_, p, v) for p, v in valeurs.items()))
    materialiser()


def _verifier_type_fixe(id_, type_, classe):
    verifier_sous_type(type_, classe)
    if not existe(id_, type_):
        raise HTTPException(400, f"Le type d'une ressource ne peut pas être modifié : supprimez-la puis recréez-la")


def _verifier_garanties(garanties):
    for g in garanties:
        exiger(g, "Garantie", "Garantie")


@router.get("/types", summary="Types et valeurs autorisés, lus dans l'ontologie (pour les listes déroulantes)")
def types():
    return {
        "contrats": sous_types("Contrat"),
        "sinistres": sous_types("Sinistre"),
        "dommages": sous_types("Dommage"),
        "garanties": sous_types("Garantie"),
        "clauses": sous_types("Clause"),
        "statutsSinistre": statuts_sinistre(),
    }


@router.get("/ontologie/classes", summary="Hiérarchie des classes avec labels, commentaires et nombre d'instances")
def classes():
    return select("""
SELECT ?id ?label ?commentaire (GROUP_CONCAT(DISTINCT STRAFTER(STR(?parent), "#"); separator=",") AS ?parents)
       (COUNT(DISTINCT ?instance) AS ?nbInstances) WHERE {
  ?id a owl:Class ; rdfs:label ?label .
  FILTER(isIRI(?id))
  OPTIONAL { ?id rdfs:comment ?commentaire }
  OPTIONAL { ?id rdfs:subClassOf ?parent FILTER(isIRI(?parent)) }
  OPTIONAL { ?instance a ?id , owl:NamedIndividual }
}
GROUP BY ?id ?label ?commentaire
ORDER BY ?label""")


# ---------- Assureurs ----------

def _lister_assureurs(id_=None):
    filtre = f"FILTER(?id = {iri(id_)})" if id_ else ""
    return select(f"""
SELECT ?id ?raisonSociale ?adresse (COUNT(DISTINCT ?c) AS ?nbContrats) (COUNT(DISTINCT ?e) AS ?nbExperts)
       (COUNT(DISTINCT ?b) AS ?nbBaremes) (GROUP_CONCAT(DISTINCT STRAFTER(STR(?g), "#"); separator=",") AS ?garanties) WHERE {{
  ?id a :Assureur ; :raisonSociale ?raisonSociale .
  OPTIONAL {{ ?id :adresse ?adresse }}
  OPTIONAL {{ ?c :assurePar ?id }}
  OPTIONAL {{ ?e :travaillePour ?id }}
  OPTIONAL {{ ?id :definitBareme ?b }}
  OPTIONAL {{ ?id :proposeGarantie ?g }}
  {filtre}
}} GROUP BY ?id ?raisonSociale ?adresse ORDER BY ?raisonSociale""")


def verifier_catalogue(assureur, garanties):
    """Une garantie utilisée (contrat, barème) doit être proposée par l'assureur concerné."""
    for g in garanties:
        if not ask(f"ASK {{ {iri(assureur)} :proposeGarantie {iri(g)} }}"):
            nom = select(f"SELECT ?n WHERE {{ {iri(assureur)} :raisonSociale ?n }}")[0]["n"]
            raise HTTPException(400, f"La garantie {g} n'est pas proposée par {nom}. "
                                     "Ajoutez-la d'abord à son catalogue (Référentiel > Assureurs).")


def _verifier_raison_sociale(raison, sauf=None):
    exclusion = f"FILTER(?a != {iri(sauf)})" if sauf else ""
    if ask(f"ASK {{ ?a :raisonSociale ?r FILTER(LCASE(?r) = LCASE({texte(raison)})) {exclusion} }}"):
        raise HTTPException(409, f"Un assureur « {raison} » existe déjà")


@router.get("/assureurs", summary="Compagnies d'assurance")
def assureurs():
    return _lister_assureurs()


@router.post("/assureurs", status_code=201, summary="Créer un assureur avec son catalogue de garanties")
def creer_assureur(a: AssureurIn):
    _verifier_raison_sociale(a.raisonSociale)
    _verifier_garanties(a.garanties)
    id_ = id_libre("Assureur_" + slug_mots(a.raisonSociale, 1))
    _creer(id_, "Assureur", [f":raisonSociale {texte(a.raisonSociale)}",
                             f":adresse {texte(a.adresse)}" if a.adresse else "",
                             ":proposeGarantie " + ", ".join(iri(g) for g in a.garanties) if a.garanties else ""])
    return _lister_assureurs(id_)[0]


@router.put("/assureurs/{id}", summary="Modifier un assureur et son catalogue de garanties")
def modifier_assureur(id: str, a: AssureurIn):
    exiger(id, "Assureur", "Assureur")
    _verifier_raison_sociale(a.raisonSociale, sauf=id)
    _verifier_garanties(a.garanties)
    # Une garantie retirée du catalogue ne doit plus servir dans un contrat ou un barème de l'assureur
    actuelles = {r["g"] for r in select(f"SELECT ?g WHERE {{ {iri(id)} :proposeGarantie ?g }}")}
    for g in actuelles - set(a.garanties):
        utilisee = select(f"""
SELECT ?x WHERE {{ {{ ?x :assurePar {iri(id)} ; :possedeGarantie {iri(g)} }}
                   UNION {{ {iri(id)} :definitBareme ?x . ?x :sAppliqueA {iri(g)} }} }} LIMIT 3""")
        if utilisee:
            raise HTTPException(409, f"La garantie {g} ne peut pas être retirée : elle est utilisée par "
                                     f"{', '.join(u['x'] for u in utilisee)}")
    _mettre_a_jour(id, {"raisonSociale": [texte(a.raisonSociale)], "adresse": [texte(a.adresse)] if a.adresse else [],
                        "proposeGarantie": [iri(g) for g in a.garanties]})
    return _lister_assureurs(id)[0]


@router.delete("/assureurs/{id}", status_code=204,
               summary="Supprimer un assureur (refusé s'il a des contrats, des experts ou des barèmes)")
def supprimer_assureur(id: str):
    exiger(id, "Assureur", "Assureur")
    baremes = [r["b"] for r in select(f"SELECT ?b WHERE {{ {iri(id)} :definitBareme ?b }}")]
    if baremes:
        raise HTTPException(409, f"Assureur qui définit des barèmes : {', '.join(baremes)}. Supprimez-les d'abord.")
    supprimer_si_inutilise(id, "Assureur", "Assureur")
    materialiser()


# ---------- Experts ----------

def _lister_experts(id_=None):
    filtre = f"FILTER(?id = {iri(id_)})" if id_ else ""
    return select(f"""
SELECT ?id ?nom ?prenom ?cin ?specialite ?adresse (COUNT(DISTINCT ?s) AS ?nbSinistres)
       (GROUP_CONCAT(DISTINCT STRAFTER(STR(?a), "#"); separator=",") AS ?assureurs)
       (GROUP_CONCAT(DISTINCT ?an; separator=", ") AS ?assureursNoms) WHERE {{
  ?id a :Expert ; :nom ?nom ; :prenom ?prenom .
  OPTIONAL {{ ?id :cin ?cin }}
  OPTIONAL {{ ?id :specialite ?specialite }}
  OPTIONAL {{ ?id :adresse ?adresse }}
  OPTIONAL {{ ?s :estExpertisePar ?id }}
  OPTIONAL {{ ?id :travaillePour ?a . ?a :raisonSociale ?an }}
  {filtre}
}} GROUP BY ?id ?nom ?prenom ?cin ?specialite ?adresse ORDER BY ?nom""")


def _verifier_assureurs(assureurs):
    for a in assureurs:
        exiger(a, "Assureur", "Assureur")


@router.get("/experts", summary="Experts en sinistres")
def experts():
    return _lister_experts()


@router.post("/experts", status_code=201, summary="Créer un expert")
def creer_expert(e: ExpertIn):
    verifier_cin_libre(e.cin)
    _verifier_assureurs(e.assureurs)
    id_ = id_libre("Expert_" + slug(e.prenom))
    _creer(id_, "Expert", [f":nom {texte(e.nom)}", f":prenom {texte(e.prenom)}", f":cin {texte(e.cin)}",
                           f":adresse {texte(e.adresse)}" if e.adresse else "",
                           f":specialite {texte(e.specialite)}" if e.specialite else "",
                           ":travaillePour " + ", ".join(iri(a) for a in e.assureurs)])
    return _lister_experts(id_)[0]


@router.put("/experts/{id}", summary="Modifier un expert et les compagnies qui le mandatent")
def modifier_expert(id: str, e: ExpertIn):
    exiger(id, "Expert", "Expert")
    verifier_cin_libre(e.cin, sauf=id)
    _verifier_assureurs(e.assureurs)
    # On ne retire pas une compagnie dont l'expert a déjà expertisé des sinistres
    for a in {r["a"] for r in select(f"SELECT ?a WHERE {{ {iri(id)} :travaillePour ?a }}")} - set(e.assureurs):
        dossiers = select(f"SELECT ?s WHERE {{ ?s :estExpertisePar {iri(id)} ; :concerneContrat/:assurePar {iri(a)} }} LIMIT 3")
        if dossiers:
            raise HTTPException(409, f"L'expert a expertisé des sinistres pour {a} ({', '.join(d['s'] for d in dossiers)}) : "
                                     "cette compagnie ne peut pas être retirée")
    _mettre_a_jour(id, {"nom": [texte(e.nom)], "prenom": [texte(e.prenom)], "cin": [texte(e.cin)],
                        "adresse": [texte(e.adresse)] if e.adresse else [],
                        "specialite": [texte(e.specialite)] if e.specialite else [],
                        "travaillePour": [iri(a) for a in e.assureurs]})
    return _lister_experts(id)[0]


@router.delete("/experts/{id}", status_code=204, summary="Supprimer un expert (refusé s'il a expertisé des sinistres)")
def supprimer_expert(id: str):
    supprimer_si_inutilise(id, "Expert", "Expert")
    materialiser()


# ---------- Garanties ----------

@router.get("/garanties", summary="Garanties (type, libellé, plafond)")
def garanties():
    return lister_garanties()


@router.post("/garanties", status_code=201, summary="Créer une garantie")
def creer_garantie(g: GarantieIn):
    verifier_sous_type(g.type, "Garantie")
    id_ = id_libre("Garantie_" + slug_mots(g.libelle))
    _creer(id_, g.type, [f":libelleGarantie {texte(g.libelle)}", f":plafondGarantie {nombre(g.plafond)}"])
    return lister_garanties(id_=id_)[0]


@router.put("/garanties/{id}", summary="Modifier une garantie (libellé, plafond)")
def modifier_garantie(id: str, g: GarantieIn):
    exiger(id, "Garantie", "Garantie")
    _verifier_type_fixe(id, g.type, "Garantie")
    _mettre_a_jour(id, {"libelleGarantie": [texte(g.libelle)], "plafondGarantie": [nombre(g.plafond)]})
    return lister_garanties(id_=id)[0]


@router.delete("/garanties/{id}", status_code=204,
               summary="Supprimer une garantie (refusé si un contrat, un sinistre, une clause ou un barème l'utilise)")
def supprimer_garantie(id: str):
    # Le catalogue d'un assureur n'empêche pas la suppression : la garantie en est simplement retirée
    supprimer_si_inutilise(id, "Garantie", "Garantie", ignorer=("proposeGarantie",))
    materialiser()


@router.get("/garanties/{id}/clauses", summary="Clauses d'exclusion qui limitent une garantie")
def exclusions_garantie(id: str):
    exiger(id, "Garantie", "Garantie")
    return select(f"""
SELECT ?id ?libelle ?texte ?reference WHERE {{
  ?id :exclut {iri(id)} ; :libelleClause ?libelle ; :texteClause ?texte ; :referenceLegale ?reference .
}}""")


# ---------- Clauses légales ----------

def _exclusions(c):
    if c.garanties and c.type != "ClauseExclusion":
        raise HTTPException(400, "Seule une clause d'exclusion peut exclure des garanties")
    _verifier_garanties(c.garanties)
    return [iri(g) for g in c.garanties]


@router.get("/clauses", summary="Clauses légales (obligations et exclusions)")
def clauses(type: str | None = Query(None, description="ClauseExclusion ou ClauseObligatoire")):
    return lister_clauses(type_=type)


@router.post("/clauses", status_code=201, summary="Créer une clause légale")
def creer_clause(c: ClauseIn):
    verifier_sous_type(c.type, "Clause")
    exclues = _exclusions(c)
    id_ = id_libre("Clause_" + slug_mots(c.libelle))
    _creer(id_, c.type, [f":libelleClause {texte(c.libelle)}", f":texteClause {texte(c.texte)}",
                         f":referenceLegale {texte(c.reference)}",
                         f":exclut {', '.join(exclues)}" if exclues else ""])
    return lister_clauses(id_=id_)[0]


@router.put("/clauses/{id}", summary="Modifier une clause légale")
def modifier_clause(id: str, c: ClauseIn):
    exiger(id, "Clause", "Clause")
    _verifier_type_fixe(id, c.type, "Clause")
    _mettre_a_jour(id, {"libelleClause": [texte(c.libelle)], "texteClause": [texte(c.texte)],
                        "referenceLegale": [texte(c.reference)], "exclut": _exclusions(c)})
    return lister_clauses(id_=id)[0]


@router.delete("/clauses/{id}", status_code=204, summary="Supprimer une clause (refusé si un contrat la contient)")
def supprimer_clause(id: str):
    supprimer_si_inutilise(id, "Clause", "Clause")
    materialiser()


# ---------- Barèmes d'indemnisation ----------

def _lister_baremes(id_=None):
    filtre = f"FILTER(?id = {iri(id_)})" if id_ else ""
    return select(f"""
SELECT ?id ?libelle ?taux ?assureur ?assureurNom (GROUP_CONCAT(DISTINCT STRAFTER(STR(?g), "#"); separator=",") AS ?garanties)
       (COUNT(DISTINCT ?i) AS ?nbIndemnisations) WHERE {{
  ?id a :BaremeIndemnisation ; :libelleBareme ?libelle ; :tauxIndemnisation ?taux .
  OPTIONAL {{ ?assureur :definitBareme ?id ; :raisonSociale ?assureurNom }}
  OPTIONAL {{ ?id :sAppliqueA ?g }}
  OPTIONAL {{ ?i :suitBareme ?id }}
  {filtre}
}} GROUP BY ?id ?libelle ?taux ?assureur ?assureurNom ORDER BY ?assureurNom ?libelle""")


@router.get("/baremes", summary="Barèmes d'indemnisation et garanties auxquelles ils s'appliquent")
def baremes():
    return _lister_baremes()


def _verifier_bareme(b):
    exiger(b.assureur, "Assureur", "Assureur")
    _verifier_garanties(b.garanties)
    verifier_catalogue(b.assureur, b.garanties)


@router.post("/baremes", status_code=201, summary="Créer un barème d'indemnisation pour un assureur")
def creer_bareme(b: BaremeIn):
    _verifier_bareme(b)
    id_ = id_libre("Bareme_" + slug_mots(b.libelle))
    _creer(id_, "BaremeIndemnisation", [f":libelleBareme {texte(b.libelle)}", f":tauxIndemnisation {nombre(b.taux)}",
                                        ":sAppliqueA " + ", ".join(iri(g) for g in b.garanties) if b.garanties else ""])
    update(f"INSERT DATA {{ {iri(b.assureur)} :definitBareme {iri(id_)} }}")
    return _lister_baremes(id_)[0]


@router.put("/baremes/{id}", summary="Modifier un barème d'indemnisation")
def modifier_bareme(id: str, b: BaremeIn):
    exiger(id, "BaremeIndemnisation", "Barème")
    _verifier_bareme(b)
    actuel = _lister_baremes(id)[0]
    if actuel.get("assureur") != b.assureur and actuel["nbIndemnisations"] > 0:
        raise HTTPException(409, "Ce barème a déjà servi à des indemnisations : son assureur ne peut plus changer")
    update(f"DELETE WHERE {{ ?a :definitBareme {iri(id)} }} ;\nINSERT DATA {{ {iri(b.assureur)} :definitBareme {iri(id)} }}")
    _mettre_a_jour(id, {"libelleBareme": [texte(b.libelle)], "tauxIndemnisation": [nombre(b.taux)],
                        "sAppliqueA": [iri(g) for g in b.garanties]})
    return _lister_baremes(id)[0]


@router.delete("/baremes/{id}", status_code=204, summary="Supprimer un barème (refusé s'il a servi à une indemnisation)")
def supprimer_bareme(id: str):
    # Le lien "l'assureur définit ce barème" disparaît avec le barème
    supprimer_si_inutilise(id, "BaremeIndemnisation", "Barème", ignorer=("definitBareme",))
    materialiser()


# ---------- Franchises ----------

def _lister_franchises(id_=None):
    filtre = f"FILTER(?id = {iri(id_)})" if id_ else ""
    return select(f"""
SELECT ?id ?montant (COUNT(DISTINCT ?c) AS ?nbContrats) WHERE {{
  ?id a :Franchise ; :montantFranchise ?montant .
  OPTIONAL {{ ?c :appliqueFranchise ?id }}
  {filtre}
}} GROUP BY ?id ?montant ORDER BY ?montant""")


@router.get("/franchises", summary="Franchises")
def franchises():
    return _lister_franchises()


@router.post("/franchises", status_code=201, summary="Créer une franchise")
def creer_franchise(f: FranchiseIn):
    id_ = id_libre(f"Franchise_{prochain_numero('Franchise_'):03d}")
    _creer(id_, "Franchise", [f":montantFranchise {nombre(f.montant)}"])
    return _lister_franchises(id_)[0]


@router.put("/franchises/{id}", summary="Modifier le montant d'une franchise")
def modifier_franchise(id: str, f: FranchiseIn):
    exiger(id, "Franchise", "Franchise")
    _mettre_a_jour(id, {"montantFranchise": [nombre(f.montant)]})
    return _lister_franchises(id)[0]


@router.delete("/franchises/{id}", status_code=204, summary="Supprimer une franchise (refusé si un contrat l'applique)")
def supprimer_franchise(id: str):
    supprimer_si_inutilise(id, "Franchise", "Franchise")
    materialiser()
