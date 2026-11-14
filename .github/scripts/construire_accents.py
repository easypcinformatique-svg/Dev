"""Table désaccentué -> accentué pour les mots présents sur le site.
Index inversé construit sur une liste de fréquences du français (formes
fléchies réelles). Un mot n'est corrigé que s'il n'est pas lui-même un mot
français courant ET qu'il n'existe qu'une seule forme accentuée plausible.
« ou », « a », « cote », « sur » sont des mots : ils ne bougent jamais."""
import sys, re, os, glob, json, unicodedata
sys.path.insert(0, "dic")
from spylls.hunspell import Dictionary
from html import unescape

DICO = Dictionary.from_files("dic/index")

def valide(m):
    return DICO.lookup(m) or DICO.lookup(m.capitalize())

SITE, SEUIL = sys.argv[1], 40          # occurrences minimales dans le corpus de référence

def nu(m):
    return "".join(c for c in unicodedata.normalize("NFD", m.lower())
                   if unicodedata.category(c) != "Mn").replace("œ", "oe")

freq, index = {}, {}
for ligne in open("dic/fr_full.txt", encoding="utf-8", errors="ignore"):
    p = ligne.split()
    if len(p) != 2:
        continue
    mot, n = p[0], int(p[1])
    if n < SEUIL or not re.fullmatch(r"[a-zà-ÿœ'-]{2,}", mot):
        continue
    freq[mot] = freq.get(mot, 0) + n
    index.setdefault(nu(mot), {})[mot] = n
print(f"référence : {len(freq)} formes fléchies retenues (≥{SEUIL} occurrences)")

def texte(html):
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.DOTALL | re.I)
    return unescape(re.sub(r"<[^>]+>", " ", h))

jetons = {}
for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
    for mot in re.findall(r"[A-Za-zÀ-ÿœŒ]{3,}", texte(open(p, encoding="utf-8").read())):
        b = mot.lower()
        if b == nu(b):
            jetons[b] = jetons.get(b, 0) + 1

table, ambigus, inconnus = {}, {}, []
for mot, n in jetons.items():
    if valide(mot):
        continue                                  # mot français valide tel qu'écrit
    accentuees = {f: k for f, k in index.get(mot, {}).items() if f != mot and valide(f)}
    if not accentuees:
        inconnus.append(mot); continue
    if len(accentuees) == 1:
        table[mot] = next(iter(accentuees))
    else:
        ambigus[mot] = (n, sorted(accentuees, key=accentuees.get, reverse=True)[:4])

json.dump(table, open("accents.json", "w"), ensure_ascii=False, indent=0, sort_keys=True)
print(f"{len(jetons)} mots sans accent sur le site · {len(table)} corrections sûres · "
      f"{len(ambigus)} ambigus · {len(inconnus)} hors référence")
print("\nCorrections les plus fréquentes :")
for m in sorted(table, key=lambda m: -jetons[m])[:18]:
    print(f"  {m:18} ×{jetons[m]:<5} -> {table[m]}")
print("\nAmbigus, laissés tels quels :")
for m, (n, b) in sorted(ambigus.items(), key=lambda kv: -kv[1][0])[:12]:
    print(f"  {m:14} ×{n:<5} {', '.join(b)}")
