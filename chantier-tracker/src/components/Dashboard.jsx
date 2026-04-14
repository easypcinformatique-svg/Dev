import { useState, useEffect, useCallback } from 'react'
import { PHASES } from '../data/phases.js'
import { OBLIGATIONS } from '../data/legal.js'
import { TOTAL_TTC } from '../data/finances.js'
import { exportZip } from '../hooks/useExport.js'
import { saveDocument, getAllDocuments, fileToBase64, DOC_CATEGORIES } from '../hooks/useDocuments.js'
import { DOC_TASK_MAP, getAutoCheckFromFilename } from '../data/docTaskMap.js'
import { guessCategory } from '../data/guessCategory.js'
import { ARTISANS } from '../data/artisans.js'

function daysUntil(dateStr) {
  const target = new Date(dateStr + 'T00:00:00')
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  return Math.ceil((target - now) / (1000 * 60 * 60 * 24))
}

function formatDate(dateStr) {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('fr-FR', {
    day: 'numeric', month: 'long', year: 'numeric'
  })
}

export default function Dashboard({ state, toggleTask, toggleLegal }) {
  const [exporting, setExporting] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [autoChecked, setAutoChecked] = useState([])
  const [recentDocs, setRecentDocs] = useState([])

  useEffect(() => {
    getAllDocuments().then(docs => {
      setRecentDocs(docs.sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 5))
    })
  }, [uploading])

  // guessCategory imported from ../data/guessCategory.js
  const handleFiles = useCallback(async (files) => {
    setUploading(true)
    const checked = []
    for (const file of files) {
      const data = await fileToBase64(file)
      const category = guessCategory(file.name)
      const doc = {
        id: Date.now() + '_' + Math.random().toString(36).slice(2, 8),
        name: file.name, size: file.size, type: file.type, data, category,
        artisanId: '', date: new Date().toISOString(), note: '',
      }
      await saveDocument(doc)
      const byFilename = getAutoCheckFromFilename(file.name)
      const byCategory = DOC_TASK_MAP[category] || { tasks: [], legal: [] }
      const tasksToCheck = [...new Set([...byFilename.tasks, ...byCategory.tasks])]
      const legalToCheck = [...new Set([...byFilename.legal, ...byCategory.legal])]
      tasksToCheck.forEach(id => { if (!state.completedTasks?.[id]) { toggleTask(id); checked.push(id) } })
      legalToCheck.forEach(id => { if (!state.completedLegal?.[id]) { toggleLegal(id); checked.push(id) } })
    }
    setUploading(false)
    if (checked.length > 0) {
      setAutoChecked(checked)
      setTimeout(() => setAutoChecked([]), 5000)
    }
  }, [state.completedTasks, state.completedLegal, toggleTask, toggleLegal])

  async function handleExport() {
    setExporting(true)
    try { await exportZip(state) } catch (e) { console.error('Export error:', e) }
    setExporting(false)
  }

  function onDragOver(e) { e.preventDefault(); setDragging(true) }
  function onDragLeave(e) { e.preventDefault(); setDragging(false) }
  function onDrop(e) { e.preventDefault(); setDragging(false); if (e.dataTransfer.files.length) handleFiles([...e.dataTransfer.files]) }
  function onFileInput(e) { if (e.target.files.length) handleFiles([...e.target.files]); e.target.value = '' }

  const allTasks = PHASES.flatMap(p => p.tasks)
  const totalTasks = allTasks.length
  const completedCount = Object.keys(state.completedTasks).length
  const pctTasks = totalTasks > 0 ? Math.round((completedCount / totalTasks) * 100) : 0

  const totalLegal = OBLIGATIONS.length
  const completedLegal = Object.keys(state.completedLegal).length
  const pctLegal = totalLegal > 0 ? Math.round((completedLegal / totalLegal) * 100) : 0

  // Alertes : tâches critiques non faites avec deadline proche
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const alerts = []

  // Alertes tâches critiques
  allTasks.forEach(t => {
    if (state.completedTasks[t.id]) return
    if (!t.deadline) return
    const days = daysUntil(t.deadline)
    if (days <= 30) {
      alerts.push({
        id: t.id,
        label: t.label,
        deadline: t.deadline,
        days,
        critical: t.critical,
        type: 'task',
        note: t.note,
      })
    }
  })

  // Alertes obligations légales
  OBLIGATIONS.forEach(o => {
    if (state.completedLegal[o.id]) return
    const days = daysUntil(o.deadline)
    if (days <= 60) {
      alerts.push({
        id: o.id,
        label: o.label,
        deadline: o.deadline,
        days,
        critical: o.critical,
        type: 'legal',
        note: o.detail,
      })
    }
  })

  alerts.sort((a, b) => a.days - b.days)

  function alertClass(days, critical) {
    if (days < 0) return 'alert-overdue'
    if (days <= 3 || critical) return 'alert-critical'
    if (days <= 14) return 'alert-warning'
    return 'alert-info'
  }

  function alertIcon(days) {
    if (days < 0) return '!!'
    if (days <= 3) return '!'
    if (days <= 14) return '~'
    return 'i'
  }

  // Avancement par phase
  const phaseProgress = PHASES.map(phase => {
    const done = phase.tasks.filter(t => state.completedTasks[t.id]).length
    const total = phase.tasks.length
    return { ...phase, done, total, pct: total > 0 ? Math.round((done / total) * 100) : 0 }
  })

  // Prochain jalon
  const nextMilestone = allTasks
    .filter(t => t.critical && !state.completedTasks[t.id] && t.deadline)
    .sort((a, b) => new Date(a.deadline) - new Date(b.deadline))[0]

  return (
    <div className="dashboard">
      {/* Zone d'upload */}
      <div
        className={`drop-zone drop-zone-dashboard ${dragging ? 'drop-active' : ''} ${uploading ? 'drop-uploading' : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => document.getElementById('dash-file-input').click()}
      >
        <input id="dash-file-input" type="file" multiple
          accept=".pdf,.jpg,.jpeg,.png,.heic,.webp,.doc,.docx,.xls,.xlsx"
          onChange={onFileInput} style={{ display: 'none' }} />
        {uploading ? (
          <div className="drop-text">Enregistrement...</div>
        ) : (
          <>
            <div className="drop-icon">{'\u{1F4E5}'}</div>
            <div className="drop-text">Glissez vos documents ici</div>
            <div className="drop-hint">Decennale, devis, DO, Consuel... → coche automatiquement les taches</div>
          </>
        )}
      </div>

      {autoChecked.length > 0 && (
        <div className="auto-check-banner">
          {'\u2705'} {autoChecked.length} tache(s) / obligation(s) cochee(s) automatiquement
        </div>
      )}

      {recentDocs.length > 0 && (
        <div className="recent-docs">
          <div className="recent-docs-title">Derniers documents</div>
          {recentDocs.map(d => (
            <div key={d.id} className="recent-doc-item">
              <span className="recent-doc-icon">{d.type?.includes('pdf') ? '\u{1F4C4}' : d.type?.startsWith('image/') ? '\u{1F5BC}' : '\u{1F4CE}'}</span>
              <span className="recent-doc-name">{d.name}</span>
              <span className="recent-doc-cat">{DOC_CATEGORIES.find(c => c.id === d.category)?.label}</span>
            </div>
          ))}
        </div>
      )}

      <div className="dashboard-actions">
        <button className="btn-export" onClick={handleExport} disabled={exporting}>
          {exporting ? 'Generation en cours...' : '\u{1F4E6} Exporter rapport + documents (ZIP)'}
        </button>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-value">{pctTasks}%</div>
          <div className="kpi-label">Avancement chantier</div>
          <div className="kpi-detail">{completedCount}/{totalTasks} taches</div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${pctTasks}%` }} />
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{pctLegal}%</div>
          <div className="kpi-label">Obligations legales</div>
          <div className="kpi-detail">{completedLegal}/{totalLegal} validees</div>
          <div className="progress-bar">
            <div className="progress-fill progress-legal" style={{ width: `${pctLegal}%` }} />
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{alerts.filter(a => a.days <= 7).length}</div>
          <div className="kpi-label">Alertes urgentes</div>
          <div className="kpi-detail">dans les 7 prochains jours</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{TOTAL_TTC.toLocaleString('fr-FR')} EUR</div>
          <div className="kpi-label">Budget ELCR</div>
          <div className="kpi-detail">Peinture non incluse</div>
        </div>
      </div>

      {nextMilestone && (
        <div className="next-milestone">
          <span className="milestone-icon">&#9670;</span>
          <div>
            <strong>Prochain jalon :</strong> {nextMilestone.label}
            <div className="milestone-date">
              {formatDate(nextMilestone.deadline)} (J-{daysUntil(nextMilestone.deadline)})
            </div>
          </div>
        </div>
      )}

      <h2 className="section-title">Alertes et echeances</h2>
      {alerts.length === 0 ? (
        <div className="empty-state">Aucune alerte dans les 30 prochains jours.</div>
      ) : (
        <div className="alerts-list">
          {alerts.map(a => (
            <div key={a.id} className={`alert-item ${alertClass(a.days, a.critical)}`}>
              <span className="alert-badge">{alertIcon(a.days)}</span>
              <div className="alert-content">
                <div className="alert-label">
                  {a.type === 'legal' && <span className="tag-legal">LEGAL</span>}
                  {a.critical && <span className="tag-critical">CRITIQUE</span>}
                  {a.label}
                </div>
                <div className="alert-meta">
                  {a.days < 0 ? (
                    <span className="overdue-text">En retard de {Math.abs(a.days)} jour(s)</span>
                  ) : a.days === 0 ? (
                    <span className="today-text">Aujourd'hui !</span>
                  ) : (
                    <span>J-{a.days} — {formatDate(a.deadline)}</span>
                  )}
                </div>
                {a.note && <div className="alert-note">{a.note}</div>}
              </div>
            </div>
          ))}
        </div>
      )}

      <h2 className="section-title">Avancement par phase</h2>
      <div className="phase-progress-list">
        {phaseProgress.map(p => (
          <div key={p.id} className="phase-progress-item">
            <div className="phase-progress-header">
              <span className="phase-dot" style={{ background: p.color }} />
              <span className="phase-name">{p.name}</span>
              <span className="phase-pct">{p.pct}%</span>
            </div>
            <div className="progress-bar progress-bar-sm">
              <div className="progress-fill" style={{ width: `${p.pct}%`, background: p.color }} />
            </div>
            <div className="phase-dates">{p.dates} — {p.done}/{p.total}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
