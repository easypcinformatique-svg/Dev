"""Fabrique l'aperçu privé du site (page Artifact claude.ai) à partir de amks-autos/.

Usage : python3 amks-autos/outils/apercu.py <dossier_sortie>

Le dossier de sortie reçoit index.html (sans <html>/<head>/<body>, que l'hébergeur
de l'aperçu ajoute lui-même), css/, js/, img/, data/ et favicon.svg. Le plan Google
Maps, qui ne s'affiche pas dans un aperçu, est remplacé par un lien.
"""
import re
import shutil
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
LIEN_PLAN = ('<a class="btn btn-signal" style="margin:24px" href="https://www.google.com/maps/search/?api=1&amp;'
             'query=115+boulevard+de+la+Milli%C3%A8re+13011+Marseille" target="_blank" rel="noopener">Voir le plan sur Google Maps</a>')


def construire(sortie: Path) -> list[str]:
    if sortie.exists():
        shutil.rmtree(sortie)
    sortie.mkdir(parents=True)
    for d in ("css", "js", "img", "data"):
        shutil.copytree(SITE / d, sortie / d)
    shutil.copy(SITE / "favicon.svg", sortie / "favicon.svg")

    s = (SITE / "index.html").read_text(encoding="utf-8")
    tete = re.search(r"<head>(.*?)</head>", s, re.S).group(1)
    tete = re.sub(r'<meta (charset|name="viewport")[^>]*>\s*', "", tete)
    tete = re.sub(r'<script type="application/ld\+json">.*?</script>\s*', "", tete, flags=re.S)
    tete = re.sub(r"<title>.*?</title>", '<title>AMKS Autos</title>\n<meta name="claude:viewport-fit-sides" content="cover">', tete, flags=re.S)
    corps = re.search(r"<body>(.*)</body>", s, re.S).group(1)
    corps = re.sub(r"<iframe.*?</iframe>", LIEN_PLAN, corps, flags=re.S)
    (sortie / "index.html").write_text(tete.strip() + "\n" + corps.strip(), encoding="utf-8")
    return sorted(str(p.relative_to(sortie)) for p in sortie.rglob("*") if p.is_file())


if __name__ == "__main__":
    for f in construire(Path(sys.argv[1] if len(sys.argv) > 1 else "apercu")):
        print(f)
