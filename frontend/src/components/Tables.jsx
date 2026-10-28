import { dateFr, Deductions, montant, Personne, StatutBadge, Tableau, ValiditeBadge } from "./ui.jsx";

export function TableSinistres({ lignes, vide = "Aucun sinistre." }) {
  return (
    <Tableau
      lignes={lignes}
      vide={vide}
      lien={(s) => `/sinistres/${s.id}`}
      colonnes={[
        { titre: "Sinistre", rendu: (s) => <><strong>{s.typeLabel}</strong><br /><span className="discret">{s.id}</span></> },
        { titre: "Date", rendu: (s) => dateFr(s.date) },
        { titre: "Assuré", rendu: (s) => <Personne id={s.assure} nom={s.assureNom} /> },
        { titre: "Statut", rendu: (s) => <StatutBadge statut={s.statut} /> },
        { titre: "Déductions", rendu: (s) => <Deductions s={s} /> },
        { titre: "Dommages", num: true, rendu: (s) => montant(s.totalEstime) },
        { titre: "Indemnisé", num: true, rendu: (s) => montant(s.montantIndemnise) },
      ]}
    />
  );
}

export function TableContrats({ lignes, vide = "Aucun contrat." }) {
  return (
    <Tableau
      lignes={lignes}
      vide={vide}
      lien={(c) => `/contrats/${c.id}`}
      colonnes={[
        { titre: "Contrat", rendu: (c) => <><strong>{c.numero}</strong><br /><span className="discret">{c.typeLabel}</span></> },
        { titre: "Assuré", rendu: (c) => <Personne id={c.assure} nom={c.assureNom} /> },
        { titre: "Assureur", champ: "assureurNom" },
        { titre: "Période", rendu: (c) => `${dateFr(c.dateDebut)} → ${dateFr(c.dateFin)}` },
        { titre: "Prime", num: true, rendu: (c) => montant(c.prime) },
        { titre: "Validité", rendu: (c) => <ValiditeBadge valide={c.valide} /> },
      ]}
    />
  );
}
