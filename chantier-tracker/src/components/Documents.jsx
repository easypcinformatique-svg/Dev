import { useState, useEffect, useCallback } from 'react'
import {
  saveDocument, getAllDocuments, deleteDocument,
  fileToBase64, DOC_CATEGORIES
} from '../hooks/useDocuments.js'
import { ARTISANS } from '../data/artisans.js'
import { DOC_TASK_MAP, getAutoCheckFromFilename } from '../data/docTaskMap.js'
import { guessCategory } from '../data/guessCategory.js'

export default function Documents({ toggleTask, toggleLegal, completedTasks, completedLegal }) {
  const [docs, setDocs] = useState([])
  const [dragging, setDragging] = useState(false)
  const [filter, setFilter] = useState('all')
  const [uploading, setUploading] = useState(false)
  const [preview, setPreview] = useState(null)

  useEffect(() => {
    getAllDocuments().then(setDocs)
  }, [])

  const [autoChecked, setAutoChecked] = useState([])

  const handleFiles = useCallback(async (files) => {
    setUploading(true)
    const checked = []
    for (const file of files) {
      const data = await fileToBase64(file)
      const category = guessCategory(file.name)
      const doc = {
        id: Date.now() + '_' + Math.random().toString(36).slice(2, 8),
        name: file.name,
        size: file.size,
        type: file.type,
        data,
        category,
        artisanId: '',
        date: new Date().toISOString(),
        note: '',
      }
      await saveDocument(doc)

      // Auto-cocher les taches liees
      const byFilename = getAutoCheckFromFilename(file.name)
      const byCategory = DOC_TASK_MAP[category] || { tasks: [], legal: [] }
      const tasksToCheck = [...new Set([...byFilename.tasks, ...byCategory.tasks])]
      const legalToCheck = [...new Set([...byFilename.legal, ...byCategory.legal])]

      tasksToCheck.forEach(taskId => {
        if (!completedTasks?.[taskId]) {
          toggleTask(taskId)
          checked.push(taskId)
        }
      })
      legalToCheck.forEach(legalId => {
        if (!completedLegal?.[legalId]) {
          toggleLegal(legalId)
          checked.push(legalId)
        }
      })
    }
    const updated = await getAllDocuments()
    setDocs(updated)
    setUploading(false)
    if (checked.length > 0) {
      setAutoChecked(checked)
      setTimeout(() => setAutoChecked([]), 5000)
    }
  }, [toggleTask, toggleLegal, completedTasks, completedLegal])

  // guessCategory imported from ../data/guessCategory.js

  function onDragOver(e) { e.preventDefault(); setDragging(true) }
  function onDragLeave(e) { e.preventDefault(); setDragging(false) }
  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files.length) handleFiles([...e.dataTransfer.files])
  }
  function onFileInput(e) {
    if (e.target.files.length) handleFiles([...e.target.files])
    e.target.value = ''
  }

  async function handleDelete(id) {
    await deleteDocument(id)
    setDocs(prev => prev.filter(d => d.id !== id))
    if (preview?.id === id) setPreview(null)
  }

  async function updateDoc(id, field, value) {
    const doc = docs.find(d => d.id === id)
    if (!doc) return
    const updated = { ...doc, [field]: value }
    await saveDocument(updated)
    setDocs(prev => prev.map(d => d.id === id ? updated : d))
  }

  const filtered = filter === 'all' ? docs : docs.filter(d => d.category === filter)
  const sorted = [...filtered].sort((a, b) => new Date(b.date) - new Date(a.date))

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' o'
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + ' Ko'
    return (bytes / (1024 * 1024)).toFixed(1) + ' Mo'
  }

  function formatDate(iso) {
    return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
  }

  function fileIcon(type) {
    if (type?.startsWith('image/')) return '\u{1F5BC}'
    if (type?.includes('pdf')) return '\u{1F4C4}'
    return '\u{1F4CE}'
  }

  return (
    <div className="documents">
      {/* Zone de drop */}
      <div
        className={`drop-zone ${dragging ? 'drop-active' : ''} ${uploading ? 'drop-uploading' : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => document.getElementById('file-input').click()}
      >
        <input
          id="file-input"
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.heic,.webp,.doc,.docx,.xls,.xlsx"
          onChange={onFileInput}
          style={{ display: 'none' }}
        />
        {uploading ? (
          <div className="drop-text">Enregistrement en cours...</div>
        ) : (
          <>
            <div className="drop-icon">{'\u{1F4E5}'}</div>
            <div className="drop-text">Glissez vos documents ici</div>
            <div className="drop-hint">Decennale, devis, factures, attestations, photos...</div>
            <div className="drop-hint">ou cliquez pour parcourir</div>
          </>
        )}
      </div>

      {/* Notification auto-coche */}
      {autoChecked.length > 0 && (
        <div className="auto-check-banner">
          {'\u2705'} {autoChecked.length} tache(s) / obligation(s) cochee(s) automatiquement
        </div>
      )}

      {/* Filtres */}
      <div className="filter-bar">
        <button
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          Tous ({docs.length})
        </button>
        {DOC_CATEGORIES.map(cat => {
          const count = docs.filter(d => d.category === cat.id).length
          if (count === 0) return null
          return (
            <button
              key={cat.id}
              className={`filter-btn ${filter === cat.id ? 'active' : ''}`}
              onClick={() => setFilter(cat.id)}
            >
              {cat.label} ({count})
            </button>
          )
        })}
      </div>

      {/* Liste des documents */}
      {sorted.length === 0 ? (
        <div className="empty-state">
          {filter === 'all'
            ? 'Aucun document. Glissez vos fichiers ci-dessus pour commencer.'
            : 'Aucun document dans cette categorie.'}
        </div>
      ) : (
        <div className="doc-list">
          {sorted.map(doc => (
            <div key={doc.id} className="doc-card">
              <div className="doc-header" onClick={() => setPreview(preview?.id === doc.id ? null : doc)}>
                <span className="doc-icon">{fileIcon(doc.type)}</span>
                <div className="doc-info">
                  <div className="doc-name">{doc.name}</div>
                  <div className="doc-meta">{formatSize(doc.size)} — {formatDate(doc.date)}</div>
                </div>
                <button className="doc-download" onClick={(e) => {
                  e.stopPropagation()
                  const a = document.createElement('a')
                  a.href = doc.data
                  a.download = doc.name
                  a.click()
                }} title="Telecharger">
                  {'\u{2B07}'}
                </button>
                <button className="note-delete" onClick={(e) => {
                  e.stopPropagation()
                  handleDelete(doc.id)
                }} title="Supprimer">
                  {'\u2715'}
                </button>
              </div>

              {preview?.id === doc.id && (
                <div className="doc-details">
                  <div className="doc-detail-row">
                    <label>Categorie</label>
                    <select
                      value={doc.category}
                      onChange={e => updateDoc(doc.id, 'category', e.target.value)}
                    >
                      {DOC_CATEGORIES.map(cat => (
                        <option key={cat.id} value={cat.id}>{cat.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="doc-detail-row">
                    <label>Artisan lie</label>
                    <select
                      value={doc.artisanId}
                      onChange={e => updateDoc(doc.id, 'artisanId', e.target.value)}
                    >
                      <option value="">— Aucun —</option>
                      {ARTISANS.map(a => (
                        <option key={a.id} value={a.id}>{a.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="doc-detail-row">
                    <label>Note</label>
                    <input
                      type="text"
                      value={doc.note}
                      onChange={e => updateDoc(doc.id, 'note', e.target.value)}
                      placeholder="Note optionnelle..."
                    />
                  </div>
                  {doc.type?.startsWith('image/') && (
                    <div className="doc-preview-img">
                      <img src={doc.data} alt={doc.name} />
                    </div>
                  )}
                  {doc.type?.includes('pdf') && (
                    <div className="doc-preview-pdf">
                      <a href={doc.data} target="_blank" rel="noopener noreferrer" className="btn-primary">
                        Ouvrir le PDF
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
