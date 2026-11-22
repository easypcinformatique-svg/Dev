import { useState } from 'react'
import { genererQuestions, chargerMeilleurScore, sauverMeilleurScore } from '../utils.js'

const NB_QUESTIONS = 10

function messageFinal(score) {
  if (score === 10) return { emoji: '🏆', texte: 'Parfait ! Tu es un vrai globe-trotteur !' }
  if (score >= 8) return { emoji: '🌟', texte: 'Excellent ! Le monde n\'a presque plus de secret pour toi.' }
  if (score >= 6) return { emoji: '✈️', texte: 'Beau voyage ! Encore un effort pour le sans-faute.' }
  if (score >= 4) return { emoji: '🧭', texte: 'Pas mal ! Continue d\'explorer, tu progresses.' }
  return { emoji: '🎒', texte: 'Le voyage ne fait que commencer. Rejoue pour apprendre !' }
}

export default function Quiz({ config, onQuitter }) {
  const [questions, setQuestions] = useState(() =>
    genererQuestions(config.continent, config.sens, NB_QUESTIONS)
  )
  const [index, setIndex] = useState(0)
  const [score, setScore] = useState(0)
  const [serie, setSerie] = useState(0)
  const [reponse, setReponse] = useState(null)
  const [fini, setFini] = useState(false)

  const q = questions[index]
  const cleScore = `best:${config.continent}:${config.sens}`

  function repondre(choix) {
    if (reponse !== null) return
    setReponse(choix)
    if (choix === q.bonne) {
      setScore(score + 1)
      setSerie(serie + 1)
    } else {
      setSerie(0)
    }
  }

  function suivante() {
    if (index + 1 >= questions.length) {
      sauverMeilleurScore(cleScore, score)
      setFini(true)
    } else {
      setIndex(index + 1)
      setReponse(null)
    }
  }

  if (fini) {
    const { emoji, texte } = messageFinal(score)
    const record = chargerMeilleurScore(cleScore)
    return (
      <div className="ecran resultat">
        <div className="emoji-final" aria-hidden="true">{emoji}</div>
        <h1>{score} / {questions.length}</h1>
        <p className="message-final">{texte}</p>
        <p className="record">🏆 Record : {record}/{questions.length}</p>
        <button className="bouton-principal" onClick={() => {
          setQuestions(genererQuestions(config.continent, config.sens, NB_QUESTIONS))
          setIndex(0); setScore(0); setSerie(0); setReponse(null); setFini(false)
        }}>
          Rejouer
        </button>
        <button className="bouton-secondaire" onClick={onQuitter}>Menu principal</button>
      </div>
    )
  }

  return (
    <div className="ecran quiz">
      <header className="entete-quiz">
        <button className="bouton-fermer" onClick={onQuitter} aria-label="Quitter la partie">✕</button>
        <div className="barre-progression" role="progressbar" aria-valuenow={index + 1} aria-valuemin={1} aria-valuemax={questions.length} aria-label={`Question ${index + 1} sur ${questions.length}`}>
          <div className="barre-remplie" style={{ width: `${((index + 1) / questions.length) * 100}%` }} />
        </div>
        <div className="infos-quiz">
          <span>Question {index + 1}/{questions.length}</span>
          <span>⭐ {score}{serie >= 2 ? ` · 🔥 ${serie}` : ''}</span>
        </div>
      </header>

      <main className="corps-quiz">
        <div className="drapeau" aria-hidden="true">{q.drapeau}</div>
        <h2 className="question">{q.question}</h2>

        <div className="choix">
          {q.choix.map((c) => {
            let classe = 'bouton-choix'
            if (reponse !== null) {
              if (c === q.bonne) classe += ' correct'
              else if (c === reponse) classe += ' incorrect'
              else classe += ' estompe'
            }
            return (
              <button key={c} className={classe} onClick={() => repondre(c)} disabled={reponse !== null}>
                {c}
              </button>
            )
          })}
        </div>

        <div aria-live="polite">
          {reponse !== null && (
            <div className="panneau-feedback">
              <p className={`verdict ${reponse === q.bonne ? 'bon' : 'mauvais'}`}>
                {reponse === q.bonne
                  ? '✅ Bonne réponse !'
                  : `❌ La bonne réponse était : ${q.bonne}`}
              </p>
              {q.anecdote && (
                <p className="anecdote"><strong>💡 Le savais-tu ?</strong> {q.anecdote}</p>
              )}
              <button className="bouton-principal" onClick={suivante} autoFocus>
                {index + 1 >= questions.length ? 'Voir le résultat' : 'Question suivante'}
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
