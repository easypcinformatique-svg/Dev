// IndexedDB storage for documents (files too large for localStorage)
const DB_NAME = 'chantier_docs'
const DB_VERSION = 1
const STORE_NAME = 'documents'

let dbInstance = null

function openDB() {
  if (dbInstance) return Promise.resolve(dbInstance)
  return new Promise((resolve, reject) => {
    try {
      const request = indexedDB.open(DB_NAME, DB_VERSION)
      request.onupgradeneeded = (e) => {
        const db = e.target.result
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
          store.createIndex('category', 'category', { unique: false })
          store.createIndex('artisanId', 'artisanId', { unique: false })
        }
      }
      request.onsuccess = () => {
        dbInstance = request.result
        dbInstance.onclose = () => { dbInstance = null }
        resolve(dbInstance)
      }
      request.onerror = () => reject(request.error)
    } catch (err) {
      reject(new Error('IndexedDB non disponible. Mode prive ou stockage plein.'))
    }
  })
}

export async function saveDocument(doc) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).put(doc)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function getAllDocuments() {
  try {
    const db = await openDB()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const request = tx.objectStore(STORE_NAME).getAll()
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  } catch {
    return []
  }
}

export async function deleteDocument(id) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).delete(id)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

export const DOC_CATEGORIES = [
  { id: 'decennale', label: 'Decennale' },
  { id: 'devis', label: 'Devis' },
  { id: 'contrat', label: 'Contrat' },
  { id: 'facture', label: 'Facture / Situation' },
  { id: 'attestation', label: 'Attestation' },
  { id: 'assurance', label: 'Assurance (DO, RC...)' },
  { id: 'administratif', label: 'Administratif (PC, DOC, DAACT...)' },
  { id: 'plan', label: 'Plan / Etude' },
  { id: 'photo', label: 'Photo chantier' },
  { id: 'autre', label: 'Autre' },
]
