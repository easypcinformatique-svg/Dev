// Utilitaires partagés pour l'upload et le traitement des documents

import { saveDocument, fileToBase64 } from '../hooks/useDocuments.js'
import { DOC_TASK_MAP, getAutoCheckFromFilename } from '../data/docTaskMap.js'
import { guessCategory } from '../data/guessCategory.js'

export function createDocFromFile(file, data, category, extra = {}) {
  return {
    id: Date.now() + '_' + Math.random().toString(36).slice(2, 8),
    name: file.name,
    size: file.size,
    type: file.type,
    data,
    category,
    artisanId: '',
    date: new Date().toISOString(),
    note: '',
    ...extra,
  }
}

/**
 * Traite un ensemble de fichiers : sauvegarde, catégorisation, et auto-coche.
 * Garde un Set local des IDs déjà cochés dans ce batch pour éviter les double-toggles.
 */
export async function processUploadedFiles(files, { completedTasks, completedLegal, toggleTask, toggleLegal }) {
  const checked = []
  const alreadyToggled = new Set(Object.keys(completedTasks || {}))
  const alreadyToggledLegal = new Set(Object.keys(completedLegal || {}))

  for (const file of files) {
    const data = await fileToBase64(file)
    const category = guessCategory(file.name)
    const doc = createDocFromFile(file, data, category)
    await saveDocument(doc)

    const byFilename = getAutoCheckFromFilename(file.name)
    const byCategory = DOC_TASK_MAP[category] || { tasks: [], legal: [] }
    const tasksToCheck = [...new Set([...byFilename.tasks, ...byCategory.tasks])]
    const legalToCheck = [...new Set([...byFilename.legal, ...byCategory.legal])]

    tasksToCheck.forEach(id => {
      if (!alreadyToggled.has(id)) {
        toggleTask(id)
        alreadyToggled.add(id)
        checked.push(id)
      }
    })
    legalToCheck.forEach(id => {
      if (!alreadyToggledLegal.has(id)) {
        toggleLegal(id)
        alreadyToggledLegal.add(id)
        checked.push(id)
      }
    })
  }
  return checked
}

export const AUTO_CHECK_TIMEOUT = 5000
