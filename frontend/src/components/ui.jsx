import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Icone } from "./icones.jsx";

const nombreFr = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });

export const montant = (v) => (v == null ? "—" : `${nombreFr.format(v)} DT`);
export const dateFr = (v) => (v ? new Date(`${v}T00:00:00`).toLocaleDateString("fr-FR") : "—");
export const pourcent = (v) => `${Math.round(v * 100)} %`;

// ---------- Chargement, erreurs, messages ----------

export function Squelette({ lignes = 4 }) {
  return (
    <div className="squelette" aria-busy="true" aria-label="Chargement">
      {Array.from({ length: lignes }, (_, i) => <span key={i} style={{ width: `${92 - (i % 3) * 14}%` }} />)}
    </div>
  );
}

/** Affiche l'erreur ou un squelette de chargement ; garde l'ancien contenu pendant un rechargement. */
export function Etat({ chargement, erreur, donnees, children }) {
  if (erreur) return <Message type="erreur">{erreur}</Message>;
  if (chargement && donnees == null) return <Squelette />;
  return donnees == null ? null : children;
}

const ICONES_MESSAGE = { erreur: "alerte", succes: "check", attention: "info" };

export function Message({ type, children }) {
  if (!children) return null;
  return (
    <div className={`message ${type}`} role={type === "erreur" ? "alert" : "status"}>
      <Icone nom={ICONES_MESSAGE[type] ?? "info"} taille={18} />
      <span>{children}</span>
    </div>
  );
}

export function Vide({ texte, icone = "recherche" }) {
  return (
    <div className="vide">
      <span className="vide-icone"><Icone nom={icone} taille={22} /></span>
      <p>{texte}</p>
    </div>
  );
}

// ---------- Badges ----------

// Statut -> [classe de couleur, icône, libellé] : la couleur n'est jamais seule
const STATUTS = {
  Declare: ["info", "○", "Déclaré"],
  EnExpertise: ["attention", "◐", "En expertise"],
  Indemnise: ["bon", "✓", "Indemnisé"],
  Refuse: ["critique", "✕", "Refusé"],
  Cloture: ["neutre", "■", "Clôturé"],
};

export const libelleStatut = (s) => STATUTS[s]?.[2] ?? s;

export function StatutBadge({ statut }) {
  const [classe, icone, libelle] = STATUTS[statut] ?? ["neutre", "•", statut];
  return (
    <span className={`badge ${classe}`}>
      <span aria-hidden="true">{icone}</span> {libelle}
    </span>
  );
}

export function ValiditeBadge({ valide }) {
  return valide ? (
    <span className="badge bon"><span aria-hidden="true">✓</span> En cours</span>
  ) : (
    <span className="badge neutre"><span aria-hidden="true">■</span> Expiré</span>
  );
}

/** Badges des faits déduits par le raisonneur (règle SWRL et classe définie). */
export function Deductions({ s }) {
  return (
    <span className="pile">
      {s.grave && (
        <span className="badge critique" title="Déduit par la règle SWRL : le sinistre cause un dommage corporel">
          <span aria-hidden="true">⚠</span> Grave
        </span>
      )}
      {s.couvert ? (
        <span className="badge info" title="Déduit de la classe définie SinistreCouvert (au moins une garantie)">
          <span aria-hidden="true">☂</span> Couvert
        </span>
      ) : (
        <span className="badge neutre" title="Aucune garantie ne couvre ce sinistre">Non couvert</span>
      )}
    </span>
  );
}

// ---------- Liens, personnes ----------

const ROUTES = { Assure_: "assures", Contrat_: "contrats", Sinistre_: "sinistres" };

export function LienEntite({ id, children }) {
  const prefixe = Object.keys(ROUTES).find((p) => id?.startsWith(p));
  if (!prefixe) return <span>{children ?? id}</span>;
  return <Link to={`/${ROUTES[prefixe]}/${id}`}>{children ?? id}</Link>;
}

export function Avatar({ texte, grand = false }) {
  const initiales = String(texte ?? "?").split(/\s+/).filter(Boolean).slice(0, 2).map((m) => m[0]).join("").toUpperCase();
  return <span className={`avatar${grand ? " grand" : ""}`} aria-hidden="true">{initiales}</span>;
}

export function Personne({ id, nom }) {
  if (!nom) return "—";
  return (
    <span className="personne">
      <Avatar texte={nom} />
      <LienEntite id={id}>{nom}</LienEntite>
    </span>
  );
}

// ---------- Formulaires ----------

export function Champ({ label, aide, children }) {
  return (
    <label className="champ">
      <span className="champ-label">{label}</span>
      {children}
      {aide && <small className="discret">{aide}</small>}
    </label>
  );
}

/** Panneau latéral pour les formulaires (Échap ou clic à l'extérieur pour fermer). */
export function Tiroir({ ouvert, titre, onFermer, children }) {
  const fermer = useRef(onFermer);
  fermer.current = onFermer;
  useEffect(() => {
    if (!ouvert) return undefined;
    const touche = (e) => e.key === "Escape" && fermer.current();
    window.addEventListener("keydown", touche);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", touche);
      document.body.style.overflow = "";
    };
  }, [ouvert]);
  if (!ouvert) return null;
  return (
    <div className="tiroir-fond" onMouseDown={(e) => e.target === e.currentTarget && onFermer()}>
      <aside className="tiroir" role="dialog" aria-modal="true" aria-label={titre}>
        <header className="tiroir-entete">
          <h2>{titre}</h2>
          <button type="button" className="icone-bouton" onClick={onFermer} aria-label="Fermer">
            <Icone nom="fermer" />
          </button>
        </header>
        <div className="tiroir-corps">{children}</div>
      </aside>
    </div>
  );
}

/** Ouverture d'un panneau pilotée par l'adresse (?nouveau=1) : un lien peut ouvrir directement le formulaire. */
export function useOuvertureUrl(nom = "nouveau") {
  const [params, setParams] = useSearchParams();
  const changer = (ouvert) => {
    const suivants = new URLSearchParams(params);
    if (ouvert) suivants.set(nom, "1");
    else suivants.delete(nom);
    setParams(suivants, { replace: true });
  };
  return [params.get(nom) === "1", () => changer(true), () => changer(false)];
}

// ---------- Confirmation ----------

const ContexteConfirmation = createContext(() => Promise.resolve(false));

export function FournisseurConfirmation({ children }) {
  const [demande, setDemande] = useState(null);
  const confirmer = useCallback((options) => new Promise((resoudre) => setDemande({ ...options, resoudre })), []);
  const repondre = (reponse) => {
    demande.resoudre(reponse);
    setDemande(null);
  };
  useEffect(() => {
    if (!demande) return undefined;
    const touche = (e) => e.key === "Escape" && repondre(false);
    window.addEventListener("keydown", touche);
    return () => window.removeEventListener("keydown", touche);
  });

  return (
    <ContexteConfirmation.Provider value={confirmer}>
      {children}
      {demande && (
        <div className="modale-fond" onMouseDown={(e) => e.target === e.currentTarget && repondre(false)}>
          <div className="modale" role="alertdialog" aria-modal="true" aria-labelledby="modale-titre">
            <span className="modale-icone"><Icone nom="poubelle" /></span>
            <h2 id="modale-titre">{demande.titre}</h2>
            <p>{demande.message}</p>
            <div className="actions">
              <button type="button" className="secondaire" onClick={() => repondre(false)} autoFocus>Annuler</button>
              <button type="button" className="danger plein" onClick={() => repondre(true)}>{demande.action ?? "Supprimer"}</button>
            </div>
          </div>
        </div>
      )}
    </ContexteConfirmation.Provider>
  );
}

export const useConfirmer = () => useContext(ContexteConfirmation);

// ---------- Recherche et tableaux ----------

const normaliser = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Garde les lignes qui contiennent tous les mots recherchés (sans accents ni majuscules) dans l'un des champs. */
export function filtrer(lignes, recherche, champs) {
  const mots = normaliser(recherche).split(/\s+/).filter(Boolean);
  if (!lignes || mots.length === 0) return lignes;
  return lignes.filter((l) => {
    const texte = normaliser(champs.map((c) => (typeof c === "function" ? c(l) : l[c])).join(" "));
    return mots.every((m) => texte.includes(m));
  });
}

export function BarreRecherche({ valeur, onChange, placeholder, affiches, total }) {
  return (
    <div className="barre-recherche">
      <Icone nom="recherche" taille={18} className="barre-recherche-icone" />
      <input type="search" value={valeur} placeholder={placeholder} aria-label={placeholder}
             onChange={(e) => onChange(e.target.value)} />
      {valeur && total != null && <span className="barre-recherche-compte">{affiches} / {total}</span>}
    </div>
  );
}

/** colonnes : [{ titre, champ | rendu(ligne), num }] ; lien(ligne) rend toute la ligne cliquable. */
export function Tableau({ colonnes, lignes, vide = "Aucun résultat.", lien }) {
  const naviguer = useNavigate();
  if (!lignes?.length) return <Vide texte={vide} />;
  const ouvrir = (e, l) => {
    if (!lien || e.target.closest("a, button, input, select")) return;
    naviguer(lien(l));
  };
  return (
    <div className="tableau-defile">
      <table>
        <thead>
          <tr>
            {colonnes.map((c) => <th key={c.titre} className={c.num ? "num" : undefined}>{c.titre}</th>)}
            {lien && <th aria-label="Ouvrir" />}
          </tr>
        </thead>
        <tbody>
          {lignes.map((l, i) => (
            <tr key={`${l.id ?? ""}-${i}`} className={lien ? "cliquable" : undefined} onClick={(e) => ouvrir(e, l)}
                tabIndex={lien ? 0 : undefined} onKeyDown={(e) => lien && e.key === "Enter" && naviguer(lien(l))}>
              {colonnes.map((c) => (
                <td key={c.titre} className={c.num ? "num" : undefined}>
                  {c.rendu ? c.rendu(l) : l[c.champ] ?? "—"}
                </td>
              ))}
              {lien && <td className="chevron"><Icone nom="fleche" taille={16} /></td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Liste({ items, rendu, vide = "—" }) {
  if (!items?.length) return <p className="discret">{vide}</p>;
  return <ul className="liste">{items.map((x, i) => <li key={x.id ?? i}>{rendu(x)}</li>)}</ul>;
}
