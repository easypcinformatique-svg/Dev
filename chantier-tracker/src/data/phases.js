// Phases et tâches du chantier 11 rue Pierre Loti, 13170 Les Pennes Mirabeau
// PC n°013 071 23 C0061 — SCI JGR — Parcelle AW 330 — R+1
// Démarrage prévu : 1er mai 2026

export const PHASES = [
  {
    id: 'phase0',
    name: 'Urgences immédiates',
    dates: '14-18 avril 2026',
    color: '#dc2626',
    tasks: [
      { id: 'p0t1', label: 'Souscrire Assurance Dommages-Ouvrage (DO)', deadline: '2026-04-18', legal: true, critical: true, note: 'Obligatoire AVANT ouverture chantier — Loi Spinetta art. L242-1. Contacter courtier BTP spécialisé.' },
      { id: 'p0t2', label: 'Demander attestation décennale à ELCR', deadline: '2026-04-18', critical: true, note: 'Nécessaire pour le dossier DO et avant signature contrat.' },
      { id: 'p0t3', label: 'DT — Déclaration de Travaux réseaux enterrés', deadline: '2026-04-14', legal: true, critical: true, note: 'Cerfa 14434*03 via reseaux-et-canalisations.ineris.fr — Délai 20 jours avant travaux.' },
      { id: 'p0t4', label: 'Signer le devis ELCR n°02303', deadline: '2026-05-10', critical: true, note: 'Expire le 10/05/2026 — 195 000€ TTC.' },
      { id: 'p0t5', label: 'Contacter la banque — préparer 1er déblocage', deadline: '2026-04-25', note: 'Acompte 10% = 19 500€ TTC à prévoir.' },
      { id: 'p0t6', label: 'Contacter courtier DO spécialisé BTP', deadline: '2026-04-15', critical: true, note: 'Délai normal 2-3 mois, courtier spécialisé 48-72h.' },
    ]
  },
  {
    id: 'phase1',
    name: 'Préparation chantier',
    dates: '19-30 avril 2026',
    color: '#ea580c',
    tasks: [
      { id: 'p1t1', label: 'DICT par ELCR (Cerfa 14434*03)', deadline: '2026-04-20', legal: true, note: 'Déclaration Intention Commencement Travaux — à faire par l\'artisan.' },
      { id: 'p1t2', label: 'Confirmer réception police DO', deadline: '2026-04-28', legal: true, critical: true, note: 'Sans DO = délit pénal (amende 75 000€ + 6 mois prison).' },
      { id: 'p1t3', label: 'Organiser transplantation des 7 arbres', deadline: '2026-04-25', note: 'Prévu au PC — obligation.' },
      { id: 'p1t4', label: 'Installation chantier (clôture, benne, sanitaires)', deadline: '2026-04-30', note: 'ELCR responsable.' },
      { id: 'p1t5', label: 'DOC — Déclaration Ouverture de Chantier (Cerfa 13407)', deadline: '2026-04-28', legal: true, critical: true, note: 'À déposer en mairie Les Pennes Mirabeau — J0 ou J-2.' },
      { id: 'p1t6', label: 'Afficher panneau PC sur chantier (visible voie publique)', deadline: '2026-04-28', legal: true, note: 'Obligatoire pendant toute la durée du chantier + 2 mois après.' },
      { id: 'p1t7', label: '1er déblocage bancaire prêt à virer (19 500€)', deadline: '2026-04-28', note: 'Acompte 10% du devis ELCR.' },
      { id: 'p1t8', label: 'Raccordement provisoire ENEDIS chantier', deadline: '2026-04-30', note: 'Électricité de chantier.' },
      { id: 'p1t9', label: 'Alimentation eau provisoire chantier', deadline: '2026-04-30', note: 'Service des eaux Les Pennes Mirabeau.' },
    ]
  },
  {
    id: 'phase2',
    name: 'Terrassement & Fondations',
    dates: 'Mai-Juin 2026',
    color: '#d97706',
    tasks: [
      { id: 'p2t1', label: 'Terrassement du terrain', deadline: '2026-05-15', note: 'Début effectif des travaux.' },
      { id: 'p2t2', label: 'Fouilles en rigole / en pleine masse', deadline: '2026-05-20' },
      { id: 'p2t3', label: 'Vérification cote plancher ≥ +50cm/TN', deadline: '2026-05-20', legal: true, note: 'Zone inondable modérée — prescription PPR obligatoire.' },
      { id: 'p2t4', label: 'Coulage fondations (semelles filantes)', deadline: '2026-05-30' },
      { id: 'p2t5', label: 'Soubassement / vide sanitaire', deadline: '2026-06-10' },
      { id: 'p2t6', label: 'Réseaux enterrés (EU, EP, AEP)', deadline: '2026-06-15', note: 'Eaux usées, eaux pluviales, adduction eau potable.' },
      { id: 'p2t7', label: 'Remblaiement et compactage', deadline: '2026-06-20' },
      { id: 'p2t8', label: 'Dallage / plancher bas sur vide sanitaire', deadline: '2026-06-30' },
    ]
  },
  {
    id: 'phase3',
    name: 'Gros œuvre — Maçonnerie',
    dates: 'Juillet-Octobre 2026',
    color: '#ca8a04',
    tasks: [
      { id: 'p3t1', label: 'Élévation murs RDC', deadline: '2026-07-15' },
      { id: 'p3t2', label: 'Linteaux et chaînages RDC', deadline: '2026-07-30' },
      { id: 'p3t3', label: 'Plancher intermédiaire (R+1)', deadline: '2026-08-15' },
      { id: 'p3t4', label: 'Élévation murs R+1', deadline: '2026-09-01' },
      { id: 'p3t5', label: 'Linteaux et chaînages R+1', deadline: '2026-09-15' },
      { id: 'p3t6', label: 'Appuis de fenêtre et seuils', deadline: '2026-09-20' },
      { id: 'p3t7', label: 'Déblocage bancaire — situation gros œuvre', deadline: '2026-09-30', note: 'Appel de fonds selon avancement.' },
    ]
  },
  {
    id: 'phase4',
    name: 'Hors d\'eau — Charpente & Couverture',
    dates: 'Octobre-Novembre 2026',
    color: '#65a30d',
    tasks: [
      { id: 'p4t1', label: 'Charpente (pose)', deadline: '2026-10-15' },
      { id: 'p4t2', label: 'Couverture / toiture (tuiles)', deadline: '2026-10-30' },
      { id: 'p4t3', label: 'Zinguerie, gouttières, descentes EP', deadline: '2026-11-05' },
      { id: 'p4t4', label: 'Étanchéité (si toiture terrasse)', deadline: '2026-11-10' },
      { id: 'p4t5', label: 'Constat HORS D\'EAU — jalon important', deadline: '2026-11-15', critical: true, note: 'Le bâtiment est protégé de la pluie. Déblocage bancaire possible.' },
    ]
  },
  {
    id: 'phase5',
    name: 'Hors d\'air — Menuiseries extérieures',
    dates: 'Novembre-Décembre 2026',
    color: '#16a34a',
    tasks: [
      { id: 'p5t1', label: 'Pose menuiseries extérieures (fenêtres, baies)', deadline: '2026-11-30' },
      { id: 'p5t2', label: 'Pose volets roulants', deadline: '2026-12-05' },
      { id: 'p5t3', label: 'Pose porte d\'entrée', deadline: '2026-12-10' },
      { id: 'p5t4', label: 'Pose porte de garage', deadline: '2026-12-10' },
      { id: 'p5t5', label: 'Constat HORS D\'AIR — jalon important', deadline: '2026-12-15', critical: true, note: 'Le bâtiment est clos. Déblocage bancaire possible.' },
    ]
  },
  {
    id: 'phase6',
    name: 'Second œuvre & Finitions',
    dates: 'Janvier-Juillet 2027',
    color: '#0891b2',
    tasks: [
      { id: 'p6t1', label: 'Électricité — passage gaines et câblage', deadline: '2027-01-30' },
      { id: 'p6t2', label: 'Plomberie — alimentation et évacuation', deadline: '2027-01-30' },
      { id: 'p6t3', label: 'Chauffage / climatisation', deadline: '2027-02-15' },
      { id: 'p6t4', label: 'VMC (ventilation mécanique contrôlée)', deadline: '2027-02-15' },
      { id: 'p6t5', label: 'Isolation intérieure (murs + combles)', deadline: '2027-02-28' },
      { id: 'p6t6', label: 'Plâtrerie / placo — cloisons et doublages', deadline: '2027-03-15' },
      { id: 'p6t7', label: 'Enduits extérieurs (façades)', deadline: '2027-03-30' },
      { id: 'p6t8', label: 'Chape', deadline: '2027-04-10' },
      { id: 'p6t9', label: 'Carrelage / revêtements de sol', deadline: '2027-04-30' },
      { id: 'p6t10', label: 'Faïence salle de bains', deadline: '2027-05-05' },
      { id: 'p6t11', label: 'Peinture intérieure', deadline: '2027-05-30', note: 'Lot non couvert par ELCR — artisan peintre à trouver.' },
      { id: 'p6t12', label: 'Pose sanitaires (WC, lavabos, douche/baignoire)', deadline: '2027-06-05' },
      { id: 'p6t13', label: 'Pose cuisine (meubles, plan de travail)', deadline: '2027-06-15' },
      { id: 'p6t14', label: 'Escalier intérieur', deadline: '2027-06-20' },
      { id: 'p6t15', label: 'Déblocage bancaire — situations second œuvre', deadline: '2027-06-30', note: 'Appels de fonds successifs.' },
    ]
  },
  {
    id: 'phase7',
    name: 'Pré-réception & Réception',
    dates: 'Août-Septembre 2027',
    color: '#2563eb',
    tasks: [
      { id: 'p7t1', label: 'Test perméabilité à l\'air RE2020 (≤ 0.60 m³/h/m²)', deadline: '2027-08-01', legal: true, note: 'Opérateur Qualibat 8711 — coût 250-400€.' },
      { id: 'p7t2', label: 'Contrôle ventilation VMC RE2020', deadline: '2027-08-01', legal: true, note: 'Obligatoire RE2020.' },
      { id: 'p7t3', label: 'Attestation RE2020 n°2 (fin travaux)', deadline: '2027-08-15', legal: true, note: 'À joindre à la DAACT — coût 300-500€.' },
      { id: 'p7t4', label: 'Consuel — attestation conformité électrique', deadline: '2027-08-15', legal: true, note: 'Cerfa 12506*03 (attestation jaune) — coût 120-200€. Sans elle, pas de raccordement ENEDIS.' },
      { id: 'p7t5', label: 'Aménagement extérieur (accès, terrasse)', deadline: '2027-08-30' },
      { id: 'p7t6', label: 'Nettoyage fin de chantier', deadline: '2027-09-01' },
      { id: 'p7t7', label: 'Pré-réception — visite avec ELCR', deadline: '2027-09-05', note: 'Lister toutes les réserves.' },
      { id: 'p7t8', label: 'PV de réception contradictoire signé', deadline: '2027-09-15', critical: true, note: 'Date de départ de toutes les garanties (GPA, biennale, décennale).' },
      { id: 'p7t9', label: 'Paiement solde 5% ELCR (8 775€ TTC)', deadline: '2027-09-15', note: 'Après PV signé sans réserves, ou consignation si réserves.' },
    ]
  },
  {
    id: 'phase8',
    name: 'Post-réception — Démarches légales',
    dates: 'Septembre-Décembre 2027',
    color: '#7c3aed',
    tasks: [
      { id: 'p8t1', label: 'DAACT en mairie (Cerfa 13408)', deadline: '2027-10-15', legal: true, critical: true, note: 'Dans les 30 jours après achèvement + joindre attestation RE2020 n°2.' },
      { id: 'p8t2', label: 'Déclaration H1 aux impôts (Cerfa 10867)', deadline: '2027-12-15', legal: true, critical: true, note: 'Dans les 90 jours après achèvement — sinon perte exonération taxe foncière 2 ans.' },
      { id: 'p8t3', label: 'Raccordement ENEDIS définitif', deadline: '2027-10-30', note: 'Après obtention Consuel.' },
      { id: 'p8t4', label: 'Raccordement eau définitif', deadline: '2027-10-30' },
      { id: 'p8t5', label: 'Retirer panneau PC (2 mois après achèvement)', deadline: '2027-11-15' },
      { id: 'p8t6', label: 'Attestation non-contestation conformité (mairie)', deadline: '2027-12-30', note: 'La mairie a 3 mois après réception DAACT pour contrôler.' },
    ]
  },
  {
    id: 'phase9',
    name: 'Garanties — Suivi long terme',
    dates: '2027-2037',
    color: '#6b7280',
    tasks: [
      { id: 'p9t1', label: 'Garantie Parfait Achèvement (GPA) — 1 an', deadline: '2028-09-15', note: 'Signaler tout désordre par LRAR à ELCR avant expiration.' },
      { id: 'p9t2', label: 'Garantie biennale (équipements) — 2 ans', deadline: '2029-09-15', note: 'LRAR à assureur décennale ELCR.' },
      { id: 'p9t3', label: 'Garantie décennale — 10 ans', deadline: '2037-09-15', note: 'Couverte par assurance décennale ELCR.' },
      { id: 'p9t4', label: 'Dommages-Ouvrage — 10 ans (à partir de 1 an post-réception)', deadline: '2038-09-15', note: 'Votre assurance DO prend le relais après la GPA.' },
    ]
  }
]
