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

# Metadata pour l'interface : label, description, min, max, step, type
PARAM_META = {
    # Bot Config
    "initial_capital": {
        "label": "Capital Initial ($)",
        "desc": "Montant de depart en dollars",
        "min": 100, "max": 1000000, "step": 100, "type": "number", "group": "Capital"
    },
    "max_position_pct": {
        "label": "Taille Max Position (%)",
        "desc": "Pourcentage max du capital par position",
        "min": 0.01, "max": 0.50, "step": 0.01, "type": "percent", "group": "Capital"
    },
    "max_total_exposure_pct": {
        "label": "Exposition Max Totale (%)",
        "desc": "Pourcentage max du capital expose",
        "min": 0.10, "max": 1.0, "step": 0.05, "type": "percent", "group": "Capital"
    },
    "max_positions": {
        "label": "Nombre Max Positions",
        "desc": "Nombre maximum de positions ouvertes",
        "min": 1, "max": 50, "step": 1, "type": "integer", "group": "Capital"
    },
    "min_volume": {
        "label": "Volume Minimum ($)",
        "desc": "Volume minimum pour filtrer les marches",
        "min": 1000, "max": 1000000, "step": 1000, "type": "number", "group": "Filtres Marches"
    },
    "min_liquidity": {
        "label": "Liquidite Minimum ($)",
        "desc": "Liquidite minimum pour filtrer les marches",
        "min": 500, "max": 100000, "step": 500, "type": "number", "group": "Filtres Marches"
    },
    "min_spread": {
        "label": "Spread Minimum",
        "desc": "Spread minimum acceptable",
        "min": 0.001, "max": 0.10, "step": 0.001, "type": "number", "group": "Filtres Marches"
    },
    "max_spread": {
        "label": "Spread Maximum",
        "desc": "Spread maximum acceptable",
        "min": 0.01, "max": 0.30, "step": 0.01, "type": "number", "group": "Filtres Marches"
    },
    "scan_interval_seconds": {
        "label": "Intervalle de Scan (sec)",
        "desc": "Temps entre chaque scan des marches",
        "min": 60, "max": 3600, "step": 30, "type": "integer", "group": "Timing"
    },
    "history_fidelity": {
        "label": "Fidelite Historique (min)",
        "desc": "Resolution de l'historique en minutes",
        "min": 1, "max": 1440, "step": 1, "type": "integer", "group": "Timing"
    },
    "daily_loss_limit_pct": {
        "label": "Limite Perte Journaliere (%)",
        "desc": "Perte journaliere max avant arret",
        "min": 0.01, "max": 0.50, "step": 0.01, "type": "percent", "group": "Risk Management"
    },
    "max_drawdown_pct": {
        "label": "Drawdown Maximum (%)",
        "desc": "Drawdown max avant arret",
        "min": 0.05, "max": 0.50, "step": 0.01, "type": "percent", "group": "Risk Management"
    },
    "dry_run": {
        "label": "Mode Simulation",
        "desc": "Activer le mode dry-run (pas de vrai argent)",
        "type": "boolean", "group": "Mode"
    },
    "strategy": {
        "label": "Strategie",
        "desc": "Strategie de trading a utiliser",
        "type": "select", "options": ["alpha_composite", "insurance_seller"], "group": "Mode"
    },
    # Strategy Config
    "min_consensus": {
        "label": "Consensus Minimum",
        "desc": "Score minimum de consensus des strategies",
        "min": 0.05, "max": 0.50, "step": 0.01, "type": "number", "group": "Strategie Alpha"
    },
    "min_agreeing_strategies": {
        "label": "Strategies Min en Accord",
        "desc": "Nombre minimum de strategies en accord",
        "min": 1, "max": 5, "step": 1, "type": "integer", "group": "Strategie Alpha"
    },
    "spread_filter": {
        "label": "Filtre Spread Strategie",
        "desc": "Spread max pour la strategie",
        "min": 0.01, "max": 0.30, "step": 0.01, "type": "number", "group": "Strategie Alpha"
    },
    "volume_percentile_filter": {
        "label": "Percentile Volume",
        "desc": "Percentile minimum du volume",
        "min": 0, "max": 100, "step": 1, "type": "integer", "group": "Strategie Alpha"
    },
    "max_price_extreme": {
        "label": "Prix Max Extreme",
        "desc": "Prix maximum (eviter les marches trop proches de 1)",
        "min": 0.50, "max": 0.99, "step": 0.01, "type": "number", "group": "Strategie Alpha"
    },
    "min_price_extreme": {
        "label": "Prix Min Extreme",
        "desc": "Prix minimum (eviter les marches trop proches de 0)",
        "min": 0.01, "max": 0.50, "step": 0.01, "type": "number", "group": "Strategie Alpha"
    },
    "stop_loss": {
        "label": "Stop Loss",
        "desc": "Seuil de perte pour fermer une position",
        "min": 0.05, "max": 0.80, "step": 0.01, "type": "number", "group": "Sortie"
    },
    "take_profit": {
        "label": "Take Profit",
        "desc": "Seuil de gain pour fermer une position",
        "min": 0.10, "max": 2.0, "step": 0.05, "type": "number", "group": "Sortie"
    },
    "trailing_stop": {
        "label": "Trailing Stop",
        "desc": "Trailing stop en pourcentage depuis le peak",
        "min": 0.05, "max": 0.50, "step": 0.01, "type": "number", "group": "Sortie"
    },
    "strategy_max_position_pct": {
        "label": "Taille Max Position Strategie (%)",
        "desc": "Override strategie pour la taille max de position",
        "min": 0.01, "max": 0.50, "step": 0.01, "type": "percent", "group": "Sortie"
    },
    "strategy_max_positions": {
        "label": "Max Positions Strategie",
        "desc": "Override strategie pour le nombre max de positions",
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

    def update_params(self, updates: dict) -> dict:
        """Met a jour les parametres actifs. Retourne les changements effectues."""
        changes = []
        for key, new_value in updates.items():
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

        return {"changes": changes, "active": self.get_active()}

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
