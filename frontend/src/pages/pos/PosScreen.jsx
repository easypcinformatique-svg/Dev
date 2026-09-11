import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../shared/utils/api'
import { TAILLE_LABELS } from '../../shared/utils/constants'

export default function PosScreen() {
  const queryClient = useQueryClient()
  const [cart, setCart] = useState([])
  const [selectedCat, setSelectedCat] = useState(null)
  const [mode, setMode] = useState('emporter')
  const [clientTel, setClientTel] = useState('')
  const [clientNom, setClientNom] = useState('')
  const [adresse, setAdresse] = useState('')
  const [creneauId, setCreneauId] = useState(null)
  const [notes, setNotes] = useState('')
  const [showPayment, setShowPayment] = useState(false)
  const [lastOrder, setLastOrder] = useState(null)

  const { data: menu = [] } = useQuery({
    queryKey: ['menu'],
    queryFn: () => api.get('/api/menu/').then((r) => r.data),
  })

  const { data: creneaux = [] } = useQuery({
    queryKey: ['creneaux'],
    queryFn: () => api.get('/api/creneaux/', { params: { disponibles_only: true } }).then((r) => r.data),
  })

  const createOrder = useMutation({
    mutationFn: (data) => api.post('/api/commandes/', data).then((r) => r.data),
    onSuccess: (data) => {
      setLastOrder(data)
      setShowPayment(true)
      queryClient.invalidateQueries(['creneaux'])
    },
  })

  const payOrder = useMutation({
    mutationFn: (data) => api.post('/api/caisse/encaisser', data).then((r) => r.data),
    onSuccess: () => {
      setCart([])
      setClientTel('')
      setClientNom('')
      setAdresse('')
      setNotes('')
      setCreneauId(null)
      setShowPayment(false)
      setLastOrder(null)
    },
  })

  const categories = menu
  const activeCat = selectedCat || categories[0]?.id
  const produits = categories.find((c) => c.id === activeCat)?.produits || []

  const addToCart = (produit, taille) => {
    setCart((prev) => [
      ...prev,
      {
        id: Date.now(),
        produit_id: produit.id,
        produit_nom: produit.nom,
        taille_id: taille.id,
        taille_label: TAILLE_LABELS[taille.taille] || taille.taille,
        prix: taille.prix,
        quantite: 1,
        notes: '',
        supplements: [],
      },
    ])
  }

  const removeFromCart = (id) => setCart((prev) => prev.filter((i) => i.id !== id))

  const total = cart.reduce((sum, item) => sum + item.prix * item.quantite, 0)

  const handleOrder = () => {
    createOrder.mutate({
      comptoir: 'accueil',
      mode,
      client_telephone: clientTel || undefined,
      client_nom: clientNom || undefined,
      creneau_id: creneauId || undefined,
      adresse_livraison: mode === 'livraison' ? adresse : undefined,
      notes: notes || undefined,
      lignes: cart.map((item) => ({
        produit_id: item.produit_id,
        taille_id: item.taille_id,
        quantite: item.quantite,
        notes: item.notes || undefined,
        supplements: item.supplements,
      })),
    })
  }

  const handlePay = (modePaiement) => {
    if (!lastOrder) return
    payOrder.mutate({
      commande_id: lastOrder.id,
      paiements: [{ mode: modePaiement, montant: lastOrder.montant_ttc }],
    })
  }

  return (
    <div className="flex h-full">
      {/* Colonne gauche : Menu */}
      <div className="flex-1 flex flex-col p-4 overflow-hidden">
        {/* Onglets categories */}
        <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCat(cat.id)}
              className={`px-4 py-2 rounded-lg whitespace-nowrap font-medium transition-colors ${
                activeCat === cat.id
                  ? 'bg-pizza-500 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {cat.nom}
            </button>
          ))}
        </div>

        {/* Grille produits */}
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 overflow-y-auto flex-1">
          {produits.filter((p) => p.actif).map((produit) => (
            <div key={produit.id} className="card hover:ring-2 hover:ring-pizza-500 cursor-pointer">
              <h3 className="font-semibold text-sm mb-2">{produit.nom}</h3>
              {produit.description && (
                <p className="text-xs text-gray-400 mb-2 line-clamp-2">{produit.description}</p>
              )}
              <div className="flex flex-wrap gap-1">
                {produit.tailles?.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => addToCart(produit, t)}
                    className="px-2 py-1 text-xs bg-gray-700 hover:bg-pizza-500 rounded transition-colors"
                  >
                    {TAILLE_LABELS[t.taille] || t.taille} {t.prix.toFixed(2)}€
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Colonne droite : Panier */}
      <div className="w-96 bg-gray-800 flex flex-col border-l border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-bold mb-3">Commande</h2>

          {/* Toggle emporter / livraison */}
          <div className="flex gap-2 mb-3">
            {['emporter', 'livraison'].map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                  mode === m ? 'bg-pizza-500 text-white' : 'bg-gray-700 text-gray-300'
                }`}
              >
                {m === 'emporter' ? '🛍️ Emporter' : '🛵 Livraison'}
              </button>
            ))}
          </div>

          {/* Client */}
          <div className="grid grid-cols-2 gap-2 mb-2">
            <input
              className="input text-sm py-2"
              placeholder="Telephone"
              value={clientTel}
              onChange={(e) => setClientTel(e.target.value)}
            />
            <input
              className="input text-sm py-2"
              placeholder="Nom"
              value={clientNom}
              onChange={(e) => setClientNom(e.target.value)}
            />
          </div>
          {mode === 'livraison' && (
            <input
              className="input text-sm py-2 mb-2"
              placeholder="Adresse de livraison"
              value={adresse}
              onChange={(e) => setAdresse(e.target.value)}
            />
          )}

          {/* Creneau */}
          <select
            className="input text-sm py-2"
            value={creneauId || ''}
            onChange={(e) => setCreneauId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">-- Creneau horaire --</option>
            {creneaux.map((c) => (
              <option key={c.id} value={c.id} disabled={!c.disponible}>
                {c.label} ({c.nb_commandes}/{c.capacite_max})
              </option>
            ))}
          </select>
        </div>

        {/* Lignes du panier */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {cart.length === 0 && (
            <p className="text-gray-500 text-center mt-8">Panier vide</p>
          )}
          {cart.map((item) => (
            <div key={item.id} className="flex items-center justify-between bg-gray-700 rounded-lg p-3">
              <div className="flex-1">
                <div className="text-sm font-medium">{item.produit_nom}</div>
                <div className="text-xs text-gray-400">{item.taille_label}</div>
              </div>
              <div className="text-sm font-semibold mr-3">{item.prix.toFixed(2)}€</div>
              <button
                onClick={() => removeFromCart(item.id)}
                className="text-red-400 hover:text-red-300 text-lg"
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        {/* Total et validation */}
        <div className="p-4 border-t border-gray-700">
          <textarea
            className="input text-sm py-2 mb-3 h-16 resize-none"
            placeholder="Notes commande..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <div className="flex justify-between items-center mb-3">
            <span className="text-lg font-bold">Total TTC</span>
            <span className="text-2xl font-bold text-pizza-400">
              {total.toFixed(2)}€
            </span>
          </div>
          <button
            onClick={handleOrder}
            disabled={cart.length === 0 || createOrder.isPending}
            className="btn-primary w-full text-lg py-4"
          >
            {createOrder.isPending ? 'Envoi...' : 'Valider la commande'}
          </button>
        </div>

        {/* Modal paiement */}
        {showPayment && lastOrder && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="card w-96 text-center">
              <h2 className="text-xl font-bold mb-2">Commande {lastOrder.numero}</h2>
              <p className="text-3xl font-bold text-pizza-400 mb-6">
                {lastOrder.montant_ttc.toFixed(2)}€
              </p>
              <div className="grid grid-cols-2 gap-3">
                <button onClick={() => handlePay('especes')} className="btn-success py-4 text-lg">
                  💵 Especes
                </button>
                <button onClick={() => handlePay('cb')} className="btn-primary py-4 text-lg">
                  💳 CB
                </button>
                <button onClick={() => handlePay('ticket_restaurant')} className="btn-secondary py-4">
                  🎫 Ticket Resto
                </button>
                <button onClick={() => setShowPayment(false)} className="btn-secondary py-4">
                  ⏳ Plus tard
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
