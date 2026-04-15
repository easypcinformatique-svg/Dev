import { useState } from 'react'
import { LOTS, TOTAL_HT, TOTAL_TTC, TVA_RATE, ECHEANCIER } from '../data/finances.js'

export default function Finances({ state, updatePayment, updateFinancement }) {
  const [editingLot, setEditingLot] = useState(null)

  const totalPaid = LOTS.reduce((sum, lot) => {
    const p = state.payments[lot.id] || {}
    return sum + (Number(p.acompte) || 0) + (Number(p.situations) || 0) + (Number(p.solde) || 0)
  }, 0)

  const pctPaid = TOTAL_TTC > 0 ? Math.round((totalPaid / TOTAL_TTC) * 100) : 0

  const pret = Number(state.financement?.pret) || 0
  const apport = Number(state.financement?.apport) || 0
  const totalFinancement = pret + apport

  // Calcul avancement reel global
  const lotsWithBudget = LOTS.filter(l => l.ht > 0)
  const avgAvancement = lotsWithBudget.length > 0
    ? Math.round(lotsWithBudget.reduce((sum, lot) => sum + (Number(state.payments[lot.id]?.avancement) || 0), 0) / lotsWithBudget.length)
    : 0

  return (
    <div className="finances">
      {/* Financement */}
      <div className="finance-section">
        <h2 className="section-title">Financement</h2>
        <div className="finance-row">
          <label>Pret bancaire</label>
          <div className="input-group">
            <input
              type="number"
              min="0"
              value={pret || ''}
              onChange={e => updateFinancement('pret', Math.max(0, Number(e.target.value)))}
              placeholder="Montant du pret"
            />
            <span className="input-suffix">EUR</span>
          </div>
        </div>
        <div className="finance-row">
          <label>Fonds propres</label>
          <div className="input-group">
            <input
              type="number"
              min="0"
              value={apport || ''}
              onChange={e => updateFinancement('apport', Math.max(0, Number(e.target.value)))}
              placeholder="Montant apport"
            />
            <span className="input-suffix">EUR</span>
          </div>
        </div>
        {totalFinancement > 0 && (
          <div className="finance-summary">
            <div>Total financement : <strong>{totalFinancement.toLocaleString('fr-FR')} EUR</strong></div>
            {totalFinancement < TOTAL_TTC && (
              <div className="warning-text">
                Il manque {(TOTAL_TTC - totalFinancement).toLocaleString('fr-FR')} EUR par rapport au devis ELCR (hors peinture)
              </div>
            )}
          </div>
        )}
      </div>

      {/* Resume paiements vs avancement */}
      <div className="finance-section">
        <h2 className="section-title">Paiements ELCR vs Avancement reel</h2>
        <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
          <div className="kpi-card kpi-card-sm">
            <div className="kpi-value-sm">{totalPaid.toLocaleString('fr-FR')}</div>
            <div className="kpi-label">Paye (EUR)</div>
          </div>
          <div className="kpi-card kpi-card-sm">
            <div className="kpi-value-sm">{(TOTAL_TTC - totalPaid).toLocaleString('fr-FR')}</div>
            <div className="kpi-label">Reste (EUR)</div>
          </div>
          <div className="kpi-card kpi-card-sm">
            <div className="kpi-value-sm">{pctPaid}%</div>
            <div className="kpi-label">% Paye</div>
          </div>
          <div className="kpi-card kpi-card-sm">
            <div className="kpi-value-sm" style={{ color: avgAvancement < pctPaid - 10 ? 'var(--danger)' : 'var(--success)' }}>
              {avgAvancement}%
            </div>
            <div className="kpi-label">% Realise</div>
          </div>
        </div>
        <div className="progress-bar" style={{ marginBottom: '0.25rem' }}>
          <div className="progress-fill progress-finance" style={{ width: `${pctPaid}%` }} />
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${avgAvancement}%`, background: 'var(--primary)' }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
          <span>Paiements (vert)</span>
          <span>Travaux realises (bleu)</span>
        </div>
        {pctPaid > avgAvancement + 15 && (
          <div className="warning-text" style={{ marginTop: '0.5rem' }}>
            Attention : les paiements ({pctPaid}%) depassent l'avancement reel ({avgAvancement}%) de plus de 15 points.
          </div>
        )}
      </div>

      {/* Echeancier */}
      <div className="finance-section">
        <h2 className="section-title">Echeancier contractuel</h2>
        <div className="echeancier">
          {Object.entries(ECHEANCIER).map(([key, val]) => (
            <div key={key} className="echeancier-item">
              <div className="echeancier-pct">{val.pct}%</div>
              <div>
                <div className="echeancier-label">{val.label}</div>
                <div className="echeancier-montant">{val.montant.toLocaleString('fr-FR')} EUR TTC</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail par lot */}
      <div className="finance-section">
        <h2 className="section-title">Detail par lot</h2>
        {LOTS.map(lot => {
          const p = state.payments[lot.id] || {}
          const lotPaid = (Number(p.acompte) || 0) + (Number(p.situations) || 0) + (Number(p.solde) || 0)
          const lotTTC = Math.round(lot.ht * (1 + TVA_RATE))
          const isEditing = editingLot === lot.id
          const avancement = Number(p.avancement) || 0
          const lotPctPaid = lotTTC > 0 ? Math.round((lotPaid / lotTTC) * 100) : 0
          const overpaid = lotPctPaid > avancement + 20

          return (
            <div key={lot.id} className={`lot-card ${lot.missing ? 'lot-missing' : ''} ${overpaid ? 'lot-overpaid' : ''}`}>
              <div className="lot-header" onClick={() => setEditingLot(isEditing ? null : lot.id)}>
                <div>
                  <div className="lot-name">
                    {lot.missing && <span className="tag-warning">A TROUVER</span>}
                    {overpaid && <span className="tag-critical">SURPAYE</span>}
                    {lot.name}
                  </div>
                  <div className="lot-artisan">{lot.artisan}</div>
                </div>
                <div className="lot-amounts">
                  {lot.ht > 0 && (
                    <>
                      <div className="lot-ht">{lot.ht.toLocaleString('fr-FR')} EUR HT</div>
                      <div className="lot-ttc">{lotTTC.toLocaleString('fr-FR')} EUR TTC</div>
                    </>
                  )}
                  {lotPaid > 0 && (
                    <div className="lot-paid">Paye : {lotPaid.toLocaleString('fr-FR')} EUR ({lotPctPaid}%)</div>
                  )}
                  {avancement > 0 && lot.ht > 0 && (
                    <div style={{ fontSize: '0.72rem', color: 'var(--primary)', marginTop: '0.1rem' }}>
                      Realise : {avancement}%
                    </div>
                  )}
                </div>
              </div>

              {isEditing && lot.ht > 0 && (
                <div className="lot-edit">
                  <div className="lot-edit-row">
                    <label>Avancement reel des travaux</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <input
                        type="range"
                        min="0" max="100" step="5"
                        value={avancement}
                        onChange={e => updatePayment(lot.id, 'avancement', e.target.value)}
                        style={{ width: '100px' }}
                      />
                      <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)', minWidth: '35px' }}>
                        {avancement}%
                      </span>
                    </div>
                  </div>
                  <div className="lot-edit-row">
                    <label>Acompte verse (10%)</label>
                    <input
                      type="number"
                      min="0"
                      value={p.acompte || ''}
                      onChange={e => updatePayment(lot.id, 'acompte', Math.max(0, Number(e.target.value) || 0).toString())}
                      placeholder={Math.round(lotTTC * 0.10).toString()}
                    />
                  </div>
                  <div className="lot-edit-row">
                    <label>Situations versees (85%)</label>
                    <input
                      type="number"
                      min="0"
                      value={p.situations || ''}
                      onChange={e => updatePayment(lot.id, 'situations', Math.max(0, Number(e.target.value) || 0).toString())}
                      placeholder={Math.round(lotTTC * 0.85).toString()}
                    />
                  </div>
                  <div className="lot-edit-row">
                    <label>Solde reception (5%)</label>
                    <input
                      type="number"
                      min="0"
                      value={p.solde || ''}
                      onChange={e => updatePayment(lot.id, 'solde', Math.max(0, Number(e.target.value) || 0).toString())}
                      placeholder={Math.round(lotTTC * 0.05).toString()}
                    />
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
