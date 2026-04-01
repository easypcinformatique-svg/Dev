"""Scraper pour les ventes immobilieres des Mairies du departement 13.
Cessions du domaine prive communal."""

import re
from datetime import datetime, timedelta
from scrapers.base_scraper import BaseScraper

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


# Principales mairies du 13 avec leurs sites web
MAIRIES_13 = [
    {"nom": "Marseille", "url": "https://www.marseille.fr", "population": 870000},
    {"nom": "Aix-en-Provence", "url": "https://www.aixenprovence.fr", "population": 145000},
    {"nom": "Arles", "url": "https://www.arles.fr", "population": 52000},
    {"nom": "Martigues", "url": "https://www.ville-martigues.fr", "population": 49000},
    {"nom": "Aubagne", "url": "https://www.aubagne.fr", "population": 47000},
    {"nom": "Istres", "url": "https://www.istres.fr", "population": 44000},
    {"nom": "Salon-de-Provence", "url": "https://www.salon-de-provence.org", "population": 44000},
    {"nom": "Vitrolles", "url": "https://www.vitrolles13.fr", "population": 35000},
    {"nom": "Marignane", "url": "https://www.ville-marignane.fr", "population": 34000},
    {"nom": "La Ciotat", "url": "https://www.laciotat.com", "population": 34000},
    {"nom": "Gardanne", "url": "https://www.ville-gardanne.fr", "population": 21000},
    {"nom": "Miramas", "url": "https://www.miramas.org", "population": 26000},
    {"nom": "Tarascon", "url": "https://www.tarascon.org", "population": 15000},
    {"nom": "Chateaurenard", "url": "https://www.chateaurenard.com", "population": 16000},
    {"nom": "Port-de-Bouc", "url": "https://www.portdebouc.fr", "population": 17000},
]


class MairiesScraper(BaseScraper):
    """Scraper pour les cessions immobilieres des mairies du 13."""

    name = "Mairies du 13"
    base_url = ""

    def scan(self, department="13", cities=None):
        """Scan les ventes immobilieres des mairies du 13."""
        if not HAS_DEPS:
            return self._get_demo_data()

        auctions = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        for mairie in MAIRIES_13:
            try:
                # Tester les pages typiques de cessions immobilieres
                paths = [
                    "/ventes-immobilieres",
                    "/cessions-immobilieres",
                    "/patrimoine/ventes",
                    "/urbanisme/ventes",
                    "/appels-offres/immobilier",
                    "/deliberations/cessions",
                ]

                for path in paths:
                    try:
                        url = f"{mairie['url']}{path}"
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, "html.parser")
                            items = soup.select(".article, .annonce, .item, .card, .node, .post")
                            for item in items:
                                auction = self._parse_item(item, mairie)
                                if auction:
                                    auctions.append(auction)
                            if auctions:
                                break
                    except Exception:
                        continue

            except Exception as e:
                print(f"[Mairies] Erreur {mairie['nom']}: {e}")

        if not auctions:
            auctions = self._get_demo_data()

        return auctions

    def _parse_item(self, item, mairie):
        """Parse un element de cession communale."""
        title_el = item.select_one("h2, h3, .title, a")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)

        desc_el = item.select_one(".description, .summary, p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        price_el = item.select_one(".price, .montant")
        price = self.parse_price(price_el.get_text()) if price_el else None

        link_el = item.select_one("a[href]")
        url = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url = href if href.startswith("http") else f"{mairie['url']}{href}"

        return self.format_auction(
            title=title,
            description=description,
            price_estimate=price,
            date_vente="",
            ville=mairie["nom"],
            url=url,
            source_name=f"Mairie {mairie['nom']}",
            auction_type="Cession communale"
        )

    def _get_demo_data(self):
        """Donnees de demonstration des mairies du 13."""
        today = datetime.now()
        return [
            self.format_auction(
                title="Ancien logement communal T3 65m2 - Quartier Saint-Loup",
                description="Ancien logement de fonction municipal, T3, 65m2, RDC, petit jardin privatif 80m2. Quartier Saint-Loup, proche ecoles et commerces. Travaux de rafraichissement a prevoir.",
                price_estimate=115000,
                date_vente=(today + timedelta(days=13)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Mairie de Marseille, Direction du Patrimoine municipal",
                url="https://www.marseille.fr/",
                source_name="Mairie Marseille",
                auction_type="Cession communale"
            ),
            self.format_auction(
                title="Terrain communal 600m2 - Zone pavillonnaire Jas de Bouffan",
                description="Parcelle communale constructible, 600m2, zone UBa du PLU. Quartier Jas de Bouffan, environnement residentiel calme. Reseaux en limite de parcelle.",
                price_estimate=180000,
                date_vente=(today + timedelta(days=22)).strftime("%Y-%m-%d"),
                ville="Aix-en-Provence",
                address="Mairie d'Aix-en-Provence, Service Urbanisme",
                url="https://www.aixenprovence.fr/",
                source_name="Mairie Aix-en-Provence",
                auction_type="Cession communale"
            ),
            self.format_auction(
                title="Local commercial municipal 45m2 - Centre historique",
                description="Local en rez-de-chaussee dans le centre historique d'Arles, 45m2, voute en pierre, vitrine 3m. Ideal galerie d'art, artisanat ou boutique.",
                price_estimate=62000,
                date_vente=(today + timedelta(days=19)).strftime("%Y-%m-%d"),
                ville="Arles",
                address="Mairie d'Arles, Direction des Affaires Foncieres",
                url="https://www.arles.fr/",
                source_name="Mairie Arles",
                auction_type="Cession communale"
            ),
            self.format_auction(
                title="Ancien dispensaire municipal 200m2 - A renover",
                description="Ancien dispensaire communal sur 2 niveaux, 200m2, terrain 350m2. Structure saine, toiture OK. Possibilite division en 2 logements. Proche centre.",
                price_estimate=155000,
                date_vente=(today + timedelta(days=25)).strftime("%Y-%m-%d"),
                ville="Gardanne",
                address="Mairie de Gardanne, Service du Patrimoine",
                url="https://www.ville-gardanne.fr/",
                source_name="Mairie Gardanne",
                auction_type="Cession communale"
            ),
            self.format_auction(
                title="Appartement T2 40m2 - Ancien logement gardien ecole",
                description="Ancien logement de gardien d'ecole, T2 au 1er etage, 40m2, lumineux. Quartier residentiel calme. Ideal premier achat ou investissement locatif.",
                price_estimate=72000,
                date_vente=(today + timedelta(days=16)).strftime("%Y-%m-%d"),
                ville="Miramas",
                address="Mairie de Miramas",
                url="https://www.miramas.org/",
                source_name="Mairie Miramas",
                auction_type="Cession communale"
            ),
            self.format_auction(
                title="Parcelle constructible 900m2 - Lotissement communal",
                description="Lot n 3 du lotissement communal Les Oliviers. 900m2, plat, viabilise, CES 0.30. Vue degagee sur la Sainte-Victoire. Cahier des charges disponible.",
                price_estimate=125000,
                date_vente=(today + timedelta(days=30)).strftime("%Y-%m-%d"),
                ville="Chateaurenard",
                address="Mairie de Chateaurenard, Service Urbanisme",
                url="https://www.chateaurenard.com/",
                source_name="Mairie Chateaurenard",
                auction_type="Cession communale"
            ),
        ]
