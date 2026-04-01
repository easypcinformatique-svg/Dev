import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useCallback } from 'react'
import api from '../../shared/utils/api'
import { useWebSocket } from '../../shared/hooks/useWebSocket'
import { STATUT_CONFIG, COMPTOIR_CONFIG } from '../../shared/utils/constants'

const STEPS = ['nouvelle', 'en_preparation', 'prete', 'en_livraison', 'livree']
const STEPS_EMPORTER = ['nouvelle', 'en_preparation', 'prete', 'recuperee']

export default function OnlineTrack() {
  const { numero } = useParams()

  const { data: commande, refetch } = useQuery({
    queryKey: ['track', numero],
    queryFn: () => api.get(`/api/commandes/numero/${numero}`).then((r) => r.data),
    refetchInterval: 15000,
  })

  const onWsMessage = useCallback(
    (msg) => {
      if (msg.data?.numero === numero) refetch()
    },
    [numero, refetch]
  )

  useWebSocket(onWsMessage)

  if (!commande) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-gray-400">Chargement...</div>
      </div>
    )
  }

  const steps = commande.mode === 'livraison' ? STEPS : STEPS_EMPORTER
  const currentIndex = steps.indexOf(commande.statut)

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="card max-w-md w-full">
        <div className="text-center mb-6">
          <h1 className="text-xl font-bold mb-1">Commande {commande.numero}</h1>
          <span className={COMPTOIR_CONFIG[commande.comptoir]?.badge || 'badge'}>
            {COMPTOIR_CONFIG[commande.comptoir]?.icone}{' '}
            {COMPTOIR_CONFIG[commande.comptoir]?.nom}
          </span>
        </div>

        {/* Progress */}
        <div className="flex items-center justify-between mb-8 px-4">
          {steps.map((step, i) => {
            const active = i <= currentIndex
            const config = STATUT_CONFIG[step]
            return (
              <div key={step} className="flex flex-col items-center flex-1">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold mb-1 ${
                    active ? config.couleur + ' text-white' : 'bg-gray-700 text-gray-500'
                  }`}
                >
                  {i + 1}
                </div>
                <span className={`text-[10px] text-center ${active ? config.text : 'text-gray-600'}`}>
                  {config.label}
                </span>
              </div>
            )
          })}
        </div>

        {/* Statut actuel */}
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">
            {commande.statut === 'nouvelle' && '⏳'}
            {commande.statut === 'en_preparation' && '👨‍🍳'}
            {commande.statut === 'prete' && '✅'}
            {commande.statut === 'en_livraison' && '🛵'}
            {commande.statut === 'livree' && '🎉'}
            {commande.statut === 'recuperee' && '🎉'}
          </div>
          <p className="text-lg font-semibold">
            {STATUT_CONFIG[commande.statut]?.label}
          </p>
        </div>

        {/* Detail */}
        <div className="border-t border-gray-700 pt-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Mode</span>
            <span>{commande.mode === 'emporter' ? '🛍️ A emporter' : '🛵 Livraison'}</span>
          </div>
          {commande.creneau && (
            <div className="flex justify-between">
              <span className="text-gray-400">Creneau</span>
              <span>{commande.creneau.label}</span>
            </div>
          )}
          <div className="flex justify-between text-lg font-bold mt-2">
            <span>Total</span>
            <span className="text-pizza-400">{commande.montant_ttc?.toFixed(2)}€</span>
          </div>
        </div>
      </div>
    </div>
  )
}
