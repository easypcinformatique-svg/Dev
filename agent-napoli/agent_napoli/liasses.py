"""Liasses fiscales déposées dans Drive « Pizza Napoli/Légal/Liasses ».

Chaque nouvelle liasse (PDF) est lue une fois par Claude : CA net HT et résultat
de l'exercice N et N-1, inscrits dans l'onglet « Exercices » s'ils n'y sont pas.
"""

from __future__ import annotations

from . import config, ia
from .exercice import COL_E, lire_exercices
from .outils import lire_date


def traiter(g, lignes_exercices: list[list[str]]) -> tuple[list[str], list[str]]:
    """Renvoie (phrases pour le rapport, erreurs)."""
    phrases, erreurs = [], []
    connus = {(e.debut, e.fin) for e in lire_exercices(lignes_exercices)}
    sources = {l[COL_E["Source"]] for l in lignes_exercices if len(l) > COL_E["Source"]}
    dossier = g.dossier(*config.DOSSIER_LIASSES)
    for f in g.lister(dossier):
        if f["name"] in sources or f["mimeType"] != "application/pdf":
            continue
        try:
            info = ia.lire_liasse(g.telecharger(f["id"], f["mimeType"]))
        except ia.ErreurIA as e:
            erreurs.append(f"Liasse « {f['name']} » : lecture impossible ({e}), nouvel essai demain")
            continue
        if not info.get("est_une_liasse"):
            erreurs.append(f"« {f['name']} » ne ressemble pas à une liasse fiscale")
            continue
        nouvelles = []
        for ex in info.get("exercices", []):
            debut, fin = lire_date(ex.get("debut")), lire_date(ex.get("fin"))
            if not debut or not fin or (debut, fin) in connus:
                continue
            connus.add((debut, fin))
            nouvelles.append([f"{debut.year}-{fin.year}", debut.isoformat(), fin.isoformat(),
                              ex.get("chiffre_affaires_net_ht"), ex.get("resultat"), "", f["name"]])
        # Une liasse déjà connue (doublon, version provisoire) est notée pour ne pas être relue.
        a_ecrire = nouvelles or [["", "", "", "", "", "", f["name"]]]
        g.ajouter("Exercices", a_ecrire)
        lignes_exercices += a_ecrire
        sources.add(f["name"])
        if nouvelles:
            phrases.append(f"Liasse « {f['name']} » lue : exercice(s) {', '.join(n[0] for n in nouvelles)} ajouté(s) au suivi.")
    return phrases, erreurs
