// Utilitaires partagés pour l'upload et le traitement des documents

import { saveDocument, getAllDocuments, fileToBase64 } from '../hooks/useDocuments.js'
import { DOC_TASK_MAP, getAutoCheckFromFilename } from '../data/docTaskMap.js'
import { guessCategory } from '../data/guessCategory.js'

/**
 * Crée un document à partir d'un fichier uploadé
 */
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
 * Traite un ensemble de fichiers : sauvegarde, catégorisation, et auto-coche
 * @returns {string[]} Liste des IDs auto-cochés
 */
export async function processUploadedFiles(files, { completedTasks, completedLegal, toggleTask, toggleLegal }) {
  const checked = []
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
      if (!completedTasks?.[id]) { toggleTask(id); checked.push(id) }
    })
    legalToCheck.forEach(id => {
      if (!completedLegal?.[id]) { toggleLegal(id); checked.push(id) }
    })
  }
  return checked
}

const AUTO_CHECK_TIMEOUT = 5000

export { AUTO_CHECK_TIMEOUT }
