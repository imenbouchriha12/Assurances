"""Corps des requêtes POST/PUT/PATCH. Les identifiants (ex. "Assureur_STAR") sont les noms locaux des individus."""
from datetime import date

from pydantic import BaseModel, Field


class AssureIn(BaseModel):
    nom: str = Field(min_length=1, max_length=80, examples=["Ben Ali"])
    prenom: str = Field(min_length=1, max_length=80, examples=["Nour"])
    cin: str = Field(pattern=r"^\d{8}$", examples=["12345699"])
    adresse: str | None = Field(None, max_length=120, examples=["Bizerte"])


class AssureMaj(BaseModel):
    nom: str | None = Field(None, min_length=1, max_length=80)
    prenom: str | None = Field(None, min_length=1, max_length=80)
    cin: str | None = Field(None, pattern=r"^\d{8}$")
    adresse: str | None = Field(None, max_length=120)


class ContratIn(BaseModel):
    type: str = Field(examples=["ContratAutomobile"])
    assure: str = Field(examples=["Assure_Ines"])
    assureur: str = Field(examples=["Assureur_COMAR"])
    dateDebut: date = Field(examples=["2026-11-01"])
    dateFin: date = Field(examples=["2027-10-31"])
    prime: float = Field(gt=0, examples=[510.0])
    garanties: list[str] = Field(min_length=1, examples=[["Garantie_RC_Auto", "Garantie_Vol_Auto"]])
    clauses: list[str] = Field(default_factory=list, examples=[["Clause_AssuranceObligatoireRC"]])
    franchise: str | None = Field(None, examples=["Franchise_Auto_001"])


class ContratMaj(BaseModel):
    assureur: str | None = None
    dateDebut: date | None = None
    dateFin: date | None = None
    prime: float | None = Field(None, gt=0)
    garanties: list[str] | None = Field(None, min_length=1)
    clauses: list[str] | None = None
    franchise: str | None = None


class DommageIn(BaseModel):
    type: str = Field(examples=["DommageMateriel"])
    montantEstime: float = Field(ge=0, examples=[1800.0])
    description: str | None = Field(None, max_length=300, examples=["Vitre arrière brisée"])


class SinistreIn(BaseModel):
    type: str = Field(examples=["SinistreAutomobile"])
    contrat: str = Field(examples=["Contrat_002"])
    dateSinistre: date = Field(examples=["2026-10-20"])
    description: str = Field(min_length=3, max_length=500, examples=["Accrochage sur un parking"])
    lieu: str | None = Field(None, max_length=120, examples=["La Marsa"])
    # Sinistre ⊑ causeDommage min 1 Dommage
    dommages: list[DommageIn] = Field(min_length=1)
    garanties: list[str] = Field(default_factory=list, examples=[["Garantie_RC_Auto"]])


class StatutIn(BaseModel):
    statut: str = Field(examples=["EnExpertise"])
    expert: str | None = Field(None, examples=["Expert_Karim"])


class IndemnisationIn(BaseModel):
    bareme: str = Field(examples=["Bareme_Habitation_2025"])


# ---------- Référentiel (le type d'une garantie ou d'une clause ne change plus après sa création) ----------

class AssureurIn(BaseModel):
    raisonSociale: str = Field(min_length=2, max_length=100, examples=["AMI Assurances"])
    adresse: str | None = Field(None, max_length=120, examples=["Tunis"])
    garanties: list[str] = Field(default_factory=list, description="Garanties proposées (catalogue de la compagnie)",
                                 examples=[["Garantie_RC_Auto"]])


class ExpertIn(AssureIn):
    specialite: str | None = Field(None, max_length=80, examples=["Automobile"])
    # Expert ⊑ ∃travaillePour.Assureur
    assureurs: list[str] = Field(min_length=1, description="Compagnies qui mandatent l'expert", examples=[["Assureur_STAR"]])


class GarantieIn(BaseModel):
    type: str = Field(examples=["GarantieVol"])
    libelle: str = Field(min_length=2, max_length=120, examples=["Vol des bagages"])
    plafond: float = Field(gt=0, examples=[5000.0])


class ClauseIn(BaseModel):
    type: str = Field(examples=["ClauseExclusion"])
    libelle: str = Field(min_length=2, max_length=150, examples=["Exclusion des catastrophes naturelles"])
    texte: str = Field(min_length=5, max_length=1000, examples=["Les dommages dus aux catastrophes naturelles ne sont pas garantis."])
    reference: str = Field(min_length=2, max_length=200, examples=["Conditions générales du contrat"])
    garanties: list[str] = Field(default_factory=list, description="Garanties exclues (clause d'exclusion seulement)",
                                 examples=[["Garantie_Incendie_Hab"]])


class BaremeIn(BaseModel):
    # Un barème est défini par exactement un assureur (axiome sur l'inverse de definitBareme)
    assureur: str = Field(examples=["Assureur_COMAR"])
    libelle: str = Field(min_length=2, max_length=120, examples=["Barème vol 2026"])
    taux: float = Field(ge=0, le=1, description="0.8 = 80 %", examples=[0.75])
    garanties: list[str] = Field(default_factory=list, examples=[["Garantie_Vol_Hab"]])


class FranchiseIn(BaseModel):
    montant: float = Field(ge=0, examples=[250.0])


class RequeteSparql(BaseModel):
    requete: str = Field(min_length=1, examples=["SELECT ?s WHERE { ?s a :SinistreGrave }"])
