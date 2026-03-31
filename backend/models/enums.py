"""Enumerations partagees par tous les modeles."""

import enum


class Comptoir(str, enum.Enum):
    ACCUEIL = "accueil"
    WEB = "web"
    WHATSAPP = "whatsapp"
    LIVRAISON_PLATFORM = "livraison_platform"


class ModeCommande(str, enum.Enum):
    EMPORTER = "emporter"
    LIVRAISON = "livraison"


class StatutCommande(str, enum.Enum):
    NOUVELLE = "nouvelle"
    EN_PREPARATION = "en_preparation"
    PRETE = "prete"
    EN_LIVRAISON = "en_livraison"
    LIVREE = "livree"
    RECUPEREE = "recuperee"
    ANNULEE = "annulee"


class TaillePizza(str, enum.Enum):
    JUNIOR = "junior"
    MEDIUM = "medium"
    LARGE = "large"
    XXL = "xxl"


class Role(str, enum.Enum):
    ADMIN = "admin"
    CAISSIER = "caissier"
    PIZZAIOLO = "pizzaiolo"
    LIVREUR = "livreur"


class StatutLivreur(str, enum.Enum):
    DISPONIBLE = "disponible"
    EN_COURSE = "en_course"
    INDISPONIBLE = "indisponible"


class ModePaiement(str, enum.Enum):
    ESPECES = "especes"
    CB = "cb"
    TICKET_RESTAURANT = "ticket_restaurant"
    EN_LIGNE = "en_ligne"
    MIXTE = "mixte"


class StatutPaiement(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    PAYE = "paye"
    REMBOURSE = "rembourse"


class EtapeWhatsApp(str, enum.Enum):
    ACCUEIL = "accueil"
    MENU = "menu"
    TAILLE = "taille"
    SUPPLEMENTS = "supplements"
    MODE = "mode"
    CRENEAU = "creneau"
    ADRESSE = "adresse"
    RECAP = "recap"
    CONFIRME = "confirme"
