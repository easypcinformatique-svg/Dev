"""Classe de base pour les scrapers d'encheres."""

import re
import hashlib
from datetime import datetime


class BaseScraper:
    """Classe abstraite pour tous les scrapers."""

    name = "base"
    base_url = ""

    CATEGORY_KEYWORDS = {
        "immobilier": [
            "appartement", "maison", "terrain", "local", "immeuble",
            "villa", "studio", "parking", "garage", "bureau", "commerce",
            "entrepot", "hangar", "fonds de commerce"
        ],
        "vehicules": [
            "voiture", "vehicule", "auto", "moto", "scooter", "camion",
            "utilitaire", "fourgon", "caravane", "bateau", "quad",
            "remorque", "tracteur", "poids lourd"
        ],
        "mobilier": [
            "meuble", "canape", "table", "chaise", "armoire", "lit",
            "bureau", "commode", "buffet", "etagere", "cuisine equipee",
            "electromenager", "vaisselle"
        ],
        "art": [
            "tableau", "peinture", "sculpture", "lithographie", "estampe",
            "gravure", "dessin", "aquarelle", "huile sur toile",
            "bronze", "ceramique", "porcelaine", "antiquite"
        ],
        "bijoux": [
            "bijou", "bague", "collier", "bracelet", "montre", "pendentif",
            "boucle", "diamant", "or", "argent", "perle", "saphir",
            "emeraude", "rubis"
        ],
        "electronique": [
            "ordinateur", "telephone", "tablette", "ecran", "televiseur",
            "tv", "console", "imprimante", "serveur", "informatique",
            "materiel informatique", "iphone", "samsung"
        ]
    }

    def scan(self, department="13", cities=None):
        """Scan les encheres. A surcharger dans les classes filles."""
        raise NotImplementedError

    def classify_category(self, title, description=""):
        """Classifie une enchere dans une categorie basee sur le titre/description."""
        text = f"{title} {description}".lower()
        # Normaliser les accents
        text = self._remove_accents(text)

        best_cat = "autre"
        best_score = 0

        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_cat = cat

        return best_cat

    def generate_id(self, source, title, date=""):
        """Genere un ID unique pour une enchere."""
        raw = f"{source}:{title}:{date}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def parse_price(self, price_str):
        """Parse un prix depuis une chaine de caracteres."""
        if not price_str:
            return None
        # Enlever les caracteres non numeriques sauf virgule et point
        cleaned = re.sub(r'[^\d,.]', '', str(price_str))
        cleaned = cleaned.replace(',', '.')
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def format_auction(self, title, description="", price_estimate=None,
                       date_vente="", ville="", address="", url="",
                       image_url="", source_name=None, lot_count=None,
                       auction_type=""):
        """Formate une enchere dans le format standard."""
        cat = self.classify_category(title, description)
        src = source_name or self.name

        return {
            "id": self.generate_id(src, title, date_vente),
            "title": title.strip(),
            "description": description.strip() if description else "",
            "price_estimate": price_estimate,
            "date_vente": date_vente,
            "ville": ville.strip() if ville else "",
            "address": address.strip() if address else "",
            "url": url,
            "image_url": image_url,
            "source": src,
            "category": cat,
            "lot_count": lot_count,
            "auction_type": auction_type,
            "scanned_at": datetime.now().isoformat()
        }

    @staticmethod
    def _remove_accents(text):
        """Supprime les accents d'un texte."""
        replacements = {
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'à': 'a', 'â': 'a', 'ä': 'a',
            'ù': 'u', 'û': 'u', 'ü': 'u',
            'ô': 'o', 'ö': 'o',
            'î': 'i', 'ï': 'i',
            'ç': 'c',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
