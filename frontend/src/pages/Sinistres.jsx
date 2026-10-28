import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, useAction, useDonnees } from "../api.js";
import { Icone } from "../components/icones.jsx";
import { TableSinistres } from "../components/Tables.jsx";
import {
  BarreRecherche, Champ, dateFr, Deductions, Etat, filtrer, libelleStatut, LienEntite, Message, montant, Personne,
  pourcent, StatutBadge, Tableau, Tiroir, useConfirmer, useOuvertureUrl,
} from "../components/ui.jsx";

const DOMMAGE_VIDE = { type: "DommageMateriel", montantEstime: "", description: "" };

function FormSinistre({ onCree, onAnnuler }) {
  const types = useDonnees("/types");
  const [v, setV] = useState({ type: "", contrat: "", dateSinistre: "", description: "", lieu: "", garanties: [] });
  const [dommages, setDommages] = useState([DOMMAGE_VIDE]);
  const [etat, executer] = useAction();

  // Un SinistreHabitation concerne un ContratHabitation, etc.
  const typeContrat = v.type ? `Contrat${v.type.replace("Sinistre", "")}` : null;
  const contrats = useDonnees(typeContrat ? "/contrats" : null, { type: typeContrat });
  const contrat = useDonnees(v.contrat ? `/contrats/${v.contrat}` : null);

  const maj = (champ) => (e) => setV({ ...v, [champ]: e.target.value });
  const majDommage = (i, champ) => (e) =>
    setDommages(dommages.map((d, j) => (j === i ? { ...d, [champ]: e.target.value } : d)));
  const basculerGarantie = (id) =>
    setV((s) => ({ ...s, garanties: s.garanties.includes(id) ? s.garanties.filter((x) => x !== id) : [...s.garanties, id] }));
  const total = dommages.reduce((t, d) => t + (Number(d.montantEstime) || 0), 0);

  const soumettre = async (e) => {
    e.preventDefault();
    const r = await executer(() => api.post("/sinistres", {
      ...v,
      lieu: v.lieu || null,
      dommages: dommages.map((d) => ({ type: d.type, montantEstime: Number(d.montantEstime), description: d.description || null })),
    }));
    if (r) onCree(r);
  };

  return (
    <form className="formulaire" onSubmit={soumettre}>
      <div className="grille-champs">
        <Champ label="Type de sinistre">
          <select required autoFocus value={v.type} onChange={(e) => setV({ ...v, type: e.target.value, contrat: "", garanties: [] })}>
            <option value="">— choisir —</option>
            {types.donnees?.sinistres.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
          </select>
        </Champ>
        <Champ label="Contrat concerné"
               aide={contrat.donnees ? `Période : ${dateFr(contrat.donnees.dateDebut)} → ${dateFr(contrat.donnees.dateFin)}` : null}>
          <select required disabled={!v.type} value={v.contrat}
                  onChange={(e) => setV({ ...v, contrat: e.target.value, garanties: [] })}>
            <option value="">{v.type ? "— choisir —" : "Choisissez d'abord un type"}</option>
            {contrats.donnees?.map((c) => <option key={c.id} value={c.id}>{c.numero} · {c.assureNom}</option>)}
          </select>
        </Champ>
        <Champ label="Date du sinistre"><input required type="date" value={v.dateSinistre} onChange={maj("dateSinistre")} /></Champ>
        <Champ label="Lieu"><input value={v.lieu} onChange={maj("lieu")} /></Champ>
      </div>
      <Champ label="Description">
        <textarea required minLength={3} rows={2} value={v.description} onChange={maj("description")} />
      </Champ>
      {contrat.donnees && (
        <fieldset>
          <legend>Garanties du contrat qui couvrent ce sinistre</legend>
          <div className="cases">
            {contrat.donnees.garanties.map((g) => (
              <label key={g.id} className={`case${v.garanties.includes(g.id) ? " cochee" : ""}`}>
                <input type="checkbox" checked={v.garanties.includes(g.id)} onChange={() => basculerGarantie(g.id)} />
                <span>{g.libelle} <span className="discret">· plafond {montant(g.plafond)}</span></span>
              </label>
            ))}
          </div>
        </fieldset>
      )}
      <fieldset>
        <legend>Dommages · total {montant(total)}</legend>
        {dommages.map((d, i) => (
          <div className="ligne-dommage" key={i}>
            <select aria-label="Type de dommage" value={d.type} onChange={majDommage(i, "type")}>
              {types.donnees?.dommages.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
            </select>
            <input aria-label="Montant estimé" required type="number" min="0" step="0.01" placeholder="Montant (DT)"
                   value={d.montantEstime} onChange={majDommage(i, "montantEstime")} />
            <button type="button" className="icone-bouton" disabled={dommages.length === 1} aria-label="Retirer ce dommage"
                    onClick={() => setDommages(dommages.filter((_, j) => j !== i))}><Icone nom="poubelle" taille={18} /></button>
            <input className="pleine-largeur" aria-label="Description du dommage" placeholder="Description du dommage"
                   value={d.description} onChange={majDommage(i, "description")} />
          </div>
        ))}
        <button type="button" className="secondaire" onClick={() => setDommages([...dommages, DOMMAGE_VIDE])}>
          <Icone nom="plus" taille={16} /> Ajouter un dommage
        </button>
      </fieldset>
      <Message type="erreur">{etat.erreur}</Message>
      <div className="actions pied-formulaire">
        <button type="button" className="secondaire" onClick={onAnnuler}>Annuler</button>
        <button type="submit" disabled={etat.enCours}>{etat.enCours ? "Déclaration…" : "Déclarer le sinistre"}</button>
      </div>
    </form>
  );
}

export function Sinistres() {
  const [filtres, setFiltres] = useState({ statut: "", type: "", grave: "", couvert: "" });
  const [recherche, setRecherche] = useState("");
  const [creation, ouvrir, fermer] = useOuvertureUrl();
  const liste = useDonnees("/sinistres", filtres);
  const lignes = filtrer(liste.donnees, recherche, [
    "id", "typeLabel", "description", "lieu", "assureNom", "numeroContrat", (s) => libelleStatut(s.statut),
  ]);
  const types = useDonnees("/types");
  const naviguer = useNavigate();
  const maj = (champ) => (e) => setFiltres({ ...filtres, [champ]: e.target.value });

  return (
    <>
      <div className="entete">
        <div>
          <h1>Sinistres</h1>
          <p className="sous-titre">Déclarations, expertises et indemnisations.</p>
        </div>
        <button onClick={ouvrir}><Icone nom="plus" taille={18} /> Déclarer un sinistre</button>
      </div>
      <Tiroir ouvert={creation} titre="Déclarer un sinistre" onFermer={fermer}>
        <FormSinistre onAnnuler={fermer} onCree={(s) => naviguer(`/sinistres/${s.id}`)} />
      </Tiroir>
      <div className="filtres">
        <BarreRecherche valeur={recherche} onChange={setRecherche}
                        placeholder="Rechercher un sinistre (description, lieu, assuré, contrat)"
                        affiches={lignes?.length} total={liste.donnees?.length} />
        <select aria-label="Statut" value={filtres.statut} onChange={maj("statut")}>
          <option value="">Tous les statuts</option>
          {types.donnees?.statutsSinistre.map((s) => <option key={s} value={s}>{libelleStatut(s)}</option>)}
        </select>
        <select aria-label="Type" value={filtres.type} onChange={maj("type")}>
          <option value="">Tous les types</option>
          {types.donnees?.sinistres.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
        </select>
        <select aria-label="Gravité" value={filtres.grave} onChange={maj("grave")}>
          <option value="">Graves et non graves</option>
          <option value="true">Graves (règle SWRL)</option>
          <option value="false">Non graves</option>
        </select>
        <select aria-label="Couverture" value={filtres.couvert} onChange={maj("couvert")}>
          <option value="">Couverts et non couverts</option>
          <option value="true">Couverts</option>
          <option value="false">Non couverts</option>
        </select>
      </div>
      <section className="carte sans-marge">
        <Etat {...liste}><TableSinistres lignes={lignes} vide="Aucun sinistre ne correspond à la recherche." /></Etat>
      </section>
    </>
  );
}

/** Frise du dossier : Déclaré → En expertise → Indemnisé (ou Refusé / Clôturé). */
function Frise({ statut }) {
  const fin = ["Refuse", "Cloture"].includes(statut) ? statut : "Indemnise";
  const etapes = ["Declare", "EnExpertise", fin];
  const courant = etapes.indexOf(statut);
  return (
    <ol className="frise">
      {etapes.map((e, i) => {
        const etat = i < courant ? "faite" : i === courant ? "courante" : "a-venir";
        return (
          <li key={e} className={`${etat}${e === "Refuse" ? " refusee" : ""}`} aria-current={i === courant ? "step" : undefined}>
            <span className="frise-point">{i < courant ? <Icone nom="check" taille={14} /> : i + 1}</span>
            <span className="frise-libelle">{libelleStatut(e)}</span>
          </li>
        );
      })}
    </ol>
  );
}

function GestionStatut({ sinistre, onModifie }) {
  const types = useDonnees("/types");
  const experts = useDonnees("/experts");
  const [v, setV] = useState({ statut: sinistre.statut, expert: sinistre.expert?.id ?? "" });
  const [etat, executer] = useAction();

  const soumettre = async (e) => {
    e.preventDefault();
    const r = await executer(() => api.patch(`/sinistres/${sinistre.id}/statut`, { statut: v.statut, expert: v.expert || null }));
    if (r) onModifie();
  };

  return (
    <form className="carte formulaire" onSubmit={soumettre}>
      <h2>Suivi du dossier</h2>
      <div className="grille-champs">
        <Champ label="Statut" aide="« Indemnisé » s'obtient avec le calcul d'indemnisation.">
          <select value={v.statut} onChange={(e) => setV({ ...v, statut: e.target.value })}>
            {types.donnees?.statutsSinistre.filter((s) => s !== "Indemnise" || s === sinistre.statut)
              .map((s) => <option key={s} value={s}>{libelleStatut(s)}</option>)}
          </select>
        </Champ>
        <Champ label="Expert" aide={`Experts mandatés par ${sinistre.assureurNom ?? "l'assureur"}`}>
          <select value={v.expert} onChange={(e) => setV({ ...v, expert: e.target.value })}>
            <option value="">Aucun</option>
            {experts.donnees?.filter((x) => x.assureurs?.split(",").includes(sinistre.assureur) || x.id === v.expert)
              .map((x) => <option key={x.id} value={x.id}>{x.prenom} {x.nom} · {x.specialite}</option>)}
          </select>
        </Champ>
      </div>
      <Message type="erreur">{etat.erreur}</Message>
      <div className="actions"><button type="submit" disabled={etat.enCours}>Mettre à jour</button></div>
    </form>
  );
}

function Indemnisation({ sinistre, onIndemnise }) {
  const baremes = useDonnees("/baremes");
  const [bareme, setBareme] = useState("");
  const [calcul, setCalcul] = useState(null);
  const [etat, executer] = useAction();
  const idsGaranties = sinistre.garanties.map((g) => g.id);
  // Barèmes de l'assureur du contrat (definitBareme) qui s'appliquent à une garantie couvrant le sinistre
  const applicables = baremes.donnees?.filter((b) => b.assureur === sinistre.assureur
    && b.garanties?.split(",").some((g) => idsGaranties.includes(g)));

  if (sinistre.indemnisation) {
    const i = sinistre.indemnisation;
    return (
      <section className="carte indemnisation-faite">
        <h2>Indemnisation</h2>
        <span className="montant-vedette">{montant(i.montant)}</span>
        {calcul && <p className="formule">Calcul : {calcul.formule} = <strong>{montant(calcul.montant)}</strong></p>}
        <dl className="infos">
          <dt>Versée le</dt><dd>{dateFr(i.date)}</dd>
          <dt>Barème</dt><dd>{i.baremeLibelle} ({pourcent(i.taux)})</dd>
        </dl>
      </section>
    );
  }

  const indemniser = async (e) => {
    e.preventDefault();
    const r = await executer(() => api.post(`/sinistres/${sinistre.id}/indemnisation`, { bareme }));
    if (r) {
      setCalcul(r.calcul);
      onIndemnise();
    }
  };

  return (
    <form className="carte formulaire" onSubmit={indemniser}>
      <h2>Indemnisation</h2>
      <p className="discret">Montant = (total des dommages − franchise du contrat) × taux du barème, dans la limite du plafond de la garantie.</p>
      {!sinistre.couvert && <Message type="attention">Ce sinistre n'est couvert par aucune garantie : il ne peut pas être indemnisé.</Message>}
      <Champ label="Barème" aide={`Barèmes définis par ${sinistre.assureurNom ?? "l'assureur"}`}>
        <select required value={bareme} onChange={(e) => setBareme(e.target.value)}>
          <option value="">— choisir —</option>
          {applicables?.map((b) => <option key={b.id} value={b.id}>{b.libelle} ({pourcent(b.taux)})</option>)}
        </select>
      </Champ>
      <Message type="erreur">{etat.erreur}</Message>
      <div className="actions">
        <button type="submit" disabled={etat.enCours || !sinistre.couvert || sinistre.statut === "Refuse"}>
          Calculer et indemniser
        </button>
      </div>
    </form>
  );
}

export function SinistreDetail() {
  const { id } = useParams();
  const naviguer = useNavigate();
  const confirmer = useConfirmer();
  const sinistre = useDonnees(`/sinistres/${id}`);
  const [etat, executer] = useAction();
  const s = sinistre.donnees;

  const supprimer = async () => {
    if (!(await confirmer({ titre: "Supprimer ce sinistre ?",
                            message: "Le sinistre, ses dommages et son indemnisation seront définitivement supprimés." }))) return;
    const r = await executer(() => api.del(`/sinistres/${id}`));
    if (r !== undefined) naviguer("/sinistres");
  };

  return (
    <Etat {...sinistre}>
      {s && (
        <>
          <Link to="/sinistres" className="lien-retour"><Icone nom="retour" taille={16} /> Sinistres</Link>
          <section className="fiche">
            <span className={`fiche-icone${s.grave ? " grave" : ""}`}><Icone nom="sinistres" taille={26} /></span>
            <div className="fiche-texte">
              <h1>{s.typeLabel}</h1>
              <p className="fiche-description">{s.description}</p>
              <div className="fiche-faits">
                <span><Icone nom="calendrier" taille={16} /> {dateFr(s.date)}</span>
                {s.lieu && <span><Icone nom="lieu" taille={16} /> {s.lieu}</span>}
                <span className="pile"><StatutBadge statut={s.statut} /> <Deductions s={s} /></span>
              </div>
            </div>
            <div className="actions">
              <button className="danger" onClick={supprimer} disabled={etat.enCours}><Icone nom="poubelle" taille={16} /> Supprimer</button>
            </div>
          </section>
          <Message type="erreur">{etat.erreur}</Message>
          <section className="carte"><Frise statut={s.statut} /></section>
          <div className="trois-colonnes">
            <section className="carte">
              <h2>Assuré</h2>
              <Personne id={s.assure} nom={s.assureNom} />
            </section>
            <section className="carte">
              <h2>Contrat</h2>
              <LienEntite id={s.contrat}>{s.numeroContrat}</LienEntite> <span className="discret">· {s.assureurNom}</span>
              <p className="discret">{s.garanties.map((g) => g.libelle).join(", ") || "Aucune garantie mobilisée"}</p>
            </section>
            <section className="carte">
              <h2>Expert</h2>
              {s.expert ? <span className="personne"><Icone nom="expert" /> {s.expert.prenom} {s.expert.nom} · {s.expert.specialite}</span>
                : <p className="discret">Non affecté</p>}
            </section>
          </div>
          <section className="carte sans-marge">
            <div className="carte-entete"><h2>Dommages</h2><strong>Total {montant(s.totalEstime)}</strong></div>
            <Tableau lignes={s.dommages} colonnes={[
              { titre: "Type", champ: "typeLabel" },
              { titre: "Description", champ: "description" },
              { titre: "Montant estimé", num: true, rendu: (d) => montant(d.montantEstime) },
            ]} />
          </section>
          <div className="deux-colonnes">
            <GestionStatut key={`${s.statut}-${s.expert?.id}`} sinistre={s} onModifie={sinistre.recharger} />
            <Indemnisation sinistre={s} onIndemnise={sinistre.recharger} />
          </div>
        </>
      )}
    </Etat>
  );
}
