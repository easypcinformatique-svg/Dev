import { useState } from 'react'
import Accueil from './components/Accueil.jsx'
import Quiz from './components/Quiz.jsx'
import Duel from './components/Duel.jsx'
import Atlas from './components/Atlas.jsx'

export default function App() {
  const [partie, setPartie] = useState(null)

  if (!partie) {
    return <Accueil onJouer={(config) => setPartie(config)} />
  }
  if (partie.mode === 'atlas') {
    return <Atlas onQuitter={() => setPartie(null)} />
  }
  if (partie.mode === 'duel') {
    return <Duel config={partie} onQuitter={() => setPartie(null)} />
  }
  return <Quiz config={partie} onQuitter={() => setPartie(null)} />
}
