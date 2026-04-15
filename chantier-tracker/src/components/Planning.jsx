import { useState } from 'react'
import { PHASES } from '../data/phases.js'
import { daysUntil, formatDateShort } from '../utils/dateUtils.js'

export default function Planning({ state, toggleTask }) {
  const [expandedPhase, setExpandedPhase] = useState(null)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')

  const firstPendingPhase = PHASES.find(p =>
    p.tasks.some(t => !state.completedTasks[t.id])
  )

  function togglePhase(phaseId) {
    setExpandedPhase(prev => prev === phaseId ? null : phaseId)
  }

  function filterTasks(tasks) {
    let result = tasks
    switch (filter) {
      case 'pending': result = result.filter(t => !state.completedTasks[t.id]); break
      case 'done': result = result.filter(t => state.completedTasks[t.id]); break
      case 'critical': result = result.filter(t => t.critical); break
      case 'legal': result = result.filter(t => t.legal); break
    }
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(t => t.label.toLowerCase().includes(q) || t.note?.toLowerCase().includes(q))
    }
    return result
  }

  const totalFiltered = PHASES.reduce((sum, p) => sum + filterTasks(p.tasks).length, 0)

  return (
    <div className="planning">
      <div className="search-bar">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Rechercher une tache..."
          className="search-input"
        />
        {search && (
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
            {totalFiltered} resultat(s)
          </span>
        )}
      </div>
      <div className="filter-bar">
        {[
          { key: 'all', label: 'Toutes' },
          { key: 'pending', label: 'A faire' },
          { key: 'done', label: 'Faites' },
          { key: 'critical', label: 'Critiques' },
          { key: 'legal', label: 'Legales' },
        ].map(f => (
          <button
            key={f.key}
            className={`filter-btn ${filter === f.key ? 'active' : ''}`}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {PHASES.map(phase => {
        const doneTasks = phase.tasks.filter(t => state.completedTasks[t.id]).length
        const totalTasks = phase.tasks.length
        const pct = totalTasks > 0 ? Math.round((doneTasks / totalTasks) * 100) : 0
        const filtered = filterTasks(phase.tasks)
        const isExpanded = expandedPhase === phase.id ||
          (expandedPhase === null && phase.id === firstPendingPhase?.id)

        return (
          <div key={phase.id} className="phase-card">
            <button
              className="phase-header"
              onClick={() => togglePhase(phase.id)}
            >
              <div className="phase-header-left">
                <span className="phase-dot-lg" style={{ background: phase.color }} />
                <div>
                  <div className="phase-title">{phase.name}</div>
                  <div className="phase-subtitle">{phase.dates}</div>
                </div>
              </div>
              <div className="phase-header-right">
                <span className="phase-count">{doneTasks}/{totalTasks}</span>
                <div className="progress-bar progress-bar-sm progress-bar-header">
                  <div className="progress-fill" style={{ width: `${pct}%`, background: phase.color }} />
                </div>
                <span className={`chevron ${isExpanded ? 'open' : ''}`}>&#9660;</span>
              </div>
            </button>

            {isExpanded && (
              <div className="phase-tasks">
                {filtered.length === 0 ? (
                  <div className="empty-tasks">Aucune tache avec ce filtre.</div>
                ) : (
                  filtered.map(task => {
                    const isDone = !!state.completedTasks[task.id]
                    const days = task.deadline ? daysUntil(task.deadline) : null
                    const isOverdue = days !== null && days < 0 && !isDone
                    const isUrgent = days !== null && days <= 7 && days >= 0 && !isDone

                    return (
                      <div
                        key={task.id}
                        className={`task-item ${isDone ? 'done' : ''} ${isOverdue ? 'overdue' : ''} ${isUrgent ? 'urgent' : ''}`}
                        onClick={() => toggleTask(task.id)}
                      >
                        <div className={`checkbox ${isDone ? 'checked' : ''}`}>
                          {isDone && <span>&#10003;</span>}
                        </div>
                        <div className="task-content">
                          <div className="task-label">
                            {task.critical && <span className="tag-critical">!</span>}
                            {task.legal && <span className="tag-legal">LOI</span>}
                            {task.label}
                          </div>
                          {task.deadline && (
                            <div className="task-deadline">
                              {isOverdue ? (
                                <span className="overdue-text">Retard {Math.abs(days)}j</span>
                              ) : (
                                <span>J-{days} — {formatDateShort(task.deadline)}</span>
                              )}
                            </div>
                          )}
                          {task.note && <div className="task-note">{task.note}</div>}
                          {task.help && <div className="task-help">{task.help}</div>}
                          {task.links && task.links.length > 0 && (
                            <div className="task-links">
                              {task.links.map((link, i) => (
                                <a key={i} href={link.url} target="_blank" rel="noopener noreferrer" className="info-link" onClick={e => e.stopPropagation()}>
                                  {'\u{1F517}'} {link.label}
                                </a>
                              ))}
                            </div>
                          )}
                          {isDone && state.completedTasks[task.id] && (
                            <div className="task-done-date">
                              Fait le {new Date(state.completedTasks[task.id]).toLocaleDateString('fr-FR')}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
