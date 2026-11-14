#!/usr/bin/env python3
"""Contrôle exhaustif des liens du site en ligne : internes, externes, ancres
et ressources. On explore toutes les pages atteignables, pas seulement celles
du sitemap, et on interroge chaque cible pour de vrai."""
import re, sys, time, json, collections, concurrent.futures as cf
import urllib.request, urllib.error
from urllib.parse import urljoin, urldefrag, urlparse

HOTE = (sys.argv[1] if len(sys.argv) > 1 else "https://pizzanapolicarpentras.fr").rstrip("/")
UA = {"User-Agent": "Mozilla/5.0 (compatible; verif-liens/1.0)"}


def requete(url, methode="GET", essais=3):
    """L'hébergeur limite les requêtes : on réessaie avant de conclure."""
    for n in range(essais):
        try:
            r = urllib.request.urlopen(
                urllib.request.Request(url, headers=UA, method=methode), timeout=25)
            return r.status, r.read().decode("utf-8", "replace") if methode == "GET" else ""
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:
                return e.code, ""
        except Exception:
            pass
        time.sleep(1.5 * (n + 1))
    return 0, ""


# ---------- exploration ----------
a_voir, vues, pages = [HOTE + "/"], set(), {}
while a_voir:
    lot = [u for u in a_voir if u not in vues][:8]
    a_voir = [u for u in a_voir if u not in lot]
    if not lot:
        break
    vues.update(lot)
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for u, (st, corps) in zip(lot, ex.map(lambda x: requete(x), lot)):
            pages[u] = (st, corps)
            if st != 200:
                continue
            for href in re.findall(r'(?:href|src)="([^"]+)"', corps):
                abs_ = urldefrag(urljoin(u, href))[0]
                if abs_.startswith(HOTE) and re.search(r"(/|\.html)$", abs_) and abs_ not in vues:
                    a_voir.append(abs_)
print(f"{len(pages)} pages explorées")

# ---------- collecte des liens ----------
internes, externes, ancres, ressources = collections.defaultdict(set), collections.defaultdict(set), [], collections.defaultdict(set)
for u, (st, corps) in pages.items():
    if st != 200:
        continue
    ids = set(re.findall(r'\sid="([^"]+)"', corps)) | set(re.findall(r'\sname="([^"]+)"', corps))
    for attr, href in re.findall(r'(href|src)="([^"]+)"', corps):
        if href.startswith(("mailto:", "tel:", "javascript:", "data:")):
            continue
        if href.startswith("#"):
            cible = href[1:]
            if cible and cible not in ids:
                ancres.append((u, href))
            continue
        abs_ = urljoin(u, href)
        base, frag = urldefrag(abs_)
        if base.startswith(HOTE):
            (ressources if attr == "src" or re.search(r"\.(webp|jpg|jpeg|png|svg|ico|css|js|pdf|xml|txt)$", base) else internes)[base].add(u)
            if frag and base == u and frag not in ids:
                ancres.append((u, href))
        elif abs_.startswith(("http://", "https://")):
            externes[base].add(u)

print(f"{len(internes)} liens internes · {len(ressources)} ressources · {len(externes)} liens externes")


def verifier(url):
    st, _ = requete(url)
    return url, st


casses_int, casses_res, casses_ext, redir = [], [], [], []
with cf.ThreadPoolExecutor(max_workers=6) as ex:
    for url, st in ex.map(verifier, sorted(internes)):
        if st != 200:
            (redir if st in (301, 308) else casses_int).append((url, st))
with cf.ThreadPoolExecutor(max_workers=6) as ex:
    for url, st in ex.map(verifier, sorted(ressources)):
        if st != 200:
            casses_res.append((url, st))
with cf.ThreadPoolExecutor(max_workers=4) as ex:
    for url, st in ex.map(verifier, sorted(externes)):
        if st in (0,) or st >= 400:
            casses_ext.append((url, st))

print("\n" + "=" * 70)
print("CONTRÔLE DES LIENS — " + HOTE)
print("=" * 70)
mauvaises = [(u, st) for u, (st, _) in pages.items() if st != 200]
print(f"\nPages explorées en erreur : {len(mauvaises)}")
for u, st in mauvaises[:10]:
    print(f"   {st}  {u[len(HOTE):]}")
print(f"\nLiens internes cassés : {len(casses_int)}")
for u, st in casses_int[:15]:
    print(f"   {st}  {u[len(HOTE):]}   (depuis {', '.join(x[len(HOTE):] or '/' for x in list(internes[u])[:2])})")
print(f"\nLiens internes redirigés : {len(redir)}")
for u, st in redir[:10]:
    print(f"   {st}  {u[len(HOTE):]}")
print(f"\nRessources manquantes (images, css, js) : {len(casses_res)}")
for u, st in casses_res[:15]:
    print(f"   {st}  {u[len(HOTE):]}   (depuis {', '.join(x[len(HOTE):] or '/' for x in list(ressources[u])[:2])})")
print(f"\nAncres pointant dans le vide : {len(ancres)}")
for u, h in ancres[:12]:
    print(f"   {h}   sur {u[len(HOTE):] or '/'}")
print(f"\nLiens externes en échec : {len(casses_ext)}")
for u, st in casses_ext[:15]:
    print(f"   {st or 'injoignable'}  {u[:80]}   (depuis {', '.join(x[len(HOTE):] or '/' for x in list(externes[u])[:2])})")
print(f"\nLiens externes vérifiés : {len(externes)}")
for u in sorted(externes):
    if u not in dict(casses_ext):
        print(f"   ok  {u[:86]}")
json.dump({"casses_int": casses_int, "casses_res": casses_res, "casses_ext": casses_ext,
           "ancres": ancres, "redir": redir}, open("liens.json", "w"), ensure_ascii=False, indent=1)
