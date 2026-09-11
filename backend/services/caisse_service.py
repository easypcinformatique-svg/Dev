"""Service pour l'encaissement et le ticket Z."""

from datetime import date

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    Commande, Paiement, ModePaiement, StatutCommande, StatutPaiement,
)


async def encaisser(
    db: AsyncSession,
    commande_id: int,
    paiements: list[dict],
    montant_recu_especes: float | None = None,
) -> Commande:
    result = await db.execute(select(Commande).where(Commande.id == commande_id))
    commande = result.scalar_one_or_none()
    if not commande:
        raise ValueError("Commande introuvable")

    total_paye = 0.0
    for p in paiements:
        paiement = Paiement(
            commande_id=commande.id,
            mode=p["mode"],
            montant=p["montant"],
            rendu_monnaie=0.0,
        )
        if p["mode"] == ModePaiement.ESPECES and montant_recu_especes:
            paiement.rendu_monnaie = max(0, montant_recu_especes - p["montant"])
        db.add(paiement)
        total_paye += p["montant"]

    if total_paye >= commande.montant_ttc:
        commande.statut_paiement = StatutPaiement.PAYE
        if len(paiements) == 1:
            commande.mode_paiement = paiements[0]["mode"]
        else:
            commande.mode_paiement = ModePaiement.MIXTE

    await db.commit()
    await db.refresh(commande)
    return commande


async def ticket_z(db: AsyncSession, jour: date) -> dict:
    """Genere le rapport de fin de journee (Ticket Z)."""
    result = await db.execute(
        select(Commande).where(
            func.date(Commande.created_at) == jour,
            Commande.statut != StatutCommande.ANNULEE,
        )
    )
    commandes = list(result.scalars().all())

    ca_ttc = sum(c.montant_ttc for c in commandes)
    ca_ht = sum(c.montant_ht for c in commandes)
    total_tva = sum(c.montant_tva for c in commandes)

    # Par comptoir
    par_comptoir = {}
    for c in commandes:
        key = c.comptoir.value
        par_comptoir[key] = par_comptoir.get(key, 0) + c.montant_ttc

    # Par mode de paiement
    paiements_result = await db.execute(
        select(Paiement).join(Commande).where(
            func.date(Commande.created_at) == jour,
            Commande.statut != StatutCommande.ANNULEE,
        )
    )
    tous_paiements = list(paiements_result.scalars().all())
    par_mode_paiement = {}
    for p in tous_paiements:
        key = p.mode.value
        par_mode_paiement[key] = par_mode_paiement.get(key, 0) + p.montant

    # Par mode (emporter / livraison)
    par_mode = {}
    for c in commandes:
        key = c.mode.value
        par_mode[key] = par_mode.get(key, 0) + c.montant_ttc

    return {
        "date": jour,
        "nb_commandes": len(commandes),
        "ca_ttc": round(ca_ttc, 2),
        "ca_ht": round(ca_ht, 2),
        "total_tva": round(total_tva, 2),
        "par_comptoir": {k: round(v, 2) for k, v in par_comptoir.items()},
        "par_mode_paiement": {k: round(v, 2) for k, v in par_mode_paiement.items()},
        "par_mode": {k: round(v, 2) for k, v in par_mode.items()},
        "fond_de_caisse": 0.0,
        "total_especes": round(par_mode_paiement.get("especes", 0), 2),
        "total_cb": round(par_mode_paiement.get("cb", 0), 2),
    }
