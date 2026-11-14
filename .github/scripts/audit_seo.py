#!/usr/bin/env python3
"""Audit SEO technique du site en ligne : redirections, indexabilité, codes de
réponse, balisage, maillage, poids. Tout est mesuré par des requêtes réelles,
rien n'est déduit du dépôt."""
import re, sys, json, time, gzip, concurrent.futures as cf
import urllib.request, urllib.error
from urllib.parse import urljoin, urlparse
from html import unescape

HOTE = sys.argv[1] if len(sys.argv) > 1 else "https://pizzanapolicarpentras.fr"
UA = {"User-Agent": "Mozilla/5.0 (compatible; audit-seo/1.0)"}
constats = []


def note(gravite, code, titre, detail=""):
    constats.append({"gravite": gravite, "code": code, "titre": titre, "detail": detail})


class Entetes(dict):
    """Les serveurs n'ont pas tous la même casse : « Location » ou « location »."""
    def get(self, cle, defaut=None):
        for k, v in self.items():
            if k.lower() == cle.lower():
                return v
        return defaut


def requete(url, methode="GET", suivre=False):
    class Sans(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    op = urllib.request.build_opener(*([] if suivre else [Sans]))
    req = urllib.request.Request(url, headers=UA, method=methode)
    try:
        r = op.open(req, timeout=25)
        corps = r.read() if methode == "GET" else b""
        if r.headers.get("Content-Encoding") == "gzip":
            corps = gzip.decompress(corps)
        return r.status, Entetes(r.headers), corps.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            corps = e.read().decode("utf-8", "replace")
        except Exception:
            corps = ""
        return e.code, Entetes(e.headers), corps
    except Exception as e:
        return 0, Entetes({"erreur": str(e)}), ""


# ---------- 1. redirections ----------
print("1. Redirections…")
attendu = HOTE.rstrip("/")
essais = [
    ("http://pizzanapolicarpentras.fr/", attendu + "/", "HTTP vers HTTPS"),
    ("https://www.pizzanapolicarpentras.fr/", attendu + "/", "www vers domaine nu"),
    ("http://www.pizzanapolicarpentras.fr/", attendu + "/", "HTTP+www vers HTTPS nu"),
]
for url, cible, libelle in essais:
    st, h, _ = requete(url)
    loc = h.get("Location", "")
    if st in (301, 308) and loc.rstrip("/") == cible.rstrip("/"):
        note("ok", "R", libelle, f"{st} → {loc}")
    elif st in (302, 307):
        note("important", "R", libelle + " : redirection temporaire",
             f"{st} au lieu de 301 — le jus de lien ne se transmet pas durablement")
    else:
        note("critique", "R", libelle + " absente", f"code {st}, Location « {loc} »")

# même page atteignable de plusieurs façons = contenu dupliqué
for chemin, libelle in (("/index.html", "/index.html"), ("/?utm_source=test", "paramètre d'URL")):
    st, h, corps = requete(attendu + chemin, suivre=True)
    if st == 200:
        can = re.search(r'rel="canonical" href="([^"]+)"', corps)
        if not can or can.group(1).rstrip("/") != attendu:
            note("important", "R", f"{libelle} accessible sans canonique vers l'accueil",
                 f"canonique = {can.group(1) if can else 'absente'}")

# ---------- 2. sitemap et robots ----------
print("2. Sitemap et robots.txt…")
st, _, robots = requete(attendu + "/robots.txt")
if st != 200:
    note("critique", "I", "robots.txt absent", f"code {st}")
else:
    if "Sitemap:" not in robots:
        note("important", "I", "robots.txt ne déclare pas le sitemap")
    if re.search(r"^Disallow:\s*/\s*$", robots, re.M):
        note("critique", "I", "robots.txt interdit tout le site")

st, _, sm = requete(attendu + "/sitemap.xml")
urls = re.findall(r"<loc>([^<]+)</loc>", sm) if st == 200 else []
if st != 200:
    note("critique", "I", "sitemap.xml inaccessible", f"code {st}")
else:
    note("ok", "I", f"sitemap.xml : {len(urls)} URL déclarées")
    hors = [u for u in urls if not u.startswith(attendu)]
    if hors:
        note("important", "I", "URL du sitemap sur un autre hôte", ", ".join(hors[:3]))

# ---------- 3. chaque page ----------
print(f"3. Analyse de {len(urls)} pages…")
pages = {}


def charger(u):
    """L'hébergeur limite les requêtes parallèles et répond 503 par rafales :
    un essai unique transformerait un ralentissement en « page en erreur »."""
    for essai in range(3):
        st, h, corps = requete(u)
        if st not in (0, 429) and st < 500:
            return u, st, h, corps
        time.sleep(1.5 * (essai + 1))
    return u, st, h, corps


with cf.ThreadPoolExecutor(max_workers=6) as ex:
    for u, st, h, corps in ex.map(charger, urls):
        pages[u] = (st, h, corps)

titres, descs, h1s, liens = {}, {}, {}, set()
for u, (st, h, corps) in pages.items():
    court = u[len(attendu):] or "/"
    if st != 200:
        note("critique", "P", f"page du sitemap en erreur : {court}", f"code {st}")
        continue
    t = re.search(r"<title>([^<]*)</title>", corps)
    titre = unescape(t.group(1)).strip() if t else ""
    d = re.search(r'<meta name="description" content="([^"]*)"', corps)
    desc = unescape(d.group(1)).strip() if d else ""
    hh = re.findall(r"<h1[^>]*>(.*?)</h1>", corps, re.S)
    can = re.search(r'rel="canonical" href="([^"]+)"', corps)
    rob = re.search(r'<meta name="robots" content="([^"]*)"', corps)

    if not titre:
        note("critique", "P", f"titre absent : {court}")
    else:
        titres.setdefault(titre, []).append(court)
        if len(titre) > 60:
            note("mineur", "P", f"titre tronqué dans Google ({len(titre)} car.) : {court}", titre[:70])
    if not desc:
        note("important", "P", f"meta description absente : {court}")
    else:
        descs.setdefault(desc, []).append(court)
        if not 70 <= len(desc) <= 165:
            note("mineur", "P", f"meta description de {len(desc)} car. : {court}")
    if len(hh) == 0:
        note("critique", "P", f"aucun H1 : {court}")
    elif len(hh) > 1:
        note("important", "P", f"{len(hh)} balises H1 : {court}")
    if rob and "noindex" in rob.group(1):
        if u in urls:
            note("critique", "I", f"page en noindex mais présente au sitemap : {court}")
    if can:
        cible = can.group(1)
        if cible.rstrip("/") != u.rstrip("/"):
            note("important", "I", f"canonique vers une autre page : {court}", f"→ {cible}")
    else:
        note("important", "I", f"canonique absente : {court}")

    if not re.search(r'<meta name="viewport"', corps):
        note("critique", "P", f"pas de balise viewport : {court}")
    if "application/ld+json" not in corps:
        note("important", "S", f"aucune donnée structurée : {court}")
    poids = len(corps.encode()) / 1024
    if poids > 250:
        note("mineur", "V", f"page de {poids:.0f} Ko : {court}")

    for href in re.findall(r'href="([^"#?]+)"', corps):
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        abs_ = urljoin(u, href)
        if abs_.startswith(attendu):
            liens.add(abs_.split("#")[0])

for titre, ou in titres.items():
    if len(ou) > 1:
        note("important", "P", f"titre identique sur {len(ou)} pages", f"« {titre[:60]} » — {', '.join(ou[:4])}")
for desc, ou in descs.items():
    if len(ou) > 1:
        note("important", "P", f"meta description identique sur {len(ou)} pages", ", ".join(ou[:4]))

def requete_reessai(u, methode="GET"):
    for essai in range(3):
        st, h, c = requete(u, methode)
        if st not in (0, 429) and st < 500:
            return st, h, c
        time.sleep(1.5 * (essai + 1))
    return st, h, c


# ---------- 4. liens internes ----------
print(f"4. Vérification de {len(liens)} liens internes…")
casses = []
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    for u, st, h, _ in ex.map(lambda x: (x,) + requete_reessai(x, 'HEAD'), sorted(liens)):
        if st in (404, 410, 0) or st >= 500:
            casses.append((u[len(attendu):], st))
        elif st in (301, 308):
            note("mineur", "L", f"lien interne redirigé : {u[len(attendu):]}", f"{st} → {h.get('Location','')}")
for chemin, st in casses:
    note("critique", "L", f"lien interne cassé : {chemin}", f"code {st}")

orphelines = [u[len(attendu):] or "/" for u in urls if u not in liens and u.rstrip("/") != attendu]
if orphelines:
    note("important", "L", f"{len(orphelines)} page(s) du sitemap sans lien entrant",
         ", ".join(orphelines[:6]))
hors_sitemap = []
for u in sorted(x for x in liens if x.endswith("/") and x not in urls and x.rstrip("/") != attendu):
    st, _h, corps = requete_reessai(u)
    if st != 200:
        continue
    rob = re.search(r'<meta name="robots" content="([^"]*)"', corps)
    can = re.search(r'rel="canonical" href="([^"]+)"', corps)
    # Exclusion légitime : la page demande à ne pas être indexée, ou désigne
    # une autre page comme version de référence.
    if rob and "noindex" in rob.group(1):
        continue
    if can and can.group(1).rstrip("/") != u.rstrip("/"):
        continue
    hors_sitemap.append(u)
if hors_sitemap:
    note("important", "I", f"{len(hors_sitemap)} page(s) indexable(s) liée(s) mais absente(s) du sitemap",
         ", ".join(x[len(attendu):] for x in hors_sitemap[:6]))

# ---------- 5. 404 ----------
print("5. Page 404…")
st, _, corps = requete(attendu + "/page-qui-nexiste-vraiment-pas-123/")
if st != 404:
    note("critique", "I", "une URL inexistante ne renvoie pas 404", f"code {st}")
elif not re.search(r"Pizza\s*Napoli", corps, re.I):
    note("mineur", "I", "page 404 sans habillage du site")
else:
    note("ok", "I", "page 404 correcte et personnalisée")

# ---------- rapport ----------
ordre = {"critique": 0, "important": 1, "mineur": 2, "ok": 3}
constats.sort(key=lambda c: (ordre[c["gravite"]], c["code"]))
compte = {}
for c in constats:
    compte[c["gravite"]] = compte.get(c["gravite"], 0) + 1
print("\n" + "=" * 72)
print("AUDIT SEO TECHNIQUE — " + HOTE)
print("=" * 72)
print("  " + " · ".join(f"{k} : {v}" for k, v in sorted(compte.items(), key=lambda x: ordre[x[0]])))
for g in ("critique", "important", "mineur", "ok"):
    lot = [c for c in constats if c["gravite"] == g]
    if not lot:
        continue
    print(f"\n--- {g.upper()} ({len(lot)}) ---")
    for c in lot:
        print(f"  [{c['code']}] {c['titre']}")
        if c["detail"]:
            print(f"        {c['detail'][:140]}")
json.dump(constats, open("audit_seo.json", "w"), ensure_ascii=False, indent=1)
