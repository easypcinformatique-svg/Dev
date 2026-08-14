import { useState } from 'react'
import { CONTINENTS, listePays } from '../utils.js'
import FichePays from './FichePays.jsx'

function normaliser(texte) {
  return texte
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
}

export default function Atlas({ onQuitter }) {
  const [continent, setContinent] = useState('Monde')
  const [recherche, setRecherche] = useState('')
  const [paysOuvert, setPaysOuvert] = useState(null)

  if (paysOuvert) {
    return <FichePays pays={paysOuvert} onRetour={() => setPaysOuvert(null)} />
  }

  const terme = normaliser(recherche.trim())
  const resultats = listePays(continent)
    .filter(
      (p) =>
        terme === '' ||
        normaliser(p.pays).includes(terme) ||
        normaliser(p.capitale).includes(terme)
    )
    .sort((a, b) => a.pays.localeCompare(b.pays, 'fr'))

  return (
    <div className="ecran atlas">
      <header className="entete-quiz">
        <div className="ligne-entete-atlas">
          <button className="bouton-fermer" onClick={onQuitter} aria-label="Retour au menu">←</button>
          <h1 className="titre-atlas">🗺️ Atlas</h1>
        </div>
        <input
          type="search"
          className="champ-recherche"
          placeholder="Cherche un pays ou une capitale…"
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          aria-label="Rechercher un pays ou une capitale"
        />
        <div className="chips chips-defilantes">
          {['Monde', ...CONTINENTS].map((c) => (
            <button
              key={c}
              className={`chip chip-compacte ${continent === c ? 'actif' : ''}`}
              onClick={() => setContinent(c)}
              aria-pressed={continent === c}
            >
              {c === 'Monde' ? '🌐 Tous' : c}
            </button>
          ))}
        </div>
      </header>

      <p className="compte-resultats" aria-live="polite">
        {resultats.length} pays
      </p>

      {resultats.length === 0 ? (
        <div className="vide-atlas">
          <p aria-hidden="true" className="emoji-vide">🔍</p>
          <p>Aucun pays trouvé pour « {recherche} ».</p>
          <p className="astuce-vide">Vérifie l'orthographe ou essaie un autre continent.</p>
        </div>
      ) : (
        <ul className="liste-pays">
          {resultats.map((p) => (
            <li key={p.pays}>
              <button className="ligne-pays" onClick={() => setPaysOuvert(p)}>
                <span className="drapeau-liste" aria-hidden="true">{p.drapeau}</span>
                <span className="nom-pays-liste">
                  <strong>{p.pays}</strong>
                  <span className="capitale-liste">{p.capitale}</span>
                </span>
                <span className="chevron" aria-hidden="true">›</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
