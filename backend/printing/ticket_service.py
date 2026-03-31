"""Service d'impression de tickets (ESC/POS pour imprimantes thermiques 80mm)."""

import os
from datetime import datetime


def generer_ticket_caisse(commande: dict, config: dict) -> str:
    """Genere le contenu texte d'un ticket de caisse."""
    lines = []
    nom = config.get("nom", "Ma Pizzeria")
    adresse = config.get("adresse", "")
    tel = config.get("telephone", "")
    siret = config.get("siret", "")

    # En-tete
    lines.append(nom.center(42))
    if adresse:
        lines.append(adresse.center(42))
    if tel:
        lines.append(f"Tel: {tel}".center(42))
    lines.append("=" * 42)

    # Info commande
    lines.append(f"Commande : {commande['numero']}")
    lines.append(f"Date : {commande.get('date', datetime.now().strftime('%d/%m/%Y %H:%M'))}")
    mode = "EMPORTER" if commande.get("mode") == "emporter" else "LIVRAISON"
    lines.append(f"Mode : {mode}")
    comptoir = commande.get("comptoir", "").upper()
    lines.append(f"Comptoir : {comptoir}")
    if commande.get("client_nom"):
        lines.append(f"Client : {commande['client_nom']}")
    if commande.get("creneau_label"):
        lines.append(f"Creneau : {commande['creneau_label']}")
    lines.append("-" * 42)

    # Lignes
    for ligne in commande.get("lignes", []):
        nom_produit = ligne.get("produit_nom", "")
        taille = ligne.get("taille", "")
        qty = ligne.get("quantite", 1)
        prix = ligne.get("prix_unitaire", 0)
        if taille:
            nom_produit += f" ({taille})"
        total_ligne = prix * qty
        line_text = f"{qty}x {nom_produit}"
        prix_text = f"{total_ligne:.2f} EUR"
        lines.append(f"{line_text:<30}{prix_text:>12}")

        # Supplements
        for sup in ligne.get("supplements", []):
            sup_nom = sup.get("nom", "")
            sup_prix = sup.get("prix", 0) * sup.get("quantite", 1)
            lines.append(f"  + {sup_nom:<26}{sup_prix:>10.2f} EUR")

        # Notes
        if ligne.get("notes"):
            lines.append(f"  >> {ligne['notes']}")

    lines.append("-" * 42)

    # Totaux
    lines.append(f"{'Total HT':<30}{commande.get('montant_ht', 0):>10.2f} EUR")
    lines.append(f"{'TVA':<30}{commande.get('montant_tva', 0):>10.2f} EUR")
    if commande.get("frais_livraison", 0) > 0:
        lines.append(f"{'Frais livraison':<30}{commande['frais_livraison']:>10.2f} EUR")
    lines.append("=" * 42)
    lines.append(f"{'TOTAL TTC':<30}{commande.get('montant_ttc', 0):>10.2f} EUR")

    # Paiement
    if commande.get("mode_paiement"):
        lines.append(f"Paye par : {commande['mode_paiement'].upper()}")

    lines.append("")
    lines.append("Merci de votre visite !".center(42))
    if siret:
        lines.append(f"SIRET: {siret}".center(42))

    return "\n".join(lines)


def generer_bon_cuisine(commande: dict) -> str:
    """Genere un bon de preparation pour la cuisine."""
    lines = []
    lines.append("*" * 42)
    lines.append(f"BON DE PREPARATION - {commande['numero']}".center(42))
    lines.append("*" * 42)

    mode = "EMPORTER" if commande.get("mode") == "emporter" else "LIVRAISON"
    comptoir = commande.get("comptoir", "").upper()
    lines.append(f"{mode} | {comptoir}")
    if commande.get("creneau_label"):
        lines.append(f"CRENEAU : {commande['creneau_label']}")
    if commande.get("client_nom"):
        lines.append(f"Client : {commande['client_nom']}")
    lines.append("-" * 42)

    for i, ligne in enumerate(commande.get("lignes", []), 1):
        nom_produit = ligne.get("produit_nom", "")
        taille = ligne.get("taille", "")
        qty = ligne.get("quantite", 1)
        if taille:
            nom_produit += f" ({taille})"
        lines.append(f"  {qty}x {nom_produit}")
        for sup in ligne.get("supplements", []):
            lines.append(f"    + {sup.get('nom', '')}")
        if ligne.get("notes"):
            lines.append(f"    >> {ligne['notes']}")

    if commande.get("notes"):
        lines.append("-" * 42)
        lines.append(f"NOTES: {commande['notes']}")

    lines.append("*" * 42)
    return "\n".join(lines)


def generer_ticket_z(data: dict) -> str:
    """Genere un ticket Z (rapport de fin de journee)."""
    lines = []
    lines.append("=" * 42)
    lines.append("TICKET Z - RAPPORT JOURNALIER".center(42))
    lines.append(f"Date : {data.get('date', '')}".center(42))
    lines.append("=" * 42)

    lines.append(f"Nombre de commandes : {data.get('nb_commandes', 0)}")
    lines.append(f"CA TTC : {data.get('ca_ttc', 0):.2f} EUR")
    lines.append(f"CA HT  : {data.get('ca_ht', 0):.2f} EUR")
    lines.append(f"TVA    : {data.get('total_tva', 0):.2f} EUR")
    lines.append("-" * 42)

    lines.append("PAR COMPTOIR :")
    for k, v in data.get("par_comptoir", {}).items():
        lines.append(f"  {k:<20}{v:>10.2f} EUR")

    lines.append("PAR MODE DE PAIEMENT :")
    for k, v in data.get("par_mode_paiement", {}).items():
        lines.append(f"  {k:<20}{v:>10.2f} EUR")

    lines.append("PAR MODE :")
    for k, v in data.get("par_mode", {}).items():
        lines.append(f"  {k:<20}{v:>10.2f} EUR")

    lines.append("=" * 42)
    lines.append(f"Especes : {data.get('total_especes', 0):.2f} EUR")
    lines.append(f"CB      : {data.get('total_cb', 0):.2f} EUR")
    lines.append("=" * 42)

    return "\n".join(lines)
