import { useEffect, useState } from "react";

export const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function chaineRequete(params) {
  if (!params) return "";
  const p = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null));
  const s = p.toString();
  return s ? `?${s}` : "";
}

async function appel(methode, chemin, corps) {
  let reponse;
  try {
    reponse = await fetch(BASE + chemin, {
      method: methode,
      headers: corps ? { "Content-Type": "application/json" } : {},
      body: corps ? JSON.stringify(corps) : undefined,
    });
  } catch {
    throw new Error(`API injoignable (${BASE}) : lancez backend\\demarrer_backend.bat`);
  }
  if (reponse.status === 204) return null;
  const donnees = await reponse.json().catch(() => null);
  if (!reponse.ok) {
    const detail = donnees?.detail;
    // 422 : erreurs de validation Pydantic (liste), sinon message texte de l'API
    const message = Array.isArray(detail)
      ? detail.map((e) => `${e.loc.slice(1).join(".")} : ${e.msg}`).join(" ; ")
      : detail;
    const erreur = new Error(message || `Erreur ${reponse.status}`);
    erreur.statut = reponse.status;
    throw erreur;
  }
  return donnees;
}

export const api = {
  get: (chemin, params) => appel("GET", chemin + chaineRequete(params)),
  post: (chemin, corps) => appel("POST", chemin, corps ?? {}),
  put: (chemin, corps) => appel("PUT", chemin, corps),
  patch: (chemin, corps) => appel("PATCH", chemin, corps),
  del: (chemin) => appel("DELETE", chemin),
};

/** Charge `chemin` (rien si null) et recharge quand le chemin ou les paramètres changent. */
export function useDonnees(chemin, params) {
  const [etat, setEtat] = useState({ chargement: !!chemin, erreur: null, donnees: null });
  const [version, setVersion] = useState(0);
  const cle = `${chemin}${JSON.stringify(params ?? {})}`;

  useEffect(() => {
    if (!chemin) {
      setEtat({ chargement: false, erreur: null, donnees: null });
      return undefined;
    }
    let actif = true;
    setEtat((e) => ({ ...e, chargement: true, erreur: null }));
    api
      .get(chemin, params)
      .then((donnees) => actif && setEtat({ chargement: false, erreur: null, donnees }))
      .catch((e) => actif && setEtat({ chargement: false, erreur: e.message, donnees: null }));
    return () => {
      actif = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cle, version]);

  return { ...etat, recharger: () => setVersion((v) => v + 1) };
}

/** Exécute une action (POST/PUT/...) en suivant son état ; renvoie undefined en cas d'erreur. */
export function useAction() {
  const [etat, setEtat] = useState({ enCours: false, erreur: null, succes: null });
  const executer = async (fn, succes) => {
    setEtat({ enCours: true, erreur: null, succes: null });
    try {
      const resultat = await fn();
      setEtat({ enCours: false, erreur: null, succes: typeof succes === "function" ? succes(resultat) : succes ?? null });
      return resultat;
    } catch (e) {
      setEtat({ enCours: false, erreur: e.message, succes: null });
      return undefined;
    }
  };
  return [etat, executer];
}
