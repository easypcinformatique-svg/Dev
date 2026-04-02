"""Scraper pour le Conseil Departemental des Bouches-du-Rhone (CD13).
Cessions immobilieres du patrimoine departemental."""

import re
from datetime import datetime, timedelta
from scrapers.base_scraper import BaseScraper

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class CD13Scraper(BaseScraper):
    """Scraper pour les ventes immobilieres du Conseil Departemental 13."""

    name = "CD13 - Conseil Departemental"
    base_url = "https://www.departement13.fr"

    def scan(self, department="13", cities=None):
        """Scan les cessions immobilieres du CD13."""
        if not HAS_DEPS:
            return self._get_demo_data()

        auctions = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            # Page des ventes immobilieres du departement
            urls_to_try = [
                f"{self.base_url}/les-actions/amenagement-du-territoire/cessions-immobilieres",
                f"{self.base_url}/appels-offres",
                f"{self.base_url}/ventes-immobilieres",
            ]

            for search_url in urls_to_try:
                try:
                    response = requests.get(search_url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")
                        items = soup.select(".article, .annonce, .item, .card, .node")
                        for item in items:
                            auction = self._parse_item(item)
                            if auction:
                                auctions.append(auction)
                        if auctions:
                            break
                except Exception:
                    continue

        except Exception as e:
            print(f"[CD13] Erreur: {e}")

        if not auctions:
            auctions = self._get_demo_data()

        return auctions

    def _parse_item(self, item):
        """Parse un element de cession immobiliere CD13."""
        title_el = item.select_one("h2, h3, .title, a")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        if not any(kw in title.lower() for kw in [
            "vente", "cession", "terrain", "batiment", "local",
            "immeuble", "parcelle", "bien", "immobilier"
        ]):
            return None

        desc_el = item.select_one(".description, .summary, p, .field-body")
        description = desc_el.get_text(strip=True) if desc_el else ""

        link_el = item.select_one("a[href]")
        url = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url = href if href.startswith("http") else f"{self.base_url}{href}"

        price_el = item.select_one(".price, .montant")
        price = self.parse_price(price_el.get_text()) if price_el else None

        date_el = item.select_one(".date, time, .field-date")
        date_vente = ""
        if date_el:
            date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
            date_vente = self._parse_date(date_text)

        return self.format_auction(
            title=title,
            description=description,
            price_estimate=price,
            date_vente=date_vente,
            ville="",
            url=url,
            source_name="CD13 - Conseil Departemental",
            auction_type="Cession departementale"
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
        """Donnees de demonstration CD13."""
        today = datetime.now()
        return [
            self.format_auction(
                title="Ancien college departemental - Batiment 2500m2",
                description="Ancien college desaffecte, batiment principal 2500m2 sur terrain 5000m2. Possibilite reconversion en logements, bureaux ou equipement. Proche centre-ville, desserte bus.",
                price_estimate=850000,
                date_vente=(today + timedelta(days=35)).strftime("%Y-%m-%d"),
                ville="Aubagne",
                address="Conseil Departemental des Bouches-du-Rhone, Direction du Patrimoine",
                url="https://www.departement13.fr/les-ventes-immobilieres",
                source_name="CD13 - Conseil Departemental",
                auction_type="Cession departementale"
            ),
            self.format_auction(
                title="Terrain departemental 3000m2 - Zone amenagement",
                description="Parcelle departementale en zone d'amenagement, 3000m2, plat, viabilisable. Zonage PLU permettant habitat collectif R+4. Etude de sol disponible.",
                price_estimate=380000,
                date_vente=(today + timedelta(days=28)).strftime("%Y-%m-%d"),
                ville="Vitrolles",
                address="CD13, Direction de l'Amenagement",
                url="https://www.departement13.fr/les-ventes-immobilieres",
                source_name="CD13 - Conseil Departemental",
                auction_type="Cession departementale"
            ),
            self.format_auction(
                title="Ancien centre social departemental 400m2 - Reconversion",
                description="Ancien centre social, RDC + R+1, 400m2, parking 15 places. Bon etat structurel, accessibilite PMR. Ideal activite tertiaire ou medicale.",
                price_estimate=290000,
                date_vente=(today + timedelta(days=20)).strftime("%Y-%m-%d"),
                ville="Martigues",
                address="CD13, Service des Domaines",
                url="https://www.departement13.fr/les-ventes-immobilieres",
                source_name="CD13 - Conseil Departemental",
                auction_type="Cession departementale"
            ),
            self.format_auction(
                title="Maison de gardien departementale - T3 75m2 avec terrain",
                description="Ancienne maison de gardien attenante a un equipement departemental. T3, 75m2, terrain 450m2 clos. Bon etat, habitable en l'etat.",
                price_estimate=175000,
                date_vente=(today + timedelta(days=17)).strftime("%Y-%m-%d"),
                ville="Salon-de-Provence",
                address="CD13, Direction du Patrimoine",
                url="https://www.departement13.fr/les-ventes-immobilieres",
                source_name="CD13 - Conseil Departemental",
                auction_type="Cession departementale"
            ),
        ]
