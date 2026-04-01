"""Scraper pour Interencheres.com - Site majeur d'encheres en France."""

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
    """Scraper pour interencheres.com."""

    name = "Interencheres"
    base_url = "https://www.interencheres.com"

    def scan(self, department="13", cities=None):
        """Scan les ventes aux encheres sur Interencheres pour le dept 13."""
        if not HAS_DEPS:
            return self._get_demo_data()

        auctions = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            # Recherche par departement 13
            search_url = f"{self.base_url}/recherche/ventes"
            params = {
                "department": department,
                "search": "Bouches-du-Rhone",
            }

            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Parser les resultats de ventes
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
            # Retourner des donnees de demo en cas d'erreur
            auctions = self._get_demo_data()

        return auctions

    def _parse_sale_card(self, card):
        """Parse une carte de vente depuis le HTML."""
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

        lot_el = card.select_one(".lot-count, .lots")
        lot_count = None
        if lot_el:
            nums = re.findall(r'\d+', lot_el.get_text())
            lot_count = int(nums[0]) if nums else None

        return self.format_auction(
            title=title,
            description=description,
            price_estimate=price,
            date_vente=date_vente,
            ville=ville,
            url=url,
            image_url=image_url,
            lot_count=lot_count,
            auction_type="Encheres volontaires"
        )

    def _parse_date(self, date_text):
        """Tente de parser une date depuis du texte."""
        if not date_text:
            return ""
        # Format ISO
        if re.match(r'\d{4}-\d{2}-\d{2}', date_text):
            return date_text[:10]
        # Format francais
        match = re.search(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})', date_text)
        if match:
            d, m, y = match.groups()
            if len(y) == 2:
                y = f"20{y}"
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        return date_text

    def _get_demo_data(self):
        """Donnees de demonstration pour le departement 13."""
        today = datetime.now()
        return [
            self.format_auction(
                title="Vente aux encheres mobilier et objets d'art",
                description="Belle vente de mobilier ancien, objets d'art et tableaux. Plus de 150 lots issus de successions marseillaises.",
                price_estimate=None,
                date_vente=(today + timedelta(days=3)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Hotel des ventes de Marseille, Rue Sylvabelle",
                url="https://www.interencheres.com/meubles-objets-art/",
                image_url="",
                lot_count=156,
                auction_type="Encheres volontaires"
            ),
            self.format_auction(
                title="Vehicules utilitaires et de tourisme - Parc Auto",
                description="Vente judiciaire de vehicules provenant de saisies. Peugeot, Renault, Citroen, Mercedes. Tous visibles sur place la veille.",
                price_estimate=2500,
                date_vente=(today + timedelta(days=5)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Fourriere municipale, Zone Arnavaux",
                url="https://www.interencheres.com/vehicules/",
                image_url="",
                lot_count=42,
                auction_type="Vente judiciaire"
            ),
            self.format_auction(
                title="Bijoux, montres et orfevrerie",
                description="Collection de bijoux en or 18k, montres de marque (Rolex, Cartier, Omega), argenterie. Expertise sur place.",
                price_estimate=800,
                date_vente=(today + timedelta(days=7)).strftime("%Y-%m-%d"),
                ville="Aix-en-Provence",
                address="Etude Me Durand, Cours Mirabeau",
                url="https://www.interencheres.com/bijoux-montres/",
                image_url="",
                lot_count=89,
                auction_type="Encheres volontaires"
            ),
            self.format_auction(
                title="Materiel informatique et bureautique - Liquidation",
                description="Liquidation judiciaire societe informatique. Ordinateurs, ecrans, serveurs, imprimantes professionnelles.",
                price_estimate=150,
                date_vente=(today + timedelta(days=2)).strftime("%Y-%m-%d"),
                ville="Vitrolles",
                address="Zone industrielle Les Estroublans",
                url="https://www.interencheres.com/materiel-professionnel/",
                image_url="",
                lot_count=234,
                auction_type="Liquidation judiciaire"
            ),
            self.format_auction(
                title="Appartement T3 65m2 - Vente sur licitation",
                description="Appartement 3 pieces, 65m2, 5eme etage avec ascenseur, balcon, vue mer partielle. Quartier Endoume.",
                price_estimate=125000,
                date_vente=(today + timedelta(days=15)).strftime("%Y-%m-%d"),
                ville="Marseille",
                address="Tribunal Judiciaire de Marseille",
                url="https://www.encheres-publiques.com/",
                image_url="",
                auction_type="Vente sur licitation"
            ),
            self.format_auction(
                title="Maison de village 120m2 avec jardin",
                description="Maison de village restauree, 120m2, 4 chambres, jardin 200m2, garage. Centre village, proche commodites.",
                price_estimate=185000,
                date_vente=(today + timedelta(days=20)).strftime("%Y-%m-%d"),
                ville="Tarascon",
                address="Tribunal Judiciaire de Tarascon",
                url="https://www.encheres-publiques.com/",
                image_url="",
                auction_type="Vente judiciaire"
            ),
        ]
