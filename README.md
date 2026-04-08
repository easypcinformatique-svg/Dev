# Gestion de Factures - Pizzeria

Application web de gestion et d'archivage de factures pour une pizzeria (vente a emporter), avec synchronisation Gmail, Google Drive et extraction OCR pour la declaration de TVA.

## Fonctionnalites

- **Import automatique Gmail** : Recupere les factures en pieces jointes de vos emails
- **Synchronisation Google Drive** : Importe les factures scannees depuis votre dossier Drive
- **Upload manuel** : Importez des factures directement depuis votre navigateur
- **OCR** : Extraction automatique des donnees (numero, date, montants, TVA) via Tesseract
- **Calcul TVA** : Synthese mensuelle et annuelle pour la declaration de TVA
- **Export CSV** : Exportez les donnees par periode pour votre comptable
- **Gestion fournisseurs** : Metro, Promocash, EDF, Orange, SFR, etc.

## Prerequis

- Python 3.10+
- Tesseract OCR (`sudo apt install tesseract-ocr tesseract-ocr-fra`)
- Poppler pour la conversion PDF (`sudo apt install poppler-utils`)
- Un projet Google Cloud avec les APIs Gmail et Drive activees

## Installation

```bash
# Cloner le projet
git clone <url-du-repo>
cd Dev

# Creer un environnement virtuel
python -m venv venv
source venv/bin/activate

# Installer les dependances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Editez .env avec vos identifiants Google OAuth
```

## Configuration Google OAuth

1. Allez sur [Google Cloud Console](https://console.cloud.google.com)
2. Creez un nouveau projet
3. Activez les APIs : **Gmail API** et **Google Drive API**
4. Allez dans "Identifiants" > "Creer des identifiants" > "ID client OAuth"
5. Type : **Application Web**
6. URI de redirection autorisee : `http://localhost:5000/auth/callback`
7. Copiez le Client ID et Client Secret dans votre fichier `.env`

## Lancement

```bash
# Mode developpement
python run.py

# Mode production
gunicorn run:app -b 0.0.0.0:5000
```

L'application est accessible sur `http://localhost:5000`

## Utilisation

### Premier lancement
1. Ouvrez l'application dans votre navigateur
2. Cliquez sur "Connecter Google" pour lier votre compte Gmail/Drive
3. Les fournisseurs par defaut (Metro, EDF, Orange...) sont deja configures

### Workflow quotidien
1. **Le soir** : Scannez vos factures et deposez-les dans votre dossier Google Drive
2. **Depuis l'app** : Cliquez "Synchroniser Drive" pour importer les scans
3. **Emails** : Cliquez "Synchroniser Gmail" pour recuperer les factures en PJ
4. **OCR** : Sur chaque facture, lancez l'OCR pour extraire les donnees
5. **Verification** : Validez les donnees extraites et corrigez si necessaire
6. **TVA** : Consultez la synthese TVA pour votre declaration

### Declaration TVA
1. Allez dans l'onglet "TVA"
2. Verifiez que toutes les factures du mois sont "validees"
3. Consultez le resume par taux de TVA
4. Exportez en CSV pour votre comptable

## Structure du projet

```
Dev/
├── run.py                    # Point d'entree
├── requirements.txt          # Dependances Python
├── .env.example              # Modele de configuration
├── app/
│   ├── create_app.py         # Factory Flask
│   ├── models.py             # Modeles de base de donnees
│   ├── routes.py             # Routes et API
│   ├── templates/            # Templates HTML
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── factures.html
│   │   ├── facture_detail.html
│   │   ├── tva.html
│   │   ├── upload.html
│   │   └── fournisseurs.html
│   ├── static/css/style.css  # Styles CSS
│   └── modules/
│       ├── auth_google.py    # Authentification Google OAuth2
│       ├── gmail_service.py  # Recuperation PJ Gmail
│       ├── drive_service.py  # Synchronisation Google Drive
│       ├── ocr_service.py    # Extraction OCR
│       └── tva_service.py    # Calcul et reporting TVA
└── uploads/                  # Factures telechargees (gitignore)
```

## Taux de TVA configures

| Categorie | Taux | Usage |
|-----------|------|-------|
| Produits alimentaires (emporter) | 5,5% | Vente a emporter |
| Restauration (sur place) | 10% | Consommation immediate |
| Boissons alcoolisees | 20% | Bieres, vins, etc. |
| Fournitures et services | 20% | Emballages, nettoyage, etc. |
| Energie | 20% | Electricite, gaz |
