#!/usr/bin/env python3
"""Génère annuaire-sem-spl-syndicats.html depuis l'export YellowBox (FedEpl).

La page publiée est enrichie chaque semaine par .github/workflows/update-sem-spl-sm.yml,
qui lit et réécrit le tableau `let DATA = [...]`. Le format de chaque entrée est donc
contraint par les expressions régulières de ce workflow :

  étape 1 : {nom:"…" … adresse:"…" … president:"…" … siren:"<9 chiffres>"}
  étape 2 : {nom:"…" … tel:"" … siren:"<9 chiffres>"}

D'où l'ordre des clés imposé ci-dessous (nom en tête, siren en dernier, adresse/tel/
president entre les deux) et une entrée par ligne — le `.` de ces regex ne franchit
pas un saut de ligne.

Usage : python3 annuaires/build_sem_spl.py
"""
import datetime
import json
import pathlib
import re
import sys

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl requis : pip install openpyxl")

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPORT = ROOT / "Export_Annuaire_23022026.xlsx"
TEMPLATE = pathlib.Path(__file__).resolve().parent / "template_sem_spl.html"
OUTPUT = ROOT / "annuaire-sem-spl-syndicats.html"

# Ordre imposé par les regex du workflow de mise à jour (cf. docstring).
KEY_ORDER = [
    "nom", "sigle", "regime", "secteur", "activite",
    "adresse", "cp", "ville", "dept", "region",
    "tel", "email", "web", "capital", "ca", "effectif",
    "president", "siren",
]
NUMERIC_KEYS = {"capital", "ca"}


def clean(value):
    """Valeur exploitable dans une chaîne JS délimitée par des guillemets doubles."""
    if value is None:
        return ""
    text = str(value).replace("\\", "").replace('"', "'")
    return re.sub(r"\s+", " ", text).strip()


def number(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 9:            # zéro initial perdu par le tableur
        digits = "0" + digits
    if len(digits) != 10:
        return ""
    return " ".join(digits[i:i + 2] for i in range(0, 10, 2))


def website(value):
    url = clean(value).lower().removeprefix("http://").removeprefix("https://").rstrip("/")
    return url if "." in url else ""


def address(row):
    parts = [clean(row[i]) for i in (13, 14, 15)]
    return ", ".join(p for p in parts if p)


def read_rows():
    workbook = openpyxl.load_workbook(EXPORT, read_only=True, data_only=True)
    sheet = workbook["Données YellowBox"]
    rows = sheet.iter_rows(values_only=True)
    next(rows)  # en-têtes
    return [r for r in rows if clean(r[3])]


def build_entry(row):
    siren = re.sub(r"\D", "", str(row[4] or ""))
    return {
        "nom": clean(row[3]),
        "sigle": clean(row[2]),
        "regime": clean(row[1]),
        "secteur": clean(row[11]),
        "activite": clean(row[12]),
        "adresse": address(row),
        "cp": clean(row[16]),
        "ville": clean(row[17]).title(),
        "dept": clean(row[18]),
        "region": clean(row[19]),
        "tel": phone(row[20]),
        "email": "",          # rempli par le workflow hebdomadaire
        "web": website(row[21]),
        "capital": number(row[8]),
        "ca": number(row[9]),
        "effectif": clean(row[10]),
        "president": "",      # rempli par le workflow hebdomadaire
        "siren": siren if len(siren) == 9 else "",
    }


def render_entry(entry):
    parts = []
    for key in KEY_ORDER:
        value = entry[key]
        parts.append(f"{key}:{value}" if key in NUMERIC_KEYS else f'{key}:"{value}"')
    return "  {" + ",".join(parts) + "}"


def main():
    entries = [build_entry(row) for row in read_rows()]
    entries.sort(key=lambda e: (e["region"], e["nom"]))

    data_block = "let DATA = [\n" + ",\n".join(render_entry(e) for e in entries) + "\n];"
    regions = sorted({e["region"] for e in entries if e["region"]})
    secteurs = sorted({e["secteur"] for e in entries if e["secteur"]})
    regimes = sorted({e["regime"] for e in entries if e["regime"]})
    now = datetime.datetime.now()

    html = TEMPLATE.read_text(encoding="utf-8")
    for placeholder, value in {
        "__DATA__": data_block,
        "__REGIONS__": json.dumps(regions, ensure_ascii=False),
        "__SECTEURS__": json.dumps(secteurs, ensure_ascii=False),
        "__REGIMES__": json.dumps(regimes, ensure_ascii=False),
        "__COUNT__": str(len(entries)),
        "__VERSION__": f"v.{now.year}.{now.month:02d}.{now.day:02d}-{now.hour:02d}h{now.minute:02d}",
        "__EXPORT_DATE__": "23/02/2026",
    }.items():
        html = html.replace(placeholder, value)

    if "__" in re.sub(r"__[A-Z]*[a-z]", "", html):
        leftovers = set(re.findall(r"__[A-Z_]+__", html))
        if leftovers:
            sys.exit(f"Placeholders non substitués : {sorted(leftovers)}")

    OUTPUT.write_text(html, encoding="utf-8")
    with_siren = sum(1 for e in entries if e["siren"])
    with_tel = sum(1 for e in entries if e["tel"])
    print(f"✅ {OUTPUT.name} — {len(entries)} structures "
          f"({with_siren} avec SIREN, {with_tel} avec téléphone)")


if __name__ == "__main__":
    main()
