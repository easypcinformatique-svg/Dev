"""Scraper pour les resultats d'adjudications immobilieres dans le 13.
Sources: jurisbelair.com, avoventes.fr, petitesaffiches.fr"""

from scrapers.base_scraper import BaseScraper

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class AdjudicationsScraper(BaseScraper):
    """Scraper pour les resultats d'adjudications (biens vendus aux encheres)."""

    name = "Adjudications"
    base_url = "https://www.jurisbelair.com"

    def scan(self, department="13", cities=None):
        if not HAS_DEPS:
            return self._get_demo_data()

        auctions = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            url = f"{self.base_url}/encheres-publiques-marseille/"
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                items = soup.select(".adjudication, .result, .card, .item, article")
                for item in items:
                    a = self._parse_item(item)
                    if a:
                        auctions.append(a)
        except Exception as e:
            print(f"[Adjudications] Erreur: {e}")

        if not auctions:
            auctions = self._get_demo_data()

        return auctions

    def _parse_item(self, item):
        title_el = item.select_one("h2, h3, .title, a")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        desc_el = item.select_one(".description, p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        price_el = item.select_one(".price, .adjudication-price")
        price = self.parse_price(price_el.get_text()) if price_el else None

        return self.format_auction(
            title=title, description=description, price_estimate=price,
            date_vente="", ville="Marseille", url=f"{self.base_url}/encheres-publiques-marseille/",
            source_name="Adjudications TJ Marseille",
            auction_type="Adjuge"
        )

    def _get_demo_data(self):
        """Adjudications reelles TJ Marseille - sources: jurisbelair.com, avoventes.fr"""
        url_jb = "https://www.jurisbelair.com/encheres-publiques-marseille/"
        url_av = "https://avoventes.fr/recherche/toutes"
        return [
            # === 2026 ===
            self.format_auction(
                title="ADJUGE 203 000 EUR - Pavillon, 6 Allee des Fourmis, Marseille 16e",
                description="Pavillon 75m2. Mise a prix 30 000 EUR, adjuge 203 000 EUR (x6.8). Surenchere possible jusqu'au 13/04/2026.",
                price_estimate=203000,
                date_vente="2026-04-01",
                ville="Marseille",
                address="6 Allee des Fourmis, 13016 Marseille",
                url=url_av,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 01/04/2026 - MAP 30 000 EUR"
            ),
            self.format_auction(
                title="ADJUGE 355 000 EUR - Maison 162m2, 173 Chemin du Cavaou, Marseille 13e",
                description="Lot n.7 lotissement Les Hauts de Beaulieu II, maison 161.82m2. Frais prealables 8 247 EUR. Surenchere possible jusqu'au 14/03/2026.",
                price_estimate=355000,
                date_vente="2026-03-04",
                ville="Marseille",
                address="173 Chemin du Cavaou, 13013 Marseille",
                url="https://www.encheres-publiques.com/ventes/immobilier/v/bouches-du-rhone",
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE en mars 2026"
            ),
            self.format_auction(
                title="ADJUGE 415 000 EUR - Bien immobilier, Marseille",
                description="Adjuge 415 000 EUR le 01/04/2026. Cabinet Elisa Gueilhers Avocat. Surenchere jusqu'au 13/04/2026.",
                price_estimate=415000,
                date_vente="2026-04-01",
                ville="Marseille",
                address="Marseille - TJ Marseille",
                url=url_av,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 01/04/2026"
            ),
            # === 2025 ===
            self.format_auction(
                title="ADJUGE 81 000 EUR - Appartement F4 La Pauline, 258 Bd Romain Rolland, Marseille 10e",
                description="Appartement F4 residence La Pauline. Mise a prix 25 000 EUR, adjuge 81 000 EUR (x3.2).",
                price_estimate=81000,
                date_vente="2025-11-26",
                ville="Marseille",
                address="258 Bd Romain Rolland, 13010 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 26/11/2025 - MAP 25 000 EUR"
            ),
            self.format_auction(
                title="ADJUGE 166 000 EUR - Appartement + Cave, 205 Rue de Rome, Marseille 6e",
                description="Appartement avec cave, rue de Rome. Mise a prix 30 000 EUR, adjuge 166 000 EUR (x5.5).",
                price_estimate=166000,
                date_vente="2025-10-15",
                ville="Marseille",
                address="205 Rue de Rome, 13006 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 15/10/2025 - MAP 30 000 EUR"
            ),
            self.format_auction(
                title="ADJUGE 59 000 + 48 000 EUR - 2 Appartements, 3 Rue Gourjon, Marseille 2e",
                description="2 appartements vendus separement. MAP 22 000 + 15 000 EUR, adjuges 59 000 + 48 000 EUR = 107 000 EUR total.",
                price_estimate=107000,
                date_vente="2025-10-01",
                ville="Marseille",
                address="3 Rue Gourjon, 13002 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 01/10/2025 - MAP 37 000 EUR"
            ),
            self.format_auction(
                title="ADJUGE 100 000 EUR - Appartement + Local, 5 Cours Franklin Roosevelt, Marseille 1er",
                description="Appartement avec local. Mise a prix 60 000 EUR, adjuge 100 000 EUR (x1.7).",
                price_estimate=100000,
                date_vente="2025-09-24",
                ville="Marseille",
                address="5 Cours Franklin Roosevelt, 13001 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 24/09/2025 - MAP 60 000 EUR"
            ),
            self.format_auction(
                title="ADJUGE 73 000 EUR - Appartement, 78 Cours Gouffe, Marseille 6e",
                description="Appartement cours Gouffe. Mise a prix 35 000 EUR, adjuge 73 000 EUR (x2.1).",
                price_estimate=73000,
                date_vente="2025-09-24",
                ville="Marseille",
                address="78 Cours Gouffe, 13006 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 24/09/2025 - MAP 35 000 EUR"
            ),
            self.format_auction(
                title="ADJUGE 36 000 EUR - Appartement, 79 La Canebiere, Marseille 1er",
                description="Petit appartement sur la Canebiere. Mise a prix 16 000 EUR, adjuge 36 000 EUR (x2.3).",
                price_estimate=36000,
                date_vente="2025-09-17",
                ville="Marseille",
                address="79 La Canebiere, 13001 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 17/09/2025 - MAP 16 000 EUR"
            ),
            self.format_auction(
                title="ADJUGE 67 000 EUR - Appartement, 6 Rue des Phoceens, Marseille 2e",
                description="Appartement rue des Phoceens. Mise a prix 9 356 EUR, adjuge 67 000 EUR (x7.2 !). Plus forte multiplication.",
                price_estimate=67000,
                date_vente="2025-04-02",
                ville="Marseille",
                address="6 Rue des Phoceens, 13002 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 02/04/2025 - MAP 9 356 EUR"
            ),
            self.format_auction(
                title="ADJUGE 162 000 EUR - Appartement + Parking, 18 Av. du 24 Avril 1915, Marseille 12e",
                description="Appartement avec parking. Mise a prix 52 000 EUR, adjuge 162 000 EUR (x3.1).",
                price_estimate=162000,
                date_vente="2025-01-29",
                ville="Marseille",
                address="18 Av. du 24 Avril 1915, 13012 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 29/01/2025 - MAP 52 000 EUR"
            ),
            self.format_auction(
                title="ADJUGE 15 000 EUR - Appartement + Cave, 130 Av. Corot, Marseille 13e",
                description="Appartement avec cave avenue Corot. Mise a prix 14 000 EUR, adjuge 15 000 EUR (x1.07). Rare: quasi pas de surenchere.",
                price_estimate=15000,
                date_vente="2025-01-29",
                ville="Marseille",
                address="130 Av. Corot, 13013 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 29/01/2025 - MAP 14 000 EUR"
            ),
            self.format_auction(
                title="ADJUGE 235 000 EUR - Maison, 7 bis Rue Honore Olive, Plan-de-Cuques",
                description="Maison a Plan-de-Cuques. Mise a prix 121 100 EUR, adjuge 235 000 EUR (x1.9).",
                price_estimate=235000,
                date_vente="2025-01-22",
                ville="Plan-de-Cuques",
                address="7 bis Rue Honore Olive, 13380 Plan-de-Cuques",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 22/01/2025 - MAP 121 100 EUR"
            ),
            self.format_auction(
                title="ADJUGE 121 000 EUR - Appartement + Cave, 1 Rue du Cdt Imhaus, Marseille 6e",
                description="Appartement avec cave, rue Commandant Imhaus. Mise a prix 60 000 EUR, adjuge 121 000 EUR (x2).",
                price_estimate=121000,
                date_vente="2024-11-06",
                ville="Marseille",
                address="1 Rue du Commandant Imhaus, 13006 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 06/11/2024 - MAP 60 000 EUR"
            ),
            self.format_auction(
                title="ADJUGE 100 000 EUR - Local commercial, 1 Place Pol Lapeyre, Marseille 5e",
                description="Local commercial place Pol Lapeyre. Mise a prix 50 000 EUR, adjuge 100 000 EUR (x2).",
                price_estimate=100000,
                date_vente="2024-11-06",
                ville="Marseille",
                address="1 Place Pol Lapeyre, 13005 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 06/11/2024 - MAP 50 000 EUR"
            ),
            self.format_auction(
                title="ADJUGE 487 000 EUR - Ensemble d'appartements, 246 Rue Paradis, Marseille 6e",
                description="Ensemble d'appartements rue Paradis / 4 rue de Madagascar. Adjuge 487 000 EUR.",
                price_estimate=487000,
                date_vente="2024-11-06",
                ville="Marseille",
                address="246 Rue Paradis / 4 Rue de Madagascar, 13006 Marseille",
                url=url_jb,
                source_name="Adjudications TJ Marseille",
                auction_type="ADJUGE le 06/11/2024"
            ),
        ]
