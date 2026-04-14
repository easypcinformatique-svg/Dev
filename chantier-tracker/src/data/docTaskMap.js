// Quand un document de ce type est uploade pour cet artisan,
// les taches et obligations correspondantes sont auto-cochees

export const DOC_TASK_MAP = {
  // Upload decennale d'un artisan → coche la demande + l'obligation legale
  decennale: {
    tasks: ['p0t2'],           // "Demander attestation décennale à ELCR"
    legal: ['leg2'],           // "Attestations décennales de tous les artisans"
  },
  // Upload devis signe → coche signature devis
  devis: {
    tasks: ['p0t4'],           // "Signer le devis ELCR n°02303"
    legal: [],
  },
  // Upload police DO → coche la souscription + confirmation + obligation
  assurance: {
    tasks: ['p0t1', 'p0t6', 'p1t2'],  // "Souscrire DO", "Contacter courtier", "Confirmer réception DO"
    legal: ['leg1'],           // "Assurance Dommages-Ouvrage"
  },
  // Upload Consuel → coche l'obligation
  attestation: {
    tasks: ['p7t4'],           // "Consuel — attestation conformité électrique"
    legal: ['leg12'],          // "Consuel — Conformité électrique"
  },
  // Upload contrat → pas de tache specifique
  contrat: {
    tasks: [],
    legal: [],
  },
  // Upload facture/situation → pas de tache specifique
  facture: {
    tasks: [],
    legal: [],
  },
  // Upload document administratif (DOC, DAACT, etc.)
  administratif: {
    tasks: [],
    legal: [],
  },
  // Plans
  plan: {
    tasks: [],
    legal: [],
  },
  // Photos
  photo: {
    tasks: [],
    legal: [],
  },
  autre: {
    tasks: [],
    legal: [],
  },
}

// Mapping specifique par nom de fichier (plus precis)
export function getAutoCheckFromFilename(filename) {
  const lower = filename.toLowerCase()
  const result = { tasks: [], legal: [] }

  // Decennale — reconnu aussi comme "attestation assurance" d'un artisan
  if (lower.includes('decennale') || lower.includes('décennale') || lower.includes('rc decennale')
    || lower.includes('attestation assurance') || lower.includes('attestation d\'assurance')
    || lower.includes('responsabilit') || lower.includes('rc pro')
    || lower.includes('orus') || lower.includes('smabtp') || lower.includes('maaf')
    || lower.includes('axa pro') || lower.includes('allianz pro')) {
    result.tasks.push('p0t2')
    result.legal.push('leg2')
  }

  // Dommages-Ouvrage (DO specifiquement, pas une decennale artisan)
  if (lower.includes('dommage') || lower.includes('dommages-ouvrage') || lower.includes('dommages ouvrage')
    || lower.includes('_do_') || (lower.includes('do ') && !lower.includes('doc '))) {
    result.tasks.push('p0t1', 'p0t6', 'p1t2')
    result.legal.push('leg1')
  }

  // Devis ELCR
  if (lower.includes('devis') || lower.includes('02303')) {
    result.tasks.push('p0t4')
  }

  // DOC
  if (lower.includes('ouverture') || lower.includes('doc ') || lower.includes('13407')) {
    result.tasks.push('p1t5')
    result.legal.push('leg4')
  }

  // DAACT
  if (lower.includes('daact') || lower.includes('achevement') || lower.includes('achèvement') || lower.includes('13408')) {
    result.tasks.push('p8t1')
    result.legal.push('leg13')
  }

  // Consuel
  if (lower.includes('consuel') || lower.includes('12506')) {
    result.tasks.push('p7t4')
    result.legal.push('leg12')
  }

  // RE2020 attestation
  if (lower.includes('re2020') || lower.includes('re 2020') || lower.includes('permeabilite') || lower.includes('perméabilité')) {
    result.tasks.push('p7t1', 'p7t3')
    result.legal.push('leg9', 'leg11')
  }

  // H1 impots
  if (lower.includes('h1') || lower.includes('10867') || lower.includes('fonciere') || lower.includes('foncière')) {
    result.tasks.push('p8t2')
    result.legal.push('leg14')
  }

  // DT / DICT
  if (lower.includes('dict') || lower.includes(' dt ') || lower.includes('14434')) {
    result.tasks.push('p0t3', 'p1t1')
    result.legal.push('leg3')
  }

  return result
}
