import { useState } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { BASE, useDonnees } from "./api.js";
import { Icone } from "./components/icones.jsx";
import { FournisseurConfirmation } from "./components/ui.jsx";
import { AssureDetail, Assures } from "./pages/Assures.jsx";
import { ContratDetail, Contrats } from "./pages/Contrats.jsx";
import Question from "./pages/Question.jsx";
import Referentiel from "./pages/Referentiel.jsx";
import { SinistreDetail, Sinistres } from "./pages/Sinistres.jsx";
import TableauDeBord from "./pages/TableauDeBord.jsx";

const RUBRIQUES = [
  { titre: "Pilotage", liens: [["/", "Tableau de bord", "tableau"]] },
  {
    titre: "Gestion",
    liens: [
      ["/assures", "Assurés", "assures"],
      ["/contrats", "Contrats", "contrats"],
      ["/sinistres", "Sinistres", "sinistres"],
      ["/referentiel", "Référentiel", "referentiel"],
    ],
  },
  { titre: "Assistant", liens: [["/question", "Poser une question", "question"]] },
];

// Titre de chaque section, pour le fil d'Ariane (premier segment de l'adresse)
const TITRES = Object.fromEntries(RUBRIQUES.flatMap((r) => r.liens.map(([chemin, libelle]) => [chemin.slice(1), libelle])));

/** « Pages / Sinistres / Sinistre_2025_058 » puis le titre de la page en gras. */
function FilAriane() {
  const { pathname } = useLocation();
  const [section = "", id] = pathname.split("/").filter(Boolean);
  const titre = TITRES[section] ?? "Page introuvable";
  const fiche = id && decodeURIComponent(id);
  return (
    <div className="fil-ariane">
      <nav className="fil-ariane-chemin" aria-label="Fil d'Ariane">
        <span>Pages</span>
        <span aria-hidden="true">/</span>
        {fiche ? (
          <>
            <Link to={`/${section}`}>{titre}</Link>
            <span aria-hidden="true">/</span>
            <span aria-current="page">{fiche}</span>
          </>
        ) : (
          <span aria-current="page">{titre}</span>
        )}
      </nav>
      <strong className="fil-ariane-titre">{fiche ?? titre}</strong>
    </div>
  );
}

/** Question en langage naturel accessible depuis toutes les pages (module NLP). */
function BarreQuestion() {
  const [texte, setTexte] = useState("");
  const naviguer = useNavigate();
  const envoyer = (e) => {
    e.preventDefault();
    if (texte.trim().length < 3) return;
    naviguer(`/question?q=${encodeURIComponent(texte.trim())}`);
    setTexte("");
  };
  return (
    <form className="barre-question" onSubmit={envoyer} role="search">
      <Icone nom="question" taille={18} className="barre-question-icone" />
      <input value={texte} onChange={(e) => setTexte(e.target.value)} aria-label="Poser une question en langage naturel"
             placeholder="Posez une question… ex. « sinistres graves à Sousse »" />
      <kbd>Entrée</kbd>
    </form>
  );
}

export default function App() {
  const sante = useDonnees("/");
  const aujourdhui = new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  return (
    <FournisseurConfirmation>
      <div className="app">
        <aside className="barre-laterale">
          <div className="marque">
            <img className="marque-logo" src="/sparquick_embleme.svg" alt="" width="34" height="39" />
            <span>
              <strong>SPAR<span>Quick</span></strong>
              <small>Posez la question, le graphe répond.</small>
            </span>
          </div>
          <nav aria-label="Navigation principale">
            {RUBRIQUES.map((r) => (
              <div key={r.titre} className="rubrique">
                <span className="rubrique-titre">{r.titre}</span>
                {r.liens.map(([chemin, libelle, icone]) => (
                  <NavLink key={chemin} to={chemin} end={chemin === "/"}>
                    <span className="nav-icone"><Icone nom={icone} taille={16} /></span>
                    <span>{libelle}</span>
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
          <div className={`carte-aide${sante.erreur ? " ko" : ""}`} role="status">
            <span className="carte-aide-icone"><Icone nom={sante.erreur ? "alerte" : "bouclier"} taille={18} /></span>
            <strong>{sante.erreur ? "Serveur injoignable" : "Ontologie en ligne"}</strong>
            <span title={sante.erreur ?? undefined}>
              {sante.erreur ? "Lancez Fuseki puis l'API" : `${sante.donnees?.triplets ?? "…"} triplets dans Fuseki`}
            </span>
            <a href={`${BASE}/docs`} target="_blank" rel="noreferrer">Documentation de l'API</a>
          </div>
        </aside>
        <div className="principal">
          <header className="barre-haut">
            <FilAriane />
            <BarreQuestion />
            <span className="date-du-jour">{aujourdhui}</span>
          </header>
          <main className="contenu">
            <Routes>
              <Route path="/" element={<TableauDeBord />} />
              <Route path="/assures" element={<Assures />} />
              <Route path="/assures/:id" element={<AssureDetail />} />
              <Route path="/contrats" element={<Contrats />} />
              <Route path="/contrats/:id" element={<ContratDetail />} />
              <Route path="/sinistres" element={<Sinistres />} />
              <Route path="/sinistres/:id" element={<SinistreDetail />} />
              <Route path="/referentiel" element={<Referentiel />} />
              <Route path="/question" element={<Question />} />
              <Route path="*" element={<p>Page introuvable.</p>} />
            </Routes>
          </main>
          <footer className="pied-page">
            Mise en page inspirée de{" "}
            <a href="https://github.com/creativetimofficial/purity-ui-dashboard" target="_blank" rel="noreferrer">Purity UI Dashboard</a>{" "}
            de Creative Tim et Simmmple (licence MIT).
          </footer>
        </div>
      </div>
    </FournisseurConfirmation>
  );
}
