"""Vocabulaire du domaine qui complète les rdfs:label / skos:altLabel lus dans l'ontologie.

Les labels de l'ontologie restent la source principale du lexique (voir lexique.py) ; ce fichier
ajoute les formulations courantes d'un utilisateur et les mots qui ne sont pas des concepts
(statuts, attributs numériques, dimensions de regroupement).
"""

# Qualificatifs : un mot seul qui précise un type ("contrats auto", "sinistres graves").
# Le sens final dépend de la classe principale de la question (voir generateur.py).
QUALIFICATIFS = {
    "automobile": ["auto", "voiture", "véhicule", "automobile", "automobiles",
                   "bagnole", "bagnoles", "caisse auto", "automobiliste", "automobilistes", "routier", "routière"],
    "habitation": ["maison", "logement", "appartement", "habitation",
                   "domicile", "villa", "appart", "résidence", "immeuble", "foyer", "multirisque habitation"],
    "santé": ["maladie", "médical", "médicale", "santé",
              "médicaux", "médicales", "soin", "soins", "hospitalisation", "hôpital", "mutuelle"],
    "vie": ["vie", "décès", "prévoyance"],
    "grave": ["grave", "graves", "sérieux", "majeur", "majeurs", "catastrophique", "catastrophiques"],
    "couvert": ["couvert", "couverts", "pris en charge", "indemnisable", "indemnisables"],
    "corporel": ["corporel", "corporels", "blessure", "blessures", "blessé", "blessés", "physique", "physiques"],
    "matériel": ["matériel", "matériels", "casse"],
    "immatériel": ["immatériel", "immatériels"],
    "exclusion": ["exclusion", "exclusions", "d'exclusion"],
    "obligatoire": ["obligatoire", "obligatoires", "obligation", "obligations"],
}

# Synonymes de classes (complètent les altLabels de l'ontologie)
CLASSES = {
    "Assure": ["client", "clients", "assuré", "assurés", "assurée", "assurées",
               "adhérent", "adhérents", "bénéficiaire", "bénéficiaires", "titulaire", "titulaires",
               "abonné", "abonnés", "personne assurée", "personnes assurées"],
    "Assureur": ["assureur", "assureurs", "compagnie", "compagnies", "société d'assurance",
                 "agence", "agences", "compagnie d'assurance", "compagnies d'assurance", "sociétés d'assurance"],
    "Sinistre": ["sinistre", "sinistres", "accident", "accidents", "déclaration", "déclarations", "dossier", "dossiers",
                 "incident", "incidents", "réclamation", "réclamations", "pépin", "pépins", "litige", "litiges"],
    "Contrat": ["contrat", "contrats", "police", "polices", "assurance",
                "souscription", "souscriptions", "adhésion", "adhésions", "formule", "formules"],
    "Expert": ["expert", "experts", "évaluateur", "évaluateurs", "inspecteur", "inspecteurs", "enquêteur", "enquêteurs"],
    "Indemnisation": ["indemnisation", "indemnisations", "indemnité", "indemnités", "remboursement", "remboursements",
                      "dédommagement", "dédommagements", "compensation", "compensations", "versement", "versements",
                      "paiement", "paiements", "règlement", "règlements"],
    "Garantie": ["garantie", "garanties", "couverture", "couvertures", "option", "options"],
    "Clause": ["clause", "clauses", "condition", "conditions", "article", "articles", "restriction", "restrictions"],
    "ContratVie": ["assurance vie", "assurances vie", "assurance décès"],
}

# Statuts d'un sinistre (valeurs de l'énumération :statutSinistre)
STATUTS = {
    "Declare": ["déclaré", "déclarés", "déclarée", "nouveau", "nouveaux", "en attente",
                "signalé", "signalés", "ouvert", "ouverts", "non traité", "non traités"],
    "EnExpertise": ["en expertise", "en cours d'expertise", "expertise en cours",
                    "en évaluation", "en examen", "en cours d'examen", "à l'étude", "en instruction"],
    "Indemnise": ["indemnisé", "indemnisés", "payé", "payés", "remboursé", "remboursés", "réglé", "réglés",
                  "dédommagé", "dédommagés", "compensé", "compensés"],
    "Refuse": ["refusé", "refusés", "rejeté", "rejetés", "refus", "décliné", "déclinés", "rejet", "rejets"],
    "Cloture": ["clôturé", "clôturés", "fermé", "fermés", "classé", "classés",
                "clos", "archivé", "archivés", "soldé", "soldés"],
}

# Attributs numériques : utilisés pour les comparaisons ("prime supérieure à 500")
# et les agrégations ("montant total indemnisé")
ATTRIBUTS = {
    "montantPrime": ["prime", "primes", "cotisation", "cotisations", "prix", "tarif",
                     "tarifs", "montant de la prime", "coût de l'assurance"],
    "montantIndemnisation": ["indemnisé", "indemnisation", "indemnisations", "remboursé", "montant indemnisé",
                             "montant remboursé", "indemnité", "indemnités", "payé", "versé",
                             "dédommagé", "montant versé", "montant payé"],
    # "cher", "coûteux" ne sont pas ici : leur sens dépend de la classe (prime d'un contrat, coût d'un sinistre),
    # c'est donc l'attribut par défaut de la classe (ATTRIBUT_PAR_DEFAUT) qui s'applique
    "montantEstime": ["dommage", "dommages", "coût", "coûts", "estimation", "montant estimé", "dégâts",
                      "dégât", "préjudice", "préjudices", "perte", "pertes", "montant des dégâts"],
    "plafondGarantie": ["plafond", "plafonds", "couverture maximale", "limite", "limites", "montant maximal couvert"],
    "montantFranchise": ["franchise", "franchises", "reste à charge"],
    "tauxIndemnisation": ["taux", "pourcentage", "taux de remboursement", "taux de prise en charge"],
}

# Attribut utilisé quand la question n'en nomme aucun (ex. "le sinistre le plus coûteux")
ATTRIBUT_PAR_DEFAUT = {
    "Contrat": "montantPrime",
    "Sinistre": "montantEstime",
    "Indemnisation": "montantIndemnisation",
    "Garantie": "plafondGarantie",
    "Dommage": "montantEstime",
    "Franchise": "montantFranchise",
    "BaremeIndemnisation": "tauxIndemnisation",
}

# Verbes qui désignent une propriété objet : "les experts et où ils travaillent" affiche l'assureur
# de chaque expert (l'autre extrémité de :travaillePour). Pas de lecture automatique des labels des
# propriétés : "est couvert par" capterait "couverts", qui est un qualificatif.
RELATIONS = {
    "travaillePour": ["travaille", "travailler", "travaillent", "employeur", "employeurs", "mandaté", "mandatés",
                      "bosse", "bosser", "bossent", "employé", "employés", "embauché", "embauchés"],
}

# Dimensions de regroupement ("par statut", "par type", "par ville", "par année")
DIMENSIONS = {
    "type": ["type", "types", "catégorie", "catégories", "genre", "genres", "sorte", "sortes", "nature", "branche", "branches"],
    "statut": ["statut", "statuts", "état", "états", "situation", "situations", "avancement"],
    "ville": ["ville", "villes", "lieu", "lieux", "région", "régions",
              "gouvernorat", "gouvernorats", "localité", "localités", "endroit", "endroits", "commune", "communes"],
    "annee": ["année", "années", "an", "ans", "exercice", "exercices"],
}

# Validité d'un contrat (calculée à partir de la date de fin)
VALIDITE = {
    True: ["en cours", "valide", "valides", "actif", "actifs", "active", "actives", "en vigueur",
           "actuel", "actuels", "actuelle", "actuelles", "courant", "courants", "non expiré", "non expirés"],
    False: ["expiré", "expirés", "expirée", "expirées", "terminé", "terminés", "échu", "échus", "inactif", "inactifs",
            "périmé", "périmés", "résilié", "résiliés", "ancien", "anciens", "fini", "finis"],
}

# Mots qui font porter le filtre de date sur la fin du contrat plutôt que sur son début
DATE_FIN = ["expire", "expirent", "expiration", "fin", "finit", "finissent", "échéance", "termine", "terminent"]

NEGATIONS = ["non", "pas", "sans", "aucun", "aucune", "jamais"]

# Affichage d'une ressource selon sa classe : colonnes du résultat et libellé (pour les regroupements)
AFFICHAGE = {
    "Sinistre": {"colonnes": [("date", "dateSinistre"), ("description", "descriptionSinistre"),
                              ("statut", "statutSinistre"), ("lieu", "lieuSinistre")],
                 "libelle": "descriptionSinistre"},
    "Contrat": {"colonnes": [("numero", "numeroContrat"), ("debut", "dateDebutContrat"),
                             ("fin", "dateFinContrat"), ("prime", "montantPrime")],
                "libelle": "numeroContrat"},
    "Assure": {"colonnes": [("prenom", "prenom"), ("nom", "nom"), ("cin", "cin"), ("adresse", "adresse")],
               "libelle": "nom"},
    "Expert": {"colonnes": [("prenom", "prenom"), ("nom", "nom"), ("specialite", "specialite")],
               "libelle": "nom"},
    "Assureur": {"colonnes": [("raisonSociale", "raisonSociale"), ("adresse", "adresse")],
                 "libelle": "raisonSociale"},
    "Garantie": {"colonnes": [("libelle", "libelleGarantie"), ("plafond", "plafondGarantie")],
                 "libelle": "libelleGarantie"},
    "Clause": {"colonnes": [("libelle", "libelleClause"), ("texte", "texteClause"), ("reference", "referenceLegale")],
               "libelle": "libelleClause"},
    "Dommage": {"colonnes": [("description", "descriptionDommage"), ("montant", "montantEstime")],
                "libelle": "descriptionDommage"},
    "Indemnisation": {"colonnes": [("montant", "montantIndemnisation"), ("date", "dateIndemnisation")],
                      "libelle": "montantIndemnisation"},
    "BaremeIndemnisation": {"colonnes": [("libelle", "libelleBareme"), ("taux", "tauxIndemnisation")],
                            "libelle": "libelleBareme"},
    "Franchise": {"colonnes": [("montant", "montantFranchise")], "libelle": "montantFranchise"},
}

# Propriété de date par défaut de chaque classe
DATES = {"Sinistre": "dateSinistre", "Contrat": "dateDebutContrat", "Indemnisation": "dateIndemnisation"}

# Nom de la variable SPARQL principale (lisible dans la requête générée)
VARIABLES = {"Sinistre": "sinistre", "Contrat": "contrat", "Assure": "assure", "Expert": "expert",
             "Assureur": "assureur", "Garantie": "garantie", "Clause": "clause", "Dommage": "dommage",
             "Indemnisation": "indemnisation", "BaremeIndemnisation": "bareme", "Franchise": "franchise"}
