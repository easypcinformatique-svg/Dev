#!/usr/bin/env python3
"""Codes INSEE des communes PACA de plus de 30 000 habitants, en JSON.

Appelé par fetch_sources.sh pour savoir quelles mairies interroger.
Usage : python3 annuaires/codes_paca.py RÉPERTOIRE_CACHE
"""
import json
import pathlib
import re
import sys

import openpyxl

PACA = {"04", "05", "06", "13", "83", "84"}
ARRONDISSEMENT = re.compile(r"^(Paris|Lyon|Marseille)\s+\d+\w*\s+Arrondissement$", re.I)

cache = pathlib.Path(sys.argv[1])
wb = openpyxl.load_workbook(cache / "insee_pop2023.xlsx", read_only=True)
codes = []
for r in list(wb["Communes"].iter_rows(values_only=True))[8:]:
    if not r or not r[6]:
        continue
    if ARRONDISSEMENT.match(str(r[6]).strip()):
        continue
    if str(r[2]) in PACA and int(r[7]) > 30000:
        codes.append(str(r[2])[:2] + str(r[5]).zfill(3))
codes.append("13055")          # Marseille, éclatée en arrondissements dans la feuille
print(json.dumps(sorted(set(codes))))
