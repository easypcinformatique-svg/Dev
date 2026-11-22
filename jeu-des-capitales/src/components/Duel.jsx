import { useState } from 'react'
import { genererQuestions } from '../utils.js'

const NB_QUESTIONS = 8

// Duel local : 2 joueurs sur le même écran, moitié haute retournée.
// Le premier qui touche la bonne réponse marque le point.
// Une mauvaise réponse bloque le joueur pour la question en cours.
export default function Duel({ config, onQuitter }) {
  const [questions, setQuestions] = useState(() =>
    genererQuestions(config.continent, config.sens, NB_QUESTIONS)
  )
  const [index, setIndex] = useState(0)
  const [scores, setScores] = useState({ j1: 0, j2: 0 })
  const [bloques, setBloques] = useState({ j1: false, j2: false })
  const [erreurs, setErreurs] = useState({ j1: null, j2: null })
  const [gagnantQuestion, setGagnantQuestion] = useState(null) // 'j1' | 'j2' | 'personne'
  const [fini, setFini] = useState(false)

  const q = questions[index]
  const enFeedback = gagnantQuestion !== null

  function repondre(joueur, choix) {
    if (enFeedback || bloques[joueur]) return
    if (choix === q.bonne) {
      setScores({ ...scores, [joueur]: scores[joueur] + 1 })
      setGagnantQuestion(joueur)
    } else {
      const nouveauxBloques = { ...bloques, [joueur]: true }
      setBloques(nouveauxBloques)
      setErreurs({ ...erreurs, [joueur]: choix })
      if (nouveauxBloques.j1 && nouveauxBloques.j2) setGagnantQuestion('personne')
    }
  }

  function suivante() {
    if (index + 1 >= questions.length) {
      setFini(true)
    } else {
      setIndex(index + 1)
      setBloques({ j1: false, j2: false })
      setErreurs({ j1: null, j2: null })
      setGagnantQuestion(null)
    }
  }

  function rejouer() {
    setQuestions(genererQuestions(config.continent, config.sens, NB_QUESTIONS))
    setIndex(0)
    setScores({ j1: 0, j2: 0 })
    setBloques({ j1: false, j2: false })
    setErreurs({ j1: null, j2: null })
    setGagnantQuestion(null)
    setFini(false)
  }

  if (fini) {
    const titre =
      scores.j1 === scores.j2
        ? '🤝 Égalité parfaite !'
        : scores.j1 > scores.j2
          ? '🔵 Joueur 1 remporte le duel !'
          : '🔴 Joueur 2 remporte le duel !'
    return (
      <div className="ecran resultat">
        <div className="emoji-final" aria-hidden="true">🏆</div>
        <h1>{titre}</h1>
        <p className="message-final score-duel-final">
          <span className="badge-j1">Joueur 1 : {scores.j1}</span>
          <span className="badge-j2">Joueur 2 : {scores.j2}</span>
        </p>
        <button className="bouton-principal" onClick={rejouer}>Revanche !</button>
        <button className="bouton-secondaire" onClick={onQuitter}>Menu principal</button>
      </div>
    )
  }

  function moitie(joueur) {
    const bloque = bloques[joueur]
    return (
      <div className={`moitie ${joueur === 'j2' ? 'retournee' : ''}`}>
        <div className="drapeau drapeau-duel" aria-hidden="true">{q.drapeau}</div>
        <p className="question question-duel">{q.question}</p>
        <div className="choix choix-duel">
          {q.choix.map((c) => {
            let classe = 'bouton-choix bouton-duel'
            if (enFeedback && c === q.bonne) classe += ' correct'
            else if (erreurs[joueur] === c) classe += ' incorrect'
            else if (enFeedback || bloque) classe += ' estompe'
            return (
              <button
                key={c}
                className={classe}
                onClick={() => repondre(joueur, c)}
                disabled={enFeedback || bloque}
              >
                {c}
              </button>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="ecran duel">
      {moitie('j2')}

      <div className="barre-centrale">
        <button className="bouton-fermer" onClick={onQuitter} aria-label="Quitter le duel">✕</button>
        <span className="badge-j2">🔴 {scores.j2}</span>
        <span className="manche">{index + 1}/{questions.length}</span>
        <span className="badge-j1">🔵 {scores.j1}</span>
        {enFeedback && (
          <button className="bouton-principal bouton-suivant-duel" onClick={suivante}>
            {gagnantQuestion === 'personne' ? 'Personne ! →' : index + 1 >= questions.length ? 'Résultat →' : 'Suivant →'}
          </button>
        )}
      </div>

      {moitie('j1')}
    </div>
  )
}
