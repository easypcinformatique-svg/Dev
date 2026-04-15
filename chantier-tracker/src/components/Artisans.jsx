import { useState } from 'react'
import { ARTISANS } from '../data/artisans.js'

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

export default function ArtisansView({ state, updateArtisan }) {
  const [expandedArtisan, setExpandedArtisan] = useState(null)

  function getArtisanData(artisan) {
    const updates = state.artisanUpdates?.[artisan.id] || {}
    return { ...artisan, ...updates }
  }

  return (
    <div className="artisans">
      {ARTISANS.map(art => {
        const data = getArtisanData(art)
        const isExpanded = expandedArtisan === art.id

        return (
          <div key={art.id} className={`artisan-card ${art.status === 'to_find' ? 'artisan-missing' : ''}`}>
            <div
              className="artisan-header"
              onClick={() => setExpandedArtisan(isExpanded ? null : art.id)}
            >
              <div className="artisan-info">
                <div className="artisan-name">{data.name}</div>
                <div className="artisan-role">{data.role}</div>
              </div>
              <div className="artisan-status" style={{ background: STATUS_COLORS[art.status] }}>
                {STATUS_LABELS[art.status]}
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
                <div className="artisan-field">
                  <label>N° police</label>
                  <input
                    type="text"
                    value={data.decennale?.numero || ''}
                    onChange={e => updateArtisan(art.id, 'decennaleNumero', e.target.value)}
                    placeholder="Numero de police"
                  />
                </div>
                <div className="artisan-field">
                  <label>Assureur</label>
                  <input
                    type="text"
                    value={data.decennale?.assureur || ''}
                    onChange={e => updateArtisan(art.id, 'decennaleAssureur', e.target.value)}
                    placeholder="Nom de l'assureur"
                  />
                </div>
                <div className="artisan-field">
                  <label>Expiration</label>
                  <input
                    type="date"
                    value={data.decennale?.expiration || ''}
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
