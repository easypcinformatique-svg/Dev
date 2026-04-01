"""Modèles de base de données pour la gestion des factures."""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Fournisseur(db.Model):
    """Fournisseur (Metro, EDF, Orange, etc.)."""

    __tablename__ = "fournisseurs"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    categorie = db.Column(db.String(100))  # alimentaire, energie, telecom, etc.
    site_url = db.Column(db.String(500))
    identifiant_site = db.Column(db.String(200))  # login pour téléchargement auto
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    factures = db.relationship("Facture", backref="fournisseur", lazy=True)

    def __repr__(self):
        return f"<Fournisseur {self.nom}>"


class Facture(db.Model):
    """Facture reçue d'un fournisseur."""

    __tablename__ = "factures"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(100))
    fournisseur_id = db.Column(
        db.Integer, db.ForeignKey("fournisseurs.id"), nullable=True
    )
    fournisseur_nom = db.Column(db.String(200))  # nom brut extrait par OCR

    date_facture = db.Column(db.Date)
    date_echeance = db.Column(db.Date)

    montant_ht = db.Column(db.Float, default=0.0)
    montant_tva = db.Column(db.Float, default=0.0)
    taux_tva = db.Column(db.Float, default=20.0)  # 5.5, 10, 20
    montant_ttc = db.Column(db.Float, default=0.0)

    # Source de la facture
    source = db.Column(db.String(50))  # gmail, drive_scan, upload, site_web
    fichier_path = db.Column(db.String(500))
    fichier_nom = db.Column(db.String(300))

    # Identifiants externes
    gmail_message_id = db.Column(db.String(200))
    drive_file_id = db.Column(db.String(200))

    # Statut
    statut = db.Column(
        db.String(50), default="a_verifier"
    )  # a_verifier, validee, payee, archivee
    ocr_traite = db.Column(db.Boolean, default=False)
    ocr_confiance = db.Column(db.Float)  # score de confiance OCR 0-100

    # Période TVA
    periode_tva = db.Column(db.String(7))  # format: 2024-01

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<Facture {self.numero} - {self.fournisseur_nom}>"


class SyncLog(db.Model):
    """Journal de synchronisation (Gmail, Drive, sites)."""

    __tablename__ = "sync_logs"

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(50), nullable=False)  # gmail, drive, metro, edf, etc.
    statut = db.Column(db.String(50))  # succes, erreur
    message = db.Column(db.Text)
    factures_importees = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<SyncLog {self.source} - {self.statut}>"


class ParametreTVA(db.Model):
    """Paramètres de TVA par catégorie de produit."""

    __tablename__ = "parametres_tva"

    id = db.Column(db.Integer, primary_key=True)
    categorie = db.Column(db.String(100), nullable=False)
    taux = db.Column(db.Float, nullable=False)  # 5.5, 10, 20
    description = db.Column(db.String(300))

    def __repr__(self):
        return f"<ParametreTVA {self.categorie} - {self.taux}%>"
