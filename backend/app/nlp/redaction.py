"""Rédaction de la réponse en français à partir des résultats SPARQL (gabarits, sans LLM).

L'accord en nombre et en genre s'appuie sur l'analyse spaCy des labels de l'ontologie :
le premier mot et les adjectifs qui le suivent passent au pluriel ("sinistre grave" -> "sinistres graves",
mais "contrat santé" -> "contrats santé"), et le genre du nom choisit "aucun" ou "aucune".
"""
from . import synonymes as syn

STATUTS = {"Declare": "déclaré", "EnExpertise": "en expertise", "Indemnise": "indemnisé",
           "Refuse": "refusé", "Cloture": "clôturé"}
MONETAIRES = {"montantPrime", "montantIndemnisation", "montantEstime", "plafondGarantie", "montantFranchise"}
DIMENSIONS = {"statut": "statut", "type": "type", "ville": "ville", "annee": "année"}

# Formulations naturelles par attribut : (somme, moyenne, maximum, minimum)
FORMULES = {
    "montantIndemnisation": ("le montant total indemnisé", "le montant moyen indemnisé",
                             "l'indemnisation la plus élevée", "l'indemnisation la plus faible"),
    "montantPrime": ("le total des primes", "la prime moyenne", "la prime la plus élevée", "la prime la plus basse"),
    "montantEstime": ("le montant total des dommages", "le coût moyen des dommages",
                      "les dommages les plus élevés", "les dommages les plus faibles"),
    "plafondGarantie": ("le total des plafonds", "le plafond moyen", "le plafond le plus élevé", "le plafond le plus bas"),
    "montantFranchise": ("le total des franchises", "la franchise moyenne", "la franchise la plus élevée", "la franchise la plus basse"),
    "tauxIndemnisation": ("la somme des taux", "le taux moyen", "le taux le plus élevé", "le taux le plus faible"),
}
_RANG = {"somme": 0, "moyenne": 1, "maximum": 2, "minimum": 3}


def nombre_fr(v, decimales=2):
    texte = f"{v:,.{decimales}f}".replace(",", " ").replace(".", ",")
    return texte[:-3] if texte.endswith(",00") else texte


def montant(v):
    return f"{nombre_fr(v)} DT"


def jour(v):
    annee, mois, j = str(v)[:10].split("-")
    return f"{j}/{mois}/{annee}"


def valeur_attribut(attribut, v):
    if v is None:
        return "—"
    if attribut in MONETAIRES:
        return montant(v)
    if attribut == "tauxIndemnisation":
        return f"{round(v * 100)} %"
    return nombre_fr(v)


def _pluriel_mot(mot):
    if mot[-1:] in ("s", "x", "z"):
        return mot
    return mot + ("x" if mot.endswith("eau") else "s")


class Redacteur:
    def __init__(self, nlp, lexique):
        self.nlp, self.lex = nlp, lexique
        self._formes = {}

    def formes(self, label):
        """(singulier, pluriel, féminin ?) d'un label de classe, en minuscule."""
        if label not in self._formes:
            doc = self.nlp(label)
            mots, accorder = [], True
            for i, t in enumerate(doc):
                if i == 0 or (accorder and t.pos_ in ("ADJ", "VERB")):
                    mots.append(_pluriel_mot(t.text) + t.whitespace_)
                else:
                    accorder = False
                    mots.append(t.text_with_ws)
            pluriel = "".join(mots)
            feminin = "Fem" in doc[0].morph.get("Gender") if len(doc) else False
            self._formes[label] = (label[:1].lower() + label[1:], pluriel[:1].lower() + pluriel[1:], feminin)
        return self._formes[label]

    def element(self, aff, ligne, variable, attribut, liees=()):
        """Une ligne de résultat sous forme lisible : titre + détails (+ valeur)."""
        l, d = ligne, []
        if aff == "Sinistre":
            titre = l.get("description") or l.get(variable)
            d = [l.get("type"), jour(l["date"]) if l.get("date") else None, l.get("lieu"), STATUTS.get(l.get("statut"))]
        elif aff == "Contrat":
            titre = l.get("numero") or l.get(variable)
            d = [l.get("type"), f"du {jour(l['debut'])} au {jour(l['fin'])}" if l.get("debut") and l.get("fin") else None,
                 f"{montant(l['prime'])} / an" if l.get("prime") is not None else None]
        elif aff in ("Assure", "Expert"):
            titre = f"{l.get('prenom', '')} {l.get('nom', '')}".strip() or l.get(variable)
            d = [l.get("specialite"), l.get("adresse"), f"CIN {l['cin']}" if l.get("cin") else None]
        elif aff == "Assureur":
            titre, d = l.get("raisonSociale") or l.get(variable), [l.get("adresse")]
        elif aff == "Garantie":
            titre = l.get("libelle") or l.get(variable)
            d = [l.get("type"), f"plafond {montant(l['plafond'])}" if l.get("plafond") is not None else None]
        elif aff == "Clause":
            titre, d = l.get("libelle") or l.get(variable), [l.get("type"), l.get("texte")]
        elif aff == "Dommage":
            titre = l.get("description") or l.get(variable)
            d = [l.get("type"), montant(l["montant"]) if l.get("montant") is not None else None]
        elif aff == "Indemnisation":
            titre = montant(l["montant"]) if l.get("montant") is not None else l.get(variable)
            d = [f"versée le {jour(l['date'])}" if l.get("date") else None]
        elif aff == "BaremeIndemnisation":
            titre = l.get("libelle") or l.get(variable)
            d = [f"taux {round(l['taux'] * 100)} %" if l.get("taux") is not None else None]
        else:
            titre = montant(l["montant"]) if l.get("montant") is not None else l.get(variable)
        d += [f"{libelle} : {l[col]}" for col, libelle in liees if l.get(col)]
        element = {"id": l.get(variable), "titre": titre, "details": [x for x in d if x]}
        if "val" in l:
            element["valeur"] = valeur_attribut(attribut, l["val"])
        return element

    def rediger(self, interpretation, colonnes, lignes):
        intention, cls, attribut = interpretation["intention"], interpretation["classe"], interpretation["attribut"]
        aff = self.lex.affichage(cls)
        singulier, pluriel, feminin = self.formes(self.lex.labels.get(cls, cls))
        e = "e" if feminin else ""
        nom_attribut = self.lex.labels.get(attribut, attribut) if attribut else ""
        formule = lambda rang: (FORMULES[attribut][rang] if attribut in FORMULES  # noqa: E731
                                else f"{('le total', 'la moyenne', 'la valeur la plus élevée', 'la valeur la plus faible')[rang]} de « {nom_attribut} »")
        criteres = [self._critere(f) for f in interpretation["filtres"]]
        regroupement = interpretation.get("regroupement")
        if regroupement:
            criteres.append(f"par {DIMENSIONS.get(regroupement, regroupement.lower())}")
        elements = []

        if "groupe" in colonnes:
            cle = next(c for c in colonnes if c not in ("groupe", "libelle"))
            quoi = f"le nombre de {pluriel}" if intention == "compter" else formule(_RANG.get(intention, 0))
            texte = f"Voici {quoi} par {DIMENSIONS.get(regroupement, (regroupement or '').lower())} :"
            for l in lignes:
                valeur = l.get(cle)
                elements.append({"titre": STATUTS.get(l.get("libelle"), l.get("libelle") or l.get("groupe")),
                                 "valeur": nombre_fr(valeur, 0) if cle == "nombre" else valeur_attribut(attribut, valeur)})
        elif intention == "compter":
            n = lignes[0]["nombre"] if lignes else 0
            texte = (f"Il n'y a aucun{e} {singulier} correspondant{e} à ces critères." if n == 0
                     else f"Il y a {n} {singulier if n == 1 else pluriel}.")
        elif intention in ("somme", "moyenne"):
            cle = "total" if intention == "somme" else "moyenne"
            valeur = lignes[0].get(cle) if lignes else None
            if valeur is None:
                texte = "Aucune valeur ne correspond à ces critères."
            else:
                phrase = formule(_RANG[intention])
                texte = f"{phrase[:1].upper()}{phrase[1:]} est de {valeur_attribut(attribut, valeur)}."
        elif intention in ("maximum", "minimum"):
            if not lignes:
                texte = f"Je n'ai trouvé aucun{e} {singulier} correspondant{e}."
            else:
                el = self.element(aff, lignes[0], colonnes[0], attribut)
                texte = f"C'est « {el['titre']} » qui a {formule(_RANG[intention])} : {el.get('valeur', '—')}."
                elements = [el]
        else:
            vus = set()
            for l in lignes:
                if l.get(colonnes[0]) not in vus:
                    vus.add(l.get(colonnes[0]))
                    elements.append(self.element(aff, l, colonnes[0], attribut, interpretation.get("liees", ())))
            n = len(elements)
            texte = (f"Je n'ai trouvé aucun{e} {singulier} correspondant{e} à ces critères." if n == 0
                     else f"J'ai trouvé {n} {singulier if n == 1 else pluriel} :")
        return {"reponse": texte, "criteres": criteres, "elements": elements}

    @staticmethod
    def _critere(filtre):
        """"Assureur = STAR" -> "assureur : STAR", "lié à Garantie vol" -> "garantie vol"..."""
        for code, libelle in STATUTS.items():
            filtre = filtre.replace(f"= {code}", f"= {libelle}").replace(f"≠ {code}", f"≠ {libelle}")
        if filtre.startswith("lié à "):
            filtre = filtre[len("lié à "):]
        if filtre.startswith("non "):
            # "non Sinistre couvert" porte sur un type de la même famille : le nom de famille est implicite
            mots = filtre[len("non "):].split(" ")
            return "non " + " ".join(mots[1:] if len(mots) > 1 else mots).lower()
        for prefixe in ("sans ", "hors "):
            if filtre.startswith(prefixe):
                reste = filtre[len(prefixe):]
                return prefixe + reste[:1].lower() + reste[1:]
        filtre = filtre.replace(" = ", " : ").replace(" ≠ ", " : pas ")
        return filtre[:1].lower() + filtre[1:]
