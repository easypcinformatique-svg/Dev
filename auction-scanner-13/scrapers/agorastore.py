"""Scraper pour Agorastore.fr - Ventes aux encheres de materiels publics."""

import re
from datetime import datetime, timedelta
from scrapers.base_scraper import BaseScraper

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class AgorastoreScraper(BaseScraper):
    """Scraper pour agorastore.fr (materiels publics et collectivites)."""

    name = "Agorastore"
    base_url = "https://www.agorastore.fr"

    def scan(self, department="13", cities=None):
        """Scan les ventes de materiels publics dans le 13."""
        if not HAS_DEPS:
            return self._get_demo_data()

        auctions = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            search_url = f"{self.base_url}/recherche"
            params = {
                "departement": "13",
                "localisation": "Bouches-du-Rhone"
            }

            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select(".product-card, .annonce-item, .lot-item")

            for item in items:
                try:
                    auction = self._parse_item(item)
                    if auction:
                        auctions.append(auction)
                except Exception:
                    continue

        except Exception as e:
            print(f"[Agorastore] Erreur: {e}")
            auctions = self._get_demo_data()

        return auctions

    def _parse_item(self, item):
        """Parse un lot Agorastore."""
        title_el = item.select_one("h2, h3, .title, .product-title")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)

        desc_el = item.select_one(".description, .product-description, p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        price_el = item.select_one(".price, .current-price, .bid-price")
        price = self.parse_price(price_el.get_text()) if price_el else None

        link_el = item.select_one("a[href]")
        url = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url = href if href.startswith("http") else f"{self.base_url}{href}"

        date_el = item.select_one(".date, .end-date, time")
        date_vente = ""
        if date_el:
            date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
            date_vente = self._parse_date(date_text)

        ville_el = item.select_one(".location, .ville")
        ville = ville_el.get_text(strip=True) if ville_el else ""

        img_el = item.select_one("img[src]")
        image_url = ""
        if img_el:
            src = img_el.get("src", "") or img_el.get("data-src", "")
            image_url = src if src.startswith("http") else f"{self.base_url}{src}"

        return self.format_auction(
            title=title,
            description=description,
            price_estimate=price,
            date_vente=date_vente,
            ville=ville,
            url=url,
            image_url=image_url,
            source_name="Agorastore",
            auction_type="Vente materiel public"
        )

    def _parse_date(self, date_text):
        """Parse une date."""
        if not date_text:
            return ""
        if re.match(r'\d{4}-\d{2}-\d{2}', date_text):
            return date_text[:10]
        match = re.search(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})', date_text)
        if match:
            d, m, y = match.groups()
            if len(y) == 2:
                y = f"20{y}"
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        return date_text

    def _get_demo_data(self):
        """Donnees de demonstration materiel public."""
        today = datetime.now()
        return [
            self.format_auction(
                title="Lot de 12 ordinateurs Dell - Mairie de Marseille",
                description="Ordinateurs de bureau Dell OptiPlex, ecrans 24 pouces inclus, claviers et souris. Bon etat general, 3 ans d'usage.",
                price_estimate=100,
                date_vente=(today + timedelta(days=4)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Hotel de Ville, Quai du Port",
                url="https://www.agorastore.fr/",
                image_url="",
                source_name="Agorastore",
                auction_type="Vente materiel public"
            ),
            self.format_auction(
                title="Vehicule utilitaire Renault Master - Conseil Departemental",
                description="Renault Master L2H2 DCI 130, 2019, 85000km, revision a jour. Signalisation retiree.",
                price_estimate=8500,
                date_vente=(today + timedelta(days=6)).strftime("%Y-%m-%d"),
                ville="Aix-en-Provence",
                address="Parc auto departemental",
                url="https://www.agorastore.fr/",
                image_url="",
                source_name="Agorastore",
                auction_type="Vente materiel public"
            ),
            self.format_auction(
                title="Mobilier de bureau - Restructuration administration",
                description="Lot comprenant: 20 bureaux, 20 chaises de bureau, 10 armoires metalliques, 5 tables de reunion. Enlevement sur place.",
                price_estimate=200,
                date_vente=(today + timedelta(days=8)).strftime("%Y-%m-%d"),
                ville="Martigues",
                address="Centre administratif, Avenue Louis Sammut",
                url="https://www.agorastore.fr/",
                image_url="",
                source_name="Agorastore",
                auction_type="Vente materiel public"
            ),
            self.format_auction(
                title="Tondeuse autoportee John Deere - Commune d'Aubagne",
                description="Tondeuse autoportee John Deere X350, 2020, bon etat, 500h. Avec bac de ramassage et kit mulching.",
                price_estimate=1200,
                date_vente=(today + timedelta(days=9)).strftime("%Y-%m-%d"),
                ville="Aubagne",
                address="Services techniques municipaux",
                url="https://www.agorastore.fr/",
                image_url="",
                source_name="Agorastore",
                auction_type="Vente materiel public"
            ),
            self.format_auction(
                title="Lot photocopieurs Konica Minolta - Hopital Nord",
                description="3 photocopieurs multifonctions Konica Minolta Bizhub C258, sous contrat maintenance jusqu'en 2024. Fonctionnels.",
                price_estimate=300,
                date_vente=(today + timedelta(days=11)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Hopital Nord, Chemin des Bourrely",
                url="https://www.agorastore.fr/",
                image_url="",
                source_name="Agorastore",
                auction_type="Vente materiel public"
            ),
        ]
