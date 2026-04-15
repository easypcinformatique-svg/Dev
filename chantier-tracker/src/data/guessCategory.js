// Detection intelligente de la categorie d'un document par son nom de fichier
// Ordre de priorite : du plus specifique au plus generique

export function guessCategory(name) {
  const lower = name.toLowerCase()

  // 1. Decennale — "attestation assurance" d'un artisan = decennale
  if (lower.includes('decennale') || lower.includes('décennale')
    || lower.includes('rc decennale') || lower.includes('rc pro')
    || lower.includes('responsabilit')) return 'decennale'

  // 2. Attestation assurance d'artisan (pas DO) = probablement decennale
  if ((lower.includes('attestation') && lower.includes('assurance'))
    || lower.includes('orus') || lower.includes('smabtp')
    || lower.includes('maaf pro') || lower.includes('axa pro')) return 'decennale'

  // 3. Dommages-ouvrage specifiquement
  if (lower.includes('dommage') || lower.includes('dommages-ouvrage')
    || lower.includes('dommages ouvrage')) return 'assurance'

  // 4. Devis
  if (lower.includes('devis') || lower.includes('02303')) return 'devis'

  // 5. Facture / situation
  if (lower.includes('facture') || lower.includes('situation')) return 'facture'

  // 6. Administratif (avant contrat generique)
  if (lower.includes('permis') || lower.includes('daact') || lower.includes('cerfa')
    || lower.includes('13407') || lower.includes('13408') || lower.includes('10867')
    || lower.includes('ouverture de chantier')) return 'administratif'

  // 7. Consuel / RE2020
  if (lower.includes('consuel') || lower.includes('12506')
    || lower.includes('re2020') || lower.includes('re 2020')
    || lower.includes('permeabilite') || lower.includes('perméabilité')) return 'attestation'

  // 8. Contrat (apres les cas specifiques)
  if (lower.includes('contrat') && !lower.includes('assurance')) return 'contrat'

  // 9. Attestation generique
  if (lower.includes('attestation')) return 'attestation'

  // 10. Assurance generique
  if (lower.includes('assurance')) return 'assurance'

  // 11. Plan / etude
  if (lower.includes('plan') || lower.includes('etude') || lower.includes('étude')) return 'plan'

  // 12. Photo
  if (lower.match(/\.(jpg|jpeg|png|heic|webp)$/)) return 'photo'

  return 'autre'
}
