"""Réglages de l'agent Pizza Napoli.

Les secrets (clés API, jetons Google) viennent des variables d'environnement,
jamais du code. Les seuils et listes ci-dessous sont ceux validés dans le plan
d'attaque ; on les modifie ici.
"""

import os
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")


def _env(nom: str, defaut: str) -> str:
    """Variable d'environnement ; une valeur vide (variable GitHub non renseignée) vaut le défaut."""
    return os.getenv(nom, "").strip() or defaut


# --- Comptes -----------------------------------------------------------------
BOITE_PIZZERIA = _env("BOITE_PIZZERIA", "carpentraspizzanapoli@gmail.com")
# Les deux gérants : reçoivent le rapport de 9h. Séparés par des virgules.
GERANTS = [a.strip() for a in _env("GERANTS_EMAILS", BOITE_PIZZERIA).split(",") if a.strip()]

# --- IA ----------------------------------------------------------------------
MODELE = _env("AGENT_MODELE", "claude-opus-5-5")

# --- L'Addition --------------------------------------------------------------
Z_EXPEDITEUR = "noreply@laddition.com"
Z_OBJET = "Votre Z quotidien"

# --- Seuils d'alerte (plan d'attaque, phase 2) ---------------------------------
SEUIL_ANNULATIONS = 0.03        # annulations après ticket > 3 % du CA TTC
SEUIL_OFFERTS = 0.05            # offerts hors offre boissons > 5 % du CA TTC
SEUIL_CORRECTIONS = 0.10        # corrections > 10 % du CA TTC (provisoire : à revoir après 1 mois)
SEUIL_BAISSE_CA = 0.20          # CA > 20 % sous le même jour de la semaine précédente
SEUIL_BAISSE_TICKET = 0.15      # ticket moyen > 15 % sous la moyenne du mois
JOURS_SANS_VENTE = 14           # pizza non vendue depuis 14 jours

# Catégories du Z qui ne sont pas des pizzas (exclues de l'alerte « pizza qui ne se vend plus »).
CATEGORIES_HORS_PIZZA = {"BOISSONS", "VIN", "BIÈRE", "BIERE", "DESSERT", "DESSERTS"}

# Offre du flyer : « 5 pizzas = soda ou rosé offert ». Ces produits passent à 0 € dans le Z.
# Prix de carte pour estimer leur valeur. À tenir à jour si la carte change.
OFFRE_BOISSONS = {
    "COCA COLA 1,25L": 3.00,
    "ICE TEA 1,5L": 3.00,
    "FANTA 1,5L": 3.00,
    "PETITE BALADE ROSÉ": 6.00,
}
# Le montant « Offerts » du Z inclut-il ces boissons à 0 € ? À confirmer sur
# l'export des lignes de ventes ; tant que ce n'est pas confirmé, on ne retire rien.
OFFERTS_INCLUENT_BOISSONS = _env("OFFERTS_INCLUENT_BOISSONS", "non") == "oui"

# --- Exercice comptable --------------------------------------------------------
EXERCICE_DEBUT_MOIS = 7          # exercice du 1er juillet au 30 juin
# Objectif de croissance du CA par rapport à la dernière liasse, sauf si un objectif
# en euros est saisi dans l'onglet « Exercices ». 0 = pas d'objectif.
OBJECTIF_CROISSANCE = float(_env("OBJECTIF_CROISSANCE", "0.10"))
DOSSIER_LIASSES = ("Légal", "Liasses")

# --- Google Drive ------------------------------------------------------------
DOSSIER_RACINE = "Pizza Napoli"
SOUS_DOSSIERS = ["Caisse", "Factures", "Banque", "Comptable", "Légal", "Personnel", "Rapports"]
DOSSIER_A_TRAITER = "À traiter"          # dans Factures/
CLASSEUR = "Pizza Napoli — Agent"        # tableur Google Sheets de l'agent
# Identifiant d'un tableur existant à utiliser (celui que lit le tableau de bord), partagé
# en modification avec le compte de la pizzeria. Vide : l'agent crée le sien dans Drive.
CLASSEUR_ID = _env("CLASSEUR_ID", "")
ONGLETS = {
    "Factures": ["Reçue le", "Fournisseur", "N° facture", "Date facture", "Échéance",
                 "HT", "TVA", "TTC", "Statut", "Catégorie", "Fichier", "Source"],
    "Ventes": ["Date", "CA TTC", "CA HT", "Ticket moyen", "Tickets (estim.)", "Offerts",
               "Corrections avant cuisine", "Corrections après cuisine", "Annulations après ticket",
               "CB (Z)", "Livraison", "A emporter"],
    "Ventes produits": ["Date", "Catégorie", "Produit", "Quantité", "TTC", "HT"],
    "Obligations": ["Libellé", "Échéance", "Récurrence", "Notes", "Agenda"],
    "Banque": ["Date", "Libellé", "Montant", "Type", "Relevé"],
    "Exercices": ["Exercice", "Début", "Fin", "CA HT", "Résultat", "Objectif CA HT", "Source"],
    "Comptes annuels": ["Exercice", "CA HT", "Achats matières", "Charges de personnel", "Valeur ajoutée",
                        "EBE", "Résultat d'exploitation", "Résultat net", "Disponibilités"],
    "Journal": ["Horodatage", "Module", "Action", "Détail"],
}

# --- Gmail -------------------------------------------------------------------
# Seul libellé créé par l'agent : il marque les mails déjà vus.
LIBELLE_TRAITE = "Agent/Traité"
# Le reste du classement utilise les libellés existants des gérants (Ticket Z, Factures,
# HYGIENES...) : l'agent n'en crée jamais. Ces deux-là sont posés sans passer par l'IA.
LIBELLE_Z = _env("LIBELLE_Z", "Ticket Z")
LIBELLE_FACTURES = _env("LIBELLE_FACTURES", "Factures")
# Catégories internes (aiguillage des traitements), distinctes des libellés Gmail.
CATEGORIES = ["facture", "z_caisse", "administratif", "client", "fournisseur", "publicite", "autre"]
AUCUN_LIBELLE = "(aucun)"
# Au premier passage, on ne remonte pas plus loin que ce nombre de jours.
JOURS_HISTORIQUE = int(_env("JOURS_HISTORIQUE", "3"))

# --- Rapport -----------------------------------------------------------------
# Jours de fermeture (pas d'alerte « Z manquant ») : 0 = lundi ... 6 = dimanche, ex. "0" ou "0,1".
JOURS_FERMES = {int(j) for j in _env("JOURS_FERMES", "").split(",") if j.strip().isdigit()}
HEURE_RAPPORT = 9                  # heure de Paris
RAPPEL_JOURS = (7, 1)              # rappels d'échéance à J-7 et J-1
