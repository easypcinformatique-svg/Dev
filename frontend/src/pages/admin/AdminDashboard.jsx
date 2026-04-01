import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import api from '../../shared/utils/api'
import { COMPTOIR_CONFIG } from '../../shared/utils/constants'

const TABS = ['dashboard', 'commandes', 'ticket-z']

export default function AdminDashboard() {
  const [tab, setTab] = useState('dashboard')
  const [periode, setPeriode] = useState('jour')

  const { data: stats } = useQuery({
    queryKey: ['stats', periode],
    queryFn: () => api.get('/api/stats/', { params: { periode } }).then((r) => r.data),
  })

  const { data: ticketZ } = useQuery({
    queryKey: ['ticket-z'],
    queryFn: () => api.get('/api/caisse/ticket-z').then((r) => r.data),
    enabled: tab === 'ticket-z',
  })

  const { data: todayOrders = [] } = useQuery({
    queryKey: ['admin-orders'],
    queryFn: () =>
      api.get('/api/commandes/', {
        params: { jour: new Date().toISOString().split('T')[0] },
      }).then((r) => r.data),
    enabled: tab === 'commandes',
  })

  const comptoirData = stats?.par_comptoir
    ? Object.entries(stats.par_comptoir).map(([key, val]) => ({
        name: COMPTOIR_CONFIG[key]?.nom || key,
        ca: val.ca_ttc || 0,
        nb: val.nb || 0,
        fill: COMPTOIR_CONFIG[key]?.couleur || '#666',
      }))
    : []

  const creneauData = stats?.par_creneau
    ? Object.entries(stats.par_creneau).map(([heure, nb]) => ({
        heure,
        commandes: nb,
      }))
    : []

  return (
    <div className="p-6 h-full overflow-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">⚙️ Administration</h1>
        <div className="flex gap-2">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${
                tab === t ? 'bg-pizza-500 text-white' : 'bg-gray-800 text-gray-300'
              }`}
            >
              {t === 'dashboard' ? '📊 Dashboard' : t === 'commandes' ? '📋 Commandes' : '🧾 Ticket Z'}
            </button>
          ))}
        </div>
      </div>

      {tab === 'dashboard' && (
        <>
          {/* Periode selector */}
          <div className="flex gap-2 mb-6">
            {['jour', 'semaine', 'mois'].map((p) => (
              <button
                key={p}
                onClick={() => setPeriode(p)}
                className={`px-3 py-1 rounded-lg text-sm ${
                  periode === p ? 'bg-pizza-500 text-white' : 'bg-gray-800 text-gray-300'
                }`}
              >
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>

          {/* KPIs */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="card text-center">
              <div className="text-3xl font-bold text-pizza-400">
                {stats?.ca_ttc?.toFixed(2) || '0.00'}€
              </div>
              <div className="text-sm text-gray-400 mt-1">CA TTC</div>
            </div>
            <div className="card text-center">
              <div className="text-3xl font-bold text-blue-400">
                {stats?.nb_commandes || 0}
              </div>
              <div className="text-sm text-gray-400 mt-1">Commandes</div>
            </div>
            <div className="card text-center">
              <div className="text-3xl font-bold text-green-400">
                {stats?.panier_moyen?.toFixed(2) || '0.00'}€
              </div>
              <div className="text-sm text-gray-400 mt-1">Panier moyen</div>
            </div>
            <div className="card text-center">
              <div className="text-3xl font-bold text-purple-400">
                {stats?.total_tva?.toFixed(2) || stats?.ca_ht ? (stats.ca_ttc - stats.ca_ht).toFixed(2) : '0.00'}€
              </div>
              <div className="text-sm text-gray-400 mt-1">TVA collectee</div>
            </div>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-2 gap-6 mb-6">
            {/* Par comptoir */}
            <div className="card">
              <h3 className="font-semibold mb-4">CA par comptoir</h3>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={comptoirData} dataKey="ca" nameKey="name" outerRadius={80} label>
                    {comptoirData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Par creneau */}
            <div className="card">
              <h3 className="font-semibold mb-4">Commandes par creneau</h3>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={creneauData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="heure" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: 8 }}
                  />
                  <Bar dataKey="commandes" fill="#F97316" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top produits */}
          <div className="card">
            <h3 className="font-semibold mb-4">Top 10 Produits</h3>
            <div className="space-y-2">
              {stats?.top_produits?.map((p, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500 w-6">{i + 1}.</span>
                    <span>{p.produit_nom}</span>
                  </div>
                  <div className="flex gap-6 text-gray-400">
                    <span>{p.quantite_vendue} vendus</span>
                    <span className="text-pizza-400 font-medium">{p.ca_ttc.toFixed(2)}€</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {tab === 'commandes' && (
        <div className="card">
          <h3 className="font-semibold mb-4">Commandes du jour ({todayOrders.length})</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-700">
                <th className="text-left py-2">N°</th>
                <th className="text-left">Comptoir</th>
                <th className="text-left">Mode</th>
                <th className="text-left">Client</th>
                <th className="text-left">Statut</th>
                <th className="text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {todayOrders.map((cmd) => (
                <tr key={cmd.id} className="border-b border-gray-700/50">
                  <td className="py-2 font-mono">{cmd.numero}</td>
                  <td>
                    <span className={COMPTOIR_CONFIG[cmd.comptoir]?.badge || ''}>
                      {COMPTOIR_CONFIG[cmd.comptoir]?.icone} {COMPTOIR_CONFIG[cmd.comptoir]?.nom}
                    </span>
                  </td>
                  <td>{cmd.mode === 'emporter' ? '🛍️' : '🛵'} {cmd.mode}</td>
                  <td className="text-gray-400">{cmd.client?.nom || '-'}</td>
                  <td>{cmd.statut}</td>
                  <td className="text-right font-medium">{cmd.montant_ttc?.toFixed(2)}€</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'ticket-z' && ticketZ && (
        <div className="card max-w-lg">
          <h3 className="font-semibold mb-4">🧾 Ticket Z - {ticketZ.date}</h3>
          <div className="space-y-3 font-mono text-sm">
            <div className="flex justify-between">
              <span>Nombre de commandes</span>
              <span className="font-bold">{ticketZ.nb_commandes}</span>
            </div>
            <div className="flex justify-between text-lg">
              <span>CA TTC</span>
              <span className="font-bold text-pizza-400">{ticketZ.ca_ttc.toFixed(2)}€</span>
            </div>
            <div className="flex justify-between">
              <span>CA HT</span>
              <span>{ticketZ.ca_ht.toFixed(2)}€</span>
            </div>
            <div className="flex justify-between">
              <span>TVA</span>
              <span>{ticketZ.total_tva.toFixed(2)}€</span>
            </div>
            <hr className="border-gray-700" />
            <div className="font-semibold">Par comptoir :</div>
            {Object.entries(ticketZ.par_comptoir || {}).map(([k, v]) => (
              <div key={k} className="flex justify-between ml-4">
                <span>{COMPTOIR_CONFIG[k]?.nom || k}</span>
                <span>{v.toFixed(2)}€</span>
              </div>
            ))}
            <hr className="border-gray-700" />
            <div className="font-semibold">Par paiement :</div>
            {Object.entries(ticketZ.par_mode_paiement || {}).map(([k, v]) => (
              <div key={k} className="flex justify-between ml-4">
                <span>{k}</span>
                <span>{v.toFixed(2)}€</span>
              </div>
            ))}
            <hr className="border-gray-700" />
            <div className="flex justify-between">
              <span>Total especes</span>
              <span>{ticketZ.total_especes.toFixed(2)}€</span>
            </div>
            <div className="flex justify-between">
              <span>Total CB</span>
              <span>{ticketZ.total_cb.toFixed(2)}€</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
