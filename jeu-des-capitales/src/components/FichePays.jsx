import DETAILS from '../data/details.json'
import ANECDOTES from '../data/anecdotes.json'

export default function FichePays({ pays, onRetour }) {
  const d = DETAILS[pays.pays] || {}
  const anecdote = ANECDOTES[pays.pays]

  const lignes = [
    { icone: '🏛️', titre: 'Capitale', valeur: pays.capitale },
    { icone: '🧭', titre: 'Continent', valeur: pays.continent },
    { icone: '👥', titre: 'Habitants', valeur: d.population },
    { icone: '📐', titre: 'Superficie', valeur: d.superficie },
    { icone: '🗣️', titre: 'Langue', valeur: d.langue },
    { icone: '💰', titre: 'Monnaie', valeur: d.monnaie },
  ].filter((l) => l.valeur)

  return (
    <div className="ecran fiche-pays">
      <header className="entete-fiche">
        <button className="bouton-fermer" onClick={onRetour} aria-label="Retour à l'atlas">←</button>
      </header>

      <div className="heros-fiche">
        <div className="drapeau drapeau-fiche" aria-hidden="true">{pays.drapeau}</div>
        <h1>{pays.pays}</h1>
        <p className="sous-titre-fiche">{pays.capitale}</p>
      </div>

      <dl className="details-fiche">
        {lignes.map((l) => (
          <div className="ligne-detail" key={l.titre}>
            <dt><span aria-hidden="true">{l.icone}</span> {l.titre}</dt>
            <dd>{l.valeur}</dd>
          </div>
        ))}
      </dl>

      {anecdote && (
        <p className="anecdote carte-anecdote">
          <strong>💡 Le savais-tu ?</strong> {anecdote}
        </p>
      )}
    </div>
  )
}
