import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api.js";
import { Icone } from "../components/icones.jsx";

const EXEMPLES = [
  "Quels sont les sinistres graves ?",
  "Liste des contrats automobiles en cours",
  "Quel est le montant total indemnisé par STAR ?",
  "Combien de sinistres par statut ?",
  "Quel est le sinistre le plus coûteux ?",
  "Quels experts travaillent pour GAT ?",
];
const AFFICHES = 8;
const ROUTES = { Assure_: "assures", Contrat_: "contrats", Sinistre_: "sinistres" };
const lienVers = (id) => {
  const prefixe = Object.keys(ROUTES).find((p) => id?.startsWith(p));
  return prefixe ? `/${ROUTES[prefixe]}/${id}` : null;
};

function Element({ e }) {
  const lien = lienVers(e.id);
  const contenu = (
    <>
      <span className="resultat-texte">
        <strong>{e.titre}</strong>
        {e.details?.length > 0 && <span className="discret">{e.details.join(" · ")}</span>}
      </span>
      {e.valeur && <span className="resultat-valeur">{e.valeur}</span>}
      {lien && <Icone nom="fleche" taille={16} className="resultat-fleche" />}
    </>
  );
  return <li>{lien ? <Link to={lien} className="resultat">{contenu}</Link> : <div className="resultat">{contenu}</div>}</li>;
}

function Reponse({ r }) {
  const [tout, setTout] = useState(false);
  const visibles = tout ? r.elements : r.elements.slice(0, AFFICHES);
  return (
    <>
      {r.corrections?.length > 0 && (
        <p className="discret">
          Mots corrigés : {r.corrections.map((c) => `« ${c.mot} » → « ${c.correction} »`).join(", ")}
        </p>
      )}
      <p className="reponse-texte">{r.reponse}</p>
      {r.criteres.length > 0 && (
        <div className="criteres" aria-label="Critères compris">
          {r.criteres.map((c) => <span key={c} className="critere">{c}</span>)}
        </div>
      )}
      {r.elements.length > 0 && (
        <ul className="resultats">
          {visibles.map((e, i) => <Element key={`${e.id ?? e.titre}-${i}`} e={e} />)}
        </ul>
      )}
      {r.elements.length > AFFICHES && (
        <button type="button" className="secondaire petit" onClick={() => setTout(!tout)}>
          {tout ? "Afficher moins" : `Afficher les ${r.elements.length - AFFICHES} autres`}
        </button>
      )}
    </>
  );
}

/** Assistant : question en français -> module NLP (spaCy + scikit-learn) -> SPARQL -> réponse rédigée. */
export default function Question() {
  const [params, setParams] = useSearchParams();
  const [question, setQuestion] = useState("");
  const [echanges, setEchanges] = useState([]);
  const dernierParametre = useRef("");
  const fin = useRef(null);

  const demander = useCallback(async (texte) => {
    const q = texte.trim();
    if (q.length < 3) return;
    const id = Date.now() + Math.random();
    setEchanges((e) => [...e, { id, question: q, enCours: true }]);
    setQuestion("");
    try {
      const r = await api.post("/nlp/question", { question: q });
      setEchanges((e) => e.map((x) => (x.id === id ? { ...x, enCours: false, reponse: r } : x)));
    } catch (err) {
      setEchanges((e) => e.map((x) => (x.id === id ? { ...x, enCours: false, erreur: err.message } : x)));
    }
  }, []);

  // Question venant de la barre du haut (?q=...) : posée une fois, puis retirée de l'adresse
  const q = params.get("q") ?? "";
  useEffect(() => {
    if (!q) {
      dernierParametre.current = "";
      return;
    }
    if (dernierParametre.current === q) return;
    dernierParametre.current = q;
    demander(q);
    setParams({}, { replace: true });
  }, [q, demander, setParams]);

  useEffect(() => {
    fin.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [echanges]);

  return (
    <>
      <div className="entete">
        <div>
          <h1>Poser une question</h1>
          <p className="sous-titre">Interrogez vos contrats, sinistres et assurés en français, sans syntaxe particulière.</p>
        </div>
        {echanges.length > 0 && (
          <button type="button" className="secondaire" onClick={() => setEchanges([])}>Nouvelle conversation</button>
        )}
      </div>

      <section className="carte assistant">
        {echanges.length === 0 ? (
          <div className="assistant-accueil">
            <span className="assistant-avatar grand"><Icone nom="question" taille={26} /></span>
            <h2>Que souhaitez-vous savoir ?</h2>
            <p className="discret">Par exemple :</p>
            <div className="pile centre">
              {EXEMPLES.map((ex) => <button type="button" key={ex} className="puce" onClick={() => demander(ex)}>{ex}</button>)}
            </div>
          </div>
        ) : (
          <div className="conversation" aria-live="polite">
            {echanges.map((x) => (
              <div key={x.id} className="echange">
                <div className="bulle utilisateur">{x.question}</div>
                <div className="message-assistant">
                  <span className="assistant-avatar"><Icone nom="question" taille={16} /></span>
                  <div className="bulle assistant-bulle">
                    {x.enCours && <span className="points" aria-label="Recherche en cours"><span /><span /><span /></span>}
                    {x.erreur && (
                      <p className="reponse-texte">
                        Je n'ai pas compris cette question. {x.erreur}
                        <br /><span className="discret">Essayez par exemple : « {EXEMPLES[0]} »</span>
                      </p>
                    )}
                    {x.reponse && <Reponse r={x.reponse} />}
                  </div>
                </div>
              </div>
            ))}
            <div ref={fin} />
          </div>
        )}

        <form className="assistant-saisie" onSubmit={(e) => { e.preventDefault(); demander(question); }}>
          <Icone nom="question" taille={20} className="question-icone" />
          <input value={question} onChange={(e) => setQuestion(e.target.value)} aria-label="Votre question"
                 placeholder="Posez votre question…" autoFocus />
          <button type="submit" disabled={question.trim().length < 3}>
            Demander <Icone nom="fleche" taille={16} />
          </button>
        </form>
      </section>
    </>
  );
}
