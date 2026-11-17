#!/usr/bin/env python3
"""Balayage approfondi : une adresse e-mail pour chaque organisme qui n'en a pas.

Part de la page de prospection, prend toutes les entrées sans adresse et, pour
chacune, cherche d'abord son site puis une adresse publiée sur ce site.

Trouver le site, par ordre de confiance :
  1. une source qui le donne : BANATIC, annuaire de l'éducation, annuaire des
     Epl, lien de contact officiel déjà dans la page, Wikidata (par SIREN),
     OpenStreetMap (par SIRET) ;
  2. à défaut, des noms de domaine plausibles tirés du sigle et du nom. Un site
     ainsi trouvé n'est retenu que s'il se confirme lui-même : il affiche le
     SIREN de l'organisme, ou bien son code postal et au moins deux mots
     distinctifs de son nom.

Lire le site : l'accueil, puis les pages vers lesquelles il renvoie pour le
contact et les mentions légales. Les adresses masquées aux robots sont
restituées (« nom [at] domaine », protection Cloudflare, entités HTML).

Garde-fous sur l'adresse retenue : son domaine est celui du site ou un domaine
voisin, ou bien une messagerie grand public relevée sur une page de contact
(cas des petits syndicats). Les adresses de prestataires, de délégués à la
protection des données, de presse et de recrutement sont écartées. Rien n'est
deviné : aucune adresse n'est construite à partir d'un nom de personne.

Usage : python3 annuaires/fouille_profonde.py CACHE
"""
import html as htmllib
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parent
PAGE = RACINE / "annuaire-prospection-paca.html"
EPL = RACINE / "annuaire-sem-spl-syndicats.html"
SORTIE = ICI / "contacts_complementaires.json"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36", "Accept-Language": "fr-FR,fr;q=0.9"}

RE_MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
EXTENSIONS = ("fr", "com", "org", "net", "eu", "info", "pro", "coop", "mc", "email", "paris",
              "bzh", "immo", "io", "co", "biz", "sante", "tv")
REJET = re.compile(
    r"(wix|squarespace|wordpress|sentry|example|exemple|domain|domaine\.|votre|your|godaddy|ovh\.|"
    r"gandi|1and1|ionos|o2switch|webmaster|no-?reply|noreply|ne-pas-repondre|^dpo|dpd@|rgpd|cnil|"
    r"privacy|abuse|informatiqueetlibert|donnees-?personnelles|postmaster|presse@|press@|recrut|emploi@|candidat|rh@|jobs?@|newsletter|"
    r"nom@|prenom|email@|adresse@|xxx|test@|user@|john|doe@|"
    r"\.(png|jpe?g|gif|webp|svg|css|js|pdf)$|@(2x|3x)\.|@sentry|@google|@facebook|@twitter)", re.I)
PREFERES = ("contact", "accueil", "siege", "secretariat", "direction", "mairie", "courrier",
            "administration", "info", "dg", "president", "communication")
MESSAGERIES = ("orange.fr", "wanadoo.fr", "gmail.com", "free.fr", "laposte.net", "outlook.fr",
               "hotmail.fr", "hotmail.com", "sfr.fr", "yahoo.fr", "outlook.com", "live.fr",
               "neuf.fr", "bbox.fr", "nordnet.fr")
RE_LIEN = re.compile(r'<a\b[^>]*?href\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', re.I | re.S)
RE_UTILE = re.compile(r"contact|mention|l[eé]gal|coordonn|nous-joindre|nous-ecrire|joindre|"
                      r"qui-sommes|siege|si[eè]ge|infos?-pratiques|organisation|equipe|[eé]quipe", re.I)
CHEMINS = ["/contact", "/nous-contacter", "/contactez-nous", "/mentions-legales",
           "/mentions-legales/", "/contact/"]
VIDES = {"ASS", "ASSO", "ASSOC", "ASSOCIATION", "ASSOCIATIONS", "DE", "DU", "DES", "LA", "LE", "LES",
         "L", "D", "ET", "POUR", "EN", "AU", "AUX", "A", "SUR", "SM", "SYNDICAT", "MIXTE", "SOCIETE",
         "INTERCOMMUNAL", "SIVU", "SIVOM", "SA", "SEM", "SPL", "ANONYME", "HABITATIONS", "LOYER",
         "MODERE", "HLM", "OFFICE", "PUBLIC", "COMMUNAUTE", "COMMUNES", "AGGLOMERATION", "GESTION",
         "ORGANISME", "ORG", "OGEC", "CENTRE", "INSTITUT", "REGIONAL", "REGIONALE", "DEPARTEMENTAL",
         "DEPARTEMENTALE", "SERVICE", "SERVICES", "AIDE", "PAYS", "VALLEE", "CANTON", "D'ECONOMIE",
         "ECONOMIE", "LOCALE", "PUBLIQUE", "AMENAGEMENT", "DEVELOPPEMENT", "PROVENCE", "ALPES",
         "COTE", "AZUR", "SUD", "CAPITAL", "VARIABLE", "COOPERATIVE", "INTERET", "COLLECTIF"}


def norme(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").upper()
    return re.sub(r"[^A-Z0-9]+", " ", s).strip()


def cle_nom(nom, dept):
    return f"nom:{norme(nom)}|{dept}"


def lire(url, delai=8):
    """(URL finale, texte) ou ("", "")."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=delai) as r:
            if "html" not in (r.headers.get("Content-Type") or "html"):
                return "", ""
            brut = r.read(900_000)
            jeu = r.headers.get_content_charset() or "utf-8"
            try:
                return r.geturl(), brut.decode(jeu, errors="replace")
            except LookupError:
                return r.geturl(), brut.decode("utf-8", errors="replace")
    except Exception:
        return "", ""


def hote(url):
    return re.sub(r"^www\.", "", urllib.parse.urlsplit(url).netloc.lower().split(":")[0])


def decfemail(h):
    try:
        b = bytes.fromhex(h)
        return "".join(chr(c ^ b[0]) for c in b[1:])
    except ValueError:
        return ""


def demasquer(page):
    """Texte de la page avec les adresses masquées remises en clair."""
    t = page
    t = re.sub(r'data-cfemail="([0-9a-f]+)"', lambda m: f'>{decfemail(m.group(1))}<', t)
    t = re.sub(r"/cdn-cgi/l/email-protection#([0-9a-f]+)", lambda m: decfemail(m.group(1)), t)
    t = urllib.parse.unquote(htmllib.unescape(t))
    t = re.sub(r"\s*[\[\(\{]\s*(?:at|arobase|a)\s*[\]\)\}]\s*", "@", t, flags=re.I)
    t = re.sub(r"\s*[\[\(\{]\s*(?:dot|point)\s*[\]\)\}]\s*", ".", t, flags=re.I)
    t = re.sub(r"\s+(?:\(at\)|\[at\]|arobase)\s+", "@", t, flags=re.I)
    return t


# Adresses relevées sur un site mais qui ne sont pas celles de l'organisme
# (association hébergée par une mairie, antenne d'une autre région).
EXCLUES = {"cdvrcm@gmail.com", "contact@presenceverte-53-61-72.fr"}


def nettoyer(m):
    m = m.strip(".,;:)»\"'<>").lower()
    if "@" not in m or REJET.search(m) or m in EXCLUES:
        return ""
    local, dom = m.rsplit("@", 1)
    if not dom.endswith(tuple("." + e for e in EXTENSIONS)):
        c = re.match(r"^(.*\.(?:fr|com|org|net|eu))[a-z]+$", dom)   # « …@site.frTél »
        if not c:
            return ""
        dom = c.group(1)
    if len(local) < 2 or len(local) > 40 or re.fullmatch(r"[0-9a-f]{16,}", local):
        return ""
    return f"{local}@{dom}"


def adresses(page, site_hote, page_contact):
    """Adresses retenables d'une page, dans l'ordre de lecture."""
    racine = site_hote.split(".")[0]
    retenues = []
    for m in RE_MAIL.findall(demasquer(page)):
        m = nettoyer(m)
        if not m:
            continue
        d = m.split("@")[1]
        voisin = d == site_hote or d.endswith("." + site_hote) or site_hote.endswith("." + d) \
            or (len(racine) >= 5 and racine[:6] in d) or (len(d.split(".")[0]) >= 5 and d.split(".")[0][:6] in site_hote)
        if voisin or (page_contact and d in MESSAGERIES):
            retenues.append(m)
    return retenues


def choisir(liste):
    liste = list(dict.fromkeys(liste))
    if not liste:
        return ""
    for p in PREFERES:
        for m in liste:
            if m.split("@")[0].startswith(p):
                return m
    # À défaut de boîte générique, l'adresse la plus citée sur le site.
    return max(liste, key=liste.count) if liste else ""


def explorer(base):
    """Lit l'accueil et les pages de contact ; (hôte final, textes, adresses)."""
    final, accueil = lire(base)
    if not accueil:
        return "", [], []
    h = hote(final)
    textes, trouvees, vus, a_voir = [accueil], adresses(accueil, h, False), {final.rstrip("/")}, []
    for href, libelle in RE_LIEN.findall(accueil):
        if RE_UTILE.search(href) or RE_UTILE.search(re.sub(r"<[^>]+>", " ", libelle)):
            u = urllib.parse.urljoin(final, href.strip())
            if u.startswith("http") and hote(u) == h and u.rstrip("/") not in vus \
                    and not re.search(r"\.(pdf|jpe?g|png|docx?|zip)(\?|$)", u, re.I):
                vus.add(u.rstrip("/"))
                a_voir.append(u)
    a_voir = sorted(a_voir, key=lambda u: (not re.search("contact", u, re.I), len(u)))[:6]
    if len(a_voir) < 2:
        a_voir += [f"https://{urllib.parse.urlsplit(final).netloc}{c}" for c in CHEMINS]
    for u in a_voir[:8]:
        _, page = lire(u)
        if page:
            textes.append(page)
            trouvees += adresses(page, h, True)
    return h, textes, trouvees


def domaines_plausibles(nom, sigle, dept):
    mots = [m.lower() for m in norme(re.sub(r"\(.*?\)", " ", nom)).split()
            if m not in VIDES and len(m) > 1]
    bases = []
    for s in filter(None, [sigle] + re.findall(r"\(([^)]{2,14})\)", nom)):
        s = norme(s)
        if len(s.replace(" ", "")) >= 3:
            bases += [s.replace(" ", "").lower(), s.replace(" ", "-").lower(),
                      s.replace(" ", "").lower() + dept, s.replace(" ", "").lower() + "-asso"]
    brut = [m.lower() for m in norme(re.sub(r"\(.*?\)", " ", nom)).split()]
    if mots:
        bases += ["".join(mots), "-".join(mots), "".join(mots[:2]), "-".join(mots[:2]),
                  "".join(mots[:3]), "-".join(mots[:3]), mots[0] + dept, mots[0]]
    if 1 < len(brut) <= 4:
        bases += ["".join(brut), "-".join(brut)]
    bases = [b for b in dict.fromkeys(bases) if 4 <= len(b) <= 40]
    # Avec et sans « www » : certains sites ne répondent que sur le domaine nu (amicial.fr).
    return [f"https://{w}{b}{t}" for b in bases[:8] for t in (".fr", ".org", ".com", ".asso.fr")
            for w in ("www.", "")]


def se_confirme(textes, c):
    """« siren », « nom » ou chaîne vide selon ce que le site affiche de l'organisme."""
    tout = " ".join(textes)
    if c.get("siren"):
        s = c["siren"]
        if re.search(r"(?<!\d)" + r"[\s .]?".join((s[:3], s[3:6], s[6:])) + r"(?!\d{6,})", tout):
            return "siren"
    plat = " " + norme(re.sub(r"<[^>]+>", " ", htmllib.unescape(tout))) + " "
    mots = [m for m in norme(re.sub(r"\(.*?\)", " ", c["nom"])).split() if m not in VIDES and len(m) >= 4]
    if c.get("cp") and f" {c['cp']} " in plat and len(mots) >= 2 \
            and sum(f" {m} " in plat for m in mots) >= min(len(mots), 3):
        return "nom"
    return ""


def traiter(c):
    """Cherche le site puis l'adresse d'une cible. Renvoie (clé, site, mail, preuve)."""
    for site in c.get("sites", []):
        h, textes, trouvees = explorer(site)
        if h:
            return c["cle"], f"https://{h}", choisir(trouvees), "source"
    if not c.get("deviner"):
        return c["cle"], "", "", ""
    for base in domaines_plausibles(c["nom"], c.get("sigle", ""), c["dept"]):
        final, accueil = lire(base, delai=6)
        if not accueil:
            continue
        h, textes, trouvees = explorer(final)
        preuve = se_confirme(textes, c) if h else ""
        if preuve:
            return c["cle"], f"https://{h}", choisir(trouvees), preuve
    return c["cle"], "", "", ""


def json_url(url, delai=60, essais=6):
    for i in range(essais):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "annuaire-paca-bot/1.0"})
            return json.loads(urllib.request.urlopen(req, timeout=delai).read())
        except Exception:
            time.sleep(2 + 2 * i)
    return None


def site_net(u):
    u = (u or "").strip()
    if not u or " " in u or "." not in u:
        return ""
    u = u if u.startswith("http") else "https://" + u
    bloque = ("annuaire-entreprises.data.gouv.fr", "service-public.fr", "demarches-simplifiees",
              "facebook.com", "linkedin.com")
    return "" if any(b in u for b in bloque) else u


def wikidata(sirens):
    """SIREN -> (site, mail) depuis Wikidata."""
    trouve = {}
    sirens = sorted(sirens)
    for i in range(0, len(sirens), 120):
        valeurs = " ".join(f'"{s}"' for s in sirens[i:i + 120])
        q = ("SELECT ?s ?w ?m WHERE { VALUES ?s {%s} ?i wdt:P1616 ?s. "
             "OPTIONAL{?i wdt:P856 ?w} OPTIONAL{?i wdt:P968 ?m} }" % valeurs)
        d = json_url("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q))
        for b in (d or {}).get("results", {}).get("bindings", []):
            site = b.get("w", {}).get("value", "")
            mail = b.get("m", {}).get("value", "").replace("mailto:", "")
            if site or mail:
                trouve.setdefault(b["s"]["value"], (site, mail))
    return trouve


def openstreetmap(sirens):
    """SIREN -> (site, mail) depuis les objets OSM de PACA qui portent un SIRET."""
    q = ('[out:json][timeout:170];area["ISO3166-2"="FR-PAC"]->.a;'
         'nwr(area.a)["ref:FR:SIRET"];out tags;')
    d = json_url("https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(q), delai=200, essais=2)
    trouve = {}
    for e in (d or {}).get("elements", []):
        t = e.get("tags", {})
        s = re.sub(r"\D", "", t.get("ref:FR:SIRET", ""))[:9]
        if s in sirens:
            site = t.get("contact:website") or t.get("website") or ""
            mail = t.get("contact:email") or t.get("email") or ""
            if site or mail:
                ancien = trouve.get(s, ("", ""))
                trouve[s] = (ancien[0] or site, ancien[1] or mail)
    return trouve


def siren_bailleur(nom, dept):
    q = urllib.parse.urlencode({"q": nom[:60], "departement": dept, "per_page": 3})
    d = json_url("https://recherche-entreprises.api.gouv.fr/search?" + q, delai=30, essais=4)
    for r in (d or {}).get("results", []):
        if norme(r.get("nom_raison_sociale") or "")[:12] == norme(nom)[:12]:
            return r["siren"], (r.get("siege") or {}).get("code_postal") or ""
    return "", ""


def main():
    cache = pathlib.Path(sys.argv[1])
    contacts = json.loads(SORTIE.read_text(encoding="utf-8")) if SORTIE.exists() else {}

    # Entrées de la page sans adresse
    bloc = re.search(r"const DATA = \[\n([\s\S]*?)\n\];", PAGE.read_text(encoding="utf-8")).group(1)
    entrees = [dict(re.findall(r'(\w+):"([^"]*)"', l)) for l in bloc.splitlines()]
    sans = [e for e in entrees if e.get("type") and not e.get("email")]
    print(f"{len(entrees)} organismes, {len(sans)} sans adresse e-mail", flush=True)

    assos = {a["siren"]: a for a in json.loads((cache / "associations.json").read_text(encoding="utf-8"))}
    par_nom = {(norme(a["nom"]), a["dept"]): s for s, a in assos.items()}
    banatic = {cle_nom(g["nom"], g["dept"]): g
               for g in json.loads((cache / "banatic_paca.json").read_text(encoding="utf-8"))}
    epl = {}
    for l in re.findall(r"^  \{nom:.*\}", EPL.read_text(encoding="utf-8"), re.M):
        e = dict(re.findall(r'(\w+):"([^"]*)"', l))
        epl[cle_nom(e["nom"], e.get("depcode", ""))] = e
    ecoles = {}
    for e in json.loads((cache / "education.json").read_text(encoding="utf-8")):
        if e.get("web") and e.get("siren_siret"):
            ecoles.setdefault(e["siren_siret"][:9], e["web"])

    cibles = []
    for e in sans:
        famille = e["type"].split(" · ")[0]
        c = {"nom": e["nom"], "dept": e["dept"], "sites": [], "sigle": "", "siren": "", "cp": "",
             "deviner": famille in ("Association", "Syndicat", "Epl", "Bailleur social")}
        if famille == "Association":
            siren = (re.search(r"/entreprise/(\d{9})", e.get("contact", "")) or [None, ""])[1]
            if not siren:   # lien déjà remplacé par le site : on retrouve le SIREN par le nom
                siren = par_nom.get((norme(re.sub(r"\s*\([^)]*\)\s*$", "", e["nom"])), e["dept"]), "")
            a = assos.get(siren, {})
            c.update(cle=f"siren:{siren}", siren=siren, nom=a.get("nom", e["nom"]),
                     sigle=a.get("sigle", ""))
            c["cp"] = (re.findall(r"\b(\d{5})\b", a.get("adresse", "")) or [""])[-1]
            c["sites"].append(ecoles.get(siren, ""))
        else:
            c["cle"] = cle_nom(e["nom"], e["dept"])
            g, x = banatic.get(c["cle"]), epl.get(c["cle"])
            if g:
                c.update(siren=g["siren"], cp=(re.findall(r"\b(\d{5})\b", g["adresse"]) or [""])[-1])
                c["sites"].append(g["web"])
            if x:
                c.update(siren=x.get("siren", "")[:9], cp=x.get("cp", ""), sigle=x.get("sigle", ""))
                c["sites"].append(x.get("web", ""))
            if famille == "Bailleur social":
                c["siren"], c["cp"] = siren_bailleur(e["nom"], e["dept"])
            c["sites"].append(e.get("contact", ""))
        c["sites"].append(contacts.get(c["cle"], {}).get("web", ""))
        cibles.append(c)

    sirens = {c["siren"] for c in cibles if c["siren"]}
    wd = wikidata(sirens)
    print(f"Wikidata : {len(wd)} organismes reconnus par leur SIREN", flush=True)
    osm = openstreetmap(sirens)
    print(f"OpenStreetMap : {len(osm)} organismes reconnus par leur SIRET", flush=True)

    def poser(cle, source, email="", web=""):
        k = contacts.setdefault(cle, {"email": "", "tel": "", "web": "", "source": ""})
        ajout = False
        if email and not k["email"]:
            k["email"], ajout = email, True
        if web and not k["web"]:
            k["web"], ajout = web, True
        if ajout and source not in k["source"]:
            k["source"] = (k["source"] + " + " + source).strip(" +")
        return ajout

    for c in cibles:
        for nom_source, base in (("Wikidata", wd), ("OpenStreetMap", osm)):
            site, mail = base.get(c["siren"], ("", ""))
            c["sites"].append(site)
            if nettoyer(mail):
                poser(c["cle"], nom_source, email=nettoyer(mail))
        c["sites"] = list(dict.fromkeys(s for s in map(site_net, c["sites"]) if s))

    a_faire = [c for c in cibles if not contacts.get(c["cle"], {}).get("email")]
    print(f"{len(a_faire)} organismes à fouiller, dont {sum(1 for c in a_faire if c['sites'])} "
          f"avec un site connu", flush=True)
    bilan = {"source": 0, "siren": 0, "nom": 0}
    mails = 0
    libelles = {"source": "site de l'organisme", "siren": "site de l'organisme (SIREN vérifié)",
                "nom": "site de l'organisme (nom et code postal concordants)"}
    with ThreadPoolExecutor(max_workers=40) as pool:
        for n, (cle, site, mail, preuve) in enumerate(pool.map(traiter, a_faire), 1):
            if site:
                bilan[preuve] += 1
                poser(cle, libelles[preuve], email=mail, web=site)
                mails += bool(mail)
            if n % 100 == 0:
                print(f"  {n}/{len(a_faire)} — {mails} adresses", flush=True)
                SORTIE.write_text(json.dumps(dict(sorted(contacts.items())), ensure_ascii=False,
                                             indent=1) + "\n", encoding="utf-8")

    contacts = {k: v for k, v in sorted(contacts.items()) if v["email"] or v["tel"] or v["web"]}
    SORTIE.write_text(json.dumps(contacts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"✅ sites lus : {bilan['source']} donnés par une source, {bilan['siren']} confirmés par "
          f"SIREN, {bilan['nom']} par nom et code postal — {mails} nouvelles adresses")
    print(f"   {SORTIE.name} : {sum(1 for v in contacts.values() if v['email'])} adresses e-mail")


if __name__ == "__main__":
    main()
