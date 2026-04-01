"""Module OCR pour l'extraction de données des factures.

Utilise Tesseract OCR pour extraire :
- Numéro de facture
- Date
- Montants (HT, TVA, TTC)
- Nom du fournisseur
"""

import os
import re
from datetime import datetime

try:
    import pytesseract
    from PIL import Image

    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False

try:
    from pdf2image import convert_from_path

    PDF_CONVERSION_DISPONIBLE = True
except ImportError:
    PDF_CONVERSION_DISPONIBLE = False


class OCRService:
    """Service d'extraction de données par OCR."""

    # Patterns pour extraire les informations des factures
    PATTERNS = {
        "numero_facture": [
            r"(?:facture|invoice|fact\.?)\s*(?:n[°o]?|#|:)\s*([A-Z0-9\-/]+)",
            r"(?:n[°o]?\s*(?:de\s+)?facture)\s*:?\s*([A-Z0-9\-/]+)",
        ],
        "date": [
            r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
            r"(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|"
            r"septembre|octobre|novembre|décembre)\s+\d{4})",
        ],
        "montant_ttc": [
            r"(?:total\s*ttc|net\s*[àa]\s*payer|montant\s*ttc)\s*:?\s*(\d+[.,]\d{2})\s*(?:€|eur)?",
            r"(?:total|ttc)\s*:?\s*(\d+[.,]\d{2})\s*(?:€|eur)?",
        ],
        "montant_ht": [
            r"(?:total\s*ht|montant\s*ht|base\s*ht)\s*:?\s*(\d+[.,]\d{2})\s*(?:€|eur)?",
            r"(?:ht)\s*:?\s*(\d+[.,]\d{2})\s*(?:€|eur)?",
        ],
        "montant_tva": [
            r"(?:tva|t\.v\.a\.?)\s*:?\s*(\d+[.,]\d{2})\s*(?:€|eur)?",
            r"(?:montant\s*tva)\s*:?\s*(\d+[.,]\d{2})\s*(?:€|eur)?",
        ],
        "taux_tva": [
            r"(?:tva|t\.v\.a\.?)\s*(?:à|a|:)?\s*(\d+[.,]?\d*)\s*%",
        ],
    }

    MOIS_FR = {
        "janvier": 1,
        "février": 2,
        "mars": 3,
        "avril": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7,
        "août": 8,
        "septembre": 9,
        "octobre": 10,
        "novembre": 11,
        "décembre": 12,
    }

    def __init__(self):
        if not OCR_DISPONIBLE:
            raise RuntimeError(
                "pytesseract et Pillow sont requis. "
                "Installez-les avec: pip install pytesseract Pillow"
            )

    def extraire_texte(self, filepath: str) -> str:
        """Extrait le texte d'un fichier (image ou PDF).

        Args:
            filepath: Chemin du fichier

        Returns:
            Texte extrait
        """
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".pdf":
            if not PDF_CONVERSION_DISPONIBLE:
                return ""
            images = convert_from_path(filepath)
            textes = []
            for img in images:
                textes.append(pytesseract.image_to_string(img, lang="fra"))
            return "\n".join(textes)
        elif ext in (".jpg", ".jpeg", ".png", ".tiff"):
            img = Image.open(filepath)
            return pytesseract.image_to_string(img, lang="fra")
        else:
            return ""

    def extraire_donnees(self, texte: str) -> dict:
        """Extrait les données structurées d'un texte de facture.

        Args:
            texte: Texte brut extrait par OCR

        Returns:
            Dict avec les données extraites
        """
        texte_lower = texte.lower()
        resultats = {}
        confiance = 0
        champs_trouves = 0

        for champ, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, texte_lower)
                if match:
                    valeur = match.group(1).strip()

                    if champ.startswith("montant") or champ == "taux_tva":
                        valeur = valeur.replace(",", ".")
                        try:
                            valeur = float(valeur)
                        except ValueError:
                            continue

                    if champ == "date":
                        valeur = self._parser_date(valeur)

                    resultats[champ] = valeur
                    champs_trouves += 1
                    break

        # Calcul du score de confiance
        total_champs = len(self.PATTERNS)
        confiance = round((champs_trouves / total_champs) * 100, 1)
        resultats["confiance"] = confiance

        return resultats

    def _parser_date(self, date_str: str):
        """Parse une date en français.

        Args:
            date_str: Chaîne de date

        Returns:
            Objet date ou None
        """
        # Format JJ/MM/AAAA ou JJ-MM-AAAA
        for sep in ["/", "-", "."]:
            parts = date_str.split(sep)
            if len(parts) == 3:
                try:
                    jour, mois, annee = parts
                    if len(annee) == 2:
                        annee = "20" + annee
                    return datetime(int(annee), int(mois), int(jour)).date()
                except (ValueError, IndexError):
                    continue

        # Format "1 janvier 2024"
        for mois_nom, mois_num in self.MOIS_FR.items():
            if mois_nom in date_str:
                parts = date_str.split()
                try:
                    jour = int(parts[0])
                    annee = int(parts[2])
                    return datetime(annee, mois_num, jour).date()
                except (ValueError, IndexError):
                    continue

        return None

    def traiter_facture(self, filepath: str) -> dict:
        """Pipeline complet : extraction texte + données.

        Args:
            filepath: Chemin du fichier facture

        Returns:
            Dict avec texte brut et données extraites
        """
        texte = self.extraire_texte(filepath)
        donnees = self.extraire_donnees(texte)

        return {
            "texte_brut": texte,
            "donnees": donnees,
        }
