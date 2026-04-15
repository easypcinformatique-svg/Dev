import { useState } from 'react'
import { OBLIGATIONS } from '../data/legal.js'

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

const CATEGORIES = ['Avant chantier', 'Ouverture', 'Pendant travaux', 'Fin travaux', 'Post-réception']

export default function Legal({ state, toggleLegal }) {
  const [expandedHelp, setExpandedHelp] = useState(null)
  const grouped = CATEGORIES.map(cat => ({
    category: cat,
    items: OBLIGATIONS.filter(o => o.category === cat),
  }))

  return (
    <div className="legal">
      <div className="legal-summary">
        {CATEGORIES.map(cat => {
          const items = OBLIGATIONS.filter(o => o.category === cat)
          const done = items.filter(o => state.completedLegal[o.id]).length
          return (
            <div key={cat} className="legal-summary-item">
              <span className="legal-summary-label">{cat}</span>
              <span className="legal-summary-count">{done}/{items.length}</span>
            </div>
          )
        })}
      </div>

      {grouped.map(group => (
        <div key={group.category} className="legal-group">
          <h3 className="legal-group-title">{group.category}</h3>
          {group.items.map(ob => {
            const isDone = !!state.completedLegal[ob.id]
            const days = daysUntil(ob.deadline)
            const isOverdue = days < 0 && !isDone
            const isUrgent = days <= 14 && days >= 0 && !isDone

            return (
              <div
                key={ob.id}
                className={`legal-item ${isDone ? 'done' : ''} ${isOverdue ? 'overdue' : ''} ${isUrgent ? 'urgent' : ''}`}
                onClick={() => toggleLegal(ob.id)}
              >
                <div className={`checkbox ${isDone ? 'checked' : ''}`}>
                  {isDone && <span>&#10003;</span>}
                </div>
                <div className="legal-content">
                  <div className="legal-label">
                    {ob.critical && <span className="tag-critical">CRITIQUE</span>}
                    {ob.label}
                  </div>
                  <div className="legal-deadline">
                    {isOverdue ? (
                      <span className="overdue-text">EN RETARD — {Math.abs(days)} jour(s)</span>
                    ) : isDone ? (
                      <span className="done-text">Fait le {new Date(state.completedLegal[ob.id]).toLocaleDateString('fr-FR')}</span>
                    ) : (
                      <span>Echeance : {formatDate(ob.deadline)} (J-{days})</span>
                    )}
                  </div>
                  <div className="legal-ref">{ob.reference}</div>
                  <div className="legal-detail">{ob.detail}</div>
                  {(ob.help || (ob.links && ob.links.length > 0)) && (
                    <button
                      className="info-toggle"
                      onClick={(e) => { e.stopPropagation(); setExpandedHelp(expandedHelp === ob.id ? null : ob.id) }}
                    >
                      {expandedHelp === ob.id ? '\u25B2 Masquer' : '\u{2139}\u{FE0F} En savoir plus'}
                    </button>
                  )}
                  {expandedHelp === ob.id && (
                    <div className="info-bubble">
                      {ob.help && <div className="info-text">{ob.help}</div>}
                      {ob.links && ob.links.length > 0 && (
                        <div className="info-links">
                          {ob.links.map((link, i) => (
                            <a key={i} href={link.url} target="_blank" rel="noopener noreferrer" className="info-link" onClick={e => e.stopPropagation()}>
                              {'\u{1F517}'} {link.label}
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
