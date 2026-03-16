"""Factory de l'application Flask."""

import os

from dotenv import load_dotenv
from flask import Flask

from app.models import Fournisseur, ParametreTVA, db
from app.routes import main

load_dotenv()


def create_app():
    """Crée et configure l'application Flask."""
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///factures.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "./uploads")

    # Google OAuth
    app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID", "")
    app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    app.config["GOOGLE_REDIRECT_URI"] = os.environ.get(
        "GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/callback"
    )
    app.config["GOOGLE_DRIVE_FOLDER_ID"] = os.environ.get(
        "GOOGLE_DRIVE_FOLDER_ID", ""
    )
    app.config["GMAIL_SEARCH_QUERY"] = os.environ.get("GMAIL_SEARCH_QUERY", "")

    # Initialiser la base de données
    db.init_app(app)

    # Enregistrer les routes
    app.register_blueprint(main)

    # Créer les tables et données initiales
    with app.app_context():
        db.create_all()
        _init_donnees()

    return app


def _init_donnees():
    """Initialise les données par défaut (fournisseurs, taux TVA)."""
    # Fournisseurs par défaut
    if Fournisseur.query.count() == 0:
        fournisseurs = [
            Fournisseur(nom="Metro", categorie="alimentaire"),
            Fournisseur(nom="Promocash", categorie="alimentaire"),
            Fournisseur(nom="EDF", categorie="energie"),
            Fournisseur(nom="Orange", categorie="telecom"),
            Fournisseur(nom="SFR", categorie="telecom"),
        ]
        db.session.add_all(fournisseurs)

    # Taux TVA par défaut
    if ParametreTVA.query.count() == 0:
        taux = [
            ParametreTVA(
                categorie="Produits alimentaires (vente à emporter)",
                taux=5.5,
                description="TVA réduite pour la vente à emporter de produits alimentaires",
            ),
            ParametreTVA(
                categorie="Produits alimentaires (consommation immédiate)",
                taux=10.0,
                description="TVA intermédiaire pour la restauration sur place",
            ),
            ParametreTVA(
                categorie="Boissons alcoolisées",
                taux=20.0,
                description="TVA normale pour les boissons alcoolisées",
            ),
            ParametreTVA(
                categorie="Fournitures et services",
                taux=20.0,
                description="TVA normale pour les achats non alimentaires",
            ),
            ParametreTVA(
                categorie="Énergie",
                taux=20.0,
                description="TVA normale pour l'électricité, gaz, etc.",
            ),
        ]
        db.session.add_all(taux)

    db.session.commit()
