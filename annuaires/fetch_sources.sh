#!/bin/bash
# Télécharge les sources officielles nécessaires aux deux générateurs.
#
#   bash annuaires/fetch_sources.sh [RÉPERTOIRE]   (défaut : annuaires/cache)
#
# Les fichiers ne sont pas versionnés : ils pèsent ~7 Mo et sont republiés
# régulièrement par leurs producteurs. Ce script les remet en place à
# l'identique.
set -uo pipefail
CACHE="${1:-$(dirname "$0")/cache}"
mkdir -p "$CACHE"

telecharger() {  # url fichier libellé
  for i in 1 2 3 4 5 6 7 8; do
    if curl -sSL --max-time 120 -H "User-Agent: annuaire-maires-bot/1.0" "$1" -o "$2" && [ -s "$2" ]; then
      echo "OK    $3 ($(stat -c%s "$2") octets)"; return 0
    fi
    sleep $(( i < 5 ? i*2 : 10 ))
  done
  echo "ÉCHEC $3"; return 1
}

# ── Populations de référence 2023 (décret du 26/12/2025, en vigueur au 01/01/2026)
telecharger "https://www.insee.fr/fr/statistiques/fichier/8680726/ensemble.xlsx" \
            "$CACHE/insee_pop2023.xlsx" "populations INSEE 2023"

# ── Répertoire National des Élus : maires en exercice
RNE=$(curl -sSL --max-time 90 -H "User-Agent: annuaire-maires-bot/1.0" \
      "https://www.data.gouv.fr/api/1/datasets/repertoire-national-des-elus-1/" \
      | python3 -c "import json,sys
d=json.load(sys.stdin)
print(next(r['url'] for r in d['resources']
           if 'maire' in r.get('title','').lower() and r.get('format')=='csv'))")
telecharger "$RNE" "$CACHE/elus-maire.csv" "RNE — maires"

# ── Résultats officiels du second tour des municipales 2026 (audit des maires)
T2=$(curl -sSL --max-time 90 -H "User-Agent: annuaire-maires-bot/1.0" \
     "https://www.data.gouv.fr/api/1/datasets/elections-municipales-2026-resultats-du-second-tour/" \
     | python3 -c "import json,sys
d=json.load(sys.stdin)
for r in d['resources']:
    t=r.get('title','').lower()
    if 'communes' in t and 'municipales 2026' in t and 'bv' not in t \
       and 'polynésie' not in t and 'arrondissement' not in t:
        print(r['url']); break")
telecharger "$T2" "$CACHE/t2.csv" "résultats second tour 2026"

# ── Coordonnées des mairies : Annuaire de l'administration (DILA)
python3 - "$CACHE" <<'PY'
import json, pathlib, subprocess, sys, urllib.parse, urllib.request
cache = pathlib.Path(sys.argv[1])
codes = json.loads(subprocess.run(
    [sys.executable, str(pathlib.Path(__file__).parent / "codes_paca.py"), str(cache)],
    capture_output=True, text=True).stdout or "[]")
BASE = ("https://api-lannuaire.service-public.fr/api/explore/v2.1/catalog/datasets/"
        "api-lannuaire-administration/records")
SELECT = ("code_insee_commune,nom,adresse,telephone,adresse_courriel,"
          "formulaire_contact,site_internet")
records = {}
for i in range(0, len(codes), 14):
    where = 'pivot LIKE "mairie" AND code_insee_commune IN (%s)' % ", ".join(
        f'"{c}"' for c in codes[i:i + 14])
    url = f"{BASE}?where={urllib.parse.quote(where)}&limit=100&select={SELECT}"
    for _ in range(8):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                for rec in json.loads(r.read()).get("results", []):
                    records.setdefault(rec["code_insee_commune"], rec)
            break
        except Exception:
            pass
(cache / "mairies.json").write_text(json.dumps(records, ensure_ascii=False, indent=1))
print(f"OK    mairies ({len(records)} / {len(codes)})")
PY
