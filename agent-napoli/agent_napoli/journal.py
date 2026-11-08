"""Journal de tout ce que fait l'agent : affiché dans les logs, puis copié dans
l'onglet « Journal » du tableur à la fin de chaque passage."""

from __future__ import annotations

import os
from datetime import datetime

from . import config


class Journal:
    def __init__(self):
        self.lignes: list[list[str]] = []

    def __call__(self, module: str, action: str, detail: str = "") -> None:
        horodatage = datetime.now(config.PARIS).strftime("%Y-%m-%d %H:%M:%S")
        self.lignes.append([horodatage, module, action, detail])
        # Dans GitHub Actions, les logs d'un dépôt public sont lisibles par tous : on n'y écrit
        # que le type d'action. Le détail (objets de mails, montants) va seulement dans le tableur.
        public = os.getenv("GITHUB_ACTIONS") == "true"
        print(f"{horodatage}  [{module}] {action}" + (f" — {detail}" if detail and not public else ""), flush=True)

    def sauver(self, g) -> None:
        g.ajouter("Journal", self.lignes)
        self.lignes = []


def deja_fait(lignes_journal: list[list[str]], action: str, marqueur: str) -> bool:
    """Vrai si le journal contient déjà `action` avec ce détail (ex. rapport du jour)."""
    return any(len(l) >= 4 and l[2] == action and l[3] == marqueur for l in lignes_journal)
