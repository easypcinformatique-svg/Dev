import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../shared/utils/api'
import { useWebSocket } from '../../shared/hooks/useWebSocket'
import { COMPTOIR_CONFIG, STATUT_CONFIG, TAILLE_LABELS } from '../../shared/utils/constants'

export default function KitchenScreen() {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState('active') // active, all

  const { data: commandes = [], refetch } = useQuery({
    queryKey: ['kitchen-orders'],
    queryFn: () =>
      api.get('/api/commandes/', {
        params: { jour: new Date().toISOString().split('T')[0] },
      }).then((r) => r.data),
    refetchInterval: 30000,
  })

  const onWsMessage = useCallback(
    (msg) => {
      if (['new_order', 'order_status_changed', 'order_cancelled'].includes(msg.event)) {
        refetch()
      }
    },
    [refetch]
  )

  const { connected } = useWebSocket(onWsMessage)

  const updateStatus = useMutation({
    mutationFn: ({ id, statut }) =>
      api.patch(`/api/commandes/${id}/statut`, { statut }).then((r) => r.data),
    onSuccess: () => refetch(),
  })

  // Filtrer les commandes actives
  const activeStatuts = ['nouvelle', 'en_preparation', 'prete']
  const displayed = filter === 'active'
    ? commandes.filter((c) => activeStatuts.includes(c.statut))
    : commandes

  // Grouper par creneau
  const byCreneau = {}
  displayed.forEach((c) => {
    const label = c.creneau?.label || 'Sans creneau'
    if (!byCreneau[label]) byCreneau[label] = []
    byCreneau[label].push(c)
  })

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold">👨‍🍳 Ecran Cuisine</h1>
          <span
            className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}
            title={connected ? 'Connecte' : 'Deconnecte'}
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('active')}
            className={`px-3 py-1 rounded-lg text-sm ${
              filter === 'active' ? 'bg-pizza-500 text-white' : 'bg-gray-700 text-gray-300'
            }`}
          >
            En cours ({commandes.filter((c) => activeStatuts.includes(c.statut)).length})
          </button>
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1 rounded-lg text-sm ${
              filter === 'all' ? 'bg-pizza-500 text-white' : 'bg-gray-700 text-gray-300'
            }`}
          >
            Tout ({commandes.length})
          </button>
        </div>
      </div>

      {/* Colonnes par creneau */}
      <div className="flex-1 overflow-x-auto p-4">
        <div className="flex gap-4 min-h-full">
          {Object.entries(byCreneau).map(([creneau, orders]) => (
            <div key={creneau} className="flex-shrink-0 w-80">
              <div className="bg-gray-800 rounded-t-lg px-4 py-2 font-semibold text-sm border-b border-gray-700">
                🕐 {creneau} ({orders.length})
              </div>
              <div className="space-y-3 mt-3">
                {orders.map((order) => (
                  <OrderCard
                    key={order.id}
                    order={order}
                    onStatusChange={(statut) =>
                      updateStatus.mutate({ id: order.id, statut })
                    }
                  />
                ))}
              </div>
            </div>
          ))}
          {Object.keys(byCreneau).length === 0 && (
            <div className="flex-1 flex items-center justify-center text-gray-500 text-xl">
              Aucune commande en cours
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function OrderCard({ order, onStatusChange }) {
  const comptoir = COMPTOIR_CONFIG[order.comptoir] || {}
  const statut = STATUT_CONFIG[order.statut] || {}
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const created = new Date(order.created_at)
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - created.getTime()) / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [order.created_at])

  const minutes = Math.floor(elapsed / 60)
  const seconds = elapsed % 60
  const timerColor = minutes >= 20 ? 'text-red-400' : minutes >= 10 ? 'text-yellow-400' : 'text-green-400'

  const nextAction = {
    nouvelle: { label: 'Preparer', statut: 'en_preparation', style: 'btn-primary' },
    en_preparation: { label: 'Prete !', statut: 'prete', style: 'btn-success' },
    prete: null,
  }[order.statut]

  return (
    <div
      className="card border-l-4"
      style={{ borderLeftColor: comptoir.couleur || '#666' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-bold">{order.numero}</span>
          <span className={comptoir.badge || 'badge'}>
            {comptoir.icone} {comptoir.nom}
          </span>
        </div>
        <span className={`font-mono text-sm ${timerColor}`}>
          {minutes}:{seconds.toString().padStart(2, '0')}
        </span>
      </div>

      {/* Mode */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-gray-400">
          {order.mode === 'emporter' ? '🛍️ Emporter' : '🛵 Livraison'}
        </span>
        {order.client?.nom && (
          <span className="text-xs text-gray-400">• {order.client.nom}</span>
        )}
      </div>

      {/* Lignes */}
      <div className="space-y-1 mb-3">
        {order.lignes?.map((l, i) => (
          <div key={i} className="text-sm">
            <span className="font-medium">
              {l.quantite}x {l.produit?.nom || `Produit #${l.produit_id}`}
            </span>
            {l.taille && (
              <span className="text-gray-400 ml-1">
                ({TAILLE_LABELS[l.taille?.taille] || l.taille})
              </span>
            )}
            {l.notes && (
              <div className="text-xs text-yellow-400 ml-4">→ {l.notes}</div>
            )}
            {l.supplements?.map((s, j) => (
              <div key={j} className="text-xs text-gray-400 ml-4">
                + {s.supplement?.nom || `Sup #${s.supplement_id}`}
              </div>
            ))}
          </div>
        ))}
      </div>

      {order.notes && (
        <div className="text-xs text-yellow-400 bg-yellow-500/10 rounded p-2 mb-3">
          📝 {order.notes}
        </div>
      )}

      {/* Action button */}
      {nextAction && (
        <button
          onClick={() => onStatusChange(nextAction.statut)}
          className={`${nextAction.style} w-full text-sm py-2`}
        >
          {nextAction.label}
        </button>
      )}
      {order.statut === 'prete' && (
        <div className="text-center text-green-400 font-semibold text-sm py-2">
          ✅ PRETE
        </div>
      )}
    </div>
  )
}
