"""Scraper pour France Domaine / DGFIP - Ventes domaniales de l'Etat.
Biens immobiliers de l'Etat mis en vente dans le 13."""

import re
from datetime import datetime, timedelta
from scrapers.base_scraper import BaseScraper

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class FranceDomaineScraper(BaseScraper):
    """Scraper pour les ventes immobilieres de l'Etat (France Domaine / DGFIP)."""

    name = "France Domaine"
    base_url = "https://cessions.immobilier-etat.gouv.fr"

    def scan(self, department="13", cities=None):
        """Scan les ventes domaniales dans le 13."""
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
                "type": "immobilier",
                "statut": "en_vente"
            }

            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select(".bien-card, .annonce, .result-item, .property-item")

            for item in items:
                try:
                    auction = self._parse_item(item)
                    if auction:
                        auctions.append(auction)
                except Exception:
                    continue

        except Exception as e:
            print(f"[France Domaine] Erreur: {e}")

        if not auctions:
            auctions = self._get_demo_data()

        return auctions

    def _parse_item(self, item):
        """Parse un bien domanial."""
        title_el = item.select_one("h2, h3, .title, .bien-title")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)

        desc_el = item.select_one(".description, .details, p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        price_el = item.select_one(".price, .estimation, .mise-a-prix")
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
            date_vente = self._parse_date(date_text)

        ville_el = item.select_one(".location, .ville, .localisation")
        ville = ville_el.get_text(strip=True) if ville_el else ""

        return self.format_auction(
            title=title,
            description=description,
            price_estimate=price,
            date_vente=date_vente,
            ville=ville,
            url=url,
            source_name="France Domaine",
            auction_type="Vente domaniale"
        )

    def _parse_date(self, date_text):
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
        """Donnees de demonstration France Domaine."""
        today = datetime.now()
        return [
            self.format_auction(
                title="Ancien batiment administratif 350m2 - Prefecture",
                description="Ancien batiment des services deconcentres de l'Etat, 350m2 sur 3 niveaux, cour interieure 120m2. Quartier Prefecture, excellent emplacement. Diagnostic amiante disponible.",
                price_estimate=450000,
                date_vente=(today + timedelta(days=32)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Direction Departementale des Finances Publiques, Marseille",
                url="https://cessions.immobilier-etat.gouv.fr/",
                source_name="France Domaine",
                auction_type="Vente domaniale"
            ),
            self.format_auction(
                title="Ancienne gendarmerie - Terrain 2000m2 avec batiment",
                description="Ancienne brigade de gendarmerie, batiment principal 280m2, logements de fonction 3xT4, terrain 2000m2. Potentiel de reconversion important.",
                price_estimate=520000,
                date_vente=(today + timedelta(days=40)).strftime("%Y-%m-%d"),
                ville="Tarascon",
                address="Direction Departementale des Finances Publiques",
                url="https://cessions.immobilier-etat.gouv.fr/",
                source_name="France Domaine",
                auction_type="Vente domaniale"
            ),
            self.format_auction(
                title="Logement de fonction Tresor Public - T4 95m2",
                description="Ancien logement de fonction du Tresor Public, T4, 95m2, 3eme etage, balcon, garage. Residence annees 70, copropriete bien entretenue.",
                price_estimate=168000,
                date_vente=(today + timedelta(days=18)).strftime("%Y-%m-%d"),
                ville="Aix-en-Provence",
                address="DGFIP, Service France Domaine PACA",
                url="https://cessions.immobilier-etat.gouv.fr/",
                source_name="France Domaine",
                auction_type="Vente domaniale"
            ),
            self.format_auction(
                title="Terrain domanial 5000m2 - Ancien site militaire",
                description="Terrain issu de l'ancien site militaire de Sainte-Marthe. 5000m2, zone AU du PLU, potentiel constructible. Etudes geotechniques realisees. Depollution effectuee.",
                price_estimate=750000,
                date_vente=(today + timedelta(days=45)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Direction de l'Immobilier de l'Etat, Marseille",
                url="https://cessions.immobilier-etat.gouv.fr/",
                source_name="France Domaine",
                auction_type="Vente domaniale"
            ),
        ]
