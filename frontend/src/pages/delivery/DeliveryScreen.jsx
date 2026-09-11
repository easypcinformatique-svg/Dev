import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../../shared/utils/api'
import { COMPTOIR_CONFIG } from '../../shared/utils/constants'

export default function DeliveryScreen() {
  const { data: commandes = [], refetch: refetchCommandes } = useQuery({
    queryKey: ['delivery-orders'],
    queryFn: () => api.get('/api/livraisons/en-attente').then((r) => r.data),
    refetchInterval: 10000,
  })

  const { data: livreurs = [] } = useQuery({
    queryKey: ['livreurs'],
    queryFn: () => api.get('/api/livraisons/livreurs').then((r) => r.data),
  })

  const { data: enCours = [] } = useQuery({
    queryKey: ['delivery-en-cours'],
    queryFn: () =>
      api.get('/api/commandes/', { params: { statut: 'en_livraison' } }).then((r) => r.data),
    refetchInterval: 10000,
  })

  const assigner = useMutation({
    mutationFn: (data) => api.post('/api/livraisons/assigner', data),
    onSuccess: () => refetchCommandes(),
  })

  const marquerLivree = useMutation({
    mutationFn: (id) => api.patch(`/api/livraisons/${id}/livree`),
    onSuccess: () => refetchCommandes(),
  })

  const livreursDispos = livreurs.filter((l) => l.statut === 'disponible')

  return (
    <div className="p-6 h-full overflow-auto">
      <h1 className="text-2xl font-bold mb-6">🛵 Gestion Livraisons</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Commandes a livrer */}
        <div>
          <h2 className="text-lg font-semibold mb-3">
            Pretes a livrer ({commandes.length})
          </h2>
          <div className="space-y-3">
            {commandes.map((cmd) => {
              const comptoir = COMPTOIR_CONFIG[cmd.comptoir] || {}
              return (
                <div key={cmd.id} className="card">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold">{cmd.numero}</span>
                    <span className={comptoir.badge || 'badge'}>
                      {comptoir.icone} {comptoir.nom}
                    </span>
                  </div>
                  {cmd.client && (
                    <div className="text-sm text-gray-400 mb-1">
                      {cmd.client.nom} - {cmd.client.telephone}
                    </div>
                  )}
                  {cmd.adresse_livraison && (
                    <div className="text-sm mb-2">📍 {cmd.adresse_livraison}</div>
                  )}
                  <div className="text-sm font-semibold text-pizza-400 mb-3">
                    {cmd.montant_ttc?.toFixed(2)}€
                  </div>

                  {/* Assigner livreur */}
                  <div className="flex gap-2">
                    {livreursDispos.map((l) => (
                      <button
                        key={l.id}
                        onClick={() =>
                          assigner.mutate({ commande_id: cmd.id, livreur_id: l.id })
                        }
                        className="btn-primary text-xs py-2 px-3"
                      >
                        🛵 {l.nom}
                      </button>
                    ))}
                    {livreursDispos.length === 0 && (
                      <span className="text-gray-500 text-sm">Aucun livreur disponible</span>
                    )}
                  </div>
                </div>
              )
            })}
            {commandes.length === 0 && (
              <p className="text-gray-500 text-center py-8">Aucune commande en attente</p>
            )}
          </div>
        </div>

        {/* En cours de livraison */}
        <div>
          <h2 className="text-lg font-semibold mb-3">
            En livraison ({enCours.length})
          </h2>
          <div className="space-y-3">
            {enCours.map((cmd) => (
              <div key={cmd.id} className="card border-l-4 border-purple-500">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold">{cmd.numero}</span>
                  <span className="text-sm text-purple-400">En livraison</span>
                </div>
                {cmd.client && (
                  <div className="text-sm text-gray-400 mb-1">
                    {cmd.client?.nom} - {cmd.adresse_livraison}
                  </div>
                )}
                <button
                  onClick={() => marquerLivree.mutate(cmd.id)}
                  className="btn-success w-full text-sm py-2 mt-2"
                >
                  ✅ Marquer comme livree
                </button>
              </div>
            ))}
            {enCours.length === 0 && (
              <p className="text-gray-500 text-center py-8">Aucune livraison en cours</p>
            )}
          </div>
        </div>
      </div>

      {/* Livreurs */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-3">Livreurs</h2>
        <div className="flex gap-4">
          {livreurs.map((l) => (
            <div key={l.id} className="card flex items-center gap-3">
              <span
                className={`w-3 h-3 rounded-full ${
                  l.statut === 'disponible' ? 'bg-green-500' : 'bg-yellow-500'
                }`}
              />
              <span className="font-medium">{l.nom}</span>
              <span className="text-xs text-gray-400">{l.telephone}</span>
              <span className="text-xs text-gray-500">{l.statut}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
