"""Scraper pour Interencheres.com - Encheres immobilieres."""

import re
from datetime import datetime, timedelta
from scrapers.base_scraper import BaseScraper

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class InterencheresScraper(BaseScraper):
    """Scraper pour interencheres.com - section immobilier."""

    name = "Interencheres"
    base_url = "https://www.interencheres.com"

    def scan(self, department="13", cities=None):
        """Scan les ventes immobilieres sur Interencheres pour le dept 13."""
        if not HAS_DEPS:
            return self._get_demo_data()

        auctions = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            search_url = f"{self.base_url}/recherche/ventes"
            params = {
                "department": department,
                "search": "immobilier Bouches-du-Rhone",
                "category": "immobilier",
            }

            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            sale_cards = soup.select(".sale-card, .vente-item, .auction-item, [data-sale-id]")

            for card in sale_cards:
                try:
                    auction = self._parse_sale_card(card)
                    if auction:
                        auctions.append(auction)
                except Exception:
                    continue

        except Exception as e:
            print(f"[Interencheres] Erreur de scraping: {e}")
            auctions = self._get_demo_data()

        return auctions

    def _parse_sale_card(self, card):
        """Parse une carte de vente immobiliere."""
        title_el = card.select_one("h2, h3, .sale-title, .title")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)

        desc_el = card.select_one(".sale-description, .description, p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        link_el = card.select_one("a[href]")
        url = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url = href if href.startswith("http") else f"{self.base_url}{href}"

        date_el = card.select_one(".sale-date, .date, time")
        date_vente = ""
        if date_el:
            date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
            date_vente = self._parse_date(date_text)

        ville_el = card.select_one(".sale-location, .location, .ville")
        ville = ville_el.get_text(strip=True) if ville_el else ""

        price_el = card.select_one(".price, .estimate, .estimation")
        price = self.parse_price(price_el.get_text()) if price_el else None

        img_el = card.select_one("img[src]")
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
            auction_type="Vente immobiliere"
        )

    def _parse_date(self, date_text):
        """Tente de parser une date depuis du texte."""
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
        """Donnees de demonstration immobilier pour le departement 13."""
        today = datetime.now()
        return [
            self.format_auction(
                title="Appartement T3 65m2 - Vente sur licitation - Endoume",
                description="Appartement 3 pieces, 65m2, 5eme etage avec ascenseur, balcon, vue mer partielle. Quartier Endoume, residence calme. Cave incluse.",
                price_estimate=125000,
                date_vente=(today + timedelta(days=8)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Tribunal Judiciaire de Marseille, 6 rue Joseph Autran",
                url="https://www.interencheres.com/carte-des-encheres",
                image_url="",
                auction_type="Vente sur licitation"
            ),
            self.format_auction(
                title="Maison de village 120m2 avec jardin - Centre Tarascon",
                description="Maison de village restauree, 120m2, 4 chambres, jardin 200m2, garage. Centre village, proche toutes commodites. DPE classe D.",
                price_estimate=185000,
                date_vente=(today + timedelta(days=14)).strftime("%Y-%m-%d"),
                ville="Tarascon",
                address="Tribunal Judiciaire de Tarascon",
                url="https://www.interencheres.com/carte-des-encheres",
                image_url="",
                auction_type="Vente judiciaire"
            ),
            self.format_auction(
                title="Studio 28m2 - Quartier Castellane - Investissement locatif",
                description="Studio meuble, 28m2, 2eme etage, loyer actuel 450 EUR/mois. Ideal investissement locatif. Proche metro Castellane.",
                price_estimate=52000,
                date_vente=(today + timedelta(days=5)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Hotel des ventes de Marseille",
                url="https://www.interencheres.com/carte-des-encheres",
                image_url="",
                auction_type="Encheres volontaires"
            ),
            self.format_auction(
                title="Terrain constructible 800m2 - Zone pavillonnaire",
                description="Terrain plat constructible, 800m2, viabilise (eau, electricite, tout-a-l'egout). Zone pavillonnaire calme, vue degagee.",
                price_estimate=95000,
                date_vente=(today + timedelta(days=18)).strftime("%Y-%m-%d"),
                ville="Marignane",
                address="Etude notariale Me Blanc, Marignane",
                url="https://www.interencheres.com/carte-des-encheres",
                image_url="",
                auction_type="Encheres volontaires"
            ),
            self.format_auction(
                title="Appartement T4 85m2 - Residence securisee - La Ciotat",
                description="Appartement 4 pieces, 85m2, terrasse 15m2, parking sous-sol. Residence recente avec piscine et gardien. Vue colline.",
                price_estimate=195000,
                date_vente=(today + timedelta(days=22)).strftime("%Y-%m-%d"),
                ville="La Ciotat",
                address="Tribunal Judiciaire de Marseille",
                url="https://www.interencheres.com/carte-des-encheres",
                image_url="",
                auction_type="Vente sur licitation"
            ),
        ]
