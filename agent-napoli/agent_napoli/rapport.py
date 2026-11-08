"""Rapport du matin (9h), envoyé aux deux gérants.

Ordre validé dans le plan : alertes, ventes de la veille, administratif à
traiter, validations en attente. Les avis et réseaux arrivent en phase 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from html import escape

from .factures import Echeance, Resultat
from .obligations import Obligation
from .tri_mails import PREFIXE_RAPPORT, MailImportant
from .z_laddition import Alerte, Z, _eur
from .z_pdf import DetailZ

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
         "septembre", "octobre", "novembre", "décembre"]


def jour_long(d: date) -> str:
    return f"{_JOURS[d.weekday()]} {d.day} {_MOIS[d.month - 1]}"


@dataclass
class DonneesRapport:
    aujourdhui: date
    veille: date
    z: Z | None = None
    etat_z: str = "manquant"     # recu, manquant, ferme, deja_traite
    detail_z: DetailZ | None = None
    top: list[tuple[str, float]] = field(default_factory=list)
    ca_semaine_precedente: float | None = None
    alertes: list[Alerte] = field(default_factory=list)
    factures: list[Resultat] = field(default_factory=list)
    echeances: list[Echeance] = field(default_factory=list)
    obligations: list[Obligation] = field(default_factory=list)
    mails_importants: list[MailImportant] = field(default_factory=list)
    nb_brouillons: int = 0
    comptable: str | None = None
    banque: list[str] = field(default_factory=list)     # phrases déjà en HTML sûr
    erreurs: list[str] = field(default_factory=list)
    lien_classeur: str = ""


def toutes_alertes(d: DonneesRapport) -> list[Alerte]:
    """Alertes de caisse + Z manquant + paiements et échéances légales à J-1 ou en retard."""
    alertes = list(d.alertes)
    if d.etat_z == "manquant":
        alertes.insert(0, Alerte("haute", "Z manquant",
                                 f"Aucun Z reçu pour le {jour_long(d.veille)}. Le service a-t-il été clôturé dans L'Addition ?"))
    for ech in d.echeances:
        if ech.jours_restants(d.aujourdhui) <= 1:
            alertes.append(Alerte("haute", "Facture à payer",
                                  f"{ech.fournisseur} — {ech.montant} € — {_quand(ech.jours_restants(d.aujourdhui))}"))
    for o in d.obligations:
        if o.jours_restants(d.aujourdhui) <= 1:
            alertes.append(Alerte("haute", "Échéance légale", f"{o.libelle} — {_quand(o.jours_restants(d.aujourdhui))}"))
    return sorted(alertes, key=lambda a: a.gravite != "haute")


def objet(d: DonneesRapport) -> str:
    hautes = sum(1 for a in toutes_alertes(d) if a.gravite == "haute")
    alerte = f" — {hautes} alerte{'s' if hautes > 1 else ''}" if hautes else ""
    return f"{PREFIXE_RAPPORT} Rapport du {jour_long(d.aujourdhui)}{alerte}"


def _quand(jours: int) -> str:
    if jours < 0:
        return f"en retard de {-jours} j"
    return {0: "aujourd'hui", 1: "demain"}.get(jours, f"dans {jours} j")


def _section(titre: str, contenu: str) -> str:
    return (f'<h2 style="font-size:17px;margin:24px 0 8px;border-bottom:2px solid #c0392b;'
            f'padding-bottom:4px">{escape(titre)}</h2>{contenu}')


def _liste(items: list[str]) -> str:
    return "<ul style='padding-left:20px;margin:4px 0'>" + "".join(f"<li style='margin:4px 0'>{i}</li>" for i in items) + "</ul>"


def construire(d: DonneesRapport) -> str:
    e = escape
    parties = [f"<p style='color:#555'>Rapport du {e(jour_long(d.aujourdhui))}, "
               f"ventes du {e(jour_long(d.veille))}.</p>"]

    # 1. Alertes
    alertes = toutes_alertes(d)
    if alertes:
        items = [f"<b style='color:{'#c0392b' if a.gravite == 'haute' else '#555'}'>{e(a.titre)}</b> : {e(a.detail)}"
                 for a in alertes]
        parties.append(_section("Alertes", _liste(items)))
    else:
        parties.append(_section("Alertes", "<p>Rien à signaler.</p>"))

    # 2. Ventes de la veille
    if d.z:
        z = d.z
        comparaison = ""
        if d.ca_semaine_precedente:
            ecart = (z.ca_ttc - d.ca_semaine_precedente) / d.ca_semaine_precedente * 100
            comparaison = f" ({ecart:+.0f} % par rapport à {_JOURS[z.jour.weekday()]} dernier)".replace(".", ",")
        dz = d.detail_z
        tickets = f"{dz.tickets}" if dz and dz.tickets else f"environ {z.tickets}"
        lignes = [
            f"CA TTC : <b>{_eur(z.ca_ttc)}</b>{e(comparaison)} — HT : {_eur(z.ca_ht)}",
            f"Tickets : {tickets} — ticket moyen : {_eur(z.ticket_moyen)}",
            f"Offerts : {_eur(z.offerts)} — remises : {_eur(z.remises)} — annulations après ticket : {_eur(z.annulations)}",
        ]
        if dz and dz.salles:
            total = sum(dz.salles.values()) or 1
            lignes.append(" — ".join(f"{e(s)} : {_eur(m)} ({m / total * 100:.0f} %)" for s, m in dz.salles.items()))
        if dz and dz.reglements:
            lignes.append("Paiements : " + " — ".join(
                f"{e(mode)} {_eur(m)} ({n})" for mode, (n, m) in dz.reglements.items()))
        if d.top:
            lignes.append("Top pizzas : " + ", ".join(f"{e(p)} ({q:g})" for p, q in d.top))
        parties.append(_section("Ventes de la veille", _liste(lignes)))
    elif d.etat_z == "ferme":
        parties.append(_section("Ventes de la veille", "<p>Jour de fermeture.</p>"))
    elif d.etat_z == "deja_traite":
        parties.append(_section("Ventes de la veille", "<p>Z déjà traité lors d'un passage précédent (voir le tableur).</p>"))

    # 3. Administratif à traiter
    admin = []
    for r in d.factures:
        couleur = {"classée": "#27ae60", "doublon": "#888", "pas une facture": "#888"}.get(r.statut, "#c0392b")
        admin.append(f"Facture <span style='color:{couleur}'>{e(r.statut)}</span> : {e(r.detail)}")
    for ech in d.echeances:
        if ech.jours_restants(d.aujourdhui) > 1:
            admin.append(f"À payer {_quand(ech.jours_restants(d.aujourdhui))} : {e(ech.fournisseur)} — {e(str(ech.montant))} €")
    for o in d.obligations:
        if 1 < o.jours_restants(d.aujourdhui) <= 7:
            admin.append(f"Échéance {_quand(o.jours_restants(d.aujourdhui))} : {e(o.libelle)}")
    for m in d.mails_importants:
        detail = f" → {e(m.action)}" if m.action else ""
        admin.append(f"Mail de {e(m.expediteur)} : <i>{e(m.objet)}</i> — {e(m.resume)}{detail}")
    if d.comptable:
        admin.append(e(d.comptable))
    admin += d.banque
    parties.append(_section("Administratif à traiter", _liste(admin) if admin else "<p>Rien de nouveau.</p>"))

    # 4. Validations en attente
    if d.nb_brouillons:
        parties.append(_section("Validations en attente", (
            f"<p>{d.nb_brouillons} brouillon(s) attendent dans Gmail (dossier Brouillons). "
            "Relisez, complétez les [À COMPLÉTER], puis envoyez ou supprimez.</p>")))

    if d.erreurs:
        parties.append(_section("Problèmes rencontrés par l'agent", _liste([e(x) for x in d.erreurs])))

    pied = (f"<p style='color:#888;font-size:12px;margin-top:24px'>Agent Pizza Napoli. "
            + (f"<a href='{e(d.lien_classeur)}'>Tableur de suivi</a>. " if d.lien_classeur else "")
            + "Pour arrêter l'agent : variable AGENT_NAPOLI_ACTIF à false dans GitHub.</p>")
    return ("<div style='font-family:Arial,sans-serif;max-width:640px;color:#222;font-size:14px'>"
            f"<h1 style='font-size:20px;color:#c0392b'>Pizza Napoli — {e(jour_long(d.aujourdhui))}</h1>"
            + "".join(parties) + pied + "</div>")
