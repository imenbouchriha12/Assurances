"""Vocabulaire du domaine qui complète les rdfs:label / skos:altLabel lus dans l'ontologie.

Les labels de l'ontologie restent la source principale du lexique (voir lexique.py) ; ce fichier
ajoute les formulations courantes d'un utilisateur et les mots qui ne sont pas des concepts
(statuts, attributs numériques, dimensions de regroupement).
"""

# Qualificatifs : un mot seul qui précise un type ("contrats auto", "sinistres graves").
# Le sens final dépend de la classe principale de la question (voir generateur.py).
QUALIFICATIFS = {
    "automobile": ["auto", "voiture", "véhicule", "automobile", "automobiles"],
    "habitation": ["maison", "logement", "appartement", "habitation"],
    "santé": ["maladie", "médical", "médicale", "santé"],
    "vie": ["vie"],
    "grave": ["grave", "graves", "sérieux"],
    "couvert": ["couvert", "couverts", "pris en charge"],
    "corporel": ["corporel", "corporels", "blessure", "blessures"],
    "matériel": ["matériel", "matériels"],
    "immatériel": ["immatériel", "immatériels"],
    "exclusion": ["exclusion", "exclusions", "d'exclusion"],
    "obligatoire": ["obligatoire", "obligatoires", "obligation", "obligations"],
}

# Synonymes de classes (complètent les altLabels de l'ontologie)
CLASSES = {
    "Assure": ["client", "clients", "assuré", "assurés", "assurée", "assurées"],
    "Assureur": ["assureur", "assureurs", "compagnie", "compagnies", "société d'assurance"],
    "Sinistre": ["sinistre", "sinistres", "accident", "accidents", "déclaration", "déclarations", "dossier", "dossiers"],
    "Contrat": ["contrat", "contrats", "police", "polices", "assurance"],
    "Expert": ["expert", "experts"],
    "Indemnisation": ["indemnisation", "indemnisations", "indemnité", "indemnités", "remboursement", "remboursements"],
    "ContratVie": ["assurance vie", "assurances vie"],
}

# Statuts d'un sinistre (valeurs de l'énumération :statutSinistre)
STATUTS = {
    "Declare": ["déclaré", "déclarés", "déclarée", "nouveau", "nouveaux", "en attente"],
    "EnExpertise": ["en expertise", "en cours d'expertise", "expertise en cours"],
    "Indemnise": ["indemnisé", "indemnisés", "payé", "payés", "remboursé", "remboursés", "réglé", "réglés"],
    "Refuse": ["refusé", "refusés", "rejeté", "rejetés", "refus"],
    "Cloture": ["clôturé", "clôturés", "fermé", "fermés", "classé", "classés"],
}

# Attributs numériques : utilisés pour les comparaisons ("prime supérieure à 500")
# et les agrégations ("montant total indemnisé")
ATTRIBUTS = {
    "montantPrime": ["prime", "primes", "cotisation", "cotisations", "prix", "tarif"],
    "montantIndemnisation": ["indemnisé", "indemnisation", "indemnisations", "remboursé", "montant indemnisé",
                             "montant remboursé", "indemnité", "indemnités", "payé", "versé"],
    # "cher", "coûteux" ne sont pas ici : leur sens dépend de la classe (prime d'un contrat, coût d'un sinistre),
    # c'est donc l'attribut par défaut de la classe (ATTRIBUT_PAR_DEFAUT) qui s'applique
    "montantEstime": ["dommage", "dommages", "coût", "coûts", "estimation", "montant estimé", "dégâts"],
    "plafondGarantie": ["plafond", "plafonds", "couverture maximale"],
    "montantFranchise": ["franchise", "franchises"],
    "tauxIndemnisation": ["taux", "pourcentage"],
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

# Dimensions de regroupement ("par statut", "par type", "par ville", "par année")
DIMENSIONS = {
    "type": ["type", "types", "catégorie", "catégories"],
    "statut": ["statut", "statuts", "état", "états"],
    "ville": ["ville", "villes", "lieu", "lieux", "région", "régions"],
    "annee": ["année", "années", "an", "ans"],
}

# Validité d'un contrat (calculée à partir de la date de fin)
VALIDITE = {
    True: ["en cours", "valide", "valides", "actif", "actifs", "active", "actives", "en vigueur"],
    False: ["expiré", "expirés", "expirée", "expirées", "terminé", "terminés", "échu", "échus", "inactif", "inactifs"],
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
