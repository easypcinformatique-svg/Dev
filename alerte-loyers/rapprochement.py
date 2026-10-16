"""Rapprochement des virements reçus avec les loyers attendus.

Logique pure (sans réseau) : on lui donne les baux et les transactions du
mois, elle renvoie l'état de chaque loyer.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal

RECU = "recu"
PARTIEL = "partiel"
MANQUANT = "manquant"


@dataclass
class Bail:
    nom: str
    montant: Decimal
    payeurs: list  # mots-clés cherchés dans le libellé ou le nom de l'émetteur
    tolerance: Decimal = Decimal("1.00")


@dataclass
class Virement:
    date: str
    montant: Decimal
    libelle: str


@dataclass
class Resultat:
    bail: Bail
    virements: list = field(default_factory=list)

    @property
    def total(self):
        return sum((v.montant for v in self.virements), Decimal("0"))

    @property
    def manque(self):
        return max(self.bail.montant - self.total, Decimal("0"))

    @property
    def statut(self):
        if self.total >= self.bail.montant - self.bail.tolerance:
            return RECU
        return PARTIEL if self.virements else MANQUANT


def normaliser(texte):
    """Majuscules, sans accents ni ponctuation : « L'Instant » -> « L INSTANT »."""
    texte = unicodedata.normalize("NFKD", texte or "")
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", texte.upper()).split())


def contient(texte_normalise, mot_cle):
    """Cherche le mot-clé en mots entiers (« CAF » ne trouve pas « CAFE »)."""
    return f" {normaliser(mot_cle)} " in f" {texte_normalise} "


def charger_baux(config):
    return [
        Bail(
            nom=b["nom"],
            montant=Decimal(str(b["montant"])),
            payeurs=list(b["payeurs"]),
            tolerance=Decimal(str(b.get("tolerance", "1.00"))),
        )
        for b in config["baux"]
    ]


def virement_depuis_transaction(tx):
    """Convertit une transaction Enable Banking en Virement, ou None si débit."""
    if tx.get("credit_debit_indicator") != "CRDT":
        return None
    morceaux = list(tx.get("remittance_information") or [])
    for partie in ("debtor", "creditor"):
        nom = (tx.get(partie) or {}).get("name")
        if nom:
            morceaux.append(nom)
    if tx.get("note"):
        morceaux.append(tx["note"])
    return Virement(
        date=tx.get("booking_date") or tx.get("value_date") or tx.get("transaction_date") or "",
        montant=Decimal(str(tx["transaction_amount"]["amount"])),
        libelle=" ".join(morceaux),
    )


def rapprocher(baux, virements):
    """Attribue chaque virement au premier bail dont un payeur apparaît dans le libellé.

    Un virement n'est compté qu'une fois, et un loyer payé en plusieurs fois
    (ou en partie par la CAF) est additionné.
    """
    resultats = [Resultat(bail) for bail in baux]
    for virement in virements:
        texte = normaliser(virement.libelle)
        for resultat in resultats:
            if any(contient(texte, p) for p in resultat.bail.payeurs):
                resultat.virements.append(virement)
                break
    return resultats
