/*
 * AKMS Autos : toutes les informations modifiables du site sont ici.
 * Changez une valeur, enregistrez, et le site se met à jour partout (en-tête,
 * pied de page, formulaires, statut « ouvert / fermé », mentions légales).
 *
 * Les valeurs marquées « À CONFIRMER » viennent des documents de l'entreprise
 * (Kbis, factures) mais doivent être vérifiées par le gérant avant la mise en ligne.
 */
window.AMKS = {
  nom: "AKMS Autos",      // nom commercial (logo). La société reste AMKS AUTOS au Kbis.
  signature: "Nikoghossian Père & Fils",
  raisonSociale: "AMKS AUTOS",
  forme: "SARL à associé unique",
  capital: "2 000 €",
  siren: "930 691 431",
  siret: "930 691 431 00017",
  rcs: "RCS Marseille 930 691 431",
  tva: "FR18 930 691 431",
  ape: "45.20A Entretien et réparation de véhicules automobiles légers",
  gerant: "Karen Nikoghossian",
  depuis: 2020, // premier garage familial (KAMS), repris par AMKS Autos en 2024

  adresse: { rue: "115 boulevard de la Millière", cp: "13011", ville: "Marseille", quartier: "La Millière, 11e arrondissement" },
  gps: { lat: 43.2921, lng: 5.4824 }, // À CONFIRMER : position approximative

  // À CONFIRMER : numéro figurant sur les factures du garage familial
  telephone: "06 64 38 21 44",
  telephoneIntl: "33664382144",   // pour WhatsApp (sans le 0 ni le +)
  email: "amks.autos2308@gmail.com",

  // À CONFIRMER : horaires. Une plage par ligne, [] = fermé. 0 = dimanche … 6 = samedi.
  horaires: {
    1: [["08:30", "12:00"], ["14:00", "18:30"]],
    2: [["08:30", "12:00"], ["14:00", "18:30"]],
    3: [["08:30", "12:00"], ["14:00", "18:30"]],
    4: [["08:30", "12:00"], ["14:00", "18:30"]],
    5: [["08:30", "12:00"], ["14:00", "18:00"]],
    6: [["09:00", "12:00"]],
    0: []
  },
  // Jours de fermeture exceptionnelle (AAAA-MM-JJ)
  fermetures: ["2026-12-25", "2027-01-01"],
  // Durée d'un créneau de rendez-vous, en minutes
  creneauMinutes: 60,

  // Forfaits affichés « à partir de », en euros TTC. Mettez null pour masquer un prix.
  forfaits: [
    { nom: "Révision vidange", detail: "Huile 5W30, filtre à huile, contrôle des niveaux", prix: 144 },
    { nom: "Révision complète", detail: "Huile, filtres à huile, air et habitacle, niveaux, pression des pneus", prix: 240 },
    { nom: "Géométrie", detail: "Contrôle et réglage du parallélisme", prix: 84 },
    { nom: "Diagnostic électronique", detail: "Lecture des codes défaut, offert si les travaux sont faits chez nous", prix: null }
  ]
};
