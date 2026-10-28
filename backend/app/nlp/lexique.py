"""Lexique construit à partir de l'ontologie (via SPARQL) : c'est lui qui relie les mots aux concepts.

Sources : rdfs:label et skos:altLabel des classes et propriétés, valeurs des individus (noms, raisons
sociales, libellés, numéros, villes), énumération des statuts, synonymes de synonymes.py.
Il contient aussi le graphe des propriétés objet (domaine -> portée) qui sert à relier deux concepts.
"""
import re
from collections import deque
from dataclasses import dataclass, field

from ..sparql import select
from . import synonymes as syn


@dataclass(frozen=True)
class Entree:
    type: str            # classe | qualificatif | individu | statut | valeur | attribut | dimension | validite
    valeur: str          # identifiant de la classe / de l'individu / statut / attribut / ville...
    classe: str = ""     # pour un individu : sa classe la plus précise
    libelle: str = ""    # texte lisible (explication)


@dataclass
class Lexique:
    phrases: list = field(default_factory=list)          # [(texte, Entree)]
    labels: dict = field(default_factory=dict)           # id de classe / propriété -> label
    parents: dict = field(default_factory=dict)          # classe -> {classes parentes directes}
    qualificatifs: dict = field(default_factory=dict)    # "automobile" -> {ContratAutomobile, SinistreAutomobile}
    aretes: list = field(default_factory=list)           # [(propriete, domaine, portee)]
    noeuds: set = field(default_factory=set)             # classes reliées par les propriétés objet
    attributs: dict = field(default_factory=dict)        # propriété numérique -> domaine
    domaines: dict = field(default_factory=dict)         # propriété de données -> {domaines}
    villes: dict = field(default_factory=dict)           # ville -> {propriétés où elle apparaît}

    def ajouter(self, texte, entree):
        texte = (texte or "").strip()
        if texte:
            self.phrases.append((texte, entree))

    # ---------- Hiérarchie ----------
    def ancetres(self, classe):
        """La classe puis ses ancêtres, du plus proche au plus lointain (parcours en largeur)."""
        vus, file = [classe], deque([classe])
        while file:
            for p in sorted(self.parents.get(file.popleft(), ())):
                if p not in vus:
                    vus.append(p)
                    file.append(p)
        return vus

    def est_sous_classe(self, classe, ancetre):
        return ancetre in self.ancetres(classe)

    def noeud(self, classe):
        """Classe du graphe des relations la plus proche (ex. SinistreGrave -> Sinistre)."""
        return next((a for a in self.ancetres(classe) if a in self.noeuds), classe)

    def affichage(self, classe):
        """Classe d'affichage (synonymes.AFFICHAGE) la plus proche (ex. ClauseExclusion -> Clause)."""
        return next((a for a in self.ancetres(classe) if a in syn.AFFICHAGE), None)

    # ---------- Chemins entre concepts ----------
    def chemin(self, depart, arrivee):
        """Plus court chemin de propriétés objet entre deux classes : [(propriete, sens)], sens -1 = inverse.
        On peut arriver sur un parent de la cible (contientClause mène à Clause, parent de ClauseExclusion) :
        le type exact est ensuite imposé par un  ?y a :Cible  dans la requête."""
        cibles = {a for a in self.ancetres(arrivee) if a in self.noeuds}
        if set(self.ancetres(depart)) & cibles:
            return []
        precedent, file = {depart: None}, deque([depart])
        while file:
            courant = file.popleft()
            for p, dom, por in self.aretes:
                for de, vers, sens in ((dom, por, 1), (por, dom, -1)):
                    # une propriété du parent s'applique aussi à la sous-classe
                    if de in self.ancetres(courant) and vers not in precedent:
                        precedent[vers] = (courant, p, sens)
                        if vers in cibles:
                            etapes, n = [], vers
                            while precedent[n]:
                                n, prop, s = precedent[n]
                                etapes.append((prop, s))
                            return list(reversed(etapes))
                        file.append(vers)
        return None


def _valeurs(requete, *variables):
    return [tuple(l.get(v) for v in variables) for l in select(requete)]


def construire_lexique():
    lex = Lexique()

    # Classes : labels, synonymes et hiérarchie
    for cls, label in _valeurs("SELECT ?c ?l WHERE { ?c a owl:Class ; rdfs:label ?l FILTER(isIRI(?c)) }", "c", "l"):
        lex.labels[cls] = label
        lex.ajouter(label, Entree("classe", cls, libelle=label))
    for cls, alt in _valeurs("SELECT ?c ?l WHERE { ?c a owl:Class ; skos:altLabel ?l }", "c", "l"):
        lex.ajouter(alt, Entree("classe", cls, libelle=lex.labels.get(cls, cls)))
    for cls, mots in syn.CLASSES.items():
        for mot in mots:
            lex.ajouter(mot, Entree("classe", cls, libelle=lex.labels.get(cls, cls)))
    for c, p in _valeurs("SELECT ?c ?p WHERE { ?c rdfs:subClassOf ?p FILTER(isIRI(?c) && isIRI(?p)) }", "c", "p"):
        lex.parents.setdefault(c, set()).add(p)

    # Qualificatifs déduits des labels : "Contrat automobile" sous "Contrat d'assurance" -> "automobile"
    for cls, parents in lex.parents.items():
        for parent in parents:
            tete = lex.labels.get(parent, "").split(" ")[0].lower()
            label = lex.labels.get(cls, "")
            if tete and label.lower().startswith(tete + " "):
                qualif = re.sub(r"^(d'|de |des )", "", label[len(tete) + 1:].strip().lower())
                lex.qualificatifs.setdefault(qualif, set()).add(cls)
    for qualif in list(lex.qualificatifs):
        for mot in [qualif] + syn.QUALIFICATIFS.get(qualif, []):
            lex.ajouter(mot, Entree("qualificatif", qualif, libelle=qualif))

    # Graphe des propriétés objet
    for p, d, r in _valeurs("""
SELECT ?p ?d ?r WHERE { ?p a owl:ObjectProperty ; rdfs:domain ?d ; rdfs:range ?r FILTER(isIRI(?d) && isIRI(?r)) }""",
                            "p", "d", "r"):
        lex.aretes.append((p, d, r))
        lex.noeuds.update((d, r))
    lex.aretes.sort()

    # Propriétés de données : labels, domaines (y compris owl:unionOf), attributs numériques
    for p, label in _valeurs("SELECT ?p ?l WHERE { ?p a owl:DatatypeProperty ; rdfs:label ?l }", "p", "l"):
        lex.labels[p] = label
    for p, d in _valeurs("""
SELECT ?p ?d WHERE { ?p a owl:DatatypeProperty .
                     { ?p rdfs:domain ?d FILTER(isIRI(?d)) } UNION { ?p rdfs:domain/owl:unionOf/rdf:rest*/rdf:first ?d } }""",
                         "p", "d"):
        lex.domaines.setdefault(p, set()).add(d)
    # xsd:float, ou restriction sur xsd:float (taux entre 0 et 1)
    for (p,) in _valeurs("""
SELECT ?p WHERE { ?p a owl:DatatypeProperty . { ?p rdfs:range xsd:float } UNION { ?p rdfs:range/owl:onDatatype xsd:float } }""",
                         "p"):
        lex.attributs[p] = next(iter(lex.domaines.get(p, {""})))
    for p, mots in syn.ATTRIBUTS.items():
        for mot in mots + [lex.labels.get(p, "")]:
            lex.ajouter(mot, Entree("attribut", p, libelle=lex.labels.get(p, p)))

    # Individus désignés par une valeur : personnes, assureurs, garanties, clauses, barèmes, contrats
    individus = _valeurs("""
SELECT ?i ?classe ?texte WHERE {
  ?i a owl:NamedIndividual , ?classe . ?classe rdfs:label ?l .
  FILTER NOT EXISTS { ?i a ?sous . ?sous rdfs:subClassOf ?classe FILTER(?sous != ?classe) }
  { ?i :prenom ?texte } UNION { ?i :nom ?texte } UNION { ?i :prenom ?p ; :nom ?n BIND(CONCAT(?p, " ", ?n) AS ?texte) }
  UNION { ?i :raisonSociale ?texte } UNION { ?i :raisonSociale ?r BIND(STRBEFORE(?r, " ") AS ?texte) }
  UNION { ?i :libelleGarantie ?texte } UNION { ?i :libelleClause ?texte } UNION { ?i :libelleBareme ?texte }
  UNION { ?i :numeroContrat ?texte }
}""", "i", "classe", "texte")
    for ind, cls, texte in individus:
        lex.ajouter(texte, Entree("individu", ind, classe=cls, libelle=texte))

    # Villes (valeurs de l'adresse ou du lieu du sinistre)
    for ville, p in _valeurs("""
SELECT DISTINCT ?v ?p WHERE { VALUES ?p { :adresse :lieuSinistre } ?x ?p ?v }""", "v", "p"):
        lex.villes.setdefault(ville.lower(), set()).add(p)
        lex.ajouter(ville, Entree("valeur", ville, libelle=ville))

    # Statuts, dimensions, validité
    for statut in _valeurs("SELECT ?v WHERE { :statutSinistre rdfs:range/owl:oneOf/rdf:rest*/rdf:first ?v }", "v"):
        lex.ajouter(statut[0], Entree("statut", statut[0], libelle=statut[0]))
    for statut, mots in syn.STATUTS.items():
        for mot in mots:
            lex.ajouter(mot, Entree("statut", statut, libelle=statut))
    for dimension, mots in syn.DIMENSIONS.items():
        for mot in mots:
            lex.ajouter(mot, Entree("dimension", dimension, libelle=dimension))
    for valide, mots in syn.VALIDITE.items():
        for mot in mots:
            lex.ajouter(mot, Entree("validite", str(valide).lower(), libelle="en cours" if valide else "expiré"))
    return lex
