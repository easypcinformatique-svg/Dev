import { useState } from 'react'
import { ARTISANS } from '../data/artisans.js'
import { daysUntil } from '../utils/dateUtils.js'

const STATUS_LABELS = {
  contracted: 'Sous contrat',
  active: 'Actif',
  to_find: 'A trouver',
  completed: 'Termine',
}

const STATUS_COLORS = {
  contracted: '#16a34a',
  active: '#2563eb',
  to_find: '#dc2626',
  completed: '#6b7280',
}

function getDecennaleStatus(expiration) {
  if (!expiration) return { label: 'Non renseignee', color: 'var(--text-dim)', icon: '?' }
  const days = daysUntil(expiration)
  if (days < 0) return { label: 'EXPIREE', color: 'var(--danger)', icon: '!!' }
  if (days <= 30) return { label: `Expire dans ${days}j`, color: 'var(--danger)', icon: '!' }
  if (days <= 90) return { label: `Expire dans ${days}j`, color: 'var(--warning)', icon: '~' }
  return { label: 'Valide', color: 'var(--success)', icon: null }
}

export default function ArtisansView({ state, updateArtisan }) {
  const [expandedArtisan, setExpandedArtisan] = useState(null)

  function getArtisanData(artisan) {
    const updates = state.artisanUpdates?.[artisan.id] || {}
    return { ...artisan, ...updates }
  }

  // Alertes globales decennale
  const decennaleAlerts = ARTISANS
    .filter(a => a.status !== 'to_find')
    .map(a => {
      const data = getArtisanData(a)
      const exp = data.decennale?.expiration || data.decennaleExpiration
      return { ...a, expiration: exp, status: getDecennaleStatus(exp) }
    })
    .filter(a => a.status.icon)

  return (
    <div className="artisans">
      {/* Resume alertes decennale */}
      {decennaleAlerts.length > 0 && (
        <div className="decennale-alerts">
          <div className="section-title" style={{ marginTop: 0 }}>Alertes assurance decennale</div>
          {decennaleAlerts.map(a => (
            <div key={a.id} className="decennale-alert-item" style={{ borderLeftColor: a.status.color }}>
              <span className="decennale-alert-icon" style={{ color: a.status.color }}>{a.status.icon}</span>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{a.name}</div>
                <div style={{ fontSize: '0.72rem', color: a.status.color }}>{a.status.label}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {ARTISANS.map(art => {
        const data = getArtisanData(art)
        const isExpanded = expandedArtisan === art.id
        const exp = data.decennale?.expiration || data.decennaleExpiration
        const decStatus = getDecennaleStatus(exp)

        return (
          <div key={art.id} className={`artisan-card ${art.status === 'to_find' ? 'artisan-missing' : ''}`}>
            <div
              className="artisan-header"
              onClick={() => setExpandedArtisan(isExpanded ? null : art.id)}
              role="button"
              aria-expanded={isExpanded}
              tabIndex={0}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpandedArtisan(isExpanded ? null : art.id) } }}
            >
              <div className="artisan-info">
                <div className="artisan-name">{data.name}</div>
                <div className="artisan-role">{data.role}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {decStatus.icon && art.status !== 'to_find' && (
                  <span
                    className="decennale-badge"
                    style={{ background: decStatus.color }}
                    title={`Decennale: ${decStatus.label}`}
                  >
                    {decStatus.icon}
                  </span>
                )}
                <div className="artisan-status" style={{ background: STATUS_COLORS[art.status] }}>
                  {STATUS_LABELS[art.status]}
                </div>
              </div>
            </div>

            {isExpanded && (
              <div className="artisan-details">
                <div className="artisan-field">
                  <label>Contact</label>
                  <input
                    type="text"
                    value={data.contact || ''}
                    onChange={e => updateArtisan(art.id, 'contact', e.target.value)}
                    placeholder="Nom du contact"
                  />
                </div>
                <div className="artisan-field">
                  <label>Telephone</label>
                  <input
                    type="tel"
                    value={data.phone || ''}
                    onChange={e => updateArtisan(art.id, 'phone', e.target.value)}
                    placeholder="06 ..."
                  />
                </div>
                <div className="artisan-field">
                  <label>Email</label>
                  <input
                    type="email"
                    value={data.email || ''}
                    onChange={e => updateArtisan(art.id, 'email', e.target.value)}
                    placeholder="email@..."
                  />
                </div>
                <div className="artisan-field">
                  <label>SIRET</label>
                  <input
                    type="text"
                    value={data.siret || ''}
                    onChange={e => updateArtisan(art.id, 'siret', e.target.value)}
                    placeholder="XXX XXX XXX XXXXX"
                  />
                </div>

                {art.montantTTC > 0 && (
                  <div className="artisan-field">
                    <label>Montant TTC</label>
                    <div className="artisan-value">{art.montantTTC.toLocaleString('fr-FR')} EUR</div>
                  </div>
                )}

                <div className="artisan-section-title">Assurance decennale</div>
                {decStatus.icon && (
                  <div style={{
                    padding: '0.4rem 0.75rem', borderRadius: '6px', marginBottom: '0.6rem',
                    background: decStatus.color === 'var(--success)' ? 'transparent' : 'var(--danger-bg)',
                    border: `1px solid ${decStatus.color}`, fontSize: '0.75rem', color: decStatus.color
                  }}>
                    {decStatus.label}
                  </div>
                )}
                <div className="artisan-field">
                  <label>N° police</label>
                  <input
                    type="text"
                    value={data.decennale?.numero || data.decennaleNumero || ''}
                    onChange={e => updateArtisan(art.id, 'decennaleNumero', e.target.value)}
                    placeholder="Numero de police"
                  />
                </div>
                <div className="artisan-field">
                  <label>Assureur</label>
                  <input
                    type="text"
                    value={data.decennale?.assureur || data.decennaleAssureur || ''}
                    onChange={e => updateArtisan(art.id, 'decennaleAssureur', e.target.value)}
                    placeholder="Nom de l'assureur"
                  />
                </div>
                <div className="artisan-field">
                  <label>Expiration</label>
                  <input
                    type="date"
                    value={exp || ''}
                    onChange={e => updateArtisan(art.id, 'decennaleExpiration', e.target.value)}
                  />
                </div>

                {art.notes && (
                  <div className="artisan-notes">
                    <strong>Notes :</strong> {art.notes}
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
