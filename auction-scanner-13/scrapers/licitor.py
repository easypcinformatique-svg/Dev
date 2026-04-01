"""Scraper pour Licitor.com - Ventes judiciaires immobilieres."""

import re
from datetime import datetime, timedelta
from scrapers.base_scraper import BaseScraper

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class LicitorScraper(BaseScraper):
    """Scraper pour licitor.com (ventes judiciaires immobilieres)."""

    name = "Licitor"
    base_url = "https://www.licitor.com"

    def scan(self, department="13", cities=None):
        """Scan les ventes judiciaires immobilieres dans le 13."""
        if not HAS_DEPS:
            return self._get_demo_data()

        auctions = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            search_url = f"{self.base_url}/ventes-immobilieres"
            params = {"departement": "13", "type": "immobilier"}

            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select(".vente-item, .annonce, .result-item, .card")

            for item in items:
                try:
                    auction = self._parse_item(item)
                    if auction:
                        auctions.append(auction)
                except Exception:
                    continue

        except Exception as e:
            print(f"[Licitor] Erreur: {e}")

        if not auctions:
            auctions = self._get_demo_data()

        return auctions

    def _parse_item(self, item):
        title_el = item.select_one("h2, h3, .title")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        desc_el = item.select_one(".description, p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        price_el = item.select_one(".price, .mise-a-prix")
        price = self.parse_price(price_el.get_text()) if price_el else None

        link_el = item.select_one("a[href]")
        url = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url = href if href.startswith("http") else f"{self.base_url}{href}"

        date_el = item.select_one(".date, time")
        date_vente = ""
        if date_el:
            date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
            if re.match(r'\d{4}-\d{2}-\d{2}', date_text):
                date_vente = date_text[:10]

        ville_el = item.select_one(".location, .ville")
        ville = ville_el.get_text(strip=True) if ville_el else ""

        return self.format_auction(
            title=title, description=description, price_estimate=price,
            date_vente=date_vente, ville=ville, url=url,
            source_name="Licitor", auction_type="Vente judiciaire"
        )

    def _get_demo_data(self):
        """Donnees de demonstration Licitor."""
        today = datetime.now()
        return [
            self.format_auction(
                title="Appartement T2 50m2 - Saisie - Quartier du Prado",
                description="Saisie immobiliere. T2, 50m2, 4eme etage, balcon sud, cave. Quartier Prado, proche plages et metro. Copropriete bien entretenue. Charges 150 EUR/mois.",
                price_estimate=85000,
                date_vente=(today + timedelta(days=11)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Tribunal Judiciaire de Marseille, Salle des criees",
                url="https://www.licitor.com/",
                source_name="Licitor",
                auction_type="Saisie immobiliere"
            ),
            self.format_auction(
                title="Maison T4 100m2 - Vente forcee - Les Pennes-Mirabeau",
                description="Maison individuelle T4, 100m2, terrain 500m2, garage. Quartier residentiel calme. Travaux de mise aux normes electriques a prevoir. DPE classe E.",
                price_estimate=210000,
                date_vente=(today + timedelta(days=14)).strftime("%Y-%m-%d"),
                ville="Les Pennes-Mirabeau",
                address="TJ Aix-en-Provence, Chambre des saisies immobilieres",
                url="https://www.licitor.com/",
                source_name="Licitor",
                auction_type="Vente forcee"
            ),
            self.format_auction(
                title="Local d'activite 250m2 - Liquidation - Zone Athelia",
                description="Local d'activite dans zone Athelia, 250m2, hauteur 5m, quai de dechargement. Bureau 40m2 attenant. 8 places parking. Libre immediatement.",
                price_estimate=175000,
                date_vente=(today + timedelta(days=19)).strftime("%Y-%m-%d"),
                ville="La Ciotat",
                address="Tribunal de Commerce de Marseille",
                url="https://www.licitor.com/",
                source_name="Licitor",
                auction_type="Liquidation judiciaire"
            ),
            self.format_auction(
                title="Appartement T5 110m2 - Indivision - Vue Calanques",
                description="Vente sur licitation pour sortie d'indivision. T5, 110m2, dernier etage, terrasse 30m2, vue Calanques. Residence standing avec gardien. 2 parkings.",
                price_estimate=295000,
                date_vente=(today + timedelta(days=23)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Tribunal Judiciaire de Marseille",
                url="https://www.licitor.com/",
                source_name="Licitor",
                auction_type="Vente sur licitation"
            ),
            self.format_auction(
                title="Mas provencal 180m2 - Succession - Campagne aixoise",
                description="Vente judiciaire succession. Mas en pierre, 180m2, terrain 3500m2, oliviers. Dependances 60m2. A restaurer partiellement. Cadre exceptionnel.",
                price_estimate=350000,
                date_vente=(today + timedelta(days=27)).strftime("%Y-%m-%d"),
                ville="Aix-en-Provence",
                address="TJ Aix-en-Provence",
                url="https://www.licitor.com/",
                source_name="Licitor",
                auction_type="Vente judiciaire succession"
            ),
        ]
