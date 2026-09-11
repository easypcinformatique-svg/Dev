"""Service pour les statistiques et rapports."""

from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    Commande, LigneCommande, Produit, Creneau,
    StatutCommande,
)


async def stats_periode(
    db: AsyncSession, date_debut: date, date_fin: date
) -> dict:
    """Statistiques sur une periode donnee."""
    base_filter = [
        func.date(Commande.created_at) >= date_debut,
        func.date(Commande.created_at) <= date_fin,
        Commande.statut != StatutCommande.ANNULEE,
    ]

    # Totaux
    result = await db.execute(
        select(
            func.count(Commande.id),
            func.coalesce(func.sum(Commande.montant_ttc), 0),
            func.coalesce(func.sum(Commande.montant_ht), 0),
        ).where(*base_filter)
    )
    row = result.one()
    nb_commandes = row[0]
    ca_ttc = float(row[1])
    ca_ht = float(row[2])
    panier_moyen = round(ca_ttc / nb_commandes, 2) if nb_commandes else 0

    # Par comptoir
    result = await db.execute(
        select(
            Commande.comptoir,
            func.count(Commande.id),
            func.coalesce(func.sum(Commande.montant_ttc), 0),
        ).where(*base_filter).group_by(Commande.comptoir)
    )
    par_comptoir = {
        row[0].value: {"nb": row[1], "ca_ttc": round(float(row[2]), 2)}
        for row in result.all()
    }

    # Par mode
    result = await db.execute(
        select(
            Commande.mode,
            func.count(Commande.id),
            func.coalesce(func.sum(Commande.montant_ttc), 0),
        ).where(*base_filter).group_by(Commande.mode)
    )
    par_mode = {
        row[0].value: {"nb": row[1], "ca_ttc": round(float(row[2]), 2)}
        for row in result.all()
    }

    # Top produits
    result = await db.execute(
        select(
            Produit.nom,
            func.sum(LigneCommande.quantite).label("qty"),
            func.sum(LigneCommande.prix_unitaire * LigneCommande.quantite).label("ca"),
        )
        .join(LigneCommande, LigneCommande.produit_id == Produit.id)
        .join(Commande, Commande.id == LigneCommande.commande_id)
        .where(*base_filter)
        .group_by(Produit.nom)
        .order_by(func.sum(LigneCommande.quantite).desc())
        .limit(10)
    )
    top_produits = [
        {"produit_nom": row[0], "quantite_vendue": int(row[1]), "ca_ttc": round(float(row[2]), 2)}
        for row in result.all()
    ]

    # Par jour
    result = await db.execute(
        select(
            func.date(Commande.created_at).label("jour"),
            func.count(Commande.id),
            func.coalesce(func.sum(Commande.montant_ttc), 0),
        ).where(*base_filter)
        .group_by(func.date(Commande.created_at))
        .order_by(func.date(Commande.created_at))
    )
    par_jour = [
        {
            "date": row[0],
            "nb_commandes": row[1],
            "ca_ttc": round(float(row[2]), 2),
            "panier_moyen": round(float(row[2]) / row[1], 2) if row[1] else 0,
        }
        for row in result.all()
    ]

    # Par creneau horaire
    result = await db.execute(
        select(
            Creneau.heure_debut,
            func.count(Commande.id),
        )
        .join(Creneau, Creneau.id == Commande.creneau_id)
        .where(*base_filter)
        .group_by(Creneau.heure_debut)
        .order_by(Creneau.heure_debut)
    )
    par_creneau = {
        row[0].strftime("%H:%M"): row[1]
        for row in result.all()
    }

    return {
        "periode": f"{date_debut} - {date_fin}",
        "ca_ttc": round(ca_ttc, 2),
        "ca_ht": round(ca_ht, 2),
        "nb_commandes": nb_commandes,
        "panier_moyen": panier_moyen,
        "par_comptoir": par_comptoir,
        "par_mode": par_mode,
        "top_produits": top_produits,
        "par_jour": par_jour,
        "par_creneau": par_creneau,
    }
