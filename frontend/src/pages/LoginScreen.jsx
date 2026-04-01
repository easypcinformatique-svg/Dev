import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../shared/hooks/useAuthStore'

export default function LoginScreen() {
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const { login } = useAuthStore()
  const navigate = useNavigate()

  const handleDigit = (digit) => {
    if (pin.length < 6) setPin((p) => p + digit)
  }

  const handleDelete = () => setPin((p) => p.slice(0, -1))

  const handleSubmit = async () => {
    try {
      setError('')
      const user = await login(pin)
      if (user.role === 'pizzaiolo') navigate('/cuisine')
      else if (user.role === 'livreur') navigate('/livraisons')
      else navigate('/pos')
    } catch {
      setError('PIN incorrect')
      setPin('')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="card w-80 text-center">
        <div className="text-5xl mb-4">🍕</div>
        <h1 className="text-2xl font-bold mb-2">PizzaCaisse</h1>
        <p className="text-gray-400 mb-6 text-sm">Entrez votre code PIN</p>

        {/* Affichage PIN */}
        <div className="flex justify-center gap-2 mb-4">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className={`w-4 h-4 rounded-full ${
                i < pin.length ? 'bg-pizza-500' : 'bg-gray-600'
              }`}
            />
          ))}
        </div>

        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

        {/* Pave numerique */}
        <div className="grid grid-cols-3 gap-2">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((digit) => (
            <button
              key={digit}
              onClick={() => handleDigit(String(digit))}
              className="btn-secondary text-xl h-14"
            >
              {digit}
            </button>
          ))}
          <button onClick={handleDelete} className="btn-secondary text-xl h-14">
            ←
          </button>
          <button
            onClick={() => handleDigit('0')}
            className="btn-secondary text-xl h-14"
          >
            0
          </button>
          <button
            onClick={handleSubmit}
            disabled={pin.length < 4}
            className="btn-primary text-xl h-14"
          >
            ✓
          </button>
        </div>
      </div>
    </div>
  )
}
