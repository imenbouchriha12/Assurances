import { Link } from "react-router-dom";

import { useDonnees } from "../api.js";
import { Anneau, MiniStat, Progression, Repartition, Tuile } from "../components/Graphiques.jsx";
import { Icone } from "../components/icones.jsx";
import {
  Deductions, Etat, libelleStatut, marqueStatut, montant, Personne, pourcent, StatutBadge, Tableau,
} from "../components/ui.jsx";

const decimal = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
const somme = (lignes, champ) => lignes.reduce((t, l) => t + (l[champ] ?? 0), 0);
const majuscule = (t) => t.charAt(0).toUpperCase() + t.slice(1);

/**
 * Chaque bloc est une zone nommée de la grille .tdb-grille : la disposition (ordre, largeurs)
 * se règle uniquement dans styles.css (grid-template-areas).
 */
export default function TableauDeBord() {
  const stats = useDonnees("/statistiques");
  const sinistres = useDonnees("/sinistres");
  const s = stats.donnees;
  const aTraiter = sinistres.donnees?.filter((x) => ["Declare", "EnExpertise"].includes(x.statut)).length;
  const indemnises = sinistres.donnees?.filter((x) => x.montantIndemnise != null) ?? [];
  // Part des dommages estimés effectivement indemnisée, sur les dossiers indemnisés
  const taux = indemnises.length ? somme(indemnises, "montantIndemnise") / (somme(indemnises, "totalEstime") || 1) : null;

  return (
    <Etat {...stats}>
      {s && (
        <div className="tdb-grille">
          <section className="zone-entete tdb-entete">
            <div>
              <span className="surtitre">Calculé à partir de l'ontologie</span>
              <h1>Vue d'ensemble</h1>
              <p>
                Portefeuille de contrats et suivi des sinistres.
                {aTraiter > 0 && <> <strong>{aTraiter} dossier{aTraiter > 1 ? "s" : ""}</strong> en attente de traitement.</>}
              </p>
            </div>
            <div className="actions">
              <Link className="bouton" to="/sinistres?nouveau=1"><Icone nom="plus" taille={18} /> Déclarer un sinistre</Link>
              <Link className="bouton secondaire" to="/contrats?nouveau=1"><Icone nom="contrats" taille={18} /> Nouveau contrat</Link>
            </div>
          </section>

          {/* Toutes les tuiles ont la même structure : titre, valeur, une ligne de contexte, pastille d'icône */}
          <div className="zone-indicateurs tuiles">
            <Tuile titre="Contrats" icone="contrats" valeur={s.totaux.nbContrats}
                   detail={<><strong>{s.totaux.nbContratsValides}</strong> en cours</>} />
            <Tuile titre="Assurés" icone="assures" valeur={s.totaux.nbAssures}
                   detail={`${decimal.format(s.totaux.nbContrats / (s.totaux.nbAssures || 1))} contrats par assuré`} />
            <Tuile titre="Primes" icone="argent" valeur={montant(s.totaux.totalPrimes)}
                   detail={`moyenne ${montant(s.totaux.totalPrimes / (s.totaux.nbContrats || 1))}`} />
            <Tuile titre="Sinistres" icone="sinistres" valeur={s.totaux.nbSinistres}
                   detail={`dont ${s.totaux.nbSinistresGraves} graves (règle SWRL)`} />
            <Tuile titre="Total indemnisé" icone="check" valeur={montant(s.totaux.totalIndemnise)}
                   detail={`${somme(s.indemnisationsParAssureur, "nombre")} indemnisations versées`} />
          </div>

          {/* Sinistres : répartition par type sur fond sombre, puis les statuts du dossier */}
          {(() => {
            const types = s.sinistresParType.map((x) => ({ label: majuscule(x.label.replace(/^Sinistre /, "")), valeur: x.nombre }));
            const assureurs = s.indemnisationsParAssureur.map((x) => ({
              label: x.raisonSociale.replace(/ Assurances$/, ""), valeur: x.total, detail: `${x.nombre} indemnisation(s)`,
            }));
            const nbIndemnisations = somme(s.indemnisationsParAssureur, "nombre");
            return (
              <>
                <section className="zone-sinistres carte">
                  <h2 className="titre-carte">Sinistres par type</h2>
                  <p className="sous-titre-carte"><strong>{aTraiter ?? 0} à traiter</strong> sur {s.totaux.nbSinistres} sinistres</p>
                  <Anneau donnees={types} total={s.totaux.nbSinistres} libelleTotal="sinistres" />
                  <div className="mini-stats separees">
                    {s.sinistresParStatut.map((x) => {
                      const { couleur, icone } = marqueStatut(x.statut);
                      const part = x.nombre / (s.totaux.nbSinistres || 1);
                      return <MiniStat key={x.statut} pastille={icone} couleur={couleur} libelle={libelleStatut(x.statut)}
                                       valeur={x.nombre} part={part} libellePart={`${pourcent(part)} des sinistres`} />;
                    })}
                  </div>
                </section>

                <section className="zone-assureurs carte">
                  <h2 className="titre-carte">Indemnisé par assureur</h2>
                  <p className="sous-titre-carte">
                    <strong>{montant(s.totaux.totalIndemnise)}</strong> versés en {nbIndemnisations} indemnisations
                  </p>
                  <Anneau donnees={assureurs} format={montant} total={montant(s.totaux.totalIndemnise)} libelleTotal="indemnisés" />
                  <div className="mini-stats separees">
                    <MiniStat pastille={<Icone nom="check" taille={14} />} libelle="Indemnisations" valeur={nbIndemnisations} />
                    <MiniStat pastille={<Icone nom="argent" taille={14} />} libelle="Montant moyen"
                              valeur={montant(Math.round(s.totaux.totalIndemnise / (nbIndemnisations || 1)))} />
                    <MiniStat pastille={<Icone nom="graphique" taille={14} />} libelle="Part des dommages"
                              valeur={taux == null ? "—" : pourcent(taux)} part={taux ?? 0}
                              libellePart="Part des dommages estimés indemnisée" />
                  </div>
                </section>
              </>
            );
          })()}

          <section className="zone-tableau carte sans-marge carte-projets">
            <div className="carte-entete">
              <div>
                <h2 className="titre-carte">Derniers sinistres</h2>
                <p className="sous-titre-carte">Les 5 plus récents sur {s.totaux.nbSinistres}</p>
              </div>
              <Link to="/sinistres" className="lien-fleche">Tous les sinistres <Icone nom="fleche" taille={16} /></Link>
            </div>
            <Etat {...sinistres}>
              <Tableau
                lignes={sinistres.donnees?.slice(0, 5)}
                vide="Aucun sinistre."
                lien={(x) => `/sinistres/${x.id}`}
                colonnes={[
                  {
                    titre: "Sinistre",
                    rendu: (x) => (
                      <span className="sinistre-nom">
                        <span className="pastille-icone"><Icone nom="sinistres" taille={15} /></span>
                        <span><strong>{x.typeLabel}</strong><br /><span className="discret">{x.id}</span></span>
                      </span>
                    ),
                  },
                  { titre: "Assuré", rendu: (x) => <Personne id={x.assure} nom={x.assureNom} /> },
                  { titre: "Statut", rendu: (x) => <span className="pile"><StatutBadge statut={x.statut} /><Deductions s={x} /></span> },
                  { titre: "Dommages", num: true, rendu: (x) => montant(x.totalEstime) },
                  {
                    titre: "Indemnisé",
                    rendu: (x) => x.montantIndemnise == null ? <span className="discret">—</span> : (
                      <span className="taux" title={`${montant(x.montantIndemnise)} sur ${montant(x.totalEstime)} de dommages`}>
                        <strong>{pourcent(x.montantIndemnise / (x.totalEstime || 1))}</strong>
                        <Progression part={x.montantIndemnise / (x.totalEstime || 1)} />
                      </span>
                    ),
                  },
                ]}
              />
            </Etat>
          </section>

          <section className="zone-contrats carte">
            <h2 className="titre-carte">Contrats par type</h2>
            <p className="sous-titre-carte"><strong>{s.totaux.nbContratsValides} en cours</strong> sur {s.totaux.nbContrats} contrats</p>
            <Repartition donnees={s.contratsParType.map((x) => ({ label: x.label, valeur: x.nombre }))} icone="contrats" />
          </section>
        </div>
      )}
    </Etat>
  );
}
