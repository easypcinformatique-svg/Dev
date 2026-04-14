import JSZip from 'jszip'
import { saveAs } from 'file-saver'
import { getAllDocuments, DOC_CATEGORIES } from '../hooks/useDocuments.js'
import { PHASES } from '../data/phases.js'
import { OBLIGATIONS } from '../data/legal.js'
import { LOTS, TOTAL_TTC, ECHEANCIER } from '../data/finances.js'
import { ARTISANS } from '../data/artisans.js'

function formatDateFR(iso) {
  if (!iso) return '—'
  return new Date(iso + (iso.includes('T') ? '' : 'T00:00:00')).toLocaleDateString('fr-FR', {
    day: 'numeric', month: 'long', year: 'numeric'
  })
}

function daysUntil(dateStr) {
  const target = new Date(dateStr + 'T00:00:00')
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  return Math.ceil((target - now) / (1000 * 60 * 60 * 24))
}

function base64ToBlob(dataUrl) {
  const parts = dataUrl.split(',')
  const mime = parts[0].match(/:(.*?);/)?.[1] || 'application/octet-stream'
  const raw = atob(parts[1])
  const arr = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i)
  return new Blob([arr], { type: mime })
}

function getCategoryLabel(id) {
  return DOC_CATEGORIES.find(c => c.id === id)?.label || id
}

function getArtisanName(id) {
  return ARTISANS.find(a => a.id === id)?.name || ''
}

function generateReport(state) {
  const now = new Date()
  const allTasks = PHASES.flatMap(p => p.tasks)
  const completedCount = Object.keys(state.completedTasks).length
  const totalTasks = allTasks.length
  const completedLegal = Object.keys(state.completedLegal).length
  const totalLegal = OBLIGATIONS.length

  let report = ''
  report += '═══════════════════════════════════════════════════════\n'
  report += '  RAPPORT DE SUIVI DE CHANTIER\n'
  report += '  11 rue Pierre Loti, 13170 Les Pennes Mirabeau\n'
  report += '  SCI JGR — PC 013 071 23 C0061\n'
  report += '═══════════════════════════════════════════════════════\n\n'
  report += `Date du rapport : ${formatDateFR(now.toISOString())}\n\n`

  // KPIs
  report += '── INDICATEURS CLES ──────────────────────────────────\n\n'
  report += `  Avancement chantier : ${completedCount}/${totalTasks} taches (${Math.round(completedCount / totalTasks * 100)}%)\n`
  report += `  Obligations legales : ${completedLegal}/${totalLegal} validees (${Math.round(completedLegal / totalLegal * 100)}%)\n`

  const totalPaid = LOTS.reduce((sum, lot) => {
    const p = state.payments[lot.id] || {}
    return sum + (Number(p.acompte) || 0) + (Number(p.situations) || 0) + (Number(p.solde) || 0)
  }, 0)
  report += `  Budget ELCR : ${TOTAL_TTC.toLocaleString('fr-FR')} EUR TTC\n`
  report += `  Paye : ${totalPaid.toLocaleString('fr-FR')} EUR (${Math.round(totalPaid / TOTAL_TTC * 100)}%)\n`
  report += `  Reste : ${(TOTAL_TTC - totalPaid).toLocaleString('fr-FR')} EUR\n\n`

  // Avancement par phase
  report += '── AVANCEMENT PAR PHASE ──────────────────────────────\n\n'
  PHASES.forEach(phase => {
    const done = phase.tasks.filter(t => state.completedTasks[t.id]).length
    const total = phase.tasks.length
    const pct = total > 0 ? Math.round(done / total * 100) : 0
    const bar = '[' + '#'.repeat(Math.round(pct / 5)) + '.'.repeat(20 - Math.round(pct / 5)) + ']'
    report += `  ${phase.name} (${phase.dates})\n`
    report += `  ${bar} ${pct}% (${done}/${total})\n\n`
  })

  // Taches completees recemment
  const recentTasks = allTasks
    .filter(t => state.completedTasks[t.id])
    .map(t => ({ ...t, doneDate: state.completedTasks[t.id] }))
    .sort((a, b) => new Date(b.doneDate) - new Date(a.doneDate))
    .slice(0, 10)

  if (recentTasks.length > 0) {
    report += '── TACHES COMPLETEES RECEMMENT ───────────────────────\n\n'
    recentTasks.forEach(t => {
      report += `  [x] ${t.label}\n`
      report += `      Fait le ${formatDateFR(t.doneDate)}\n`
    })
    report += '\n'
  }

  // Alertes
  const alerts = allTasks
    .filter(t => !state.completedTasks[t.id] && t.deadline && daysUntil(t.deadline) <= 30)
    .sort((a, b) => daysUntil(a.deadline) - daysUntil(b.deadline))

  if (alerts.length > 0) {
    report += '── ALERTES (30 prochains jours) ──────────────────────\n\n'
    alerts.forEach(t => {
      const d = daysUntil(t.deadline)
      const status = d < 0 ? 'EN RETARD' : d === 0 ? 'AUJOURD\'HUI' : `J-${d}`
      report += `  ${t.critical ? '!! ' : '   '}${status} — ${t.label}\n`
      report += `      Echeance : ${formatDateFR(t.deadline)}\n`
      if (t.note) report += `      Note : ${t.note}\n`
    })
    report += '\n'
  }

  // Obligations legales
  report += '── OBLIGATIONS LEGALES ───────────────────────────────\n\n'
  OBLIGATIONS.forEach(ob => {
    const done = state.completedLegal[ob.id]
    const status = done ? `[x] Fait le ${formatDateFR(done)}` : `[ ] Echeance ${formatDateFR(ob.deadline)}`
    report += `  ${status}\n`
    report += `  ${ob.label}\n`
    report += `  Ref: ${ob.reference}\n\n`
  })

  // Finances par lot
  report += '── FINANCES PAR LOT ─────────────────────────────────\n\n'
  LOTS.forEach(lot => {
    const p = state.payments[lot.id] || {}
    const lotPaid = (Number(p.acompte) || 0) + (Number(p.situations) || 0) + (Number(p.solde) || 0)
    const lotTTC = Math.round(lot.ht * 1.20)
    report += `  ${lot.name} (${lot.artisan})\n`
    if (lot.missing) {
      report += `  ** ARTISAN A TROUVER **\n`
    } else {
      report += `  HT: ${lot.ht.toLocaleString('fr-FR')} EUR | TTC: ${lotTTC.toLocaleString('fr-FR')} EUR | Paye: ${lotPaid.toLocaleString('fr-FR')} EUR\n`
    }
    report += '\n'
  })

  // Notes
  if (state.notes?.length > 0) {
    report += '── JOURNAL DE CHANTIER ──────────────────────────────\n\n'
    state.notes.slice(0, 20).forEach(n => {
      report += `  ${formatDateFR(n.date)}\n`
      report += `  ${n.text}\n\n`
    })
  }

  report += '═══════════════════════════════════════════════════════\n'
  report += '  Genere par Chantier Tracker — ' + now.toLocaleString('fr-FR') + '\n'
  report += '═══════════════════════════════════════════════════════\n'

  return report
}

export async function exportZip(state) {
  const zip = new JSZip()
  const docs = await getAllDocuments()

  // Rapport texte
  const report = generateReport(state)
  zip.file('Rapport_Chantier_11_Pierre_Loti.txt', report)

  // Documents classes par categorie
  if (docs.length > 0) {
    const byCategory = {}
    docs.forEach(doc => {
      const catLabel = getCategoryLabel(doc.category)
      if (!byCategory[catLabel]) byCategory[catLabel] = []
      byCategory[catLabel].push(doc)
    })

    for (const [catName, catDocs] of Object.entries(byCategory)) {
      const folder = zip.folder(catName)
      catDocs.forEach(doc => {
        const blob = base64ToBlob(doc.data)
        const artisan = doc.artisanId ? ` (${getArtisanName(doc.artisanId)})` : ''
        folder.file(`${doc.name}`, blob)
      })
    }
  }

  // Generer le ZIP
  const content = await zip.generateAsync({ type: 'blob' })
  const date = new Date().toISOString().slice(0, 10)
  saveAs(content, `Chantier_Pierre_Loti_${date}.zip`)
}
