"""Interprétation de l'analyse et génération de la requête SPARQL.

1. Classe principale : premier concept de type classe ("sinistres", "contrats auto"...) ;
   pour "montant total indemnisé par STAR", c'est le domaine de l'attribut (Indemnisation).
2. Chaque autre mention devient un filtre. Pour relier deux concepts, on cherche le plus court
   chemin de propriétés objet dans l'ontologie (lexique.chemin) : "contrats de STAR" -> :assurePar,
   "sinistres de STAR" -> :concerneContrat/:assurePar.
3. Comparaisons, dates, négations, regroupements ("par statut").
4. Gabarit SELECT selon l'intention : lister, compter, somme, moyenne, maximum, minimum.
"""
from ..sparql import iri, nombre, texte
from . import synonymes as syn

AGREGATS = {"compter", "somme", "moyenne"}
SUPERLATIFS = {"maximum", "minimum"}
_DERIVEE = ("FILTER NOT EXISTS {{ {t} owl:equivalentClass ?def_ }} "
            "FILTER NOT EXISTS {{ ?regle_ swrl:head/rdf:rest*/rdf:first/swrl:classPredicate {t} }}")
_OPERATEURS = {">": "supérieur à", ">=": "au moins", "<": "inférieur à", "<=": "au plus"}


class Incompris(Exception):
    pass


def _chemin_sparql(etapes):
    return "/".join(f"{'' if sens == 1 else '^'}:{p}" for p, sens in etapes)


class _Construction:
    def __init__(self, lexique, analyse, intention):
        self.lex, self.a, self.intention = lexique, analyse, intention
        self.where, self.filtres, self.avertissements, self.entites = [], [], [], []
        self.compteur = 0
        self.attribut = None
        self.val_lie = False
        self.groupe = None
        self.principale = None

    # ---------- utilitaires ----------
    def libre(self, nom):
        self.compteur += 1
        return f"?{nom}{self.compteur}"

    def label(self, id_):
        return self.lex.labels.get(id_, id_)

    def noter(self, mention, type_, valeur, libelle=None):
        self.entites.append({"texte": mention.texte, "type": type_, "valeur": valeur, "libelle": libelle or valeur,
                             "negation": mention.negation, "regroupement": mention.regroupement})

    def lier(self, cible, motif, negation=False):
        """Ajoute  ?v <chemin vers cible> <motif>  ; motif reçoit la variable d'arrivée."""
        etapes = self.lex.chemin(self.cls, cible)
        if etapes is None:
            self.avertissements.append(f"Aucun lien entre {self.label(self.cls)} et {self.label(cible)} dans l'ontologie")
            return False
        if etapes:
            y = self.libre("x")
            bloc = f"{self.v} {_chemin_sparql(etapes)} {y} . {motif(y)}"
        else:
            bloc = motif(self.v)
        self.where.append(f"FILTER NOT EXISTS {{ {bloc} }}" if negation else bloc)
        return True

    # ---------- 1. classe principale ----------
    def choisir_principale(self):
        mentions = [m for m in self.a.mentions if not m.regroupement]
        for m in mentions:
            classes = m.de_type("classe")
            if classes and not m.negation:
                self.principale, cls = m, classes[0].valeur
                self.noter(m, "classe principale", cls, self.label(cls))
                return cls
        attributs = [e.valeur for m in mentions for e in m.de_type("attribut") if e.valeur in self.lex.attributs]
        if attributs and self.intention in AGREGATS | SUPERLATIFS:
            return self.lex.attributs[attributs[0]]
        for m in mentions:
            for e in m.de_type("qualificatif"):
                options = sorted(self.lex.qualificatifs.get(e.valeur, ()),
                                 key=lambda c: list(syn.AFFICHAGE).index(self.lex.affichage(c) or "Franchise"))
                if options:
                    self.principale = m
                    self.noter(m, "classe principale", options[0], self.label(options[0]))
                    return options[0]
        for m in mentions:
            for e in m.de_type("individu"):
                # "STAR" seul : on affiche l'individu (le filtre ?v = :Assureur_STAR est ajouté par appliquer)
                return e.classe
        raise Incompris("Je n'ai reconnu aucun concept de l'ontologie (sinistre, contrat, assuré, garantie...) "
                        "dans la question.")

    # ---------- 2. mentions -> filtres ----------
    def appliquer(self, m):
        types = {e.type for e in m.entrees}
        premier = lambda t: m.de_type(t)[0]  # noqa: E731
        if m.regroupement:
            return self.regrouper(m)
        if "attribut" in types and self.attribut is None and not types & {"individu", "valeur"} \
                and premier("attribut").valeur in self.lex.attributs \
                and (self.a.comparaisons or self.intention in AGREGATS | SUPERLATIFS):
            self.attribut = premier("attribut").valeur
            self.noter(m, "attribut", self.attribut, self.label(self.attribut))
            return
        if "validite" in types:
            return self.validite(m, premier("validite").valeur == "true")
        if "statut" in types:
            statut = premier("statut").valeur
            if statut == "Declare" and self.a.dates:
                return  # "sinistres déclarés en 2025" : le verbe porte sur la date, pas sur le statut
            return self.statut(m, statut)
        if "individu" in types:
            return self.individu(m, premier("individu"))
        if "classe" in types:
            return self.classe(m, premier("classe").valeur)
        if "qualificatif" in types:
            return self.qualificatif(m, premier("qualificatif").valeur)
        if "valeur" in types:
            return self.ville(m, premier("valeur").valeur)

    def meme_famille(self, cls):
        return self.lex.affichage(cls) == self.aff

    def classe(self, m, cls):
        if self.meme_famille(cls):
            if cls != self.cls:
                bloc = f"{self.v} a {iri(cls)} ."
                self.where.append(f"FILTER NOT EXISTS {{ {bloc} }}" if m.negation else bloc)
                self.filtres.append(f"{'non ' if m.negation else ''}{self.label(cls)}")
                self.noter(m, "type", cls, self.label(cls))
            return
        # "le contrat CT-2025-003" : l'individu qui suit rend la classe inutile
        if any(e.classe and self.lex.affichage(e.classe) == self.lex.affichage(cls)
               for x in self.a.mentions for e in x.de_type("individu")):
            return
        if self.lier(cls, lambda y: f"{y} a {iri(cls)} .", m.negation):
            self.filtres.append(f"{'sans' if m.negation else 'lié à'} {self.label(cls)}")
            self.noter(m, "classe liée", cls, self.label(cls))

    def qualificatif(self, m, qualif):
        options = self.lex.qualificatifs.get(qualif, set())
        meme = [c for c in options if self.meme_famille(c)]
        if meme:
            return self.classe(m, meme[0])
        possibles = [(len(ch), c) for c in sorted(options) if (ch := self.lex.chemin(self.cls, c)) is not None]
        if possibles:
            self.classe(m, min(possibles)[1])

    def individu(self, m, e):
        if self.meme_famille(e.classe):
            self.where.append(f"FILTER({self.v} {'!=' if m.negation else '='} {iri(e.valeur)})")
        elif not self.lier(e.classe, lambda y: f"FILTER({y} = {iri(e.valeur)})", m.negation):
            return
        self.filtres.append(f"{'hors' if m.negation else ''} {self.label(e.classe)} = {e.libelle}".strip())
        self.noter(m, "individu", e.valeur, e.libelle)

    def statut(self, m, statut):
        if self.lier("Sinistre", lambda y: f"{y} :statutSinistre {texte(statut)} .", m.negation):
            self.filtres.append(f"statut {'≠' if m.negation else '='} {statut}")
            self.noter(m, "statut", statut)

    def ville(self, m, ville):
        filtre = lambda y, p: f"{y} :{p} ?v_ . FILTER(LCASE(STR(?v_)) = {texte(ville.lower())})"  # noqa: E731
        options = []
        for p in sorted(self.lex.villes.get(ville.lower(), ())):
            for d in self.lex.domaines.get(p, ()):
                if self.lex.est_sous_classe(self.cls, d):
                    options.append((0, p, self.cls))
                for n in sorted(self.lex.noeuds):
                    if self.lex.est_sous_classe(n, d) and (ch := self.lex.chemin(self.cls, n)) is not None:
                        options.append((len(ch), p, n))
        if options:
            _, p, cible = min(options)
            self.lier(cible, lambda y: filtre(y, p).replace("?v_", self.libre("ville")), m.negation)
            self.filtres.append(f"{self.label(p)} = {ville}")
            self.noter(m, "ville", ville)

    def validite(self, m, valide):
        if not valide and self.a.dates:
            return  # "contrats qui expirent en 2026" : filtre sur la date de fin, pas sur la validité
        if self.aff == "Sinistre":
            if valide:  # sinistre "en cours" : pas encore indemnisé, refusé ou clôturé
                st = self.libre("statut")
                self.where.append(f'{self.v} :statutSinistre {st} . FILTER({st} IN ("Declare", "EnExpertise"))')
                self.filtres.append("sinistre en cours de traitement")
                self.noter(m, "validité", "en cours de traitement")
            return
        fin = self.libre("fin")
        op = ">=" if valide else "<"
        if self.lier("Contrat", lambda y: f"{y} :dateFinContrat {fin} . FILTER({fin} {op} xsd:date(NOW()))"):
            self.filtres.append("contrat en cours" if valide else "contrat expiré")
            self.noter(m, "validité", "en cours" if valide else "expiré")

    def regrouper(self, m):
        types = {e.type for e in m.entrees}
        if "individu" in types:  # "par STAR" : un filtre, pas un regroupement
            m.regroupement = False
            return self.individu(m, m.de_type("individu")[0])
        if self.groupe:
            return
        if "dimension" in types:
            dim = m.de_type("dimension")[0].valeur
            if dim == "type":
                self.where.append(f"{self.v} a ?groupe . ?groupe rdfs:subClassOf {iri(self.aff)} ; rdfs:label ?libelle . "
                                  + _DERIVEE.format(t="?groupe"))
            elif dim == "statut":
                self.lier("Sinistre", lambda y: f"{y} :statutSinistre ?groupe . BIND(?groupe AS ?libelle)")
            elif dim == "ville":
                prop = "lieuSinistre" if self.aff == "Sinistre" else "adresse"
                cible = "Sinistre" if self.aff == "Sinistre" else ("Assure" if self.aff not in ("Assure", "Expert", "Assureur") else self.cls)
                self.lier(cible, lambda y: f"{y} :{prop} ?groupe . BIND(?groupe AS ?libelle)")
            elif dim == "annee":
                prop = syn.DATES.get(self.aff)
                if not prop:
                    return self.avertissements.append("Pas de date pour regrouper par année")
                self.where.append(f"{self.v} :{prop} ?d_ . BIND(YEAR(?d_) AS ?groupe) BIND(STR(?groupe) AS ?libelle)")
            self.groupe = dim
            self.noter(m, "regroupement", dim)
            return
        if m.de_type("classe"):
            cls = m.de_type("classe")[0].valeur
        elif m.de_type("qualificatif"):
            options = sorted(self.lex.qualificatifs.get(m.de_type("qualificatif")[0].valeur, ()))
            if not options:
                return
            cls = options[0]
        else:
            return
        aff = self.lex.affichage(cls)
        if aff in ("Assure", "Expert"):
            libelle = lambda y: (f"OPTIONAL {{ {y} :prenom ?p_ ; :nom ?n_ }} "  # noqa: E731
                                 f'BIND(CONCAT(?p_, " ", ?n_) AS ?libelle)')
        else:
            prop = syn.AFFICHAGE.get(aff, {}).get("libelle")
            libelle = lambda y: f"OPTIONAL {{ {y} :{prop} ?libelle }}" if prop else ""  # noqa: E731
        if self.lier(cls, lambda y: f"{y} a {iri(cls)} . BIND({y} AS ?groupe) {libelle(y)}"):
            self.groupe = self.label(cls)
            self.noter(m, "regroupement", cls, self.label(cls))

    # ---------- 3. attribut, comparaisons, dates ----------
    def lier_attribut(self):
        if self.val_lie:
            return True
        attr = self.attribut or syn.ATTRIBUT_PAR_DEFAUT.get(self.aff)
        if attr not in self.lex.attributs:
            return False
        self.attribut = attr
        if self.aff == "Sinistre" and attr == "montantEstime":
            # total des dommages du sinistre (un sinistre peut avoir plusieurs dommages)
            self.where.append(f"{{ SELECT {self.v} (SUM(?m_) AS ?val) WHERE {{ {self.v} :causeDommage/:montantEstime ?m_ }} "
                              f"GROUP BY {self.v} }}")
        elif not self.lier(self.lex.attributs[attr], lambda y: f"{y} :{attr} ?val ."):
            return False
        self.val_lie = True
        return True

    def comparaisons(self):
        for c in self.a.comparaisons:
            if not self.lier_attribut():
                self.avertissements.append(f"Comparaison « {c.texte} » ignorée : aucun montant pour {self.label(self.cls)}")
                continue
            if c.operateur == "entre":
                bas, haut = sorted(c.valeurs[:2])
                self.where.append(f"FILTER(?val >= {nombre(bas)} && ?val <= {nombre(haut)})")
                self.filtres.append(f"{self.label(self.attribut)} entre {bas:g} et {haut:g}")
            else:
                self.where.append(f"FILTER(?val {c.operateur} {nombre(c.valeurs[0])})")
                self.filtres.append(f"{self.label(self.attribut)} {_OPERATEURS[c.operateur]} {c.valeurs[0]:g}")
            self.entites.append({"texte": c.texte, "type": "comparaison", "valeur": f"{c.operateur} {c.valeurs}",
                                 "libelle": c.texte, "negation": False, "regroupement": False})

    def dates(self):
        if not self.a.dates:
            return
        if self.aff == "Contrat" and self.a.cles & {s for s in syn.DATE_FIN}:
            cible, prop = "Contrat", "dateFinContrat"
        elif self.aff in syn.DATES:
            cible, prop = self.cls, syn.DATES[self.aff]
        else:
            cible, prop = "Sinistre", "dateSinistre"
        d = self.libre("date")
        conditions = []
        for f in self.a.dates:
            if f.operateur == "annee":
                conditions.append(f"YEAR({d}) = {f.valeurs[0]}")
                self.filtres.append(f"{self.label(prop)} en {f.valeurs[0]}")
            elif f.operateur == "entre":
                conditions.append(f'{d} >= "{f.valeurs[0]}"^^xsd:date && {d} < "{f.valeurs[1]}"^^xsd:date')
                self.filtres.append(f"{self.label(prop)} : {f.texte}")
            else:
                conditions.append(f'{d} {f.operateur} "{f.valeurs[0]}"^^xsd:date')
                self.filtres.append(f"{self.label(prop)} {f.operateur} {f.valeurs[0]}")
            self.entites.append({"texte": f.texte, "type": "date", "valeur": f"{f.operateur} {f.valeurs}",
                                 "libelle": f.texte, "negation": False, "regroupement": False})
        self.lier(cible, lambda y: f"{y} :{prop} {d} . FILTER({' && '.join(conditions)})")

    # ---------- 4. requête finale ----------
    def construire(self):
        self.cls = self.choisir_principale()
        self.aff = self.lex.affichage(self.cls) or "Sinistre"
        self.v = f"?{syn.VARIABLES.get(self.aff, 'x')}"
        self.where.append(f"{self.v} a {iri(self.cls)} .")
        for m in self.a.mentions:
            if m is not self.principale:
                self.appliquer(m)
        self.comparaisons()
        self.dates()

        groupe = "?groupe ?libelle " if self.groupe else ""
        par = f"GROUP BY ?groupe ?libelle" if self.groupe else ""
        if self.intention == "compter":
            corps = self.corps()
            select = f"SELECT {groupe}(COUNT(DISTINCT {self.v}) AS ?nombre) WHERE {{\n{corps}\n}}"
            select += f"\n{par} ORDER BY DESC(?nombre)" if self.groupe else ""
        elif self.intention in ("somme", "moyenne") and self.lier_attribut():
            agregat, nom = ("SUM", "total") if self.intention == "somme" else ("AVG", "moyenne")
            select = (f"SELECT {groupe}({agregat}(?val) AS ?{nom}) WHERE {{\n"
                      f"  SELECT DISTINCT {self.v} ?val {groupe}WHERE {{\n{self.corps(4)}\n  }}\n}}")
            select += f"\n{par} ORDER BY DESC(?{nom})" if self.groupe else ""
        elif self.intention in SUPERLATIFS and self.lier_attribut():
            sens = "DESC" if self.intention == "maximum" else "ASC"
            colonnes = self.colonnes()
            select = f"SELECT DISTINCT {self.v} {colonnes} ?val WHERE {{\n{self.corps()}\n}}\nORDER BY {sens}(?val) LIMIT 1"
        else:
            # lister, ou agrégat impossible faute de montant : on liste
            self.intention = "lister"
            colonnes = self.colonnes() + (" ?val" if self.val_lie else "")
            select = f"SELECT DISTINCT {self.v} {colonnes} WHERE {{\n{self.corps()}\n}}\nORDER BY {self.v} LIMIT 200"
        return select

    def colonnes(self):
        variables = []
        for nom, prop in syn.AFFICHAGE.get(self.aff, {}).get("colonnes", []):
            self.where.append(f"OPTIONAL {{ {self.v} :{prop} ?{nom} }}")
            variables.append(f"?{nom}")
        if self.aff in ("Sinistre", "Contrat", "Garantie", "Clause", "Dommage"):
            self.where.append(f"OPTIONAL {{ {self.v} a ?classe_ . ?classe_ rdfs:subClassOf {iri(self.aff)} ; rdfs:label ?type . "
                              + _DERIVEE.format(t="?classe_") + " }")
            variables.insert(0, "?type")
        return " ".join(variables)

    def corps(self, retrait=2):
        return "\n".join(" " * retrait + w for w in self.where)

    def explication(self):
        quoi = self.label(self.cls)
        attr = self.label(self.attribut) if self.attribut else ""
        debut = {
            "lister": f"Liste : {quoi}",
            "compter": f"Nombre de « {quoi} »",
            "somme": f"Somme de « {attr} » pour « {quoi} »",
            "moyenne": f"Moyenne de « {attr} » pour « {quoi} »",
            "maximum": f"« {quoi} » avec « {attr} » le plus élevé",
            "minimum": f"« {quoi} » avec « {attr} » le plus faible",
        }[self.intention]
        details = ([f"filtres : {' ; '.join(self.filtres)}"] if self.filtres else []) + \
                  ([f"regroupé par {self.groupe}"] if self.groupe else [])
        return debut + (" — " + ", ".join(details) if details else "")


def generer(lexique, analyse, intention):
    c = _Construction(lexique, analyse, intention)
    requete = c.construire()
    return {
        "sparql": requete,
        "intention": c.intention,
        "explication": c.explication(),
        "classe": c.cls,
        "attribut": c.attribut,
        "regroupement": c.groupe,
        "filtres": c.filtres,
        "entites": c.entites,
        "avertissements": c.avertissements,
    }
