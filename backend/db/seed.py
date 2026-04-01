"""Donnees de demonstration pour initialiser la pizzeria."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.db.database import engine, async_session
from backend.models.base import Base
from backend.models import (
    Categorie, Produit, ProduitTaille, Supplement, Formule, FormuleElement,
    Utilisateur, CreneauConfig, ZoneLivraison, Livreur, Ingredient,
    TaillePizza, Role,
)
from backend.services.auth_service import hash_pin


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # ── Utilisateurs ──
        admin = Utilisateur(nom="Admin", pin_hash=hash_pin("1234"), role=Role.ADMIN)
        caissier = Utilisateur(nom="Caissier", pin_hash=hash_pin("5678"), role=Role.CAISSIER)
        pizzaiolo = Utilisateur(nom="Pizzaiolo", pin_hash=hash_pin("9999"), role=Role.PIZZAIOLO)
        db.add_all([admin, caissier, pizzaiolo])

        # ── Categories ──
        cat_pizzas = Categorie(nom="Pizzas", ordre=1, tva_taux=10.0)
        cat_boissons = Categorie(nom="Boissons", ordre=2, tva_taux=5.5)
        cat_desserts = Categorie(nom="Desserts", ordre=3, tva_taux=5.5)
        db.add_all([cat_pizzas, cat_boissons, cat_desserts])
        await db.flush()

        # ── Pizzas ──
        pizzas = [
            ("Margherita", "Tomate, mozzarella, basilic", "tomate", [8.0, 10.0, 13.0, 16.0]),
            ("Reine", "Tomate, mozzarella, jambon, champignons", "tomate", [9.0, 11.0, 14.0, 17.0]),
            ("4 Fromages", "Creme, mozzarella, gorgonzola, chevre, parmesan", "creme", [9.5, 12.0, 15.0, 18.0]),
            ("Calzone", "Tomate, mozzarella, jambon, oeuf", "tomate", [9.0, 11.5, 14.5, 17.5]),
            ("Pepperoni", "Tomate, mozzarella, pepperoni", "tomate", [9.0, 11.0, 14.0, 17.0]),
            ("Vegetarienne", "Tomate, mozzarella, poivrons, oignons, olives, champignons", "tomate", [8.5, 10.5, 13.5, 16.5]),
            ("BBQ Chicken", "Sauce BBQ, mozzarella, poulet, oignons", "bbq", [10.0, 12.5, 15.5, 19.0]),
            ("Napolitaine", "Tomate, mozzarella, anchois, olives, capres", "tomate", [9.0, 11.0, 14.0, 17.0]),
            ("Savoyarde", "Creme, mozzarella, raclette, pommes de terre, lardons", "creme", [10.0, 12.5, 15.5, 19.0]),
            ("Orientale", "Tomate, mozzarella, merguez, poivrons, oignons", "tomate", [9.5, 12.0, 15.0, 18.0]),
        ]
        tailles = [TaillePizza.JUNIOR, TaillePizza.MEDIUM, TaillePizza.LARGE, TaillePizza.XXL]

        for nom, desc, base, prix_list in pizzas:
            produit = Produit(
                categorie_id=cat_pizzas.id, nom=nom, description=desc,
                base_sauce=base, actif=True, ordre=pizzas.index((nom, desc, base, prix_list)),
            )
            db.add(produit)
            await db.flush()
            for taille, prix in zip(tailles, prix_list):
                db.add(ProduitTaille(produit_id=produit.id, taille=taille, prix=prix))

        # ── Boissons ──
        boissons = [
            ("Coca-Cola 33cl", 2.50),
            ("Coca-Cola Zero 33cl", 2.50),
            ("Orangina 33cl", 2.50),
            ("Eau minerale 50cl", 1.50),
            ("Perrier 33cl", 2.00),
            ("Ice Tea 33cl", 2.50),
        ]
        for nom, prix in boissons:
            p = Produit(categorie_id=cat_boissons.id, nom=nom, actif=True)
            db.add(p)
            await db.flush()
            db.add(ProduitTaille(produit_id=p.id, taille=TaillePizza.MEDIUM, prix=prix))

        # ── Desserts ──
        desserts = [
            ("Tiramisu", 4.50),
            ("Panna Cotta", 4.00),
            ("Fondant au chocolat", 5.00),
            ("Glace 2 boules", 3.50),
        ]
        for nom, prix in desserts:
            p = Produit(categorie_id=cat_desserts.id, nom=nom, actif=True)
            db.add(p)
            await db.flush()
            db.add(ProduitTaille(produit_id=p.id, taille=TaillePizza.MEDIUM, prix=prix))

        # ── Supplements ──
        supplements = [
            ("Double fromage", 2.00, "fromage"),
            ("Mozzarella supplementaire", 1.50, "fromage"),
            ("Jambon", 1.50, "viande"),
            ("Pepperoni", 1.50, "viande"),
            ("Poulet", 2.00, "viande"),
            ("Champignons", 1.00, "legume"),
            ("Poivrons", 1.00, "legume"),
            ("Olives", 1.00, "legume"),
            ("Oignons", 0.80, "legume"),
            ("Oeuf", 1.00, "autre"),
        ]
        for nom, prix, cat in supplements:
            db.add(Supplement(nom=nom, prix=prix, categorie=cat))

        # ── Formule ──
        formule = Formule(nom="Menu Pizza + Boisson + Dessert", prix=15.90)
        db.add(formule)
        await db.flush()
        db.add(FormuleElement(formule_id=formule.id, categorie_id=cat_pizzas.id, nb_choix=1))
        db.add(FormuleElement(formule_id=formule.id, categorie_id=cat_boissons.id, nb_choix=1))
        db.add(FormuleElement(formule_id=formule.id, categorie_id=cat_desserts.id, nb_choix=1))

        # ── Creneaux Config (Lundi-Dimanche, 11h-14h et 18h-22h) ──
        for jour in range(7):
            # Service midi
            db.add(CreneauConfig(
                jour_semaine=jour, heure_debut="11:00", heure_fin="14:00",
                intervalle_minutes=15, capacite_max=8,
            ))
            # Service soir
            db.add(CreneauConfig(
                jour_semaine=jour, heure_debut="18:00", heure_fin="22:30",
                intervalle_minutes=15, capacite_max=10,
            ))

        # ── Zones de livraison ──
        db.add(ZoneLivraison(nom="Zone 1 - Centre", codes_postaux=["75001", "75002", "75003", "75004"], frais_livraison=0.0))
        db.add(ZoneLivraison(nom="Zone 2 - Proche", codes_postaux=["75005", "75006", "75007", "75008"], frais_livraison=2.50))
        db.add(ZoneLivraison(nom="Zone 3 - Eloigne", codes_postaux=["75009", "75010", "75011", "75012"], frais_livraison=4.00))

        # ── Livreurs ──
        db.add(Livreur(nom="Karim", telephone="0612345678"))
        db.add(Livreur(nom="Lucas", telephone="0698765432"))

        # ── Ingredients (stock) ──
        ingredients = [
            ("Pate a pizza", "boule", 50, 10),
            ("Sauce tomate", "litre", 20, 5),
            ("Mozzarella", "kg", 15, 3),
            ("Jambon", "kg", 8, 2),
            ("Champignons", "kg", 5, 1),
            ("Pepperoni", "kg", 5, 1),
            ("Poulet", "kg", 5, 1),
            ("Olives", "kg", 3, 1),
            ("Poivrons", "kg", 4, 1),
            ("Oignons", "kg", 4, 1),
        ]
        for nom, unite, stock, seuil in ingredients:
            db.add(Ingredient(nom=nom, unite=unite, quantite_stock=stock, seuil_alerte=seuil))

        await db.commit()
        print("Seed data cree avec succes !")
        print("Utilisateurs :")
        print("  Admin    -> PIN: 1234")
        print("  Caissier -> PIN: 5678")
        print("  Pizzaiolo -> PIN: 9999")


if __name__ == "__main__":
    asyncio.run(seed())
