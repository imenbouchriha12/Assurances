import { Icone } from "./icones.jsx";

/** Indicateur chiffré (pas de graphique pour une valeur seule). */
export function Tuile({ titre, valeur, detail, icone }) {
  return (
    <div className="tuile">
      <div className="tuile-entete">
        <span className="tuile-titre">{titre}</span>
        {icone && <span className="tuile-icone"><Icone nom={icone} taille={18} /></span>}
      </div>
      <span className="tuile-valeur">{valeur}</span>
      {detail && <span className="tuile-detail">{detail}</span>}
    </div>
  );
}

/**
 * Barres horizontales à une seule série : une couleur, pas de légende (le titre nomme la série),
 * valeur écrite en bout de barre, info-bulle au survol ou au focus clavier.
 * Une barre peut porter sa propre couleur et son icône (`couleur`, `icone`) quand elle représente
 * un statut : les mêmes que sur les badges, et le libellé reste écrit.
 */
export function Barres({ titre, donnees, format = (v) => v, icone, resume }) {
  const max = Math.max(0, ...donnees.map((d) => d.valeur)) || 1;
  return (
    <figure className="carte graphique">
      <figcaption>
        {icone && <span className="tuile-icone"><Icone nom={icone} taille={16} /></span>}
        <span>{titre}</span>
        {resume && <span className="graphique-resume">{resume}</span>}
      </figcaption>
      {donnees.length === 0 ? (
        <p className="discret">Aucune donnée.</p>
      ) : (
        <ul className="barres">
          {donnees.map((d) => (
            <li key={d.label} tabIndex={0} aria-label={`${d.label} : ${format(d.valeur)}`}>
              <span className="barre-label">
                {d.icone && <span className="barre-icone" aria-hidden="true" style={{ color: d.couleur }}>{d.icone}</span>}
                {d.label}
              </span>
              <span className="barre-piste">
                <span className="barre-remplie" style={{ width: `${(d.valeur / max) * 100}%`, background: d.couleur }} />
              </span>
              <span className="barre-valeur">{format(d.valeur)}</span>
              <span className="infobulle" role="tooltip">
                <strong>{d.label}</strong>
                <span>{format(d.valeur)}{d.detail ? ` · ${d.detail}` : ""}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </figure>
  );
}
