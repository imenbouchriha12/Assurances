import { useState } from "react";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";

import { useDonnees } from "./api.js";
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
            <span className="marque-logo"><Icone nom="bouclier" taille={20} /></span>
            <span>
              <strong>Assurance</strong>
              <small>& Sinistres</small>
            </span>
          </div>
          <nav aria-label="Navigation principale">
            {RUBRIQUES.map((r) => (
              <div key={r.titre} className="rubrique">
                <span className="rubrique-titre">{r.titre}</span>
                {r.liens.map(([chemin, libelle, icone]) => (
                  <NavLink key={chemin} to={chemin} end={chemin === "/"}>
                    <Icone nom={icone} taille={19} />
                    <span>{libelle}</span>
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
          <div className="etat-serveur" role="status">
            {sante.erreur ? (
              <span className="pastille ko" title={sante.erreur}>Serveur injoignable</span>
            ) : sante.donnees ? (
              <span className="pastille ok">Ontologie en ligne · {sante.donnees.triplets} triplets</span>
            ) : null}
          </div>
        </aside>
        <div className="principal">
          <header className="barre-haut">
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
        </div>
      </div>
    </FournisseurConfirmation>
  );
}
