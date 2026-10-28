"""Classification de l'intention de la question (scikit-learn : TF-IDF + régression logistique).

Le classifieur ne voit pas les mots du domaine : l'analyseur les remplace par CONCEPT, ATTRIBUT,
COMPARAISON, DATE, NOMBRE (texte délexicalisé). Il apprend donc la forme de la question
("combien de CONCEPT", "le CONCEPT le plus ATTRIBUT"...), ce qui le rend indépendant des données.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline

EXEMPLES = {
    "lister": [
        "Quels sont les sinistres graves ?", "Liste des contrats automobiles en cours", "Affiche les assurés de Sousse",
        "Montre-moi les sinistres refusés", "Quels contrats a STAR ?", "Donne les garanties du contrat CT-2025-003",
        "Quelles clauses d'exclusion concernent la garantie vol ?", "Sinistres habitation à Sousse", "Les contrats expirés",
        "Quels experts ont expertisé des sinistres automobiles ?", "Je veux voir les indemnisations de 2025",
        "Contrats avec une prime supérieure à 500", "Sinistres de plus de 5000 dinars",
        "Quels sont les assurés qui ont un contrat santé ?", "Recherche les accidents de voiture",
        "Quelles garanties couvrent le vol ?", "Trouve les sinistres de Sarra", "Afficher les barèmes d'indemnisation",
        "Les sinistres déclarés après 2025", "Quels sont les dommages corporels ?", "Quel est le plafond de la garantie incendie ?",
        "Qui sont les clients de COMAR ?", "Donne-moi la liste des experts", "Contrats qui expirent en 2026",
        "Sinistres entre 2024 et 2025", "Quelles sont les clauses obligatoires ?", "assurances vie",
        "Quel est le taux du barème auto 2024 ?", "Quelle est la prime du contrat CT-2026-002 ?",
        "Quel est le montant de la franchise du contrat CT-2025-006 ?",
    ],
    "compter": [
        "Combien de sinistres graves ?", "Combien de contrats a STAR ?", "Nombre de sinistres par statut",
        "Combien d'assurés habitent à Tunis ?", "Quel est le nombre de contrats en cours ?", "Nombre total de sinistres en 2025",
        "Combien y a-t-il de garanties ?", "Compte les sinistres non couverts", "Combien de contrats par type ?",
        "Nombre de clauses d'exclusion", "Combien de sinistres a déclaré Youssef ?", "Combien d'experts ?",
        "Nombre de sinistres par ville", "Combien de contrats habitation ?", "Combien de dossiers refusés ?",
        "Combien de sinistres par assureur ?", "Le nombre d'assurés", "Combien de sinistres de plus de 5000 ?",
    ],
    "somme": [
        "Quel est le montant total indemnisé par STAR ?", "Total des indemnisations par assureur",
        "Somme des primes des contrats en cours", "Montant total des dommages des sinistres habitation",
        "Combien a été indemnisé au total ?", "Total des primes par assureur", "Quel est le total des remboursements en 2025 ?",
        "Additionne les primes des contrats automobiles", "Montant cumulé des indemnisations", "Total des dommages estimés",
        "Somme des indemnités versées par COMAR", "Combien a payé GAT au total ?", "Chiffre total des primes encaissées",
        "Total indemnisé par type de sinistre",
    ],
    "moyenne": [
        "Quelle est la prime moyenne ?", "Montant moyen des indemnisations", "Moyenne des primes des contrats automobiles",
        "Prime moyenne par type de contrat", "Coût moyen des sinistres", "En moyenne combien coûte un sinistre habitation ?",
        "Quel est le plafond moyen des garanties ?", "Moyenne des dommages par sinistre", "Indemnisation moyenne par assureur",
        "Taux moyen des barèmes", "Quelle est la moyenne des primes ?",
    ],
    "maximum": [
        "Quel est le sinistre le plus coûteux ?", "Le contrat avec la prime la plus élevée", "Quelle est la plus grosse indemnisation ?",
        "Quelle garantie a le plafond le plus haut ?", "Le sinistre le plus cher", "Prime maximale des contrats",
        "Quel est le dommage le plus important ?", "Le barème avec le taux le plus élevé",
        "Quel assureur a versé la plus grande indemnisation ?", "Indemnisation maximale", "Le plus gros sinistre",
    ],
    "minimum": [
        "Quel est le sinistre le moins coûteux ?", "Le contrat le moins cher", "Quelle est la plus petite indemnisation ?",
        "La prime la plus basse", "Quelle garantie a le plafond le plus bas ?", "Prime minimale", "Le dommage le plus faible",
        "Indemnisation minimale", "Le contrat avec la plus petite prime", "Quel est le barème avec le taux le plus faible ?",
        "Le sinistre le moins cher",
    ],
}

SEUIL_CONFIANCE = 0.35


def _modele():
    return make_pipeline(
        TfidfVectorizer(ngram_range=(1, 3), token_pattern=r"\S+", sublinear_tf=True),
        LogisticRegression(max_iter=2000, C=20),
    )


class ClassifieurIntention:
    def __init__(self, analyseur):
        self.textes, self.etiquettes = [], []
        for intention, phrases in EXEMPLES.items():
            for phrase in phrases:
                self.textes.append(analyseur.analyser(phrase).texte_delexicalise)
                self.etiquettes.append(intention)
        self.modele = _modele().fit(self.textes, self.etiquettes)

    def predire(self, analyse):
        probas = self.modele.predict_proba([analyse.texte_delexicalise])[0]
        meilleure = probas.argmax()
        intention, confiance = self.modele.classes_[meilleure], float(probas[meilleure])
        # Peu sûr : on liste simplement les résultats
        return (intention if confiance >= SEUIL_CONFIANCE else "lister"), round(confiance, 3)

    def evaluer(self, plis=5):
        """Exactitude moyenne en validation croisée (pour le rapport)."""
        scores = cross_val_score(_modele(), self.textes, self.etiquettes, cv=plis)
        return round(float(scores.mean()), 3), round(float(scores.std()), 3)
