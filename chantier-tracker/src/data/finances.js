// Données financières — Devis ELCR n°02303
// Total : 162 500€ HT / 195 000€ TTC (TVA 20%)
// Échéancier : 10% acompte / 85% situations / 5% solde réception

export const LOTS = [
  { id: 'lot1', name: 'Terrassement — VRD', ht: 18500, artisan: 'ELCR' },
  { id: 'lot2', name: 'Gros œuvre — Maçonnerie', ht: 45000, artisan: 'ELCR' },
  { id: 'lot3', name: 'Charpente — Couverture', ht: 22000, artisan: 'ELCR' },
  { id: 'lot4', name: 'Menuiseries extérieures', ht: 15000, artisan: 'ELCR' },
  { id: 'lot5', name: 'Plomberie — Sanitaire', ht: 14000, artisan: 'ELCR' },
  { id: 'lot6', name: 'Électricité', ht: 12000, artisan: 'ELCR' },
  { id: 'lot7', name: 'Plâtrerie — Isolation', ht: 16000, artisan: 'ELCR' },
  { id: 'lot8', name: 'Carrelage — Revêtements', ht: 11000, artisan: 'ELCR' },
  { id: 'lot9', name: 'Enduits extérieurs', ht: 9000, artisan: 'ELCR' },
  { id: 'lot10', name: 'Peinture intérieure', ht: 0, artisan: 'À trouver', missing: true },
]

export const TVA_RATE = 0.20
export const TOTAL_HT = 162500
export const TOTAL_TTC = 195000

// Échéancier de paiement ELCR
export const ECHEANCIER = {
  acompte: { pct: 10, label: 'Acompte signature', montant: 19500 },
  situations: { pct: 85, label: 'Situations d\'avancement', montant: 165750 },
  solde: { pct: 5, label: 'Solde à réception', montant: 9750 },
}

// Structure financement
export const FINANCEMENT = {
  pret: { label: 'Prêt bancaire', montant: 0, note: 'Montant à renseigner' },
  apport: { label: 'Fonds propres', montant: 0, note: 'Montant à renseigner' },
}
