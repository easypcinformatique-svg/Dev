import { useState } from 'react'
import { CONTINENTS, listePays, chargerMeilleurScore } from '../utils.js'

const SENS = [
  { id: 'pc', label: 'Pays → Capitale' },
  { id: 'cp', label: 'Capitale → Pays' },
  { id: 'mixte', label: 'Mélangé' },
]

export default function Accueil({ onJouer }) {
  const [mode, setMode] = useState('solo')
  const [continent, setContinent] = useState('Monde')
  const [sens, setSens] = useState('pc')

  const meilleur = chargerMeilleurScore(`best:${continent}:${sens}`)

  return (
    <div className="ecran accueil">
      <header className="entete-accueil">
        <div className="globe" aria-hidden="true">🌍</div>
        <h1>Capital Défi</h1>
        <p className="slogan">Le tour du monde des capitales, en famille</p>
      </header>

      <section aria-labelledby="titre-mode">
        <h2 id="titre-mode" className="titre-section">Mode de jeu</h2>
        <div className="grille-modes">
          <button
            className={`carte-mode ${mode === 'solo' ? 'actif' : ''}`}
            onClick={() => setMode('solo')}
            aria-pressed={mode === 'solo'}
          >
            <span className="icone-mode" aria-hidden="true">🎒</span>
            <span className="nom-mode">Solo</span>
            <span className="desc-mode">10 questions, à ton rythme</span>
          </button>
          <button
            className={`carte-mode ${mode === 'duel' ? 'actif' : ''}`}
            onClick={() => setMode('duel')}
            aria-pressed={mode === 'duel'}
          >
            <span className="icone-mode" aria-hidden="true">⚔️</span>
            <span className="nom-mode">Duel</span>
            <span className="desc-mode">2 joueurs, 1 écran, le plus rapide gagne</span>
          </button>
        </div>
      </section>

      <section aria-labelledby="titre-continent">
        <h2 id="titre-continent" className="titre-section">Destination</h2>
        <div className="chips">
          {['Monde', ...CONTINENTS].map((c) => (
            <button
              key={c}
              className={`chip ${continent === c ? 'actif' : ''}`}
              onClick={() => setContinent(c)}
              aria-pressed={continent === c}
            >
              {c === 'Monde' ? '🌐 Monde entier' : c}
              <span className="compte">{listePays(c).length}</span>
            </button>
          ))}
        </div>
      </section>

      <section aria-labelledby="titre-sens">
        <h2 id="titre-sens" className="titre-section">Sens des questions</h2>
        <div className="chips">
          {SENS.map((s) => (
            <button
              key={s.id}
              className={`chip ${sens === s.id ? 'actif' : ''}`}
              onClick={() => setSens(s.id)}
              aria-pressed={sens === s.id}
            >
              {s.label}
            </button>
          ))}
        </div>
      </section>

      {mode === 'solo' && meilleur > 0 && (
        <p className="meilleur-score">🏆 Ton record ici : {meilleur}/10</p>
      )}

      <button className="bouton-principal" onClick={() => onJouer({ mode, continent, sens })}>
        C'est parti !
      </button>

      <footer className="pied-accueil">
        197 pays · 100 % hors-ligne · sans publicité
      </footer>
    </div>
  )
}
