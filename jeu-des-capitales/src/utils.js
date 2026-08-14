import PAYS from './data/pays.json'
import ANECDOTES from './data/anecdotes.json'

export const CONTINENTS = [
  'Europe',
  'Asie',
  'Afrique',
  'Amérique du Nord',
  'Amérique du Sud',
  'Océanie',
]

export function listePays(continent) {
  if (!continent || continent === 'Monde') return PAYS
  return PAYS.filter((p) => p.continent === continent)
}

export function melanger(tableau) {
  const copie = [...tableau]
  for (let i = copie.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copie[i], copie[j]] = [copie[j], copie[i]]
  }
  return copie
}

function distracteurs(bon, sens, nombre) {
  const cle = sens === 'pc' ? 'capitale' : 'pays'
  const memesContinent = PAYS.filter(
    (p) => p.continent === bon.continent && p[cle] !== bon[cle]
  )
  const autres = PAYS.filter(
    (p) => p.continent !== bon.continent && p[cle] !== bon[cle]
  )
  const pool = melanger(memesContinent).concat(melanger(autres))
  const choisis = []
  const vus = new Set([bon[cle]])
  for (const p of pool) {
    if (choisis.length >= nombre) break
    if (vus.has(p[cle])) continue
    vus.add(p[cle])
    choisis.push(p[cle])
  }
  return choisis
}

// sens : 'pc' (pays → capitale), 'cp' (capitale → pays) ou 'mixte'
export function genererQuestions(continent, sens, nombre) {
  const pool = melanger(listePays(continent)).slice(0, nombre)
  return pool.map((p) => {
    const sensReel = sens === 'mixte' ? (Math.random() < 0.5 ? 'pc' : 'cp') : sens
    const bonne = sensReel === 'pc' ? p.capitale : p.pays
    const choix = melanger([bonne, ...distracteurs(p, sensReel, 3)])
    return {
      drapeau: p.drapeau,
      pays: p.pays,
      capitale: p.capitale,
      continent: p.continent,
      sens: sensReel,
      question:
        sensReel === 'pc'
          ? `Quelle est la capitale de ce pays : ${p.pays} ?`
          : `${p.capitale} est la capitale de quel pays ?`,
      bonne,
      choix,
      anecdote: ANECDOTES[p.pays] || null,
    }
  })
}

export function chargerMeilleurScore(cle) {
  try {
    const v = localStorage.getItem(`capital-defi:${cle}`)
    return v ? Number(v) : 0
  } catch {
    return 0
  }
}

export function sauverMeilleurScore(cle, score) {
  try {
    const actuel = chargerMeilleurScore(cle)
    if (score > actuel) {
      localStorage.setItem(`capital-defi:${cle}`, String(score))
      return true
    }
  } catch {
    /* stockage indisponible : le jeu reste jouable sans meilleurs scores */
  }
  return false
}
