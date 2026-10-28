"""Analyse linguistique d'une question avec spaCy (modèle fr_core_news_md).

Étapes :
  1. pré-traitement (apostrophes, nombres "5 000" -> "5000") ;
  2. pipeline spaCy : tokenisation, étiquetage morpho-syntaxique (POS), lemmatisation, entités nommées ;
  3. reconnaissance des concepts de l'ontologie avec un spacy.Matcher : chaque entrée du lexique devient
     un motif qui compare le lemme OU la forme de chaque mot, sans tenir compte des accents
     ("contrats automobiles" et "contrat automobile" donnent le même motif) ;
  4. motifs de comparaison ("plus de 5000", "supérieure à 500", "entre 1000 et 3000") avec un second Matcher ;
  5. dates (années, dates complètes), négations ("non couverts") et regroupements ("par statut").
Avant l'étape 3, les fautes de frappe sont corrigées : un mot inconnu du modèle spaCy est remplacé par
le mot du lexique le plus proche ("expprt" -> "expert").
"""
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import get_close_matches

from spacy.matcher import Matcher
from spacy.tokens import Token

from . import synonymes as syn


def sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFKD", texte) if not unicodedata.combining(c))


# Clés de comparaison d'un mot : sa forme et son lemme, en minuscules et sans accents
Token.set_extension("cles", getter=lambda t: sorted({sans_accents(t.lower_), sans_accents(t.lemma_.lower())}), force=True)


@dataclass
class Mention:
    debut: int
    fin: int
    texte: str
    entrees: list
    negation: bool = False
    regroupement: bool = False

    def de_type(self, *types):
        return [e for e in self.entrees if e.type in types]


@dataclass
class Comparaison:
    operateur: str          # >, >=, <, <=, entre
    valeurs: list
    texte: str
    debut: int = 0
    fin: int = 0


@dataclass
class FiltreDate:
    operateur: str          # annee, >=, <, entre, =
    valeurs: list           # dates ISO (ou années pour "annee")
    texte: str
    debut: int = 0
    fin: int = 0


@dataclass
class Analyse:
    question: str
    tokens: list = field(default_factory=list)          # [{texte, lemme, pos}]
    entites_nommees: list = field(default_factory=list)  # entités spaCy (LOC, PER...)
    mentions: list = field(default_factory=list)
    comparaisons: list = field(default_factory=list)
    dates: list = field(default_factory=list)
    cles: set = field(default_factory=set)               # lemmes sans accents de la question
    texte_delexicalise: str = ""                         # entrée du classifieur d'intention
    corrections: list = field(default_factory=list)      # [{mot, correction}] fautes de frappe corrigées


_NOMBRES = re.compile(r"(?<=\d)[\s  ](?=\d{3}\b)")
_DATE_COMPLETE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")

# Motifs de comparaison (token patterns spaCy)
_NOMBRE = {"LIKE_NUM": True}
_MOTIFS_COMPARAISON = {
    "entre": [[{"LOWER": "entre"}, _NOMBRE, {"LOWER": {"IN": ["dt", "dinars", "tnd"]}, "OP": "?"}, {"LOWER": "et"}, _NOMBRE]],
    ">=": [[{"LOWER": "au"}, {"LOWER": "moins"}, _NOMBRE]],
    "<=": [[{"LOWER": "au"}, {"LOWER": "plus"}, _NOMBRE]],
    ">": [
        [{"LOWER": "plus"}, {"LOWER": {"IN": ["de", "d'", "que"]}}, _NOMBRE],
        [{"LEMMA": {"IN": ["supérieur", "dépasser", "excéder"]}}, {"LOWER": {"IN": ["à", "au", "de"]}, "OP": "?"}, _NOMBRE],
        [{"LOWER": {"IN": ["supérieur", "supérieure", "supérieurs", "supérieures"]}},
         {"LOWER": {"IN": ["à", "au"]}, "OP": "?"}, _NOMBRE],
        [{"LOWER": "au"}, {"LOWER": {"IN": ["-", "dessus"]}}, {"LOWER": "dessus", "OP": "?"}, {"LOWER": "de"}, _NOMBRE],
        [{"ORTH": ">"}, _NOMBRE],
    ],
    "<": [
        [{"LOWER": "moins"}, {"LOWER": {"IN": ["de", "d'", "que"]}}, _NOMBRE],
        [{"LEMMA": {"IN": ["inférieur"]}}, {"LOWER": {"IN": ["à", "au"]}, "OP": "?"}, _NOMBRE],
        [{"LOWER": {"IN": ["inférieur", "inférieure", "inférieurs", "inférieures"]}},
         {"LOWER": {"IN": ["à", "au"]}, "OP": "?"}, _NOMBRE],
        [{"LOWER": "en"}, {"LOWER": "dessous"}, {"LOWER": "de"}, _NOMBRE],
        [{"ORTH": "<"}, _NOMBRE],
    ],
}


def _nombre(texte):
    try:
        return float(texte.replace(",", "."))
    except ValueError:
        return None


class Analyseur:
    def __init__(self, nlp, lexique):
        self.nlp = nlp
        self.lexique = lexique
        self.matcher = Matcher(nlp.vocab)
        self.entrees = {}
        self.vocabulaire = {}  # mot sans accents -> mot du lexique (correction des fautes de frappe)
        # Chaque phrase du lexique passe par le même pipeline que la question
        groupes = {}
        textes = [p for p, _ in lexique.phrases]
        for (_, entree), doc in zip(lexique.phrases, nlp.pipe(textes, batch_size=128)):
            for t in doc:
                if t.is_alpha and len(t) >= 4:
                    self.vocabulaire.setdefault(sans_accents(t.lower_), t.lower_)
            cle = tuple(tuple(t._.cles) for t in doc if not t.is_punct or t.text in ("'", "-"))
            if cle:
                groupes.setdefault(cle, set()).add(entree)
        for i, (cle, entrees) in enumerate(groupes.items()):
            nom = f"LEX{i}"
            self.matcher.add(nom, [[{"_": {"cles": {"INTERSECTS": list(c)}}} for c in cle]])
            self.entrees[nom] = sorted(entrees, key=lambda e: (e.type, e.valeur))

        self.comparateurs = Matcher(nlp.vocab)
        for operateur, motifs in _MOTIFS_COMPARAISON.items():
            self.comparateurs.add(operateur, motifs)

    def corriger(self, doc):
        """Fautes de frappe -> {indice du mot: correction}. Seuls les mots absents du modèle spaCy (is_oov)
        et du lexique sont corrigés : un mot français correct n'est jamais remplacé."""
        corrections = {}
        for t in doc:
            cle = sans_accents(t.lower_)
            if t.is_alpha and len(t) >= 4 and t.is_oov and cle not in self.vocabulaire:
                proches = get_close_matches(cle, self.vocabulaire, n=1, cutoff=0.8)
                if proches:
                    corrections[t.i] = self.vocabulaire[proches[0]]
        return corrections

    def analyser(self, question):
        texte = _NOMBRES.sub("", question.replace("’", "'").strip())
        texte = _DATE_COMPLETE.sub(lambda m: f"{m[3]}-{int(m[2]):02d}-{int(m[1]):02d}", texte)
        doc = self.nlp(texte)
        corrections = self.corriger(doc)
        if corrections:
            texte = "".join(corrections[t.i] + t.whitespace_ if t.i in corrections else t.text_with_ws for t in doc)
        a = Analyse(question=question)
        a.corrections = [{"mot": doc[i].text, "correction": c} for i, c in corrections.items()]
        if corrections:
            doc = self.nlp(texte)
        a.tokens = [{"texte": t.text, "lemme": t.lemma_, "pos": t.pos_} for t in doc]
        a.entites_nommees = [{"texte": e.text, "type": e.label_} for e in doc.ents]
        a.cles = {sans_accents(t.lemma_.lower()) for t in doc} | {sans_accents(t.lower_) for t in doc}
        occupe = set()

        # Comparaisons (prioritaires : "plus de 5000" ne doit pas être lu comme un superlatif)
        for match_id, debut, fin in sorted(self.comparateurs(doc), key=lambda m: (m[1], -(m[2] - m[1]))):
            if occupe & set(range(debut, fin)):
                continue
            valeurs = [v for t in doc[debut:fin] if t.like_num and (v := _nombre(t.text)) is not None]
            operateur = self.nlp.vocab.strings[match_id]
            if operateur == "entre" and all(v.is_integer() and 1900 <= v <= 2100 for v in valeurs):
                continue  # "entre 2024 et 2025" : intervalle de dates, traité plus bas
            if valeurs:
                a.comparaisons.append(Comparaison(self.nlp.vocab.strings[match_id], valeurs, doc[debut:fin].text, debut, fin))
                occupe |= set(range(debut, fin))

        # Concepts de l'ontologie : on garde les correspondances les plus longues, sans chevauchement.
        # Avant les dates : dans "barème habitation 2025", l'année fait partie du nom de l'individu.
        candidats = {}
        for match_id, debut, fin in self.matcher(doc):
            candidats.setdefault((debut, fin), []).extend(self.entrees[self.nlp.vocab.strings[match_id]])
        for (debut, fin), entrees in sorted(candidats.items(), key=lambda c: (-(c[0][1] - c[0][0]), c[0][0])):
            if occupe & set(range(debut, fin)):
                continue
            avant = [x.lower_ for x in doc[max(0, debut - 3):debut]]
            mention = Mention(debut, fin, doc[debut:fin].text, list(dict.fromkeys(entrees)))
            mention.negation = any(m in syn.NEGATIONS for m in avant[-2:])
            # "par statut" (regroupement) mais pas "par la garantie vol" (relation)
            mention.regroupement = bool(avant) and (avant[-1] in ("par", "chaque", "selon"))
            a.mentions.append(mention)
            occupe |= set(range(debut, fin))
        a.mentions.sort(key=lambda m: m.debut)

        # Dates : AAAA-MM-JJ (dates complètes normalisées plus haut) puis années seules
        for t in doc:
            if t.i in occupe:
                continue
            precedent = " ".join(x.lower_ for x in doc[max(0, t.i - 3):t.i])
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t.text):
                op = ">=" if re.search(r"(après|depuis|partir de)$", precedent) else "<" if precedent.endswith("avant") else "="
                a.dates.append(FiltreDate(op, [t.text], t.text, t.i, t.i + 1))
                occupe.add(t.i)
            elif re.fullmatch(r"(19|20)\d{2}", t.text):
                annee = int(t.text)
                if re.search(r"entre$", precedent) and t.i + 2 < len(doc) and doc[t.i + 1].lower_ == "et" \
                        and re.fullmatch(r"(19|20)\d{2}", doc[t.i + 2].text):
                    fin_ = int(doc[t.i + 2].text)
                    a.dates.append(FiltreDate("entre", [f"{annee}-01-01", f"{fin_ + 1}-01-01"], doc[t.i:t.i + 3].text, t.i, t.i + 3))
                    occupe |= {t.i, t.i + 1, t.i + 2}
                    continue
                if re.search(r"(depuis|partir de)$", precedent):
                    a.dates.append(FiltreDate(">=", [f"{annee}-01-01"], t.text, t.i, t.i + 1))
                elif precedent.endswith("après"):
                    a.dates.append(FiltreDate(">=", [f"{annee + 1}-01-01"], t.text, t.i, t.i + 1))
                elif precedent.endswith("avant"):
                    a.dates.append(FiltreDate("<", [f"{annee}-01-01"], t.text, t.i, t.i + 1))
                else:
                    a.dates.append(FiltreDate("annee", [annee], t.text, t.i, t.i + 1))
                occupe.add(t.i)

        # Texte délexicalisé pour le classifieur : les concepts deviennent leur type
        morceaux, i = [], 0
        while i < len(doc):
            mention = next((m for m in a.mentions if m.debut == i), None)
            comparaison = next((c for c in a.comparaisons if c.debut == i), None)
            date = next((d for d in a.dates if d.debut == i), None)
            if mention:
                types = {e.type for e in mention.entrees}
                morceaux.append("ATTRIBUT" if types == {"attribut"} else "CONCEPT")
                i = mention.fin
            elif comparaison:
                morceaux.append("COMPARAISON")
                i = comparaison.fin
            elif date:
                morceaux.append("DATE")
                i = date.fin
            else:
                t = doc[i]
                if t.like_num and any(ch.isdigit() for ch in t.text):  # "une" n'est pas un nombre ici
                    morceaux.append("NOMBRE")
                elif not t.is_punct:
                    morceaux.append(sans_accents(t.lemma_.lower()))
                i += 1
        a.texte_delexicalise = " ".join(morceaux)
        return a
