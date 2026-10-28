import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api, useAction, useDonnees } from "../api.js";
import { Icone } from "../components/icones.jsx";
import {
  BarreRecherche, Champ, Etat, filtrer, Message, montant, pourcent, Tableau, Tiroir, useConfirmer, useOuvertureUrl,
} from "../components/ui.jsx";

/*
 * Chaque ressource du référentiel est décrite ici : colonnes du tableau, champs du formulaire, champs
 * de recherche. Les champs de type "types" proposent les sous-classes lues dans l'ontologie (GET /types).
 */
const RESSOURCES = {
  assureurs: {
    icone: "entreprise",
    titre: "Assureurs", nouveau: "Nouvel assureur",
    recherche: ["raisonSociale", "adresse"],
    colonnes: [
      { titre: "Raison sociale", champ: "raisonSociale" },
      { titre: "Adresse", champ: "adresse" },
      { titre: "Garanties proposées", num: true, rendu: (a) => (a.garanties ? a.garanties.split(",").filter(Boolean).length : 0) },
      { titre: "Experts", num: true, champ: "nbExperts" },
      { titre: "Barèmes", num: true, champ: "nbBaremes" },
      { titre: "Contrats", num: true, champ: "nbContrats" },
    ],
    champs: [
      { nom: "raisonSociale", label: "Raison sociale", requis: true },
      { nom: "adresse", label: "Adresse (ville)" },
      { nom: "garanties", label: "Garanties proposées (catalogue de la compagnie)", type: "garanties" },
    ],
  },
  experts: {
    icone: "expert",
    titre: "Experts", nouveau: "Nouvel expert",
    recherche: ["prenom", "nom", "cin", "specialite", "adresse", "assureursNoms"],
    colonnes: [
      { titre: "Expert", rendu: (e) => `${e.prenom} ${e.nom}` },
      { titre: "CIN", champ: "cin" },
      { titre: "Spécialité", champ: "specialite" },
      { titre: "Mandaté par", champ: "assureursNoms" },
      { titre: "Sinistres", num: true, champ: "nbSinistres" },
    ],
    champs: [
      { nom: "nom", label: "Nom", requis: true },
      { nom: "prenom", label: "Prénom", requis: true },
      { nom: "cin", label: "CIN", requis: true, motif: "\\d{8}", aide: "8 chiffres, unique" },
      { nom: "specialite", label: "Spécialité" },
      { nom: "adresse", label: "Adresse (ville)" },
      { nom: "assureurs", label: "Travaille pour (au moins une compagnie)", type: "assureurs" },
    ],
  },
  garanties: {
    icone: "bouclier",
    titre: "Garanties", nouveau: "Nouvelle garantie",
    recherche: ["libelle", "typeLabel"],
    colonnes: [
      { titre: "Garantie", champ: "libelle" },
      { titre: "Type", champ: "typeLabel" },
      { titre: "Plafond", num: true, rendu: (g) => montant(g.plafond) },
      { titre: "Contrats", num: true, champ: "nbContrats" },
    ],
    champs: [
      { nom: "type", label: "Type de garantie", type: "types", source: "garanties", requis: true, fixe: true },
      { nom: "libelle", label: "Libellé", requis: true },
      { nom: "plafond", label: "Plafond (DT)", type: "nombre", requis: true, min: 1, pas: 0.01 },
    ],
  },
  clauses: {
    icone: "contrats",
    titre: "Clauses légales", nouveau: "Nouvelle clause",
    recherche: ["libelle", "texte", "reference", "typeLabel", "garantiesExclues"],
    colonnes: [
      { titre: "Clause", rendu: (c) => <><strong>{c.libelle}</strong><br /><span className="discret">{c.texte}</span></> },
      { titre: "Type", champ: "typeLabel" },
      { titre: "Garanties exclues", rendu: (c) => c.garantiesExclues || "—" },
      { titre: "Référence", champ: "reference" },
    ],
    champs: [
      { nom: "type", label: "Type de clause", type: "types", source: "clauses", requis: true, fixe: true },
      { nom: "libelle", label: "Libellé", requis: true },
      { nom: "reference", label: "Référence légale", requis: true, aide: "ex. Code des assurances, Conditions générales" },
      { nom: "texte", label: "Texte de la clause", type: "texte-long", requis: true },
      { nom: "garanties", label: "Garanties exclues", type: "garanties", visible: (v) => v.type === "ClauseExclusion" },
    ],
  },
  baremes: {
    icone: "graphique",
    titre: "Barèmes", nouveau: "Nouveau barème",
    recherche: ["libelle", "assureurNom"],
    colonnes: [
      { titre: "Barème", champ: "libelle" },
      { titre: "Assureur", champ: "assureurNom" },
      { titre: "Taux", num: true, rendu: (b) => pourcent(b.taux) },
      { titre: "Garanties", rendu: (b, libelles) => b.garanties?.split(",").filter(Boolean).map(libelles).join(", ") || "—" },
      { titre: "Indemnisations", num: true, champ: "nbIndemnisations" },
    ],
    champs: [
      { nom: "assureur", label: "Assureur", type: "assureur", requis: true },
      { nom: "libelle", label: "Libellé", requis: true },
      { nom: "taux", label: "Taux d'indemnisation", type: "nombre", requis: true, min: 0, max: 1, pas: 0.01,
        aide: "entre 0 et 1 (0.8 = 80 %)" },
      { nom: "garanties", label: "S'applique aux garanties (catalogue de l'assureur)", type: "garanties", catalogue: "assureur" },
    ],
  },
  franchises: {
    icone: "argent",
    titre: "Franchises", nouveau: "Nouvelle franchise",
    recherche: ["montant", "id"],
    colonnes: [
      { titre: "Franchise", champ: "id" },
      { titre: "Montant", num: true, rendu: (f) => montant(f.montant) },
      { titre: "Contrats", num: true, champ: "nbContrats" },
    ],
    champs: [{ nom: "montant", label: "Montant (DT)", type: "nombre", requis: true, min: 0, pas: 0.01 }],
  },
};

/** Valeurs du formulaire à partir d'une ligne de la liste (les garanties arrivent en "id1,id2"). */
function valeursInitiales(config, ligne) {
  return Object.fromEntries(config.champs.map((c) => {
    const v = ligne?.[c.nom];
    if (["garanties", "assureurs"].includes(c.type)) return [c.nom, typeof v === "string" ? v.split(",").filter(Boolean) : []];
    return [c.nom, v ?? ""];
  }));
}

function Formulaire({ cle, config, ligne, onEnregistre, onAnnuler }) {
  const types = useDonnees("/types");
  const garanties = useDonnees("/garanties");
  const assureurs = useDonnees("/assureurs");
  const [v, setV] = useState(valeursInitiales(config, ligne));
  // Garanties proposables : tout le catalogue, ou seulement celles de l'assureur choisi (barèmes)
  const catalogue = (c) => {
    if (!c.catalogue) return garanties.donnees;
    const ids = assureurs.donnees?.find((a) => a.id === v[c.catalogue])?.garanties?.split(",") ?? [];
    return garanties.donnees?.filter((g) => ids.includes(g.id));
  };
  const [etat, executer] = useAction();
  const maj = (nom) => (e) => setV({ ...v, [nom]: e.target.value });
  const basculer = (nom, id) =>
    setV((s) => ({ ...s, [nom]: s[nom].includes(id) ? s[nom].filter((x) => x !== id) : [...s[nom], id] }));

  const soumettre = async (e) => {
    e.preventDefault();
    const corps = Object.fromEntries(config.champs.map((c) => {
      if (c.type === "nombre") return [c.nom, Number(v[c.nom])];
      if (c.type === "garanties") {
        if (c.visible && !c.visible(v)) return [c.nom, []];
        const permises = catalogue(c)?.map((g) => g.id) ?? [];
        return [c.nom, v[c.nom].filter((id) => permises.includes(id))];
      }
      if (c.type === "assureurs") return [c.nom, v[c.nom]];
      return [c.nom, v[c.nom] === "" ? null : v[c.nom]];
    }));
    const r = await executer(() => (ligne ? api.put(`/${cle}/${ligne.id}`, corps) : api.post(`/${cle}`, corps)));
    if (r) onEnregistre(r);
  };

  const champ = (c) => {
    if (c.visible && !c.visible(v)) return null;
    if (c.type === "garanties" || c.type === "assureurs") {
      const items = c.type === "assureurs" ? assureurs.donnees : catalogue(c);
      return (
        <fieldset key={c.nom}>
          <legend>{c.label}</legend>
          {c.catalogue && !v[c.catalogue] && <p className="discret">Choisissez d'abord l'assureur.</p>}
          {c.catalogue && v[c.catalogue] && !items?.length && <p className="discret">Cet assureur ne propose encore aucune garantie.</p>}
          <div className="cases">
            {items?.map((x) => (
              <label key={x.id} className={`case${v[c.nom].includes(x.id) ? " cochee" : ""}`}>
                <input type="checkbox" checked={v[c.nom].includes(x.id)} onChange={() => basculer(c.nom, x.id)} />
                {c.type === "assureurs"
                  ? <span>{x.raisonSociale}</span>
                  : <span>{x.libelle} <span className="discret">· {x.typeLabel}</span></span>}
              </label>
            ))}
          </div>
        </fieldset>
      );
    }
    let saisie;
    if (c.type === "assureur") {
      saisie = (
        <select required={c.requis} value={v[c.nom]} onChange={maj(c.nom)}>
          <option value="">— choisir —</option>
          {assureurs.donnees?.map((a) => <option key={a.id} value={a.id}>{a.raisonSociale}</option>)}
        </select>
      );
    } else if (c.type === "types") {
      saisie = (
        <select required={c.requis} disabled={c.fixe && !!ligne} value={v[c.nom]} onChange={maj(c.nom)}>
          <option value="">— choisir —</option>
          {types.donnees?.[c.source].map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
        </select>
      );
    } else if (c.type === "texte-long") {
      saisie = <textarea required={c.requis} rows={3} value={v[c.nom]} onChange={maj(c.nom)} />;
    } else if (c.type === "nombre") {
      saisie = <input type="number" required={c.requis} min={c.min} max={c.max} step={c.pas} value={v[c.nom]} onChange={maj(c.nom)} />;
    } else {
      saisie = <input required={c.requis} pattern={c.motif} value={v[c.nom]} onChange={maj(c.nom)} />;
    }
    const aide = c.fixe && ligne ? "Le type ne peut pas être modifié" : c.aide;
    return <Champ key={c.nom} label={c.label} aide={aide}>{saisie}</Champ>;
  };

  const larges = ["texte-long", "garanties", "assureurs"];
  const simples = config.champs.filter((c) => !larges.includes(c.type));
  const blocs = config.champs.filter((c) => larges.includes(c.type));
  return (
    <form className="formulaire" onSubmit={soumettre}>
      <div className="grille-champs">{simples.map(champ)}</div>
      {blocs.map(champ)}
      <Message type="erreur">{etat.erreur}</Message>
      <div className="actions pied-formulaire">
        <button type="button" className="secondaire" onClick={onAnnuler}>Annuler</button>
        <button type="submit" disabled={etat.enCours}>{etat.enCours ? "Enregistrement…" : "Enregistrer"}</button>
      </div>
    </form>
  );
}

function Onglet({ cle }) {
  const config = RESSOURCES[cle];
  const liste = useDonnees(`/${cle}`);
  const garanties = useDonnees(cle === "baremes" ? "/garanties" : null);
  const [recherche, setRecherche] = useState("");
  const [creation, ouvrir, fermer] = useOuvertureUrl();
  const [edition, setEdition] = useState(null); // ligne en cours de modification
  const confirmer = useConfirmer();
  const [etat, executer] = useAction();
  const lignes = filtrer(liste.donnees, recherche, config.recherche);
  const libelleGarantie = (id) => garanties.donnees?.find((g) => g.id === id)?.libelle ?? id;

  const supprimer = async (ligne) => {
    if (!(await confirmer({ titre: "Supprimer cet élément ?", message: "Cette suppression est définitive." }))) return;
    const r = await executer(() => api.del(`/${cle}/${ligne.id}`), "Élément supprimé.");
    if (r !== undefined) liste.recharger();
  };

  return (
    <>
      <div className="entete">
        <h2 className="titre-onglet">{config.titre}</h2>
        <button onClick={ouvrir}><Icone nom="plus" taille={18} /> {config.nouveau}</button>
      </div>
      <Tiroir ouvert={creation} titre={config.nouveau} onFermer={fermer}>
        <Formulaire cle={cle} config={config} onAnnuler={fermer} onEnregistre={() => { fermer(); liste.recharger(); }} />
      </Tiroir>
      <Tiroir ouvert={!!edition} titre="Modifier" onFermer={() => setEdition(null)}>
        {edition && (
          <Formulaire key={edition.id} cle={cle} config={config} ligne={edition} onAnnuler={() => setEdition(null)}
                      onEnregistre={() => { setEdition(null); liste.recharger(); }} />
        )}
      </Tiroir>
      <div className="filtres">
        <BarreRecherche valeur={recherche} onChange={setRecherche} placeholder={`Rechercher dans : ${config.titre.toLowerCase()}`}
                        affiches={lignes?.length} total={liste.donnees?.length} />
      </div>
      <Message type="erreur">{etat.erreur}</Message>
      <Message type="succes">{etat.succes}</Message>
      <section className="carte sans-marge">
        <Etat {...liste}>
          <Tableau lignes={lignes} colonnes={[
            ...config.colonnes.map((c) => (c.rendu ? { ...c, rendu: (l) => c.rendu(l, libelleGarantie) } : c)),
            {
              titre: "Actions",
              rendu: (l) => (
                <span className="actions-ligne">
                  <button className="icone-bouton" onClick={() => setEdition(l)} aria-label="Modifier" title="Modifier">
                    <Icone nom="crayon" taille={17} />
                  </button>
                  <button className="icone-bouton danger" onClick={() => supprimer(l)} disabled={etat.enCours}
                          aria-label="Supprimer" title="Supprimer">
                    <Icone nom="poubelle" taille={17} />
                  </button>
                </span>
              ),
            },
          ]} />
        </Etat>
      </section>
    </>
  );
}

export default function Referentiel() {
  const [params, setParams] = useSearchParams();
  const actif = RESSOURCES[params.get("onglet")] ? params.get("onglet") : "assureurs";

  return (
    <>
      <div className="entete">
        <div>
          <h1>Référentiel</h1>
          <p className="sous-titre">Données de référence utilisées par les contrats et les sinistres.</p>
        </div>
      </div>
      <div className="onglets" role="tablist">
        {Object.entries(RESSOURCES).map(([cle, r]) => (
          <button key={cle} role="tab" aria-selected={cle === actif} className={cle === actif ? "actif" : ""}
                  onClick={() => setParams({ onglet: cle })}>
            <Icone nom={r.icone} taille={17} />
            {r.titre}
          </button>
        ))}
      </div>
      <Onglet key={actif} cle={actif} />
    </>
  );
}
