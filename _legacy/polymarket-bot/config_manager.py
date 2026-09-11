"""
Gestionnaire de configurations pour le Hedge Fund Bot.

Permet de :
    - Sauvegarder les parametres d'origine (defaults)
    - Creer des profils de configuration nommes
    - Modifier les parametres en cours
    - Restaurer les parametres d'origine en un clic
    - Comparer le profil actuel vs les defaults

Stockage : fichier JSON unique (bot_configs.json)
"""

import json
import copy
from pathlib import Path
from datetime import datetime
from dataclasses import asdict


# Valeurs par defaut — ce sont les parametres d'origine du bot
DEFAULT_BOT_CONFIG = {
    "initial_capital": 1000.0,
    "max_position_pct": 0.05,
    "max_total_exposure_pct": 0.30,
    "max_positions": 8,
    "min_volume": 50000.0,
    "min_liquidity": 5000.0,
    "min_spread": 0.005,
    "max_spread": 0.08,
    "scan_interval_seconds": 300,
    "history_fidelity": 60,
    "daily_loss_limit_pct": 0.05,
    "max_drawdown_pct": 0.15,
    "dry_run": True,
    "strategy": "alpha_composite",
}

DEFAULT_STRATEGY_CONFIG = {
    "min_consensus": 0.14,
    "min_agreeing_strategies": 2,
    "spread_filter": 0.10,
    "volume_percentile_filter": 28,
    "max_price_extreme": 0.89,
    "min_price_extreme": 0.09,
    "stop_loss": 0.25,
    "take_profit": 0.50,
    "trailing_stop": 0.17,
    "strategy_max_position_pct": 0.08,
    "strategy_max_positions": 12,
}

# Metadata pour l'interface : label, description, exemple, icone, min, max, step, type
PARAM_META = {
    # Bot Config
    "initial_capital": {
        "label": "Capital Initial ($)",
        "desc": "Montant de depart en dollars pour le bot",
        "tooltip": "C'est l'argent total que le bot peut utiliser pour trader. Exemple : avec 1000$, le bot repartit ce capital entre ses differentes positions.",
        "example": "1000$ = le bot demarre avec 1000$ et ne depasse jamais ce montant",
        "icon": "dollar",
        "min": 100, "max": 1000000, "step": 100, "type": "number", "group": "Capital"
    },
    "max_position_pct": {
        "label": "Taille Max Position (%)",
        "desc": "Pourcentage max du capital par position",
        "tooltip": "Limite combien le bot peut miser sur un seul marche. Plus c'est bas, plus le risque est reparti. Plus c'est haut, plus chaque trade a d'impact.",
        "example": "5% de 1000$ = max 50$ par position. Si le marche perd 20%, tu perds 10$ (pas 200$)",
        "icon": "target",
        "min": 0.01, "max": 0.50, "step": 0.01, "type": "percent", "group": "Capital"
    },
    "max_total_exposure_pct": {
        "label": "Exposition Max Totale (%)",
        "desc": "Pourcentage max du capital expose en meme temps",
        "tooltip": "Limite le montant total investi simultanement. Le reste reste en cash comme reserve de securite.",
        "example": "30% de 1000$ = max 300$ investis en meme temps, 700$ restent en cash",
        "icon": "shield",
        "min": 0.10, "max": 1.0, "step": 0.05, "type": "percent", "group": "Capital"
    },
    "max_positions": {
        "label": "Nombre Max Positions",
        "desc": "Nombre maximum de positions ouvertes simultanement",
        "tooltip": "Combien de paris differents le bot peut avoir en meme temps. Plus il y en a, plus le risque est diversifie mais les gains par position sont plus petits.",
        "example": "8 positions = le bot peut parier sur 8 marches differents en meme temps",
        "icon": "layers",
        "min": 1, "max": 50, "step": 1, "type": "integer", "group": "Capital"
    },
    "min_volume": {
        "label": "Volume Minimum ($)",
        "desc": "Volume minimum echange sur le marche",
        "tooltip": "Filtre les marches trop petits ou inactifs. Un volume eleve = plus de traders = prix plus fiable. Les petits marches sont risques car les prix bougent facilement.",
        "example": "50000$ = ignore les marches avec moins de 50k$ de volume. Le marche 'Trump wins 2024' avait +10M$ de volume",
        "icon": "chart",
        "min": 1000, "max": 1000000, "step": 1000, "type": "number", "group": "Filtres Marches"
    },
    "min_liquidity": {
        "label": "Liquidite Minimum ($)",
        "desc": "Liquidite minimum disponible sur le marche",
        "tooltip": "La liquidite = combien d'argent est disponible pour acheter/vendre sans faire bouger le prix. Faible liquidite = tu paies plus cher a l'achat et recois moins a la vente.",
        "example": "5000$ de liquidite = assez d'offres pour entrer/sortir sans impact majeur sur le prix",
        "icon": "droplet",
        "min": 500, "max": 100000, "step": 500, "type": "number", "group": "Filtres Marches"
    },
    "min_spread": {
        "label": "Spread Minimum",
        "desc": "Ecart minimum entre prix d'achat et de vente",
        "tooltip": "Le spread = difference entre le prix d'achat (ask) et de vente (bid). Un spread trop petit = pas assez de marge pour profiter. Le bot a besoin d'un minimum de spread pour etre rentable.",
        "example": "0.005 = au moins 0.5% d'ecart. Si YES est a 0.60/0.605, le spread est 0.005",
        "icon": "arrows",
        "min": 0.001, "max": 0.10, "step": 0.001, "type": "number", "group": "Filtres Marches"
    },
    "max_spread": {
        "label": "Spread Maximum",
        "desc": "Ecart maximum entre prix d'achat et de vente",
        "tooltip": "Un spread trop large = marche illiquide et dangereux. Si l'ecart est enorme, c'est que personne ne trade ce marche et le prix n'est pas fiable.",
        "example": "0.08 = max 8% d'ecart. Si YES est a 0.50/0.58, le spread (0.08) est trop large = marche evite",
        "icon": "arrows",
        "min": 0.01, "max": 0.30, "step": 0.01, "type": "number", "group": "Filtres Marches"
    },
    "scan_interval_seconds": {
        "label": "Intervalle de Scan (sec)",
        "desc": "Temps d'attente entre chaque analyse des marches",
        "tooltip": "Combien de secondes le bot attend entre deux scans. Court = plus reactif mais consomme plus d'API. Long = moins de requetes mais peut rater des opportunites.",
        "example": "300 sec = le bot scanne les marches toutes les 5 minutes. 60 sec = toutes les minutes (plus agressif)",
        "icon": "clock",
        "min": 60, "max": 3600, "step": 30, "type": "integer", "group": "Timing"
    },
    "history_fidelity": {
        "label": "Fidelite Historique (min)",
        "desc": "Resolution des donnees historiques en minutes",
        "tooltip": "Precision des bougies (candles) utilisees pour l'analyse technique. 1 min = tres precis mais lourd. 60 min = moins precis mais rapide a charger.",
        "example": "60 = bougies de 1 heure. Le bot analyse les tendances sur des periodes d'1h",
        "icon": "clock",
        "min": 1, "max": 1440, "step": 1, "type": "integer", "group": "Timing"
    },
    "daily_loss_limit_pct": {
        "label": "Limite Perte Journaliere (%)",
        "desc": "Perte max par jour avant que le bot s'arrete",
        "tooltip": "Protection contre les mauvais jours. Si le bot perd trop en une journee, il arrete de trader pour limiter les degats. Se reinitialise a minuit.",
        "example": "5% de 1000$ = si le bot perd 50$ dans la journee, il s'arrete et attend le lendemain",
        "icon": "alert",
        "min": 0.01, "max": 0.50, "step": 0.01, "type": "percent", "group": "Risk Management"
    },
    "max_drawdown_pct": {
        "label": "Drawdown Maximum (%)",
        "desc": "Perte max depuis le plus haut avant arret total",
        "tooltip": "Le drawdown = combien tu as perdu depuis ton meilleur moment. C'est le 'frein d'urgence' du bot. Si l'equity chute trop depuis son pic, tout s'arrete.",
        "example": "15% = si l'equity etait a 1200$ (pic) et tombe a 1020$ (-15%), le bot s'arrete completement",
        "icon": "alert",
        "min": 0.05, "max": 0.50, "step": 0.01, "type": "percent", "group": "Risk Management"
    },
    "dry_run": {
        "label": "Mode Simulation",
        "desc": "Simuler les trades sans utiliser de vrai argent",
        "tooltip": "En mode DRY RUN, le bot fait tout normalement (scan, analyse, decisions) mais ne place aucun vrai ordre. Parfait pour tester une strategie sans risque.",
        "example": "Active = aucun vrai argent utilise, tout est simule. Desactive = VRAI ARGENT, trades reels sur Polymarket",
        "icon": "toggle",
        "type": "boolean", "group": "Mode"
    },
    "strategy": {
        "label": "Strategie",
        "desc": "Algorithme de trading utilise par le bot",
        "tooltip": "alpha_composite = combine plusieurs sous-strategies (momentum, mean-reversion, volume) et ne trade que si elles sont d'accord. insurance_seller = vend des options peu probables (style assurance).",
        "example": "alpha_composite = le bot verifie 4-5 indicateurs avant de trader. Plus prudent mais plus fiable",
        "icon": "brain",
        "type": "select", "options": ["alpha_composite", "insurance_seller"], "group": "Mode"
    },
    # Strategy Config
    "min_consensus": {
        "label": "Consensus Minimum",
        "desc": "Score minimum d'accord entre les sous-strategies",
        "tooltip": "Chaque sous-strategie vote pour ou contre un trade. Le consensus = moyenne des votes. Plus ce seuil est haut, moins le bot trade mais avec plus de conviction.",
        "example": "0.14 = au moins 14% de consensus. Si 3 strategies sur 5 disent 'acheter', le consensus est ~0.20 (OK). Si 1 sur 5, c'est ~0.04 (rejete)",
        "icon": "users",
        "min": 0.05, "max": 0.50, "step": 0.01, "type": "number", "group": "Strategie Alpha"
    },
    "min_agreeing_strategies": {
        "label": "Strategies Min en Accord",
        "desc": "Nombre minimum de sous-strategies qui doivent etre d'accord",
        "tooltip": "En plus du consensus, ce nombre minimum de strategies doivent voter dans la meme direction. C'est un filtre supplementaire pour eviter les faux signaux.",
        "example": "2 = au moins 2 strategies sur 5 doivent dire 'acheter YES'. Si une seule dit oui, pas de trade",
        "icon": "users",
        "min": 1, "max": 5, "step": 1, "type": "integer", "group": "Strategie Alpha"
    },
    "spread_filter": {
        "label": "Filtre Spread Strategie",
        "desc": "Spread max accepte par la strategie pour un signal",
        "tooltip": "Filtre au niveau de la strategie (en plus du filtre global). Rejette les signaux sur des marches ou le spread est trop large, meme si le signal est fort.",
        "example": "0.10 = la strategie ignore les marches avec plus de 10% de spread, meme si le signal est bon",
        "icon": "filter",
        "min": 0.01, "max": 0.30, "step": 0.01, "type": "number", "group": "Strategie Alpha"
    },
    "volume_percentile_filter": {
        "label": "Percentile Volume",
        "desc": "Percentile minimum du volume parmi tous les marches",
        "tooltip": "Classe les marches par volume et ne garde que ceux au-dessus du percentile choisi. 28 = garde les 72% de marches les plus actifs.",
        "example": "28 = sur 100 marches, ignore les 28 avec le moins de volume. Garde seulement les 72 plus actifs",
        "icon": "chart",
        "min": 0, "max": 100, "step": 1, "type": "integer", "group": "Strategie Alpha"
    },
    "max_price_extreme": {
        "label": "Prix Max Extreme",
        "desc": "Prix YES maximum pour accepter un trade",
        "tooltip": "Evite d'acheter YES quand le prix est deja tres haut (proche de 1.00). A 0.95 par ex., le potentiel de gain est minime mais le risque de perte est enorme.",
        "example": "0.89 = n'achete pas YES si le prix est > 0.89. Un marche a 0.92 est ignore car trop cher (peu de marge)",
        "icon": "trendUp",
        "min": 0.50, "max": 0.99, "step": 0.01, "type": "number", "group": "Strategie Alpha"
    },
    "min_price_extreme": {
        "label": "Prix Min Extreme",
        "desc": "Prix YES minimum pour accepter un trade",
        "tooltip": "Evite d'acheter YES quand le prix est deja tres bas (proche de 0). Un prix tres bas = le marche pense que c'est tres improbable, souvent a raison.",
        "example": "0.09 = n'achete pas YES si le prix est < 0.09. Un marche a 0.03 est ignore car trop improbable",
        "icon": "trendDown",
        "min": 0.01, "max": 0.50, "step": 0.01, "type": "number", "group": "Strategie Alpha"
    },
    "stop_loss": {
        "label": "Stop Loss",
        "desc": "Perte max toleree avant de fermer une position",
        "tooltip": "Si une position perd plus que ce pourcentage, le bot la ferme automatiquement pour limiter les pertes. C'est le 'coupe-circuit' par position.",
        "example": "0.25 = ferme la position si elle perd 25%. Achat a 0.50, fermeture auto si ca tombe a 0.375",
        "icon": "scissors",
        "min": 0.05, "max": 0.80, "step": 0.01, "type": "number", "group": "Sortie"
    },
    "take_profit": {
        "label": "Take Profit",
        "desc": "Gain cible pour encaisser les profits",
        "tooltip": "Si une position gagne plus que ce pourcentage, le bot la ferme pour securiser le profit. Evite de tout perdre en attendant trop.",
        "example": "0.50 = prend le profit a +50%. Achat a 0.40, vente auto si ca monte a 0.60",
        "icon": "trophy",
        "min": 0.10, "max": 2.0, "step": 0.05, "type": "number", "group": "Sortie"
    },
    "trailing_stop": {
        "label": "Trailing Stop",
        "desc": "Stop mobile qui suit le prix a la hausse",
        "tooltip": "Au lieu d'un stop fixe, le trailing stop monte avec le prix. Si le prix recule de X% depuis son pic, on vend. Permet de laisser courir les gains tout en protegeant les profits.",
        "example": "0.17 = si le prix monte de 0.50 a 0.70 (pic), le stop se place a 0.70 - 17% = 0.58. Si le prix redescend a 0.58, on vend",
        "icon": "trendUp",
        "min": 0.05, "max": 0.50, "step": 0.01, "type": "number", "group": "Sortie"
    },
    "strategy_max_position_pct": {
        "label": "Taille Max Position Strategie (%)",
        "desc": "Override de la strategie pour la taille max de chaque position",
        "tooltip": "La strategie peut avoir sa propre limite de taille de position, independante du parametre global. C'est un deuxieme filet de securite.",
        "example": "8% = la strategie ne met jamais plus de 8% du capital sur un trade, meme si le parametre global autorise plus",
        "icon": "target",
        "min": 0.01, "max": 0.50, "step": 0.01, "type": "percent", "group": "Sortie"
    },
    "strategy_max_positions": {
        "label": "Max Positions Strategie",
        "desc": "Override de la strategie pour le nombre max de positions",
        "tooltip": "La strategie peut limiter le nombre de positions de son cote. Peut etre different (plus haut ou plus bas) que la limite globale du bot.",
        "example": "12 = la strategie autorise jusqu'a 12 positions, meme si le bot global est limite a 8 (c'est le plus restrictif qui gagne)",
        "icon": "layers",
        "min": 1, "max": 50, "step": 1, "type": "integer", "group": "Sortie"
    },
}


class ConfigManager:
    """Gestionnaire de configurations avec profils et restauration."""

    def __init__(self, config_file: str = "bot_configs.json"):
        self.config_file = Path(config_file)
        self.data = self._load()

    def _load(self) -> dict:
        """Charge le fichier de configs ou initialise avec les defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, KeyError):
                pass

        # Initialiser avec les defaults
        data = {
            "defaults": {
                "bot": copy.deepcopy(DEFAULT_BOT_CONFIG),
                "strategy": copy.deepcopy(DEFAULT_STRATEGY_CONFIG),
            },
            "active": {
                "bot": copy.deepcopy(DEFAULT_BOT_CONFIG),
                "strategy": copy.deepcopy(DEFAULT_STRATEGY_CONFIG),
            },
            "profiles": {},
            "history": [],
        }
        self._save(data)
        return data

    def _save(self, data: dict = None):
        """Sauvegarde le fichier de configs."""
        if data is None:
            data = self.data
        tmp = self.config_file.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)
        tmp.replace(self.config_file)

    def get_defaults(self) -> dict:
        """Retourne les parametres d'origine."""
        return {
            "bot": copy.deepcopy(self.data["defaults"]["bot"]),
            "strategy": copy.deepcopy(self.data["defaults"]["strategy"]),
        }

    def get_active(self) -> dict:
        """Retourne la configuration active."""
        return {
            "bot": copy.deepcopy(self.data["active"]["bot"]),
            "strategy": copy.deepcopy(self.data["active"]["strategy"]),
        }

    def get_active_with_meta(self) -> dict:
        """Retourne la config active avec les metadonnees pour l'UI."""
        active = self.get_active()
        defaults = self.get_defaults()
        all_params = {**active["bot"], **active["strategy"]}
        all_defaults = {**defaults["bot"], **defaults["strategy"]}

        params_with_meta = []
        for key, value in all_params.items():
            meta = PARAM_META.get(key, {})
            is_modified = value != all_defaults.get(key)
            params_with_meta.append({
                "key": key,
                "value": value,
                "default": all_defaults.get(key),
                "modified": is_modified,
                **meta,
            })

        return {
            "params": params_with_meta,
            "profiles": list(self.data.get("profiles", {}).keys()),
            "history": self.data.get("history", [])[-20:],
        }

    def validate_param(self, key: str, value) -> tuple[bool, str]:
        """Valide qu'un parametre est dans les bornes autorisees."""
        meta = PARAM_META.get(key)
        if not meta:
            return True, ""
        param_type = meta.get("type", "")
        if param_type in ("number", "percent", "integer"):
            try:
                val = float(value)
            except (TypeError, ValueError):
                return False, f"{meta.get('label', key)}: valeur numerique attendue"
            mn = meta.get("min")
            mx = meta.get("max")
            if mn is not None and val < mn:
                return False, f"{meta.get('label', key)}: minimum {mn}, recu {val}"
            if mx is not None and val > mx:
                return False, f"{meta.get('label', key)}: maximum {mx}, recu {val}"
        if param_type == "select":
            options = meta.get("options", [])
            if options and value not in options:
                return False, f"{meta.get('label', key)}: valeurs possibles {options}"
        return True, ""

    def update_params(self, updates: dict) -> dict:
        """Met a jour les parametres actifs. Retourne les changements effectues."""
        changes = []
        errors = []
        for key, new_value in updates.items():
            # Validation des ranges
            valid, err = self.validate_param(key, new_value)
            if not valid:
                errors.append(err)
                continue

            # Determiner si c'est un param bot ou strategy
            if key in self.data["active"]["bot"]:
                old_value = self.data["active"]["bot"][key]
                self.data["active"]["bot"][key] = new_value
            elif key in self.data["active"]["strategy"]:
                old_value = self.data["active"]["strategy"][key]
                self.data["active"]["strategy"][key] = new_value
            else:
                continue

            if old_value != new_value:
                changes.append({
                    "key": key,
                    "old": old_value,
                    "new": new_value,
                    "time": datetime.now().isoformat(),
                })

        if changes:
            self.data.setdefault("history", []).extend(changes)
            # Garder les 200 derniers changements
            self.data["history"] = self.data["history"][-200:]
            self._save()

        result = {"changes": changes, "active": self.get_active()}
        if errors:
            result["errors"] = errors
        return result

    def reset_to_defaults(self) -> dict:
        """Restaure les parametres d'origine."""
        self.data["active"] = copy.deepcopy(self.data["defaults"])
        self.data.setdefault("history", []).append({
            "key": "__reset__",
            "old": "custom",
            "new": "defaults",
            "time": datetime.now().isoformat(),
        })
        self._save()
        return self.get_active()

    def save_profile(self, name: str) -> dict:
        """Sauvegarde la config active comme profil nomme."""
        self.data.setdefault("profiles", {})[name] = {
            "bot": copy.deepcopy(self.data["active"]["bot"]),
            "strategy": copy.deepcopy(self.data["active"]["strategy"]),
            "saved_at": datetime.now().isoformat(),
        }
        self._save()
        return {"profiles": list(self.data["profiles"].keys())}

    def load_profile(self, name: str) -> dict:
        """Charge un profil sauvegarde."""
        profile = self.data.get("profiles", {}).get(name)
        if not profile:
            return {"error": f"Profil '{name}' introuvable"}

        self.data["active"]["bot"] = copy.deepcopy(profile["bot"])
        self.data["active"]["strategy"] = copy.deepcopy(profile["strategy"])
        self.data.setdefault("history", []).append({
            "key": "__load_profile__",
            "old": "previous",
            "new": name,
            "time": datetime.now().isoformat(),
        })
        self._save()
        return self.get_active()

    def delete_profile(self, name: str) -> dict:
        """Supprime un profil."""
        profiles = self.data.get("profiles", {})
        if name in profiles:
            del profiles[name]
            self._save()
        return {"profiles": list(profiles.keys())}

    def get_diff(self) -> list:
        """Compare la config active vs les defaults."""
        defaults = {**self.data["defaults"]["bot"], **self.data["defaults"]["strategy"]}
        active = {**self.data["active"]["bot"], **self.data["active"]["strategy"]}

        diffs = []
        for key in defaults:
            if active.get(key) != defaults[key]:
                meta = PARAM_META.get(key, {})
                diffs.append({
                    "key": key,
                    "label": meta.get("label", key),
                    "default": defaults[key],
                    "current": active.get(key),
                })
        return diffs

    def apply_to_bot_config(self, bot_config) -> None:
        """Applique la config active a un objet BotConfig existant."""
        active_bot = self.data["active"]["bot"]
        for key, value in active_bot.items():
            if hasattr(bot_config, key):
                setattr(bot_config, key, value)

    def get_strategy_params(self) -> dict:
        """Retourne les parametres de strategie actifs."""
        return copy.deepcopy(self.data["active"]["strategy"])
