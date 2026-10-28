import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, useAction, useDonnees } from "../api.js";
import { Icone } from "../components/icones.jsx";
import { TableContrats, TableSinistres } from "../components/Tables.jsx";
import {
  BarreRecherche, Champ, dateFr, Etat, filtrer, Message, montant, Personne, Tableau, Tiroir, useConfirmer,
  useOuvertureUrl, ValiditeBadge,
} from "../components/ui.jsx";

/** Cases à cocher multiples. */
function Cases({ items, choisis, onBascule, rendu }) {
  return (
    <div className="cases">
      {items?.map((x) => (
        <label key={x.id} className={`case${choisis.includes(x.id) ? " cochee" : ""}`}>
          <input type="checkbox" checked={choisis.includes(x.id)} onChange={() => onBascule(x.id)} />
          <span>{rendu(x)}</span>
        </label>
      ))}
    </div>
  );
}

function FormContrat({ onCree, onAnnuler }) {
  const types = useDonnees("/types");
  const assures = useDonnees("/assures");
  const assureurs = useDonnees("/assureurs");
  const garanties = useDonnees("/garanties");
  const clauses = useDonnees("/clauses");
  const franchises = useDonnees("/franchises");
  const [v, setV] = useState({
    type: "", assure: "", assureur: "", dateDebut: "", dateFin: "", prime: "",
    garanties: [], clauses: [], franchise: "",
  });
  const [etat, executer] = useAction();
  const maj = (champ) => (e) => setV({ ...v, [champ]: e.target.value });
  const basculer = (champ, id) =>
    setV((s) => ({ ...s, [champ]: s[champ].includes(id) ? s[champ].filter((x) => x !== id) : [...s[champ], id] }));
  // Seules les garanties du catalogue de l'assureur choisi sont proposées (proposeGarantie)
  const catalogue = assureurs.donnees?.find((a) => a.id === v.assureur)?.garanties?.split(",") ?? [];
  const garantiesProposees = garanties.donnees?.filter((g) => catalogue.includes(g.id));
  const changerAssureur = (e) => {
    const ids = assureurs.donnees?.find((a) => a.id === e.target.value)?.garanties?.split(",") ?? [];
    setV({ ...v, assureur: e.target.value, garanties: v.garanties.filter((g) => ids.includes(g)) });
  };

  const soumettre = async (e) => {
    e.preventDefault();
    const r = await executer(() =>
      api.post("/contrats", { ...v, prime: Number(v.prime), franchise: v.franchise || null }));
    if (r) onCree(r);
  };

  return (
    <form className="formulaire" onSubmit={soumettre}>
      <div className="grille-champs">
        <Champ label="Type de contrat">
          <select required autoFocus value={v.type} onChange={maj("type")}>
            <option value="">— choisir —</option>
            {types.donnees?.contrats.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
          </select>
        </Champ>
        <Champ label="Assuré">
          <select required value={v.assure} onChange={maj("assure")}>
            <option value="">— choisir —</option>
            {assures.donnees?.map((a) => <option key={a.id} value={a.id}>{a.prenom} {a.nom} ({a.cin})</option>)}
          </select>
        </Champ>
        <Champ label="Assureur">
          <select required value={v.assureur} onChange={changerAssureur}>
            <option value="">— choisir —</option>
            {assureurs.donnees?.map((a) => <option key={a.id} value={a.id}>{a.raisonSociale}</option>)}
          </select>
        </Champ>
        <Champ label="Prime annuelle (DT)">
          <input required type="number" min="1" step="0.01" value={v.prime} onChange={maj("prime")} />
        </Champ>
        <Champ label="Date de début"><input required type="date" value={v.dateDebut} onChange={maj("dateDebut")} /></Champ>
        <Champ label="Date de fin"><input required type="date" value={v.dateFin} onChange={maj("dateFin")} /></Champ>
        <Champ label="Franchise">
          <select value={v.franchise} onChange={maj("franchise")}>
            <option value="">Aucune</option>
            {franchises.donnees?.map((f) => <option key={f.id} value={f.id}>{montant(f.montant)}</option>)}
          </select>
        </Champ>
      </div>
      <fieldset>
        <legend>Garanties proposées par l'assureur</legend>
        <p className="discret">
          {v.assureur ? "Auto : responsabilité civile obligatoire · santé : frais médicaux · vie : décès (axiomes de l'ontologie)."
            : "Choisissez d'abord l'assureur : seules les garanties de son catalogue peuvent être souscrites."}
        </p>
        <Cases items={garantiesProposees} choisis={v.garanties} onBascule={(id) => basculer("garanties", id)}
               rendu={(g) => <>{g.libelle} <span className="discret">· {g.typeLabel} · plafond {montant(g.plafond)}</span></>} />
      </fieldset>
      <fieldset>
        <legend>Clauses légales</legend>
        <Cases items={clauses.donnees} choisis={v.clauses} onBascule={(id) => basculer("clauses", id)}
               rendu={(c) => <>{c.libelle} <span className="discret">· {c.typeLabel}</span></>} />
      </fieldset>
      <Message type="erreur">{etat.erreur}</Message>
      <div className="actions pied-formulaire">
        <button type="button" className="secondaire" onClick={onAnnuler}>Annuler</button>
        <button type="submit" disabled={etat.enCours}>{etat.enCours ? "Création…" : "Créer le contrat"}</button>
      </div>
    </form>
  );
}

export function Contrats() {
  const [filtres, setFiltres] = useState({ type: "", assureur: "", valide: "" });
  const [recherche, setRecherche] = useState("");
  const [creation, ouvrir, fermer] = useOuvertureUrl();
  const liste = useDonnees("/contrats", filtres);
  const types = useDonnees("/types");
  const assureurs = useDonnees("/assureurs");
  const naviguer = useNavigate();
  const maj = (champ) => (e) => setFiltres({ ...filtres, [champ]: e.target.value });
  const lignes = filtrer(liste.donnees, recherche,
                         ["numero", "typeLabel", "assureNom", "assureurNom", (c) => (c.valide ? "en cours" : "expiré")]);

  return (
    <>
      <div className="entete">
        <div>
          <h1>Contrats</h1>
          <p className="sous-titre">Polices d'assurance, leurs garanties et leurs clauses légales.</p>
        </div>
        <button onClick={ouvrir}><Icone nom="plus" taille={18} /> Nouveau contrat</button>
      </div>
      <Tiroir ouvert={creation} titre="Nouveau contrat" onFermer={fermer}>
        <FormContrat onAnnuler={fermer} onCree={(c) => naviguer(`/contrats/${c.id}`)} />
      </Tiroir>
      <div className="filtres">
        <BarreRecherche valeur={recherche} onChange={setRecherche} placeholder="Rechercher un contrat (numéro, assuré, assureur)"
                        affiches={lignes?.length} total={liste.donnees?.length} />
        <select aria-label="Type" value={filtres.type} onChange={maj("type")}>
          <option value="">Tous les types</option>
          {types.donnees?.contrats.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
        </select>
        <select aria-label="Assureur" value={filtres.assureur} onChange={maj("assureur")}>
          <option value="">Tous les assureurs</option>
          {assureurs.donnees?.map((a) => <option key={a.id} value={a.id}>{a.raisonSociale}</option>)}
        </select>
        <select aria-label="Validité" value={filtres.valide} onChange={maj("valide")}>
          <option value="">En cours et expirés</option>
          <option value="true">En cours</option>
          <option value="false">Expirés</option>
        </select>
      </div>
      <section className="carte sans-marge">
        <Etat {...liste}><TableContrats lignes={lignes} vide="Aucun contrat ne correspond à la recherche." /></Etat>
      </section>
    </>
  );
}

function FormModifContrat({ contrat, onEnregistre, onAnnuler }) {
  const assureurs = useDonnees("/assureurs");
  const [v, setV] = useState({ assureur: contrat.assureur, dateFin: contrat.dateFin, prime: contrat.prime });
  const [etat, executer] = useAction();
  const maj = (champ) => (e) => setV({ ...v, [champ]: e.target.value });

  const soumettre = async (e) => {
    e.preventDefault();
    const r = await executer(() => api.put(`/contrats/${contrat.id}`, { ...v, prime: Number(v.prime) }));
    if (r) onEnregistre();
  };

  return (
    <form className="formulaire" onSubmit={soumettre}>
      <div className="grille-champs">
        <Champ label="Assureur">
          <select value={v.assureur} onChange={maj("assureur")}>
            {assureurs.donnees?.map((a) => <option key={a.id} value={a.id}>{a.raisonSociale}</option>)}
          </select>
        </Champ>
        <Champ label="Date de fin"><input type="date" required value={v.dateFin} onChange={maj("dateFin")} /></Champ>
        <Champ label="Prime (DT)"><input type="number" min="1" step="0.01" required value={v.prime} onChange={maj("prime")} /></Champ>
      </div>
      <Message type="erreur">{etat.erreur}</Message>
      <div className="actions pied-formulaire">
        <button type="button" className="secondaire" onClick={onAnnuler}>Annuler</button>
        <button type="submit" disabled={etat.enCours}>Enregistrer</button>
      </div>
    </form>
  );
}

/** Avancement dans la période du contrat. */
function Periode({ debut, fin }) {
  const jour = 86400000;
  const d = new Date(`${debut}T00:00:00`), f = new Date(`${fin}T00:00:00`), maintenant = new Date();
  const part = Math.min(1, Math.max(0, (maintenant - d) / (f - d)));
  const restants = Math.ceil((f - maintenant) / jour);
  const texte = restants > 0 ? `${restants} jour${restants > 1 ? "s" : ""} restant${restants > 1 ? "s" : ""}`
    : `Expiré depuis ${-restants} jour${-restants > 1 ? "s" : ""}`;
  return (
    <div className="periode">
      <div className="periode-dates"><span>{dateFr(debut)}</span><strong>{texte}</strong><span>{dateFr(fin)}</span></div>
      <div className="periode-piste" role="progressbar" aria-valuemin={0} aria-valuemax={100}
           aria-valuenow={Math.round(part * 100)} aria-label="Avancement de la période du contrat">
        <span className={restants > 0 ? "" : "expire"} style={{ width: `${part * 100}%` }} />
      </div>
    </div>
  );
}

export function ContratDetail() {
  const { id } = useParams();
  const naviguer = useNavigate();
  const confirmer = useConfirmer();
  const contrat = useDonnees(`/contrats/${id}`);
  const [edition, setEdition] = useState(false);
  const [etat, executer] = useAction();
  const c = contrat.donnees;

  const supprimer = async () => {
    if (!(await confirmer({ titre: "Supprimer ce contrat ?", message: `Le contrat ${c.numero} sera définitivement supprimé.` }))) return;
    const r = await executer(() => api.del(`/contrats/${id}`));
    if (r !== undefined) naviguer("/contrats");
  };

  return (
    <Etat {...contrat}>
      {c && (
        <>
          <Link to="/contrats" className="lien-retour"><Icone nom="retour" taille={16} /> Contrats</Link>
          <section className="fiche">
            <span className="fiche-icone"><Icone nom="contrats" taille={26} /></span>
            <div className="fiche-texte">
              <h1>{c.numero} <ValiditeBadge valide={c.valide} /></h1>
              <div className="fiche-faits">
                <span>{c.typeLabel}</span>
                <span><Icone nom="entreprise" taille={16} /> {c.assureurNom}</span>
                <span><Icone nom="argent" taille={16} /> {montant(c.prime)} / an</span>
                <span>Franchise {c.franchise ? montant(c.franchise.montant) : "aucune"}</span>
              </div>
            </div>
            <div className="actions">
              <button className="secondaire" onClick={() => setEdition(true)}><Icone nom="crayon" taille={16} /> Modifier</button>
              <button className="danger" onClick={supprimer} disabled={etat.enCours}><Icone nom="poubelle" taille={16} /> Supprimer</button>
            </div>
          </section>
          <Message type="erreur">{etat.erreur}</Message>
          <Tiroir ouvert={edition} titre={`Modifier le contrat ${c.numero}`} onFermer={() => setEdition(false)}>
            <FormModifContrat contrat={c} onAnnuler={() => setEdition(false)}
                              onEnregistre={() => { setEdition(false); contrat.recharger(); }} />
          </Tiroir>
          <div className="deux-colonnes">
            <section className="carte">
              <h2>Assuré</h2>
              <Personne id={c.assure} nom={c.assureNom} />
            </section>
            <section className="carte">
              <h2>Période de couverture</h2>
              <Periode debut={c.dateDebut} fin={c.dateFin} />
            </section>
          </div>
          <section className="carte sans-marge">
            <div className="carte-entete"><h2>Garanties</h2></div>
            <Tableau lignes={c.garanties} colonnes={[
              { titre: "Garantie", champ: "libelle" },
              { titre: "Type", champ: "typeLabel" },
              { titre: "Plafond", num: true, rendu: (g) => montant(g.plafond) },
            ]} />
          </section>
          <section className="carte sans-marge">
            <div className="carte-entete"><h2>Clauses légales</h2></div>
            <Tableau lignes={c.clauses} vide="Aucune clause." colonnes={[
              { titre: "Clause", rendu: (x) => <><strong>{x.libelle}</strong><br /><span className="discret">{x.texte}</span></> },
              { titre: "Type", champ: "typeLabel" },
              { titre: "Garanties exclues", rendu: (x) => x.garantiesExclues || "—" },
              { titre: "Référence", champ: "reference" },
            ]} />
          </section>
          <section className="carte sans-marge">
            <div className="carte-entete"><h2>Sinistres</h2></div>
            <TableSinistres lignes={c.sinistres} vide="Aucun sinistre sur ce contrat." />
          </section>
        </>
      )}
    </Etat>
  );
}
