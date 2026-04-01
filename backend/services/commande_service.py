"""Service pour la gestion des commandes."""

import random
import string
from datetime import date, datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import (
    Client, Commande, LigneCommande, LigneCommandeSupplement,
    Produit, ProduitTaille, Supplement, Creneau,
    Comptoir, ModeCommande, StatutCommande, StatutPaiement,
)
from backend.services import creneau_service


def _generer_numero() -> str:
    """Genere un numero de commande unique (ex: CMD-A3X7)."""
    chars = string.ascii_uppercase + string.digits
    code = "".join(random.choices(chars, k=4))
    return f"CMD-{code}"


async def _get_or_create_client(
    db: AsyncSession,
    client_id: int | None = None,
    telephone: str | None = None,
    nom: str | None = None,
) -> Client | None:
    if client_id:
        result = await db.execute(select(Client).where(Client.id == client_id))
        return result.scalar_one_or_none()
    if telephone:
        result = await db.execute(select(Client).where(Client.telephone == telephone))
        client = result.scalar_one_or_none()
        if client:
            if nom and not client.nom:
                client.nom = nom
            return client
        if nom:
            client = Client(nom=nom, telephone=telephone)
            db.add(client)
            await db.flush()
            return client
    return None


async def creer_commande(db: AsyncSession, data: dict) -> Commande:
    """Cree une commande complete avec lignes et supplements."""
    # Client
    client = await _get_or_create_client(
        db,
        client_id=data.get("client_id"),
        telephone=data.get("client_telephone"),
        nom=data.get("client_nom"),
    )

    # Creneau
    if data.get("creneau_id"):
        creneau = await creneau_service.incrementer_creneau(db, data["creneau_id"])
        if not creneau:
            raise ValueError("Creneau complet ou indisponible")

    # Numero unique
    numero = _generer_numero()

    commande = Commande(
        numero=numero,
        client_id=client.id if client else None,
        comptoir=data["comptoir"],
        mode=data["mode"],
        creneau_id=data.get("creneau_id"),
        adresse_livraison=data.get("adresse_livraison"),
        notes=data.get("notes"),
        utilisateur_id=data.get("utilisateur_id"),
    )
    db.add(commande)
    await db.flush()

    montant_ht = 0.0
    tva_taux = 10.0  # Taux emporter/livraison

    for ligne_data in data.get("lignes", []):
        # Recuperer le prix
        prix = 0.0
        if ligne_data.get("taille_id"):
            result = await db.execute(
                select(ProduitTaille).where(ProduitTaille.id == ligne_data["taille_id"])
            )
            taille = result.scalar_one_or_none()
            if taille:
                prix = taille.prix
        else:
            # Produit sans taille (boisson, dessert)
            result = await db.execute(
                select(ProduitTaille).where(ProduitTaille.produit_id == ligne_data["produit_id"])
            )
            taille = result.scalars().first()
            if taille:
                prix = taille.prix

        ligne = LigneCommande(
            commande_id=commande.id,
            produit_id=ligne_data["produit_id"],
            taille_id=ligne_data.get("taille_id"),
            quantite=ligne_data.get("quantite", 1),
            prix_unitaire=prix,
            notes=ligne_data.get("notes"),
        )
        db.add(ligne)
        await db.flush()

        montant_ligne = prix * ligne.quantite

        # Supplements
        for sup_data in ligne_data.get("supplements", []):
            result = await db.execute(
                select(Supplement).where(Supplement.id == sup_data["supplement_id"])
            )
            sup = result.scalar_one_or_none()
            if sup:
                sup_prix = sup.prix * sup_data.get("quantite", 1)
                ligne_sup = LigneCommandeSupplement(
                    ligne_id=ligne.id,
                    supplement_id=sup.id,
                    quantite=sup_data.get("quantite", 1),
                    prix=sup.prix,
                )
                db.add(ligne_sup)
                montant_ligne += sup_prix

        montant_ht += montant_ligne

    # Calcul TVA
    montant_tva = round(montant_ht * tva_taux / 100, 2)
    commande.montant_ht = round(montant_ht, 2)
    commande.montant_tva = montant_tva
    commande.frais_livraison = data.get("frais_livraison", 0.0)
    commande.montant_ttc = round(montant_ht + montant_tva + commande.frais_livraison, 2)

    await db.commit()
    await db.refresh(commande)
    return commande


async def get_commande(db: AsyncSession, commande_id: int) -> Commande | None:
    result = await db.execute(
        select(Commande)
        .options(
            selectinload(Commande.lignes).selectinload(LigneCommande.supplements),
            selectinload(Commande.lignes).selectinload(LigneCommande.produit),
            selectinload(Commande.lignes).selectinload(LigneCommande.taille),
            selectinload(Commande.client),
            selectinload(Commande.creneau),
        )
        .where(Commande.id == commande_id)
    )
    return result.scalar_one_or_none()


async def get_commande_par_numero(db: AsyncSession, numero: str) -> Commande | None:
    result = await db.execute(
        select(Commande)
        .options(
            selectinload(Commande.lignes).selectinload(LigneCommande.supplements),
            selectinload(Commande.lignes).selectinload(LigneCommande.produit),
            selectinload(Commande.client),
            selectinload(Commande.creneau),
        )
        .where(Commande.numero == numero)
    )
    return result.scalar_one_or_none()


async def lister_commandes(
    db: AsyncSession,
    jour: date | None = None,
    comptoir: Comptoir | None = None,
    statut: StatutCommande | None = None,
    creneau_id: int | None = None,
) -> list[Commande]:
    stmt = (
        select(Commande)
        .options(
            selectinload(Commande.lignes).selectinload(LigneCommande.produit),
            selectinload(Commande.lignes).selectinload(LigneCommande.supplements),
            selectinload(Commande.client),
            selectinload(Commande.creneau),
        )
        .order_by(Commande.created_at.desc())
    )
    if jour:
        stmt = stmt.where(func.date(Commande.created_at) == jour)
    if comptoir:
        stmt = stmt.where(Commande.comptoir == comptoir)
    if statut:
        stmt = stmt.where(Commande.statut == statut)
    if creneau_id:
        stmt = stmt.where(Commande.creneau_id == creneau_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def changer_statut(
    db: AsyncSession, commande_id: int, nouveau_statut: StatutCommande
) -> Commande | None:
    commande = await get_commande(db, commande_id)
    if not commande:
        return None
    commande.statut = nouveau_statut
    if nouveau_statut == StatutCommande.ANNULEE and commande.creneau_id:
        await creneau_service.decrementer_creneau(db, commande.creneau_id)
    await db.commit()
    await db.refresh(commande)
    return commande


async def annuler_commande(db: AsyncSession, commande_id: int) -> bool:
    result = await changer_statut(db, commande_id, StatutCommande.ANNULEE)
    return result is not None
