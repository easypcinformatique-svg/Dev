// Carte du monde stylisée « carnet de voyage » — dessinée à la main en SVG,
// aucune ressource externe. Chaque continent est cliquable.
const FORMES = {
  'Amérique du Nord':
    'M14,52 Q8,40 22,34 Q34,24 52,30 Q68,22 84,30 Q98,36 94,48 Q100,56 92,64 Q96,74 86,80 Q88,90 78,92 Q74,102 66,96 Q56,98 50,88 Q38,86 32,76 Q20,70 22,60 Z',
  'Amérique du Sud':
    'M70,106 Q76,96 86,102 Q98,104 98,116 Q102,130 94,144 Q90,162 82,172 Q74,180 70,166 Q62,150 65,134 Q60,120 66,112 Z',
  'Europe':
    'M150,52 Q146,40 158,36 Q164,22 176,28 Q186,20 192,30 Q202,34 198,44 Q204,52 196,58 Q188,66 176,62 Q162,68 154,60 Z',
  'Afrique':
    'M150,74 Q158,64 174,68 Q190,62 200,72 Q208,82 200,92 Q210,102 202,116 Q198,132 188,144 Q184,158 174,152 Q162,148 160,132 Q152,118 155,102 Q147,86 150,74 Z',
  'Asie':
    'M200,38 Q202,24 220,26 Q244,16 268,22 Q296,16 316,28 Q334,34 328,48 Q338,58 324,66 Q318,80 302,76 Q294,90 280,82 Q276,98 264,90 Q254,102 246,88 Q232,94 224,82 Q210,78 212,64 Q200,56 204,48 Z',
  'Océanie':
    'M288,132 Q294,122 310,126 Q326,124 332,136 Q338,150 326,158 Q312,166 298,160 Q286,156 286,144 Z',
}

const ETIQUETTES = {
  'Amérique du Nord': { x: 54, y: 62 },
  'Amérique du Sud': { x: 81, y: 140 },
  'Europe': { x: 175, y: 47 },
  'Afrique': { x: 178, y: 110 },
  'Asie': { x: 268, y: 54 },
  'Océanie': { x: 310, y: 145 },
}

export default function CarteMonde({ selection, onSelect }) {
  return (
    <svg
      className="carte-monde"
      viewBox="0 0 352 195"
      role="group"
      aria-label="Carte du monde : choisis un continent"
    >
      {/* petites îles décoratives */}
      <circle cx="103" cy="30" r="6" className="ile" />
      <circle cx="242" cy="112" r="3" className="ile" />
      <circle cx="252" cy="120" r="2.4" className="ile" />
      <circle cx="342" cy="166" r="3" className="ile" />
      <circle cx="123" cy="128" r="2" className="ile" />

      {Object.entries(FORMES).map(([continent, d]) => (
        <path
          key={continent}
          d={d}
          className={`continent ${selection === continent ? 'choisi' : ''}`}
          role="button"
          tabIndex={0}
          aria-pressed={selection === continent}
          aria-label={continent}
          onClick={() => onSelect(continent)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              onSelect(continent)
            }
          }}
        >
          <title>{continent}</title>
        </path>
      ))}

      {Object.entries(ETIQUETTES).map(([continent, pos]) => (
        <text key={continent} x={pos.x} y={pos.y} className="etiquette-continent">
          {continent.replace('Amérique du ', 'Am. ')}
        </text>
      ))}
    </svg>
  )
}
