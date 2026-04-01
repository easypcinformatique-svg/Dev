"""Donnees de demonstration pour initialiser la pizzeria."""

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


async def seed():
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

        # ── Categories ──
        cat_pizzas = Categorie(nom="Pizzas", ordre=1, tva_taux=10.0)
        cat_boissons = Categorie(nom="Boissons", ordre=2, tva_taux=5.5)
        cat_desserts = Categorie(nom="Desserts", ordre=3, tva_taux=5.5)
        cat_entrees = Categorie(nom="Entrees", ordre=0, tva_taux=10.0)
        db.add_all([cat_entrees, cat_pizzas, cat_boissons, cat_desserts])
        await db.flush()

        # ── Entrees ──
        entrees = [
            ("Bruschetta", "Tomate, basilic, huile d'olive", 4.50),
            ("Salade Cesar", "Salade, poulet, parmesan, croutons", 6.50),
            ("Ail au fromage", "Pain a l'ail gratine", 3.50),
            ("Mozzarella sticks", "Batonnets de mozzarella panes", 5.00),
        ]
        for nom, desc, prix in entrees:
            p = Produit(categorie_id=cat_entrees.id, nom=nom, description=desc, actif=True, est_pizza=False, temps_preparation=5)
            db.add(p)
            await db.flush()
            db.add(ProduitTaille(produit_id=p.id, taille=TaillePizza.MEDIUM, prix=prix))

        # ── Pizzas ──
        pizzas = [
            ("Margherita", "Tomate, mozzarella, basilic frais", "tomate", "gluten,lactose", [8.0, 10.0, 13.0, 16.0]),
            ("Reine", "Tomate, mozzarella, jambon, champignons", "tomate", "gluten,lactose", [9.0, 11.0, 14.0, 17.0]),
            ("4 Fromages", "Creme, mozzarella, gorgonzola, chevre, parmesan", "creme", "gluten,lactose", [9.5, 12.0, 15.0, 18.0]),
            ("Calzone", "Tomate, mozzarella, jambon, oeuf, champignons", "tomate", "gluten,lactose,oeuf", [9.0, 11.5, 14.5, 17.5]),
            ("Pepperoni", "Tomate, mozzarella, pepperoni piquant", "tomate", "gluten,lactose", [9.0, 11.0, 14.0, 17.0]),
            ("Vegetarienne", "Tomate, mozzarella, poivrons, oignons, olives, champignons", "tomate", "gluten,lactose", [8.5, 10.5, 13.5, 16.5]),
            ("BBQ Chicken", "Sauce BBQ, mozzarella, poulet marine, oignons rouges", "bbq", "gluten,lactose", [10.0, 12.5, 15.5, 19.0]),
            ("Napolitaine", "Tomate, mozzarella, anchois, olives, capres", "tomate", "gluten,lactose,poisson", [9.0, 11.0, 14.0, 17.0]),
            ("Savoyarde", "Creme, mozzarella, raclette, pommes de terre, lardons", "creme", "gluten,lactose", [10.0, 12.5, 15.5, 19.0]),
            ("Orientale", "Tomate, mozzarella, merguez, poivrons, oignons, epices", "tomate", "gluten,lactose", [9.5, 12.0, 15.0, 18.0]),
            ("Saumon", "Creme, mozzarella, saumon fume, aneth, citron", "creme", "gluten,lactose,poisson", [11.0, 13.5, 16.5, 20.0]),
            ("Chevre Miel", "Creme, mozzarella, chevre, miel, noix", "creme", "gluten,lactose,fruits_a_coque", [10.0, 12.5, 15.5, 19.0]),
        ]
        tailles = [TaillePizza.JUNIOR, TaillePizza.MEDIUM, TaillePizza.LARGE, TaillePizza.XXL]

        for i, (nom, desc, base, allergenes, prix_list) in enumerate(pizzas):
            produit = Produit(
                categorie_id=cat_pizzas.id, nom=nom, description=desc,
                base_sauce=base, actif=True, ordre=i, est_pizza=True,
                allergenes=allergenes, temps_preparation=12,
            )
            db.add(produit)
            await db.flush()
            for taille, prix in zip(tailles, prix_list):
                db.add(ProduitTaille(produit_id=produit.id, taille=taille, prix=prix))

        # ── Boissons ──
        boissons = [
            ("Coca-Cola 33cl", 2.50), ("Coca-Cola Zero 33cl", 2.50),
            ("Orangina 33cl", 2.50), ("Eau minerale 50cl", 1.50),
            ("Perrier 33cl", 2.00), ("Ice Tea Peche 33cl", 2.50),
            ("Limonade maison 50cl", 3.00), ("Biere artisanale 33cl", 4.00),
        ]
        for nom, prix in boissons:
            p = Produit(categorie_id=cat_boissons.id, nom=nom, actif=True, temps_preparation=0)
            db.add(p)
            await db.flush()
            db.add(ProduitTaille(produit_id=p.id, taille=TaillePizza.MEDIUM, prix=prix))

        # ── Desserts ──
        desserts = [
            ("Tiramisu maison", 4.50, "gluten,lactose,oeuf"),
            ("Panna Cotta fruits rouges", 4.00, "lactose"),
            ("Fondant au chocolat", 5.00, "gluten,lactose,oeuf"),
            ("Glace artisanale 2 boules", 3.50, "lactose"),
            ("Tarte Nutella banane", 5.50, "gluten,lactose,fruits_a_coque"),
        ]
        for nom, prix, allergenes in desserts:
            p = Produit(categorie_id=cat_desserts.id, nom=nom, actif=True, allergenes=allergenes, temps_preparation=0)
            db.add(p)
            await db.flush()
            db.add(ProduitTaille(produit_id=p.id, taille=TaillePizza.MEDIUM, prix=prix))

        # ── Supplements ──
        supplements = [
            ("Double fromage", 2.00, "fromage", "lactose"),
            ("Mozzarella supp.", 1.50, "fromage", "lactose"),
            ("Jambon", 1.50, "viande", None),
            ("Pepperoni", 1.50, "viande", None),
            ("Poulet", 2.00, "viande", None),
            ("Champignons frais", 1.00, "legume", None),
            ("Poivrons", 1.00, "legume", None),
            ("Olives noires", 1.00, "legume", None),
            ("Oignons caramelises", 1.00, "legume", None),
            ("Oeuf", 1.00, "autre", "oeuf"),
            ("Anchois", 1.50, "poisson", "poisson"),
            ("Roquette", 0.80, "legume", None),
            ("Truffe (huile)", 3.00, "premium", None),
        ]
        for nom, prix, cat, allergenes in supplements:
            db.add(Supplement(nom=nom, prix=prix, categorie=cat, allergenes=allergenes))

        # ── Formules ──
        f1 = Formule(nom="Menu Midi (Pizza + Boisson)", prix=12.90, description="Disponible le midi uniquement")
        db.add(f1)
        await db.flush()
        db.add(FormuleElement(formule_id=f1.id, categorie_id=cat_pizzas.id, nb_choix=1))
        db.add(FormuleElement(formule_id=f1.id, categorie_id=cat_boissons.id, nb_choix=1))

        f2 = Formule(nom="Menu Complet (Pizza + Boisson + Dessert)", prix=16.90)
        db.add(f2)
        await db.flush()
        db.add(FormuleElement(formule_id=f2.id, categorie_id=cat_pizzas.id, nb_choix=1))
        db.add(FormuleElement(formule_id=f2.id, categorie_id=cat_boissons.id, nb_choix=1))
        db.add(FormuleElement(formule_id=f2.id, categorie_id=cat_desserts.id, nb_choix=1))

        # ── Promotions ──
        db.add(Promotion(code="BIENVENUE", nom="Bienvenue -10%", type_promo="pourcentage", valeur=10, montant_min=15))
        db.add(Promotion(code="LIVGRATUITE", nom="Livraison gratuite", type_promo="livraison_gratuite", valeur=0, montant_min=25))
        db.add(Promotion(code="5EUROS", nom="5 euros offerts", type_promo="montant_fixe", valeur=5, montant_min=20))

        # ── Creneaux Config ──
        for jour in range(7):
            db.add(CreneauConfig(jour_semaine=jour, heure_debut=time(11, 0), heure_fin=time(14, 0), intervalle_minutes=15, capacite_max=8))
            db.add(CreneauConfig(jour_semaine=jour, heure_debut=time(18, 0), heure_fin=time(22, 30), intervalle_minutes=15, capacite_max=10))

        # ── Zones de livraison ──
        db.add(ZoneLivraison(nom="Zone 1 - Gratuit (<2km)", codes_postaux=["75001", "75002", "75003", "75004"], frais_livraison=0.0))
        db.add(ZoneLivraison(nom="Zone 2 - 2.50 EUR (2-5km)", codes_postaux=["75005", "75006", "75007", "75008"], frais_livraison=2.50))
        db.add(ZoneLivraison(nom="Zone 3 - 4.00 EUR (5-8km)", codes_postaux=["75009", "75010", "75011", "75012"], frais_livraison=4.00))

        # ── Livreurs ──
        db.add(Livreur(nom="Karim", telephone="0612345678"))
        db.add(Livreur(nom="Lucas", telephone="0698765432"))
        db.add(Livreur(nom="Yassine", telephone="0654321098"))

        # ── Ingredients (stock) ──
        ingredients = [
            ("Pate a pizza", "boule", 100, 20),
            ("Sauce tomate", "litre", 30, 5),
            ("Mozzarella", "kg", 20, 3),
            ("Jambon", "kg", 10, 2),
            ("Champignons", "kg", 8, 2),
            ("Pepperoni", "kg", 6, 1),
            ("Poulet", "kg", 8, 2),
            ("Olives", "kg", 5, 1),
            ("Poivrons", "kg", 6, 1),
            ("Oignons", "kg", 6, 1),
            ("Creme fraiche", "litre", 10, 2),
            ("Sauce BBQ", "litre", 5, 1),
            ("Saumon fume", "kg", 3, 1),
            ("Chevre", "kg", 4, 1),
            ("Merguez", "kg", 5, 1),
        ]
        for nom, unite, stock, seuil in ingredients:
            db.add(Ingredient(nom=nom, unite=unite, quantite_stock=stock, seuil_alerte=seuil))

        await db.commit()
        print("Seed data cree avec succes !")
        print("Utilisateurs :")
        print("  Admin     -> PIN: 1234")
        print("  Caissier  -> PIN: 5678")
        print("  Pizzaiolo -> PIN: 9999")
        print("  Livreur   -> PIN: 1111")


if __name__ == "__main__":
    asyncio.run(seed())
