import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../../shared/utils/api'
import { TAILLE_LABELS } from '../../shared/utils/constants'

export default function OnlineMenu() {
  const [cart, setCart] = useState([])
  const [mode, setMode] = useState('emporter')
  const [nom, setNom] = useState('')
  const [tel, setTel] = useState('')
  const [adresse, setAdresse] = useState('')
  const [creneauId, setCreneauId] = useState(null)
  const [step, setStep] = useState('menu') // menu, checkout, confirmation
  const [orderResult, setOrderResult] = useState(null)

  const { data: menu = [] } = useQuery({
    queryKey: ['online-menu'],
    queryFn: () => api.get('/api/menu/', { params: { actif: true } }).then((r) => r.data),
  })

  const { data: creneaux = [] } = useQuery({
    queryKey: ['online-creneaux'],
    queryFn: () => api.get('/api/creneaux/', { params: { disponibles_only: true } }).then((r) => r.data),
  })

  const createOrder = useMutation({
    mutationFn: (data) => api.post('/api/commandes/', data).then((r) => r.data),
    onSuccess: (data) => {
      setOrderResult(data)
      setStep('confirmation')
    },
  })

  const addToCart = (produit, taille) => {
    setCart((prev) => [
      ...prev,
      {
        id: Date.now(),
        produit_id: produit.id,
        produit_nom: produit.nom,
        taille_id: taille.id,
        taille_label: TAILLE_LABELS[taille.taille],
        prix: taille.prix,
      },
    ])
  }

  const removeFromCart = (id) => setCart((prev) => prev.filter((i) => i.id !== id))
  const total = cart.reduce((sum, i) => sum + i.prix, 0)

  const handleSubmit = () => {
    createOrder.mutate({
      comptoir: 'web',
      mode,
      client_nom: nom,
      client_telephone: tel,
      creneau_id: creneauId || undefined,
      adresse_livraison: mode === 'livraison' ? adresse : undefined,
      lignes: cart.map((item) => ({
        produit_id: item.produit_id,
        taille_id: item.taille_id,
        quantite: 1,
        supplements: [],
      })),
    })
  }

  if (step === 'confirmation' && orderResult) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="card max-w-md w-full text-center">
          <div className="text-6xl mb-4">✅</div>
          <h1 className="text-2xl font-bold mb-2">Commande confirmee !</h1>
          <p className="text-3xl font-bold text-pizza-400 mb-2">{orderResult.numero}</p>
          <p className="text-gray-400 mb-4">Total : {orderResult.montant_ttc?.toFixed(2)}€</p>
          <a
            href={`/suivi/${orderResult.numero}`}
            className="btn-primary inline-block"
          >
            Suivre ma commande
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 py-4 px-6 sticky top-0 z-10 border-b border-gray-700">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold">🍕 Commander en ligne</h1>
          {cart.length > 0 && (
            <button
              onClick={() => setStep(step === 'menu' ? 'checkout' : 'menu')}
              className="btn-primary text-sm"
            >
              {step === 'menu' ? `🛒 Panier (${cart.length}) - ${total.toFixed(2)}€` : '← Retour au menu'}
            </button>
          )}
        </div>
      </header>

      <div className="max-w-4xl mx-auto p-4">
        {step === 'menu' && (
          <>
            {menu.map((cat) => (
              <div key={cat.id} className="mb-8">
                <h2 className="text-lg font-bold mb-3 text-pizza-400">{cat.nom}</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {cat.produits?.filter((p) => p.actif).map((produit) => (
                    <div key={produit.id} className="card">
                      <h3 className="font-semibold mb-1">{produit.nom}</h3>
                      {produit.description && (
                        <p className="text-xs text-gray-400 mb-3">{produit.description}</p>
                      )}
                      <div className="flex flex-wrap gap-2">
                        {produit.tailles?.map((t) => (
                          <button
                            key={t.id}
                            onClick={() => addToCart(produit, t)}
                            className="px-3 py-2 text-sm bg-gray-700 hover:bg-pizza-500 rounded-lg transition-colors"
                          >
                            {TAILLE_LABELS[t.taille]} - {t.prix.toFixed(2)}€
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </>
        )}

        {step === 'checkout' && (
          <div className="max-w-md mx-auto">
            <h2 className="text-lg font-bold mb-4">Votre commande</h2>

            {/* Panier */}
            <div className="space-y-2 mb-6">
              {cart.map((item) => (
                <div key={item.id} className="card flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm">{item.produit_nom}</div>
                    <div className="text-xs text-gray-400">{item.taille_label}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-semibold">{item.prix.toFixed(2)}€</span>
                    <button onClick={() => removeFromCart(item.id)} className="text-red-400">✕</button>
                  </div>
                </div>
              ))}
              <div className="text-right text-xl font-bold text-pizza-400">
                Total : {total.toFixed(2)}€
              </div>
            </div>

            {/* Mode */}
            <div className="flex gap-2 mb-4">
              {['emporter', 'livraison'].map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`flex-1 py-3 rounded-lg font-medium ${
                    mode === m ? 'bg-pizza-500 text-white' : 'bg-gray-800 text-gray-300'
                  }`}
                >
                  {m === 'emporter' ? '🛍️ A emporter' : '🛵 Livraison'}
                </button>
              ))}
            </div>

            {/* Formulaire */}
            <div className="space-y-3 mb-4">
              <input className="input" placeholder="Votre nom *" value={nom} onChange={(e) => setNom(e.target.value)} />
              <input className="input" placeholder="Telephone *" value={tel} onChange={(e) => setTel(e.target.value)} />
              {mode === 'livraison' && (
                <input className="input" placeholder="Adresse de livraison *" value={adresse} onChange={(e) => setAdresse(e.target.value)} />
              )}
              <select
                className="input"
                value={creneauId || ''}
                onChange={(e) => setCreneauId(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">-- Choisir un creneau --</option>
                {creneaux.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label} ({c.nb_commandes}/{c.capacite_max} commandes)
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleSubmit}
              disabled={!nom || !tel || cart.length === 0 || createOrder.isPending}
              className="btn-primary w-full py-4 text-lg"
            >
              {createOrder.isPending ? 'Envoi...' : `Commander - ${total.toFixed(2)}€`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
