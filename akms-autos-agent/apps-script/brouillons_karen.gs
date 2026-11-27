/**
 * Crée dans la boîte Gmail d'AMKS AUTOS (amks.autos2308@gmail.com) les brouillons
 * à envoyer par Karen. À coller dans un projet Apps Script ouvert AVEC LE COMPTE AMKS,
 * puis exécuter la fonction creerBrouillons. Rien n'est envoyé : les brouillons
 * apparaissent dans Gmail > Brouillons, à relire puis envoyer.
 */

const SIGNATURE = '\n\nBien cordialement,\n\nKaren NIKOGHOSSIAN\nGérant – SARL AMKS AUTOS\n115 boulevard de la Millière, 13011 Marseille\nSIREN 930 691 431';
const COPIE = 'robert.manossian@gmail.com';

function creerBrouillons() {
  // 1. Alliance Automotive : relevé de compte + 17 factures manquantes
  GmailApp.createDraft(
    'facturation_demat@allianceautomotive.fr',
    'AMKS AUTOS – clients n° 70715073 et 70402625 : relevé de compte et duplicatas de factures',
    'Bonjour,\n\n'
    + 'Je suis le gérant de la SARL AMKS AUTOS (SIREN 930 691 431, TVA FR18930691431), 115 boulevard de la Millière, 13011 Marseille, votre client sous les numéros 70715073 et 70402625.\n\n'
    + 'Mon cabinet comptable reprend la comptabilité de la société depuis sa création. Pourriez-vous m\'envoyer :\n\n'
    + '1. Le relevé de compte complet de mes deux numéros de client, du 1er juillet 2024 à aujourd\'hui (factures, avoirs et règlements), en Excel si possible.\n\n'
    + '2. Les duplicatas PDF des factures correspondant à ces 17 prélèvements LCR, que je ne retrouve pas :\n'
    + '- 04/03/2025 : LCR 981083, 967,44 €\n'
    + '- 01/04/2025 : LCR 009776, 504,00 €\n'
    + '- 30/05/2025 : LCR 074734, 202,28 €\n'
    + '- 01/07/2025 : LCR 108855, 1 965,49 €\n'
    + '- 02/08/2025 : LCR 158006, 838,08 €\n'
    + '- 02/09/2025 : LCR 183051, 4 730,24 €\n'
    + '- 18/02/2026 : LCR 369230, 808,32 €\n'
    + '- 28/02/2026 : LCR 384610, 102,00 €\n'
    + '- 03/03/2026 : LCR 380919, 4 220,41 €\n'
    + '- 03/03/2026 : LCR 390256, 356,21 €\n'
    + '- 03/03/2026 : LCR 390288, 28,80 €\n'
    + '- 02/05/2026 : LCR 445314, 1 843,43 €\n'
    + '- 03/07/2026 : LCR 528563, 1 084,13 €\n'
    + '- 20/10/2026 : LCR 641777, 58,94 €\n'
    + '- 22/10/2026 : LCR 644020, 255,42 €\n'
    + '- 23/10/2026 : LCR 643851, 700,08 €\n'
    + '- 23/10/2026 : LCR 644529, 47,16 €\n'
    + 'Total : 18 712,43 €\n\n'
    + '3. Si certaines factures ont été faites au nom de mon ancienne société KAMS (SIRET 889 079 927) pour des achats d\'AMKS AUTOS, merci de me le signaler et, si possible, de me les renvoyer au nom d\'AMKS AUTOS.\n\n'
    + 'Merci de me répondre à cette adresse, en PDF ou Excel.'
    + SIGNATURE,
    { cc: 'callcenter@allianceautomotive.fr,' + COPIE, name: 'AMKS AUTOS – Karen NIKOGHOSSIAN' }
  );

  // 2. Bailleur Millière Invest (gestionnaire SPORT IMMO) : relevé de compte locataire
  GmailApp.createDraft(
    'ncourtais@sportimmo.com',
    'SARL AMKS AUTOS – réf. client 000043 / 01000041 : relevé de compte locataire',
    'Bonjour Madame COURTAIS,\n\n'
    + 'Merci pour l\'envoi des factures de loyer de 2025 et 2026 (FA 2500041 à FA 2600142) pour les locaux La Millière, lot F1 et terrain, 115 boulevard de la Millière (références client 000043 / 01000041).\n\n'
    + 'Mon cabinet comptable reprend la comptabilité de la société depuis sa création. Pourriez-vous m\'envoyer :\n\n'
    + '1. Le relevé de compte locataire complet depuis l\'entrée dans les lieux (juin 2024) jusqu\'à aujourd\'hui, avec les factures, avoirs, règlements et le solde.\n\n'
    + '2. Les factures de loyer de juillet à décembre 2024 : je n\'ai que la facture 2400083 (loyer du 14 au 30 juin 2024) et l\'appel du dépôt de garantie L2400082.\n\n'
    + 'Le relevé me permettra aussi de comprendre trois prélèvements plus élevés que la facture du mois :\n'
    + '- 04/02/2025 : 9 823,71 € prélevés pour un loyer de janvier 2025 de 3 485,15 € (écart 6 338,56 €) ;\n'
    + '- 10/04/2025 : 4 493,40 € prélevés pour une facture d\'avril 2025 de 3 506,64 € (écart 986,76 €) ;\n'
    + '- 10/07/2025 : 3 834,17 € prélevés pour une facture de juillet 2025 de 3 632,21 € (écart 201,96 €).\n'
    + 'Si ces écarts correspondent à des factures ou à des compléments de dépôt de garantie, merci de m\'en envoyer une copie.\n\n'
    + 'Merci de me répondre à cette adresse, en PDF.'
    + SIGNATURE,
    { cc: 'jtorlai@sportimmo.com,' + COPIE, name: 'AMKS AUTOS – Karen NIKOGHOSSIAN' }
  );

  console.log('2 brouillons créés dans Gmail > Brouillons : à relire puis envoyer.');
}
