import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, useAction, useDonnees } from "../api.js";
import { Icone } from "../components/icones.jsx";
import { TableContrats, TableSinistres } from "../components/Tables.jsx";
import {
  Avatar, BarreRecherche, Champ, Etat, filtrer, Message, Personne, Tableau, Tiroir, useConfirmer, useOuvertureUrl,
} from "../components/ui.jsx";

function FormAssure({ initial, onEnregistre, onAnnuler }) {
  const [v, setV] = useState({ nom: "", prenom: "", cin: "", adresse: "", ...initial });
  const [etat, executer] = useAction();
  const maj = (champ) => (e) => setV({ ...v, [champ]: e.target.value });

  const soumettre = async (e) => {
    e.preventDefault();
    const corps = { nom: v.nom, prenom: v.prenom, cin: v.cin, adresse: v.adresse || null };
    const r = await executer(() => (initial?.id ? api.put(`/assures/${initial.id}`, corps) : api.post("/assures", corps)));
    if (r) onEnregistre(r);
  };

  return (
    <form className="formulaire" onSubmit={soumettre}>
      <div className="grille-champs">
        <Champ label="Prénom"><input required autoFocus value={v.prenom} onChange={maj("prenom")} /></Champ>
        <Champ label="Nom"><input required value={v.nom} onChange={maj("nom")} /></Champ>
        <Champ label="CIN" aide="8 chiffres, unique (clé de Personne)">
          <input required pattern="\d{8}" inputMode="numeric" value={v.cin} onChange={maj("cin")} />
        </Champ>
        <Champ label="Adresse (ville)"><input value={v.adresse ?? ""} onChange={maj("adresse")} /></Champ>
      </div>
      <Message type="erreur">{etat.erreur}</Message>
      <div className="actions pied-formulaire">
        <button type="button" className="secondaire" onClick={onAnnuler}>Annuler</button>
        <button type="submit" disabled={etat.enCours}>{etat.enCours ? "Enregistrement…" : "Enregistrer"}</button>
      </div>
    </form>
  );
}

export function Assures() {
  const [recherche, setRecherche] = useState("");
  const [creation, ouvrir, fermer] = useOuvertureUrl();
  const liste = useDonnees("/assures");
  const naviguer = useNavigate();
  const lignes = filtrer(liste.donnees, recherche, ["prenom", "nom", "cin", "adresse", "id"]);

  return (
    <>
      <div className="entete">
        <div>
          <h1>Assurés</h1>
          <p className="sous-titre">Personnes ayant souscrit au moins un contrat.</p>
        </div>
        <button onClick={ouvrir}><Icone nom="plus" taille={18} /> Nouvel assuré</button>
      </div>
      <Tiroir ouvert={creation} titre="Nouvel assuré" onFermer={fermer}>
        <FormAssure onAnnuler={fermer} onEnregistre={(a) => naviguer(`/assures/${a.id}`)} />
      </Tiroir>
      <div className="filtres">
        <BarreRecherche valeur={recherche} onChange={setRecherche} placeholder="Rechercher un assuré (nom, prénom, CIN, ville)"
                        affiches={lignes?.length} total={liste.donnees?.length} />
      </div>
      <section className="carte sans-marge">
        <Etat {...liste}>
          <Tableau
            lignes={lignes}
            vide="Aucun assuré ne correspond à la recherche."
            lien={(a) => `/assures/${a.id}`}
            colonnes={[
              { titre: "Assuré", rendu: (a) => <Personne id={a.id} nom={`${a.prenom} ${a.nom}`} /> },
              { titre: "CIN", champ: "cin" },
              { titre: "Ville", champ: "adresse" },
              { titre: "Contrats", num: true, champ: "nbContrats" },
              { titre: "Sinistres", num: true, champ: "nbSinistres" },
            ]}
          />
        </Etat>
      </section>
    </>
  );
}

export function AssureDetail() {
  const { id } = useParams();
  const naviguer = useNavigate();
  const confirmer = useConfirmer();
  const assure = useDonnees(`/assures/${id}`);
  const [edition, setEdition] = useState(false);
  const [etat, executer] = useAction();
  const a = assure.donnees;

  const supprimer = async () => {
    if (!(await confirmer({ titre: "Supprimer cet assuré ?", message: `${a.prenom} ${a.nom} sera définitivement supprimé.` }))) return;
    const r = await executer(() => api.del(`/assures/${id}`));
    if (r !== undefined) naviguer("/assures");
  };

  return (
    <Etat {...assure}>
      {a && (
        <>
          <Link to="/assures" className="lien-retour"><Icone nom="retour" taille={16} /> Assurés</Link>
          <section className="fiche">
            <Avatar texte={`${a.prenom} ${a.nom}`} grand />
            <div className="fiche-texte">
              <h1>{a.prenom} {a.nom}</h1>
              <div className="fiche-faits">
                <span><Icone nom="contrats" taille={16} /> CIN {a.cin}</span>
                {a.adresse && <span><Icone nom="lieu" taille={16} /> {a.adresse}</span>}
                <span><Icone nom="contrats" taille={16} /> {a.contrats.length} contrat(s)</span>
                <span><Icone nom="sinistres" taille={16} /> {a.sinistres.length} sinistre(s)</span>
              </div>
            </div>
            <div className="actions">
              <button className="secondaire" onClick={() => setEdition(true)}><Icone nom="crayon" taille={16} /> Modifier</button>
              <button className="danger" onClick={supprimer} disabled={etat.enCours}><Icone nom="poubelle" taille={16} /> Supprimer</button>
            </div>
          </section>
          <Message type="erreur">{etat.erreur}</Message>
          <Tiroir ouvert={edition} titre="Modifier l'assuré" onFermer={() => setEdition(false)}>
            <FormAssure initial={a} onAnnuler={() => setEdition(false)}
                        onEnregistre={() => { setEdition(false); assure.recharger(); }} />
          </Tiroir>
          <section className="carte sans-marge">
            <div className="carte-entete"><h2>Contrats</h2></div>
            <TableContrats lignes={a.contrats} vide="Aucun contrat pour cet assuré." />
          </section>
          <section className="carte sans-marge">
            <div className="carte-entete"><h2>Sinistres déclarés</h2></div>
            <TableSinistres lignes={a.sinistres} vide="Aucun sinistre déclaré." />
          </section>
        </>
      )}
    </Etat>
  );
}
