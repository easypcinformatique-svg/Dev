import { useState } from 'react'
import { PHASES } from '../data/phases.js'

function daysUntil(dateStr) {
  const target = new Date(dateStr + 'T00:00:00')
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  return Math.ceil((target - now) / (1000 * 60 * 60 * 24))
}

function formatDate(dateStr) {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('fr-FR', {
    day: 'numeric', month: 'short'
  })
}

export default function Planning({ state, toggleTask }) {
  const [expandedPhase, setExpandedPhase] = useState(null)
  const [filter, setFilter] = useState('all') // all, pending, done, critical, legal

  // Auto-expand first phase with pending tasks
  const firstPendingPhase = PHASES.find(p =>
    p.tasks.some(t => !state.completedTasks[t.id])
  )

  function togglePhase(phaseId) {
    setExpandedPhase(prev => prev === phaseId ? null : phaseId)
  }

  function filterTasks(tasks) {
    switch (filter) {
      case 'pending': return tasks.filter(t => !state.completedTasks[t.id])
      case 'done': return tasks.filter(t => state.completedTasks[t.id])
      case 'critical': return tasks.filter(t => t.critical)
      case 'legal': return tasks.filter(t => t.legal)
      default: return tasks
    }
  }

  return (
    <div className="planning">
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
                                <span>J-{days} — {formatDate(task.deadline)}</span>
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
