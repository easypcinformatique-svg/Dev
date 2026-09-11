# PizzaCaisse - Logiciel de Caisse Pizzeria

Logiciel de caisse (POS) complet pour pizzeria, optimise pour la **vente a emporter** et la **livraison**.

## Stack Technique

| Composant | Technologie |
|-----------|------------|
| Backend | Python / FastAPI |
| Frontend | React.js + TailwindCSS |
| Base de donnees | PostgreSQL |
| Temps reel | WebSockets |
| Impression | ESC/POS (thermique 80mm) |
| Deploiement | Docker |

## Structure du Projet

```
backend/
  api/routes/       # Routes FastAPI (commandes, menu, clients, stats, auth)
  models/           # Modeles SQLAlchemy + schemas Pydantic
  services/         # Logique metier (prix, stocks, zones livraison)
  websocket/        # Notifications temps reel (cuisine, suivi commande)
  printing/         # Generation tickets ESC/POS
  db/migrations/    # Migrations Alembic

frontend/
  pos/              # Interface caisse (prise de commande, encaissement)
  kitchen/          # Ecran cuisine (KDS - Kitchen Display System)
  delivery/         # Gestion des livraisons
  admin/            # Dashboard, stats, gestion menu/stocks/users
  online/           # Module commande en ligne (client)
  shared/           # Composants, hooks et utils partages

tests/
  backend/          # Tests API et services
  frontend/         # Tests composants React

docker/             # Fichiers Docker
docs/               # Documentation
```

## Modules

1. **Gestion du Menu** - Pizzas (multi-tailles), supplements, formules, TVA
2. **Prise de Commande** - Interface tactile, mode emporter/livraison, historique client
3. **Ecran Cuisine (KDS)** - File d'attente temps reel, timer, statuts couleur
4. **Livraisons** - Gestion livreurs, zones, suivi statut, frais par zone
5. **Encaissement** - Especes, CB, ticket resto, paiement mixte, ticket Z
6. **Commande en Ligne** - Menu web, panier, paiement Stripe, suivi temps reel
7. **Statistiques** - CA, top pizzas, panier moyen, performance livreurs
8. **Stocks** - Ingredients, decompte auto, alertes, fiches techniques
9. **Utilisateurs** - Roles (admin/caissier/pizzaiolo/livreur), PIN, journal
10. **Configuration** - Infos pizzeria, horaires, imprimantes, promos

## Demarrage Rapide

```bash
# Cloner et lancer
docker-compose up -d

# Backend seul (dev)
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# Frontend seul (dev)
cd frontend && npm install && npm run dev
```

## Conformite

- **NF525** : Signature et inalterabilite des tickets
- **RGPD** : Protection des donnees clients
