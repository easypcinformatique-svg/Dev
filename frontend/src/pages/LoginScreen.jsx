import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../shared/hooks/useAuthStore'

export default function LoginScreen() {
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuthStore()
  const navigate = useNavigate()

  const handleDigit = (digit) => {
    if (pin.length < 6) {
      setPin((p) => p + digit)
      setError('')
    }
  }

  const handleDelete = () => setPin((p) => p.slice(0, -1))

  const handleSubmit = async () => {
    if (pin.length < 4 || loading) return
    setLoading(true)
    setError('')
    try {
      const user = await login(pin)
      if (user.role === 'pizzaiolo') navigate('/cuisine')
      else if (user.role === 'livreur') navigate('/livraisons')
      else navigate('/pos')
    } catch (err) {
      const msg = err?.response?.data?.detail || 'PIN incorrect'
      setError(msg)
      setPin('')
    } finally {
      setLoading(false)
    }
  }

  // Auto-submit quand 4 chiffres sont tapes
  const handleDigitAndCheck = (digit) => {
    const newPin = pin + digit
    if (newPin.length <= 6) {
      setPin(newPin)
      setError('')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="card w-80 text-center">
        <div className="text-5xl mb-4">🍕</div>
        <h1 className="text-2xl font-bold mb-1">PizzaCaisse</h1>
        <p className="text-gray-400 mb-6 text-sm">Entrez votre code PIN</p>

        {/* Affichage PIN */}
        <div className="flex justify-center gap-3 mb-4">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className={`w-4 h-4 rounded-full transition-colors ${
                i < pin.length ? 'bg-pizza-500' : 'bg-gray-600'
              }`}
            />
          ))}
        </div>

        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
        {loading && <p className="text-pizza-400 text-sm mb-4">Connexion...</p>}

        {/* Pave numerique */}
        <div className="grid grid-cols-3 gap-2">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((digit) => (
            <button
              key={digit}
              onClick={() => handleDigitAndCheck(String(digit))}
              disabled={loading}
              className="btn-secondary text-xl h-14 active:bg-gray-600"
            >
              {digit}
            </button>
          ))}
          <button onClick={handleDelete} disabled={loading} className="btn-secondary text-xl h-14">
            ←
          </button>
          <button
            onClick={() => handleDigitAndCheck('0')}
            disabled={loading}
            className="btn-secondary text-xl h-14"
          >
            0
          </button>
          <button
            onClick={handleSubmit}
            disabled={pin.length < 4 || loading}
            className="btn-primary text-xl h-14"
          >
            ✓
          </button>
        </div>
      </div>
    </div>
  )
}
