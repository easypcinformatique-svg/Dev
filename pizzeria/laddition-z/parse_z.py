#!/usr/bin/env python3
"""Extrait les indicateurs d'anomalie des mails "Z quotidien" de L'Addition.

Usage :
    python3 parse_z.py                  # lit data/*.txt, ecrit z_daily.csv + rapport_z.html
    python3 parse_z.py --data autre_dir

Un fichier par journee : copier-coller brut du mail (texte), nom libre.
La date est lue dans le corps du mail, pas dans le nom du fichier.
"""

import argparse
import csv
import glob
import os
import re
import sys
import unicodedata
from datetime import date

# Seuils d'alerte, en % du CA TTC. Au-dela, la journee est signalee.
SEUILS = {
    "corr_avant": 5.0,
    "corr_apres": 2.0,
    "annulations": 2.0,
    "offerts": 3.0,
}

JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def sans_accents(texte):
    """Neutralise les accents : les mails passent parfois en ASCII degrade."""
    decompose = unicodedata.normalize("NFD", texte)
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def montant(texte, motif):
    """Cherche 'motif : 123.45' et rend un float, ou None si absent."""
    trouve = re.search(motif + r"\s*:?\s*(-?[\d ]+[.,]\d{2})", texte, re.IGNORECASE)
    if not trouve:
        return None
    return float(trouve.group(1).replace(" ", "").replace(",", "."))


def parse_mail(texte):
    """Rend un dict d'indicateurs pour une journee, ou None si ce n'est pas un Z."""
    plat = sans_accents(texte)

    jour = re.search(r"journee du\s*(\d{4}-\d{2}-\d{2})", plat, re.IGNORECASE)
    if not jour:
        jour = re.search(r"\|\s*(\d{4}-\d{2}-\d{2})\s*\)", plat)
    if not jour:
        return None

    ca_ttc = montant(plat, r"CA TTC")
    if ca_ttc is None:
        return None

    ligne_moyennes = re.search(
        r"Couvert\(s\)\s*:\s*([\d.,]+)\s*\|.*?Ticket moyen\s*:\s*([\d.,]+)", plat
    )
    couverts = ticket_moyen = 0.0
    if ligne_moyennes:
        couverts = float(ligne_moyennes.group(1).replace(",", "."))
        ticket_moyen = float(ligne_moyennes.group(2).replace(",", "."))

    return {
        "date": jour.group(1),
        "ca_ttc": ca_ttc,
        "ca_ht": montant(plat, r"CA HT") or 0.0,
        "remises": montant(plat, r"Remises") or 0.0,
        "offerts": montant(plat, r"Offerts") or 0.0,
        "couverts": couverts,
        "ticket_moyen": ticket_moyen,
        "corr_avant": montant(plat, r"Corrections avant envoi en cuisine") or 0.0,
        "corr_apres": montant(plat, r"Corrections apres envoi en cuisine") or 0.0,
        "annulations": montant(
            plat, r"Annulations cuisine apres ticket de caisse\s*/\s*fermeture de commande"
        )
        or 0.0,
        "offerts_articles": articles_offerts(plat),
    }


def articles_offerts(plat):
    """Lignes de vente sorties a 0.00 TTC alors que la quantite est > 0."""
    offerts = []
    for ligne in plat.splitlines():
        cellules = [c.strip() for c in ligne.split("\t") if c.strip()]
        if len(cellules) != 5:
            continue
        try:
            qte, ttc = float(cellules[2]), float(cellules[3])
        except ValueError:
            continue
        if qte > 0 and ttc == 0.0:
            offerts.append({"categorie": cellules[0], "produit": cellules[1], "qte": qte})
    return offerts


def enrichir(j):
    """Ajoute les ratios, le nombre de tickets estime et les alertes."""
    ca = j["ca_ttc"]
    for cle in ("corr_avant", "corr_apres", "annulations", "offerts", "remises"):
        j[cle + "_pct"] = round(100 * j[cle] / ca, 2) if ca else 0.0

    j["total_ecarts"] = round(
        j["corr_avant"] + j["corr_apres"] + j["annulations"] + j["offerts"], 2
    )
    j["total_ecarts_pct"] = round(100 * j["total_ecarts"] / ca, 2) if ca else 0.0

    # Le Z ne donne pas le nombre de tickets : on le reconstruit par CA / ticket moyen.
    j["tickets"] = round(ca / j["ticket_moyen"]) if j["ticket_moyen"] else 0
    j["offerts_en_tickets"] = (
        round(j["offerts"] / j["ticket_moyen"], 1) if j["ticket_moyen"] else 0.0
    )

    j["alertes"] = [cle for cle, seuil in SEUILS.items() if j[cle + "_pct"] > seuil]

    annee, mois, jour_num = (int(x) for x in j["date"].split("-"))
    j["jour_semaine"] = JOURS_FR[date(annee, mois, jour_num).weekday()]
    return j


def charger(repertoire):
    journees = []
    for chemin in sorted(glob.glob(os.path.join(repertoire, "*.txt"))):
        with open(chemin, encoding="utf-8") as f:
            parsee = parse_mail(f.read())
        if parsee is None:
            print(f"  ignore (pas un Z lisible) : {os.path.basename(chemin)}", file=sys.stderr)
            continue
        journees.append(enrichir(parsee))
    return sorted(journees, key=lambda j: j["date"])


COLONNES_CSV = [
    "date", "jour_semaine", "ca_ttc", "ca_ht", "tickets", "ticket_moyen",
    "corr_avant", "corr_avant_pct", "corr_apres", "corr_apres_pct",
    "annulations", "annulations_pct", "offerts", "offerts_pct",
    "remises", "total_ecarts", "total_ecarts_pct", "alertes",
]


def ecrire_csv(journees, chemin):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        ecrivain = csv.DictWriter(f, fieldnames=COLONNES_CSV, extrasaction="ignore", delimiter=";")
        ecrivain.writeheader()
        for j in journees:
            ligne = dict(j)
            ligne["alertes"] = " ".join(j["alertes"])
            ecrivain.writerow(ligne)


LIBELLES = {
    "corr_avant": "Corrections avant cuisine",
    "corr_apres": "Corrections apres cuisine",
    "annulations": "Annulations apres ticket",
    "offerts": "Offerts",
}


def moyenne(valeurs):
    return sum(valeurs) / len(valeurs) if valeurs else 0.0


def euro(v):
    return f"{v:,.2f}".replace(",", " ").replace(".", ",") + " €"


def pct(v):
    return f"{v:.2f}".replace(".", ",") + " %"


def ecrire_html(journees, chemin):
    ca_total = sum(j["ca_ttc"] for j in journees)
    cumuls = {c: sum(j[c] for j in journees) for c in LIBELLES}
    jours_alertes = [j for j in journees if j["alertes"]]

    tuiles = []
    for cle, libelle in LIBELLES.items():
        part = 100 * cumuls[cle] / ca_total if ca_total else 0.0
        etat = "alerte" if part > SEUILS[cle] else "ok"
        tuiles.append(
            f'<div class="tuile {etat}"><h3>{libelle}</h3>'
            f'<p class="montant">{euro(cumuls[cle])}</p>'
            f'<p class="part">{pct(part)} du CA <span class="seuil">seuil {SEUILS[cle]:g} %</span></p></div>'
        )

    lignes = []
    for j in journees:
        cellules = [f'<td class="d">{j["date"]}<span class="js">{j["jour_semaine"]}</span></td>',
                    f'<td class="n">{euro(j["ca_ttc"])}</td>',
                    f'<td class="n">{j["tickets"] or "—"}</td>']
        for cle in LIBELLES:
            classe = "n alerte" if cle in j["alertes"] else "n"
            cellules.append(
                f'<td class="{classe}">{euro(j[cle])}<span class="p">{pct(j[cle + "_pct"])}</span></td>'
            )
        total_classe = "n total" + (" alerte" if j["total_ecarts_pct"] > 8 else "")
        cellules.append(
            f'<td class="{total_classe}">{euro(j["total_ecarts"])}'
            f'<span class="p">{pct(j["total_ecarts_pct"])}</span></td>'
        )
        lignes.append("<tr>" + "".join(cellules) + "</tr>")

    moyennes = "".join(
        f"<li><strong>{libelle}</strong> : {pct(moyenne([j[cle + '_pct'] for j in journees]))} "
        f"en moyenne / jour (seuil {SEUILS[cle]:g} %)</li>"
        for cle, libelle in LIBELLES.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alertes Z quotidien</title>
<style>
:root {{ --fond:#faf9f7; --carte:#fff; --texte:#1c1b19; --doux:#6b6862;
        --trait:#e5e2dc; --rouge:#b3261e; --rouge-fond:#fdf0ef; --vert:#1f6f43; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --fond:#171614; --carte:#201f1c; --texte:#f2f0ec; --doux:#a5a199;
  --trait:#34322d; --rouge:#f2b8b5; --rouge-fond:#3b1b19; --vert:#7fd0a0; }} }}
:root[data-theme="dark"] {{ --fond:#171614; --carte:#201f1c; --texte:#f2f0ec; --doux:#a5a199;
  --trait:#34322d; --rouge:#f2b8b5; --rouge-fond:#3b1b19; --vert:#7fd0a0; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:32px 16px 64px; background:var(--fond); color:var(--texte);
  font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
.page {{ max-width:1080px; margin:0 auto; }}
h1 {{ font-size:26px; margin:0 0 4px; letter-spacing:-.01em; }}
.sous {{ color:var(--doux); margin:0 0 28px; }}
.tuiles {{ display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); margin-bottom:28px; }}
.tuile {{ background:var(--carte); border:1px solid var(--trait); border-radius:12px; padding:16px; }}
.tuile.alerte {{ border-color:var(--rouge); background:var(--rouge-fond); }}
.tuile h3 {{ margin:0 0 8px; font-size:12px; font-weight:600; text-transform:uppercase;
  letter-spacing:.06em; color:var(--doux); }}
.montant {{ margin:0; font-size:24px; font-weight:650; font-variant-numeric:tabular-nums; }}
.part {{ margin:4px 0 0; font-size:13px; color:var(--doux); }}
.tuile.alerte .part {{ color:var(--rouge); font-weight:600; }}
.seuil {{ display:block; font-size:11px; font-weight:400; color:var(--doux); margin-top:2px; }}
.cadre {{ background:var(--carte); border:1px solid var(--trait); border-radius:12px; overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; min-width:760px; }}
th, td {{ padding:11px 12px; text-align:left; border-bottom:1px solid var(--trait); }}
th {{ font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--doux);
  font-weight:600; white-space:nowrap; }}
tr:last-child td {{ border-bottom:none; }}
td.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
td.d {{ font-variant-numeric:tabular-nums; white-space:nowrap; }}
.js {{ display:block; font-size:11px; color:var(--doux); text-transform:capitalize; }}
.p {{ display:block; font-size:11px; color:var(--doux); }}
td.alerte {{ background:var(--rouge-fond); color:var(--rouge); font-weight:600; }}
td.alerte .p {{ color:var(--rouge); }}
td.total {{ font-weight:650; }}
.notes {{ margin-top:28px; background:var(--carte); border:1px solid var(--trait);
  border-radius:12px; padding:18px 22px; }}
.notes h2 {{ font-size:14px; margin:0 0 10px; text-transform:uppercase;
  letter-spacing:.05em; color:var(--doux); }}
.notes ul {{ margin:0; padding-left:20px; }}
.notes li {{ margin-bottom:6px; }}
</style></head><body><div class="page">
<h1>Alertes Z quotidien — Pizza Napoli Carpentras</h1>
<p class="sous">{len(journees)} journee(s) analysee(s) · CA TTC cumule {euro(ca_total)} ·
{len(jours_alertes)} journee(s) hors seuil</p>
<div class="tuiles">{"".join(tuiles)}</div>
<div class="cadre"><table>
<thead><tr><th>Date</th><th class="n">CA TTC</th><th class="n">Tickets</th>
<th class="n">Corr. avant</th><th class="n">Corr. apres</th>
<th class="n">Annul. ticket</th><th class="n">Offerts</th><th class="n">Total ecarts</th></tr></thead>
<tbody>{"".join(lignes)}</tbody></table></div>
<div class="notes"><h2>Moyennes et reperes</h2><ul>{moyennes}
<li>Le nombre de tickets est <em>reconstruit</em> (CA TTC / ticket moyen) : le Z ne le fournit pas.</li>
<li>Une case rouge signale un depassement du seuil defini dans <code>SEUILS</code> (parse_z.py).</li>
</ul></div></div></body></html>"""

    with open(chemin, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data", help="repertoire des mails Z (defaut: data)")
    ap.add_argument("--csv", default="z_daily.csv")
    ap.add_argument("--html", default="rapport_z.html")
    args = ap.parse_args()

    journees = charger(args.data)
    if not journees:
        print(f"Aucun Z exploitable dans {args.data}/", file=sys.stderr)
        return 1

    ecrire_csv(journees, args.csv)
    ecrire_html(journees, args.html)

    print(f"{len(journees)} journee(s) -> {args.csv} + {args.html}\n")
    for j in journees:
        drapeau = "  ALERTE: " + ", ".join(j["alertes"]) if j["alertes"] else ""
        print(
            f"{j['date']} ({j['jour_semaine']:9s}) CA {j['ca_ttc']:8.2f}  "
            f"avant {j['corr_avant_pct']:5.2f}%  apres {j['corr_apres_pct']:5.2f}%  "
            f"annul {j['annulations_pct']:5.2f}%  offerts {j['offerts_pct']:5.2f}%{drapeau}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
