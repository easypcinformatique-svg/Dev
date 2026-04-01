"""Enumerations partagees par tous les modeles."""

import enum


class Comptoir(str, enum.Enum):
    ACCUEIL = "accueil"
    WEB = "web"
    WHATSAPP = "whatsapp"
    TELEPHONE = "telephone"
    UBER_EATS = "uber_eats"
    DELIVEROO = "deliveroo"
    JUST_EAT = "just_eat"


class ModeCommande(str, enum.Enum):
    EMPORTER = "emporter"
    LIVRAISON = "livraison"


class StatutCommande(str, enum.Enum):
    NOUVELLE = "nouvelle"
    CONFIRMEE = "confirmee"
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


class TypePate(str, enum.Enum):
    CLASSIQUE = "classique"
    FINE = "fine"
    EPAISSE = "epaisse"
    SANS_GLUTEN = "sans_gluten"
    COMPLETE = "complete"


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
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"


class StatutPaiement(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    PAYE = "paye"
    REMBOURSE = "rembourse"


class EtapeWhatsApp(str, enum.Enum):
    ACCUEIL = "accueil"
    MENU = "menu"
    TAILLE = "taille"
    PATE = "pate"
    SUPPLEMENTS = "supplements"
    MODE = "mode"
    CRENEAU = "creneau"
    ADRESSE = "adresse"
    RECAP = "recap"
    CONFIRME = "confirme"


class TypePromo(str, enum.Enum):
    POURCENTAGE = "pourcentage"
    MONTANT_FIXE = "montant_fixe"
    GRATUIT = "gratuit"  # ex: 3eme pizza offerte
    LIVRAISON_GRATUITE = "livraison_gratuite"
