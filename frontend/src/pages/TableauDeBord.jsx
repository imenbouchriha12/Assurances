import { Link } from "react-router-dom";

import { useDonnees } from "../api.js";
import { Barres, Tuile } from "../components/Graphiques.jsx";
import { Icone } from "../components/icones.jsx";
import { TableSinistres } from "../components/Tables.jsx";
import { Etat, libelleStatut, marqueStatut, montant } from "../components/ui.jsx";

const decimal = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
const somme = (lignes, champ) => lignes.reduce((t, l) => t + (l[champ] ?? 0), 0);

export default function TableauDeBord() {
  const stats = useDonnees("/statistiques");
  const sinistres = useDonnees("/sinistres");
  const s = stats.donnees;
  const aTraiter = sinistres.donnees?.filter((x) => ["Declare", "EnExpertise"].includes(x.statut)).length;

  return (
    <>
      <section className="banniere">
        <div>
          <h1>Vue d'ensemble</h1>
          <p>
            Portefeuille de contrats et suivi des sinistres, calculés à partir de l'ontologie.
            {aTraiter > 0 && <> <strong>{aTraiter} dossier{aTraiter > 1 ? "s" : ""}</strong> en attente de traitement.</>}
          </p>
        </div>
        <div className="actions">
          <Link className="bouton" to="/sinistres?nouveau=1"><Icone nom="plus" taille={18} /> Déclarer un sinistre</Link>
          <Link className="bouton secondaire" to="/contrats?nouveau=1"><Icone nom="contrats" taille={18} /> Nouveau contrat</Link>
        </div>
      </section>

      <Etat {...stats}>
        {s && (
          <>
            {/* Toutes les tuiles ont la même structure : titre + icône, valeur, une ligne de contexte */}
            <div className="tuiles">
              <Tuile titre="Contrats" icone="contrats" valeur={s.totaux.nbContrats}
                     detail={`${s.totaux.nbContratsValides} en cours`} />
              <Tuile titre="Assurés" icone="assures" valeur={s.totaux.nbAssures}
                     detail={`${decimal.format(s.totaux.nbContrats / (s.totaux.nbAssures || 1))} contrats par assuré`} />
              <Tuile titre="Primes" icone="argent" valeur={montant(s.totaux.totalPrimes)}
                     detail={`moyenne ${montant(s.totaux.totalPrimes / (s.totaux.nbContrats || 1))}`} />
              <Tuile titre="Sinistres" icone="sinistres" valeur={s.totaux.nbSinistres}
                     detail={`dont ${s.totaux.nbSinistresGraves} graves (règle SWRL)`} />
              <Tuile titre="Total indemnisé" icone="check" valeur={montant(s.totaux.totalIndemnise)}
                     detail={`${somme(s.indemnisationsParAssureur, "nombre")} indemnisations versées`} />
            </div>

            {/* Lecture de gauche à droite : portefeuille, sinistralité, puis indemnisation */}
            <div className="grille-graphiques">
              <Barres titre="Contrats par type" icone="contrats" resume={`${s.totaux.nbContrats} au total`}
                      donnees={s.contratsParType.map((x) => ({ label: x.label, valeur: x.nombre }))} />
              <Barres titre="Sinistres par type" icone="sinistres" resume={`${s.totaux.nbSinistres} au total`}
                      donnees={s.sinistresParType.map((x) => ({ label: x.label, valeur: x.nombre }))} />
              <Barres titre="Sinistres par statut" icone="graphique" resume={`${aTraiter ?? 0} à traiter`}
                      donnees={s.sinistresParStatut.map((x) => ({ label: libelleStatut(x.statut), valeur: x.nombre, ...marqueStatut(x.statut) }))} />
              <Barres titre="Indemnisé par assureur" icone="entreprise" format={montant} resume={montant(s.totaux.totalIndemnise)}
                      donnees={s.indemnisationsParAssureur.map((x) => ({
                        label: x.raisonSociale, valeur: x.total, detail: `${x.nombre} indemnisation(s)`,
                      }))} />
            </div>
          </>
        )}
      </Etat>

      <section className="carte sans-marge">
        <div className="carte-entete">
          <h2 className="titre-icone"><span className="tuile-icone"><Icone nom="calendrier" taille={16} /></span> Derniers sinistres</h2>
          <Link to="/sinistres" className="lien-fleche">Tous les sinistres <Icone nom="fleche" taille={16} /></Link>
        </div>
        <Etat {...sinistres}>
          <TableSinistres lignes={sinistres.donnees?.slice(0, 5)} />
        </Etat>
      </section>
    </>
  );
}
