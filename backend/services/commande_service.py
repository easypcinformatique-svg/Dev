"""Service pour la gestion des commandes."""

import random
import string
from datetime import date, datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import (
    Client, Commande, LigneCommande, LigneCommandeSupplement,
    Produit, ProduitTaille, Supplement, Creneau, Promotion,
    Comptoir, ModeCommande, StatutCommande,
)
from backend.services import creneau_service


def _generer_numero() -> str:
    """Genere un numero de commande unique (ex: P-A3X7)."""
    chars = string.ascii_uppercase + string.digits
    code = "".join(random.choices(chars, k=4))
    return f"P-{code}"


async def _get_or_create_client(
    db: AsyncSession,
    client_id: int | None = None,
    telephone: str | None = None,
    nom: str | None = None,
    adresse: str | None = None,
) -> Client | None:
    if client_id:
        result = await db.execute(select(Client).where(Client.id == client_id))
        return result.scalar_one_or_none()
    if telephone:
        result = await db.execute(select(Client).where(Client.telephone == telephone))
        client = result.scalar_one_or_none()
        if client:
            if nom:
                client.nom = nom
            if adresse:
                client.adresse = adresse
            return client
        if nom:
            client = Client(nom=nom, telephone=telephone, adresse=adresse)
            db.add(client)
            await db.flush()
            return client
    return None


async def _appliquer_promo(db: AsyncSession, code: str, montant: float) -> float:
    """Applique un code promo et retourne la remise."""
    if not code:
        return 0.0
    result = await db.execute(
        select(Promotion).where(
            Promotion.code == code.upper(),
            Promotion.actif.is_(True),
        )
    )
    promo = result.scalar_one_or_none()
    if not promo:
        return 0.0
    if promo.montant_min > 0 and montant < promo.montant_min:
        return 0.0
    if promo.max_utilisations and promo.nb_utilisations >= promo.max_utilisations:
        return 0.0

    remise = 0.0
    if promo.type_promo == "pourcentage":
        remise = montant * promo.valeur / 100
    elif promo.type_promo == "montant_fixe":
        remise = min(promo.valeur, montant)
    elif promo.type_promo == "livraison_gratuite":
        remise = 0.0  # Gere via frais_livraison

    promo.nb_utilisations += 1
    return round(remise, 2)


def _estimer_temps(nb_pizzas: int, nb_commandes_queue: int) -> int:
    """Estime le temps de preparation en minutes."""
    base = 8  # temps mini
    par_pizza = 3  # minutes par pizza
    par_commande_queue = 2  # minutes par commande en attente
    return base + (nb_pizzas * par_pizza) + (nb_commandes_queue * par_commande_queue)


async def creer_commande(db: AsyncSession, data: dict) -> Commande:
    """Cree une commande complete avec lignes et supplements."""
    # Client
    client = await _get_or_create_client(
        db,
        client_id=data.get("client_id"),
        telephone=data.get("client_telephone"),
        nom=data.get("client_nom"),
        adresse=data.get("adresse_livraison"),
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
        code_promo=data.get("code_promo"),
    )
    db.add(commande)
    await db.flush()

    montant_ht = 0.0
    tva_taux = 10.0  # Taux emporter/livraison en France
    nb_pizzas = 0

    for ligne_data in data.get("lignes", []):
        prix = 0.0
        if ligne_data.get("taille_id"):
            result = await db.execute(
                select(ProduitTaille).where(ProduitTaille.id == ligne_data["taille_id"])
            )
            taille = result.scalar_one_or_none()
            if taille:
                prix = taille.prix
        else:
            result = await db.execute(
                select(ProduitTaille).where(ProduitTaille.produit_id == ligne_data["produit_id"])
            )
            taille = result.scalars().first()
            if taille:
                prix = taille.prix

        # Moitie-moitie : prix = max des deux moities
        if ligne_data.get("moitie_moitie") and ligne_data.get("moitie_produit_id"):
            nb_pizzas += 1
        else:
            # Verifier si c'est une pizza
            result = await db.execute(select(Produit).where(Produit.id == ligne_data["produit_id"]))
            produit = result.scalar_one_or_none()
            if produit and produit.est_pizza:
                nb_pizzas += ligne_data.get("quantite", 1)

        ligne = LigneCommande(
            commande_id=commande.id,
            produit_id=ligne_data["produit_id"],
            taille_id=ligne_data.get("taille_id"),
            quantite=ligne_data.get("quantite", 1),
            prix_unitaire=prix,
            type_pate=ligne_data.get("type_pate"),
            moitie_moitie=ligne_data.get("moitie_moitie", False),
            moitie_produit_id=ligne_data.get("moitie_produit_id"),
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
                db.add(LigneCommandeSupplement(
                    ligne_id=ligne.id,
                    supplement_id=sup.id,
                    quantite=sup_data.get("quantite", 1),
                    prix=sup.prix,
                ))
                montant_ligne += sup_prix

        montant_ht += montant_ligne

    # Code promo
    remise = await _appliquer_promo(db, data.get("code_promo", ""), montant_ht)

    # Frais livraison
    frais = data.get("frais_livraison", 0.0)

    # Calcul TVA sur montant apres remise
    montant_apres_remise = montant_ht - remise
    montant_tva = round(montant_apres_remise * tva_taux / 100, 2)

    commande.montant_ht = round(montant_apres_remise, 2)
    commande.montant_tva = montant_tva
    commande.frais_livraison = frais
    commande.remise = remise
    commande.montant_ttc = round(montant_apres_remise + montant_tva + frais, 2)

    # Estimation temps
    nb_en_queue = await _count_commandes_en_queue(db)
    commande.temps_estime = _estimer_temps(nb_pizzas, nb_en_queue)

    # Fidelite : +1 commande, +1 point par euro
    if client:
        client.nb_commandes += 1
        client.points_fidelite += int(commande.montant_ttc)

    await db.commit()
    await db.refresh(commande)
    return commande


async def _count_commandes_en_queue(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Commande.id)).where(
            Commande.statut.in_([StatutCommande.NOUVELLE, StatutCommande.CONFIRMEE, StatutCommande.EN_PREPARATION]),
            func.date(Commande.created_at) == date.today(),
        )
    )
    return result.scalar() or 0


async def get_commande(db: AsyncSession, commande_id: int) -> Commande | None:
    result = await db.execute(
        select(Commande)
        .options(
            selectinload(Commande.lignes).selectinload(LigneCommande.supplements),
            selectinload(Commande.lignes).selectinload(LigneCommande.produit),
            selectinload(Commande.lignes).selectinload(LigneCommande.taille),
            selectinload(Commande.lignes).selectinload(LigneCommande.moitie_produit),
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
    limit: int = 100,
) -> list[Commande]:
    stmt = (
        select(Commande)
        .options(
            selectinload(Commande.lignes).selectinload(LigneCommande.produit),
            selectinload(Commande.lignes).selectinload(LigneCommande.supplements),
            selectinload(Commande.lignes).selectinload(LigneCommande.taille),
            selectinload(Commande.lignes).selectinload(LigneCommande.moitie_produit),
            selectinload(Commande.client),
            selectinload(Commande.creneau),
        )
        .order_by(Commande.created_at.desc())
        .limit(limit)
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
