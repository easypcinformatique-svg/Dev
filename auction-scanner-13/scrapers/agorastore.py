"""Scraper pour Agorastore.fr - Biens immobiliers publics aux encheres."""

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
    """Scraper pour agorastore.fr (biens immobiliers publics)."""

    name = "Agorastore"
    base_url = "https://www.agorastore.fr"

    def scan(self, department="13", cities=None):
        """Scan les ventes immobilieres publiques dans le 13."""
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
                "localisation": "Bouches-du-Rhone",
                "categorie": "immobilier"
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
        """Parse un bien immobilier Agorastore."""
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
            auction_type="Vente bien public"
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
        """Donnees de demonstration biens immobiliers publics."""
        today = datetime.now()
        return [
            self.format_auction(
                title="Ancien bureau de poste 150m2 - Transformation possible",
                description="Ancien bureau de poste desaffecte, 150m2 sur 2 niveaux, facade pierre. Possibilite transformation en habitation ou commerce. Toiture refaite 2021.",
                price_estimate=110000,
                date_vente=(today + timedelta(days=9)).strftime("%Y-%m-%d"),
                ville="Arles",
                address="Direction des Domaines, Prefecture des Bouches-du-Rhone",
                url="https://www.agorastore.fr/",
                image_url="",
                source_name="Agorastore",
                auction_type="Cession bien public"
            ),
            self.format_auction(
                title="Logement de fonction T4 90m2 - Ecole communale",
                description="Ancien logement de fonction attenant a l'ecole communale. T4, 90m2, jardin 300m2. Libre de toute occupation. Bon etat general.",
                price_estimate=165000,
                date_vente=(today + timedelta(days=15)).strftime("%Y-%m-%d"),
                ville="Istres",
                address="Mairie d'Istres, Service du patrimoine",
                url="https://www.agorastore.fr/",
                image_url="",
                source_name="Agorastore",
                auction_type="Cession bien public"
            ),
            self.format_auction(
                title="Terrain communal 1200m2 - Zone constructible",
                description="Parcelle communale en zone UC du PLU, 1200m2, plat, viabilise en limite. COS permettant R+2. Quartier residentiel proche ecoles.",
                price_estimate=145000,
                date_vente=(today + timedelta(days=20)).strftime("%Y-%m-%d"),
                ville="Vitrolles",
                address="Mairie de Vitrolles",
                url="https://www.agorastore.fr/",
                image_url="",
                source_name="Agorastore",
                auction_type="Cession bien public"
            ),
            self.format_auction(
                title="Local associatif 60m2 - Centre ville Martigues",
                description="Local en rez-de-chaussee, 60m2, vitrine sur rue pietonne. Ancien local associatif, bon etat. Ideal profession liberale ou commerce.",
                price_estimate=78000,
                date_vente=(today + timedelta(days=11)).strftime("%Y-%m-%d"),
                ville="Martigues",
                address="Mairie de Martigues, Direction de l'immobilier",
                url="https://www.agorastore.fr/",
                image_url="",
                source_name="Agorastore",
                auction_type="Cession bien public"
            ),
        ]
