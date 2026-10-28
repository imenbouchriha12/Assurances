/** Icônes au trait (24 × 24), dessinées en SVG pour ne dépendre d'aucune bibliothèque. */
const TRACES = {
  bouclier: <path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3z" />,
  tableau: <path d="M4 4h7v7H4zM13 4h7v4h-7zM13 10h7v10h-7zM4 13h7v7H4z" />,
  assures: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M16.5 5.2a3 3 0 010 5.6M17.5 14.3c2.1.6 3.5 2.6 3.5 5.7" />
    </>
  ),
  contrats: <path d="M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6" />,
  sinistres: <path d="M12 4l9 16H3zM12 10v4M12 17.2v.1" />,
  referentiel: <path d="M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5M3 17.5l9 5 9-5" />,
  question: <path d="M12 3l1.8 4.7 4.7 1.8-4.7 1.8L12 16l-1.8-4.7-4.7-1.8 4.7-1.8zM19 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z" />,
  recherche: <path d="M11 4a7 7 0 100 14 7 7 0 000-14zM20 20l-4-4" />,
  plus: <path d="M12 5v14M5 12h14" />,
  fermer: <path d="M6 6l12 12M18 6L6 18" />,
  crayon: <path d="M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4" />,
  poubelle: <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6" />,
  fleche: <path d="M5 12h14M13 6l6 6-6 6" />,
  retour: <path d="M19 12H5M11 6l-6 6 6 6" />,
  argent: (
    <>
      <rect x="3" y="6" width="18" height="12" rx="2" />
      <circle cx="12" cy="12" r="2.5" />
    </>
  ),
  calendrier: (
    <>
      <rect x="4" y="5" width="16" height="15" rx="2" />
      <path d="M4 10h16M9 3v4M15 3v4" />
    </>
  ),
  lieu: <path d="M12 21s-6-5.3-6-11a6 6 0 1112 0c0 5.7-6 11-6 11zM12 8a2 2 0 100 4 2 2 0 000-4z" />,
  check: <path d="M5 12l5 5 9-10" />,
  alerte: <path d="M12 3a9 9 0 100 18 9 9 0 000-18zM12 8v5M12 16v.1" />,
  info: <path d="M12 3a9 9 0 100 18 9 9 0 000-18zM12 11v5M12 8v.1" />,
  expert: <path d="M10 4a6 6 0 100 12 6 6 0 000-12zM20 20l-5.5-5.5M8 10l1.5 1.5L12.5 8" />,
  entreprise: <path d="M4 20V6l8-3v17M12 9h8v11M4 20h16M7 8h2M7 12h2M7 16h2M15 13h2M15 17h2" />,
  graphique: <path d="M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-6" />,
};

export function Icone({ nom, taille = 20, className }) {
  return (
    <svg className={className} width={taille} height={taille} viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {TRACES[nom]}
    </svg>
  );
}
