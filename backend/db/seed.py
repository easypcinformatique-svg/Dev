"""Import de la carte Pizza Napoli Carpentras depuis l'export L'Addition."""

import asyncio
import sys
from datetime import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.db.database import engine, async_session
from backend.models.base import Base
from backend.models import (
    Categorie, Produit, ProduitTaille, Supplement, Formule, FormuleElement,
    Utilisateur, CreneauConfig, ZoneLivraison, Livreur, Ingredient, Promotion,
    TaillePizza, Role,
)
from backend.services.auth_service import hash_pin

# ── Carte Pizza Napoli Carpentras (export L'Addition) ─────────
# Format: (nom, prix_normal, prix_petite, categorie_l_addition)
# prix_petite = None si pas de version petite

PIZZAS_CLASSIQUES = [
    ("MARGHARITA", 9.90, 7.00),
    ("REINE", 12.50, 7.90),
    ("ROMAINE", 12.00, 7.90),
    ("ROYALE", 13.00, 7.90),
    ("CHORIZO", 12.00, 7.90),
    ("ANCHOIS", 12.00, 7.90),
    ("MERGUEZ", 12.50, 7.90),
]

PIZZAS_FROMAGES = [
    ("3 FRO", 13.00, 7.90),
    ("4 FRO", 13.50, 7.90),
    ("CHEVRE", 12.00, 7.90),
    ("CHEVRE-MIEL", 12.50, 7.90),
    ("MOZZA", 12.00, 7.90),
    ("MEGAFROMAGE", 13.90, 8.00),
    ("PARMESANE", 12.50, 7.90),
    ("ROQUEFORT", 11.50, None),
]

PIZZAS_CARNIVORES = [
    ("ARMÉNIENNE", 13.50, 7.90),
    ("BARAKOBAMA", 13.00, 7.90),
    ("BOLOGNAISE", 13.50, 7.90),
    ("BUFFALO", 12.50, 7.90),
    ("BURGER", 13.50, 8.00),
    ("CHILIENNE", 13.00, 7.90),
    ("CIRCUS", 13.90, 7.90),
    ("FARWEST", 13.50, 7.90),
    ("HAWAÏENNE", 13.50, 7.90),
    ("INDIANA", 13.00, 7.90),
    ("KEBAB", 13.50, 7.90),
    ("KIDECHIRE", 12.90, 7.90),
    ("MANHATTAN", 13.00, 7.90),
    ("MEXICAINE", 12.50, 7.90),
    ("ORIENTALE", 12.90, 7.90),
    ("WANABIE", 13.50, 7.90),
    ("APHRODITE", 14.90, 8.50),
]

PIZZAS_BLANCHES = [
    ("BARAKA", 13.90, 7.90),
    ("BERGÈRE", 12.50, 7.90),
    ("BRETONNE", 11.00, None),
    ("CAMEMBERT", 13.50, 7.90),
    ("CHTI PIZZ", 13.50, 7.90),
    ("DAME BLANCHE", 13.00, 7.90),
    ("DAUPHINOISE", 13.00, 7.90),
    ("DÉLICIEUSE", 12.90, 7.90),
    ("FLAMKEUCH", 12.00, 7.90),
    ("JAKASS", 12.50, 7.90),
    ("LORRAINE", 12.00, None),
    ("MONT BLANC", 13.50, 7.90),
    ("NAPOLI", 13.50, 7.50),
    ("SAUMON", 12.50, 7.90),
    ("SWEETY CHÈVRE", 13.50, 7.90),
    ("TARTIFLETTE", 13.90, 8.00),
    ("XENA", 12.90, 7.90),
    ("RAVIOLE BASILIC", 12.50, 7.90),
    ("RAVIOLE SAUMON", 13.90, 8.50),
]

PIZZAS_COMPOSEES = [
    ("CAMPAGNARDE", 13.90, 8.50),
    ("CANADIENNE", 11.50, 7.50),
    ("COCHONAILLE", 13.90, 7.90),
    ("EL PASO", 12.00, 7.90),
    ("FORESTIÈRE", 12.50, 7.90),
    ("MEGAROYALE", 13.90, 7.90),
    ("NORDISTE", 13.00, 7.90),
    ("PAYSANNE", 13.00, 7.90),
    ("SWEET CHORIZO", 13.00, 8.50),
]

PIZZAS_LEGUMES = [
    ("4 SAISONS", 13.50, 7.90),
    ("ACROPOLIS", 13.00, 7.90),
    ("AUBERGINES", 12.50, None),
    ("MILANO", 13.00, 7.90),
    ("MOUSSAKA", 13.90, 7.90),
    ("POIVRONS", 11.00, None),
    ("VÉGÉTARIENNE", 13.50, 7.90),
]

PIZZAS_MARITIMES = [
    ("CATALANE", 11.50, None),
    ("FRUIT DE MER", 11.50, 7.90),
    ("PISSALADIÈRE", 11.50, 7.90),
    ("THONCAPRE", 12.00, 7.90),
    ("SAINT JACQUES", 13.90, 8.00),
]

PIZZAS_ALPINES = [
    ("MONTAGNARDE", 13.00, 7.90),
    ("PYRÉNÉENNE", 13.00, 7.90),
    ("RACLON", 13.50, 7.90),
    ("SAVOYARDE", 13.00, 7.90),
]

PIZZAS_NOUVEAUTES = [
    ("GRANDIOSA", 13.50, None),
    ("MOZZA DI BUFALA", 13.50, None),
    ("TARTUFO", 13.50, None),
]

PLAQUES = [
    ("MARGHA plaque", 25.00),
    ("REINE plaque", 30.00),
    ("ROMAINE plaque", 30.00),
    ("CHORIZO plaque", 30.00),
    ("CHEVRE plaque", 30.00),
    ("FLAMKEUCH plaque", 35.00),
    ("PISSALADIÈRE plaque", 35.00),
]

DESSERTS = [
    ("CHOCOBANANE", 9.50),
    ("CHOCOANANAS", 9.50),
    ("CHOCOPOIRE", 9.50),
    ("SPECULOOS", 9.00),
    ("DONNUTS", 1.50),
    ("SUNDAE", 2.00),
]

BOISSONS = [
    ("Canette Coca 33cl", 1.60),
    ("Canette Coca Cherry 33cl", 1.60),
    ("Canette Oasis 33cl", 1.60),
    ("Canette Oasis Pomme Cassis 33cl", 1.60),
    ("Schweppes Pomme", 1.60),
    ("Coca-Cola 1.25L", 3.00),
    ("Fanta 1.5L", 3.00),
    ("Ice Tea 1.5L", 3.00),
]

BIERES = [
    ("Heineken 33cl", 1.60),
    ("Corona", 2.50),
    ("Desperado", 2.50),
]

VINS = [
    ("Petite Balade Rosé", 6.00),
]


async def seed():
    """Importe la vraie carte Pizza Napoli Carpentras."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # ── Utilisateurs ──
        db.add_all([
            Utilisateur(nom="Admin", pin_hash=hash_pin("1234"), role=Role.ADMIN),
            Utilisateur(nom="Caissier", pin_hash=hash_pin("5678"), role=Role.CAISSIER),
            Utilisateur(nom="Pizzaiolo", pin_hash=hash_pin("9999"), role=Role.PIZZAIOLO),
            Utilisateur(nom="Livreur", pin_hash=hash_pin("1111"), role=Role.LIVREUR),
        ])

        # ── Categories Pizzas ──
        cats = {}
        pizza_categories = [
            ("Les Classiques", 1),
            ("Les Fromages", 2),
            ("Les Carnivores", 3),
            ("Les Blanches", 4),
            ("Les Composées", 5),
            ("Les Légumes", 6),
            ("Les Maritimes", 7),
            ("Les Alpines", 8),
            ("Nouveautés", 9),
            ("Plaques Pizza", 10),
            ("Desserts", 11),
            ("Boissons", 12),
            ("Bières", 13),
            ("Vins", 14),
        ]
        for nom, ordre in pizza_categories:
            tva = 10.0  # Pizzas et desserts
            if nom in ("Boissons", "Bières"):
                tva = 5.5
            elif nom == "Vins":
                tva = 20.0
            cat = Categorie(nom=nom, ordre=ordre, tva_taux=tva)
            db.add(cat)
            cats[nom] = cat
        await db.flush()

        # ── Helper pour ajouter des pizzas ──
        async def add_pizzas(pizza_list, cat_name):
            cat = cats[cat_name]
            for i, pizza in enumerate(pizza_list):
                nom, prix_normal, prix_petite = pizza[0], pizza[1], pizza[2] if len(pizza) > 2 else None
                produit = Produit(
                    categorie_id=cat.id, nom=nom, actif=True, est_pizza=True,
                    ordre=i, temps_preparation=12, allergenes="gluten,lactose",
                )
                db.add(produit)
                await db.flush()
                # Taille normale (LARGE)
                db.add(ProduitTaille(produit_id=produit.id, taille=TaillePizza.LARGE, prix=prix_normal))
                # Petite taille (JUNIOR) si disponible
                if prix_petite:
                    db.add(ProduitTaille(produit_id=produit.id, taille=TaillePizza.JUNIOR, prix=prix_petite))

        await add_pizzas(PIZZAS_CLASSIQUES, "Les Classiques")
        await add_pizzas(PIZZAS_FROMAGES, "Les Fromages")
        await add_pizzas(PIZZAS_CARNIVORES, "Les Carnivores")
        await add_pizzas(PIZZAS_BLANCHES, "Les Blanches")
        await add_pizzas(PIZZAS_COMPOSEES, "Les Composées")
        await add_pizzas(PIZZAS_LEGUMES, "Les Légumes")
        await add_pizzas(PIZZAS_MARITIMES, "Les Maritimes")
        await add_pizzas(PIZZAS_ALPINES, "Les Alpines")
        await add_pizzas(PIZZAS_NOUVEAUTES, "Nouveautés")

        # ── Plaques ──
        cat_plaques = cats["Plaques Pizza"]
        for i, (nom, prix) in enumerate(PLAQUES):
            p = Produit(categorie_id=cat_plaques.id, nom=nom, actif=True, est_pizza=True, ordre=i, temps_preparation=20)
            db.add(p)
            await db.flush()
            db.add(ProduitTaille(produit_id=p.id, taille=TaillePizza.XXL, prix=prix))

        # ── Desserts ──
        cat_desserts = cats["Desserts"]
        for i, (nom, prix) in enumerate(DESSERTS):
            est_pizza = nom.startswith("CHOCO") or nom == "SPECULOOS"
            p = Produit(categorie_id=cat_desserts.id, nom=nom, actif=True, est_pizza=est_pizza, ordre=i, temps_preparation=8 if est_pizza else 0)
            db.add(p)
            await db.flush()
            db.add(ProduitTaille(produit_id=p.id, taille=TaillePizza.MEDIUM, prix=prix))

        # ── Boissons ──
        cat_boissons = cats["Boissons"]
        for i, (nom, prix) in enumerate(BOISSONS):
            p = Produit(categorie_id=cat_boissons.id, nom=nom, actif=True, temps_preparation=0, ordre=i)
            db.add(p)
            await db.flush()
            db.add(ProduitTaille(produit_id=p.id, taille=TaillePizza.MEDIUM, prix=prix))

        # ── Bières ──
        cat_bieres = cats["Bières"]
        for i, (nom, prix) in enumerate(BIERES):
            p = Produit(categorie_id=cat_bieres.id, nom=nom, actif=True, temps_preparation=0, ordre=i)
            db.add(p)
            await db.flush()
            db.add(ProduitTaille(produit_id=p.id, taille=TaillePizza.MEDIUM, prix=prix))

        # ── Vins ──
        cat_vins = cats["Vins"]
        for i, (nom, prix) in enumerate(VINS):
            p = Produit(categorie_id=cat_vins.id, nom=nom, actif=True, temps_preparation=0, ordre=i)
            db.add(p)
            await db.flush()
            db.add(ProduitTaille(produit_id=p.id, taille=TaillePizza.MEDIUM, prix=prix))

        # ── Supplements ──
        supplements = [
            ("Double fromage", 2.00, "fromage"),
            ("Mozzarella supp.", 1.50, "fromage"),
            ("Jambon", 1.50, "viande"),
            ("Chorizo", 1.50, "viande"),
            ("Merguez", 1.50, "viande"),
            ("Poulet", 2.00, "viande"),
            ("Champignons", 1.00, "legume"),
            ("Poivrons", 1.00, "legume"),
            ("Olives", 1.00, "legume"),
            ("Oignons", 0.80, "legume"),
            ("Oeuf", 1.00, "autre"),
            ("Anchois", 1.50, "poisson"),
        ]
        for nom, prix, cat in supplements:
            db.add(Supplement(nom=nom, prix=prix, categorie=cat))

        # ── Formules ──
        f1 = Formule(nom="Menu Pizza + Boisson", prix=13.90, description="Pizza au choix + boisson 33cl")
        db.add(f1)
        await db.flush()
        db.add(FormuleElement(formule_id=f1.id, categorie_id=cats["Les Classiques"].id, nb_choix=1))
        db.add(FormuleElement(formule_id=f1.id, categorie_id=cats["Boissons"].id, nb_choix=1))

        # ── Promotions ──
        db.add(Promotion(code="BIENVENUE", nom="Bienvenue -10%", type_promo="pourcentage", valeur=10, montant_min=15))
        db.add(Promotion(code="LIVGRATUITE", nom="Livraison offerte", type_promo="livraison_gratuite", valeur=0, montant_min=25))

        # ── Creneaux Config ──
        for jour in range(7):
            db.add(CreneauConfig(jour_semaine=jour, heure_debut=time(11, 0), heure_fin=time(14, 0), intervalle_minutes=15, capacite_max=8))
            db.add(CreneauConfig(jour_semaine=jour, heure_debut=time(18, 0), heure_fin=time(22, 30), intervalle_minutes=15, capacite_max=12))

        # ── Zones de livraison (Carpentras) ──
        db.add(ZoneLivraison(nom="Carpentras centre", codes_postaux=["84200"], frais_livraison=0.0))
        db.add(ZoneLivraison(nom="Proche Carpentras", codes_postaux=["84210", "84170", "84380"], frais_livraison=2.50))
        db.add(ZoneLivraison(nom="Eloigné", codes_postaux=["84330", "84340", "84570"], frais_livraison=4.00))

        # ── Livreurs ──
        db.add(Livreur(nom="Livreur 1", telephone="0600000001"))
        db.add(Livreur(nom="Livreur 2", telephone="0600000002"))

        await db.commit()
        print("Import Pizza Napoli Carpentras termine !")
        print(f"Categories: {len(pizza_categories)}")
        total_pizzas = sum(len(lst) for lst in [
            PIZZAS_CLASSIQUES, PIZZAS_FROMAGES, PIZZAS_CARNIVORES, PIZZAS_BLANCHES,
            PIZZAS_COMPOSEES, PIZZAS_LEGUMES, PIZZAS_MARITIMES, PIZZAS_ALPINES,
            PIZZAS_NOUVEAUTES, PLAQUES,
        ])
        print(f"Pizzas: {total_pizzas}")
        print(f"Boissons/Bieres/Vins: {len(BOISSONS) + len(BIERES) + len(VINS)}")
        print(f"Desserts: {len(DESSERTS)}")
        print("Utilisateurs: Admin:1234, Caissier:5678, Pizzaiolo:9999, Livreur:1111")


if __name__ == "__main__":
    asyncio.run(seed())
