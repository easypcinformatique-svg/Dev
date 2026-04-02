"""Scraper pour Encheres-Publiques.com - Encheres immobilieres judiciaires."""

import re
from datetime import datetime, timedelta
from scrapers.base_scraper import BaseScraper

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class EncheresPubliquesScraper(BaseScraper):
    """Scraper pour encheres-publiques.com (immobilier judiciaire)."""

    name = "Encheres Publiques"
    base_url = "https://www.encheres-publiques.com"

    def scan(self, department="13", cities=None):
        """Scan les ventes immobilieres judiciaires dans le 13."""
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
                "type": "immobilier"
            }

            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select(".bien-item, .annonce, .result-item, .property-card")

            for item in items:
                try:
                    auction = self._parse_item(item)
                    if auction:
                        auctions.append(auction)
                except Exception:
                    continue

        except Exception as e:
            print(f"[Encheres Publiques] Erreur: {e}")
            auctions = self._get_demo_data()

        return auctions

    def _parse_item(self, item):
        """Parse un element immobilier."""
        title_el = item.select_one("h2, h3, .title, .bien-title")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)

        desc_el = item.select_one(".description, .details, p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        price_el = item.select_one(".price, .mise-a-prix, .estimation")
        price = self.parse_price(price_el.get_text()) if price_el else None

        link_el = item.select_one("a[href]")
        url = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url = href if href.startswith("http") else f"{self.base_url}{href}"

        date_el = item.select_one(".date, .date-audience, time")
        date_vente = ""
        if date_el:
            date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
            date_vente = self._parse_date(date_text)

        ville_el = item.select_one(".location, .ville, .localisation")
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
            source_name="Encheres Publiques",
            auction_type="Vente judiciaire immobiliere"
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
        """Donnees de demonstration immobilier judiciaire."""
        today = datetime.now()
        return [
            self.format_auction(
                title="Appartement T2 45m2 - Saisie immobiliere - Castellane",
                description="Vente sur saisie immobiliere. Appartement T2, 45m2, 3eme etage, cave. Mise a prix fixee par le juge. Quartier en pleine renovation.",
                price_estimate=65000,
                date_vente=(today + timedelta(days=10)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Tribunal Judiciaire de Marseille, 6 rue Joseph Autran",
                url="https://www.encheres-publiques.com/immobilier/bouches-du-rhone-13",
                image_url="",
                source_name="Encheres Publiques",
                auction_type="Saisie immobiliere"
            ),
            self.format_auction(
                title="Local commercial 80m2 - Liquidation judiciaire - Centre Aix",
                description="Local commercial en rez-de-chaussee, vitrine 6m sur rue passante, excellent emplacement centre-ville. Possibilite transformation habitation.",
                price_estimate=95000,
                date_vente=(today + timedelta(days=16)).strftime("%Y-%m-%d"),
                ville="Aix-en-Provence",
                address="Tribunal Judiciaire d'Aix-en-Provence",
                url="https://www.encheres-publiques.com/immobilier/bouches-du-rhone-13",
                image_url="",
                source_name="Encheres Publiques",
                auction_type="Liquidation judiciaire"
            ),
            self.format_auction(
                title="Villa T5 150m2 avec piscine - Les Alpilles",
                description="Villa provencale, 5 pieces, 150m2 habitables, terrain 2000m2, piscine 10x5, garage double. Vue Alpilles. DPE classe C.",
                price_estimate=320000,
                date_vente=(today + timedelta(days=25)).strftime("%Y-%m-%d"),
                ville="Salon-de-Provence",
                address="Tribunal Judiciaire de Salon-de-Provence",
                url="https://www.encheres-publiques.com/immobilier/bouches-du-rhone-13",
                image_url="",
                source_name="Encheres Publiques",
                auction_type="Vente sur licitation"
            ),
            self.format_auction(
                title="Parking souterrain - Vieux Port - Investissement",
                description="Place de parking en sous-sol securise, residence recente, acces badge 24h/24. A 200m du Vieux-Port. Rendement locatif 5%.",
                price_estimate=18000,
                date_vente=(today + timedelta(days=7)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Tribunal Judiciaire de Marseille",
                url="https://www.encheres-publiques.com/immobilier/bouches-du-rhone-13",
                image_url="",
                source_name="Encheres Publiques",
                auction_type="Vente judiciaire"
            ),
            self.format_auction(
                title="Immeuble de rapport 6 lots - Quartier Noailles",
                description="Immeuble R+3, 6 appartements (2xT1 + 3xT2 + 1xT3), 280m2 total. Loyers actuels 3200 EUR/mois. Ravalement recente.",
                price_estimate=420000,
                date_vente=(today + timedelta(days=30)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Tribunal Judiciaire de Marseille",
                url="https://www.encheres-publiques.com/immobilier/bouches-du-rhone-13",
                image_url="",
                source_name="Encheres Publiques",
                auction_type="Vente judiciaire"
            ),
            self.format_auction(
                title="Appartement T3 70m2 - Dernier etage - Aubagne",
                description="Appartement T3 lumineux, 70m2, dernier etage, terrasse 20m2, vue collines. 2 places parking. Residence avec piscine.",
                price_estimate=145000,
                date_vente=(today + timedelta(days=12)).strftime("%Y-%m-%d"),
                ville="Aubagne",
                address="Tribunal Judiciaire de Marseille",
                url="https://www.encheres-publiques.com/immobilier/bouches-du-rhone-13",
                image_url="",
                source_name="Encheres Publiques",
                auction_type="Saisie immobiliere"
            ),
        ]
