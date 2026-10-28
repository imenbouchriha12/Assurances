import { Icone } from "./icones.jsx";

/** Indicateur chiffré (pas de graphique pour une valeur seule) : texte à gauche, pastille d'icône à droite. */
export function Tuile({ titre, valeur, detail, icone }) {
  return (
    <div className="tuile">
      <div className="tuile-texte">
        <span className="tuile-titre">{titre}</span>
        <span className="tuile-valeur">{valeur}</span>
        {detail && <span className="tuile-detail">{detail}</span>}
      </div>
      {icone && <span className="tuile-icone"><Icone nom={icone} taille={20} /></span>}
    </div>
  );
}

/** Barre de progression (part entre 0 et 1), couleur de l'accent sauf indication contraire. */
export function Progression({ part, couleur, libelle }) {
  return (
    <span className="progression" role="img" aria-label={libelle ?? `${Math.round(part * 100)} %`}>
      <span style={{ width: `${Math.min(1, Math.max(0, part)) * 100}%`, background: couleur }} />
    </span>
  );
}

/** Mini-indicateur : pastille, libellé, valeur, et barre de progression si `part` est donnée. */
export function MiniStat({ pastille, couleur, libelle, valeur, part, libellePart }) {
  return (
    <div className="mini-stat">
      <span className="mini-stat-entete">
        <span className="pastille-icone" style={{ background: couleur }} aria-hidden="true">{pastille}</span>
        {libelle}
      </span>
      <span className="mini-stat-valeur">{valeur}</span>
      {part != null && <Progression part={part} couleur={couleur} libelle={libellePart} />}
    </div>
  );
}

// Couleurs des catégories (validées : séparation daltonisme, contraste ≥ 3:1, distinctes des statuts).
// Attribuées par ordre alphabétique du libellé : une catégorie garde sa couleur quel que soit son rang.
const CATEGORIES = ["#1c5cab", "#d55181", "#1aa3b5"];

/** Anneau : parts d'un tout, total au centre, légende avec valeur et pourcentage (jamais la couleur seule). */
export function Anneau({ donnees, format = (v) => v, total, libelleTotal }) {
  const somme = donnees.reduce((t, d) => t + d.valeur, 0) || 1;
  const ordre = [...donnees].map((d) => d.label).sort((a, b) => a.localeCompare(b));
  const couleur = (label) => CATEGORIES[ordre.indexOf(label)] ?? "var(--texte-3)";
  const r = 60;
  const circonference = 2 * Math.PI * r;
  let debut = 0;
  return (
    <div className="anneau">
      <svg viewBox="0 0 160 160" role="img" aria-label={donnees.map((d) => `${d.label} : ${format(d.valeur)}`).join(", ")}>
        <circle cx="80" cy="80" r={r} fill="none" stroke="var(--piste)" strokeWidth="22" />
        {donnees.map((d) => {
          const longueur = (d.valeur / somme) * circonference;
          const segment = (
            <circle key={d.label} cx="80" cy="80" r={r} fill="none" stroke={couleur(d.label)} strokeWidth="22"
                    strokeDasharray={`${Math.max(0, longueur - 2)} ${circonference}`} strokeDashoffset={-debut}
                    transform="rotate(-90 80 80)"><title>{`${d.label} : ${format(d.valeur)}`}</title></circle>
          );
          debut += longueur;
          return segment;
        })}
        <text x="80" y="78" textAnchor="middle" className="anneau-total">{total}</text>
        <text x="80" y="98" textAnchor="middle" className="anneau-libelle">{libelleTotal}</text>
      </svg>
      <ul className="anneau-legende">
        {donnees.map((d) => (
          <li key={d.label}>
            <span className="anneau-pastille" style={{ background: couleur(d.label) }} aria-hidden="true" />
            <span>{d.label}</span>
            <strong>{format(d.valeur)}</strong>
            <span className="discret">{Math.round((d.valeur / somme) * 100)} %</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Liste répartie : pastille d'icône, libellé, valeur et part, barre de progression. */
export function Repartition({ donnees, format = (v) => v, icone }) {
  const somme = donnees.reduce((t, d) => t + d.valeur, 0) || 1;
  return (
    <ul className="repartition">
      {donnees.map((d) => (
        <li key={d.label}>
          <span className="pastille-icone"><Icone nom={icone} taille={15} /></span>
          <strong>{d.label}</strong>
          <span className="discret">{format(d.valeur)} · {Math.round((d.valeur / somme) * 100)} %</span>
          <Progression part={d.valeur / somme} />
        </li>
      ))}
    </ul>
  );
}
