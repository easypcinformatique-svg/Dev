"""Outils de gestion interne (reserves a l'equipe AKMS AUTOS) : planning, demandes, stock, ventes, tableau de bord."""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from datetime import date, datetime, timedelta
from typing import Any

from tools import JOURS, GarageTools, OutilError, _strict

STATUTS_RDV = ["a_confirmer", "confirme", "termine", "annule", "absent"]
STATUTS_DEMANDE = ["nouveau", "en_cours", "traite", "perdu"]
TYPES_DEMANDE = ["devis", "reprise", "achat_vehicule", "financement", "rappel", "autre"]
CHAMPS_GARAGE = ["adresse", "telephone", "email", "site_web"] + [f"horaires.{j}" for j in JOURS]

_NULL_STR = {"type": ["string", "null"]}
_NULL_INT = {"type": ["integer", "null"]}


def _enum_null(valeurs: list[str]) -> dict:
    return {"type": ["string", "null"], "enum": [*valeurs, None]}


GESTION_TOOLS: list[dict] = [
    {
        "name": "tableau_de_bord",
        "description": "Synthese de l'activite sur les N derniers jours : rendez-vous par statut, RDV du jour et de demain, demandes par statut et type, demandes non traitees, ventes et chiffre d'affaires vehicules, marge sur prix affiche, valeur et anciennete du stock.",
        "input_schema": _strict({
            "type": "object",
            "properties": {"jours": {"type": "integer", "description": "Periode en jours (ex : 7, 30)"}},
            "required": ["jours"],
        }),
    },
    {
        "name": "planning",
        "description": "Liste les rendez-vous (atelier et essais) entre deux dates incluses, tous statuts, avec coordonnees client.",
        "input_schema": _strict({
            "type": "object",
            "properties": {
                "du": {"type": "string", "description": "AAAA-MM-JJ"},
                "au": {"type": "string", "description": "AAAA-MM-JJ (inclus)"},
            },
            "required": ["du", "au"],
        }),
    },
    {
        "name": "modifier_rendez_vous",
        "description": "Change le statut d'un rendez-vous, le deplace et/ou ajoute une note interne. Pour un deplacement, le creneau est verifie (horaires, postes libres) sauf si forcer=true.",
        "input_schema": _strict({
            "type": "object",
            "properties": {
                "numero": {"type": "integer"},
                "statut": _enum_null(STATUTS_RDV),
                "nouveau_debut": {**_NULL_STR, "description": "AAAA-MM-JJTHH:MM"},
                "note": _NULL_STR,
                "forcer": {"type": "boolean", "description": "Ignorer la verification du creneau (demande explicite de l'utilisateur)"},
            },
            "required": ["numero", "statut", "nouveau_debut", "note", "forcer"],
        }),
    },
    {
        "name": "creer_rendez_vous",
        "description": "Cree un rendez-vous saisi par l'equipe (client au telephone ou au comptoir). Statut confirme par defaut.",
        "input_schema": _strict({
            "type": "object",
            "properties": {
                "prestation": {"type": "string"},
                "debut": {"type": "string", "description": "AAAA-MM-JJTHH:MM"},
                "nom": {"type": "string"},
                "telephone": {"type": "string"},
                "vehicule": _NULL_STR,
                "immatriculation": _NULL_STR,
                "note": _NULL_STR,
                "forcer": {"type": "boolean"},
            },
            "required": ["prestation", "debut", "nom", "telephone", "vehicule", "immatriculation", "note", "forcer"],
        }),
    },
    {
        "name": "lister_demandes",
        "description": "Liste les demandes clients (devis, reprise, achat, financement, rappel) avec filtres optionnels (null = pas de filtre).",
        "input_schema": _strict({
            "type": "object",
            "properties": {"statut": _enum_null(STATUTS_DEMANDE), "type": _enum_null(TYPES_DEMANDE)},
            "required": ["statut", "type"],
        }),
    },
    {
        "name": "traiter_demande",
        "description": "Met a jour le statut d'une demande client et/ou y ajoute une note interne (ex : 'rappele, devis envoye 350 EUR').",
        "input_schema": _strict({
            "type": "object",
            "properties": {"numero": {"type": "integer"}, "statut": _enum_null(STATUTS_DEMANDE), "note": _NULL_STR},
            "required": ["numero", "statut", "note"],
        }),
    },
    {
        "name": "stock_lister",
        "description": "Liste tout le stock de vehicules avec prix, km, disponibilite et date d'entree.",
        "input_schema": _strict({
            "type": "object",
            "properties": {"inclure_vendus": {"type": "boolean"}},
            "required": ["inclure_vendus"],
        }),
    },
    {
        "name": "stock_ajouter",
        "description": "Ajoute un vehicule au stock en vente. La reference est attribuee automatiquement.",
        "input_schema": _strict({
            "type": "object",
            "properties": {
                "marque": {"type": "string"}, "modele": {"type": "string"}, "version": {"type": "string"},
                "annee": {"type": "integer"}, "km": {"type": "integer"},
                "carburant": {"type": "string", "enum": ["essence", "diesel", "hybride", "electrique", "gpl"]},
                "boite": {"type": "string", "enum": ["manuelle", "automatique"]},
                "prix": {"type": "integer", "description": "Prix affiche TTC en euros"},
                "prix_achat": {**_NULL_INT, "description": "Prix d'achat / de reprise (interne, jamais montre aux clients)"},
                "couleur": _NULL_STR, "places": _NULL_INT, "critair": _NULL_INT,
                "options": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["marque", "modele", "version", "annee", "km", "carburant", "boite", "prix",
                         "prix_achat", "couleur", "places", "critair", "options"],
        }),
    },
    {
        "name": "stock_modifier",
        "description": "Modifie un vehicule du stock (prix, km, disponibilite, options, prix d'achat). Les champs a null ne changent pas.",
        "input_schema": _strict({
            "type": "object",
            "properties": {
                "ref": {"type": "string"}, "prix": _NULL_INT, "km": _NULL_INT, "prix_achat": _NULL_INT,
                "disponible": {"type": ["boolean", "null"]},
                "options": {"type": ["array", "null"], "items": {"type": "string"}},
            },
            "required": ["ref", "prix", "km", "prix_achat", "disponible", "options"],
        }),
    },
    {
        "name": "stock_vendre",
        "description": "Enregistre la vente d'un vehicule du stock : le retire de la vente et inscrit la vente (prix reel) pour le chiffre d'affaires.",
        "input_schema": _strict({
            "type": "object",
            "properties": {
                "ref": {"type": "string"}, "prix_vente": {"type": "integer"},
                "client": _NULL_STR, "date_vente": {**_NULL_STR, "description": "AAAA-MM-JJ, aujourd'hui si null"},
                "note": _NULL_STR,
            },
            "required": ["ref", "prix_vente", "client", "date_vente", "note"],
        }),
    },
    {
        "name": "modifier_infos_garage",
        "description": "Modifie une information publique du garage, vue par l'assistant clients : adresse, telephone, email, site_web ou horaires d'un jour (format '08:30-12:00, 14:00-18:30' ou 'ferme').",
        "input_schema": _strict({
            "type": "object",
            "properties": {"champ": {"type": "string", "enum": CHAMPS_GARAGE}, "valeur": {"type": "string"}},
            "required": ["champ", "valeur"],
        }),
    },
    {
        "name": "modifier_prestation",
        "description": "Modifie le prix indicatif et/ou la duree (minutes) d'une prestation atelier. null = inchange.",
        "input_schema": _strict({
            "type": "object",
            "properties": {"code": {"type": "string"}, "prix_indicatif": _NULL_STR, "duree_min": _NULL_INT},
            "required": ["code", "prix_indicatif", "duree_min"],
        }),
    },
]
for _t in GESTION_TOOLS:
    _t["strict"] = True

ACTIONS_ECRITURE = {"modifier_rendez_vous", "creer_rendez_vous", "traiter_demande", "stock_ajouter",
                    "stock_modifier", "stock_vendre", "modifier_infos_garage", "modifier_prestation"}

_HORAIRE_RE = re.compile(r"^(ferme|\d{2}:\d{2}-\d{2}:\d{2}(, ?\d{2}:\d{2}-\d{2}:\d{2})*)$")
_ECRITURE_LOCK = threading.Lock()


def _ecrire_json(path, data) -> None:
    """Ecriture atomique : jamais de fichier a moitie ecrit lu par l'assistant clients."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


class GestionTools(GarageTools):
    def run(self, name: str, args: dict[str, Any]) -> str:
        fn = getattr(self, f"g_{name}", None)
        if fn is None:
            raise OutilError(f"Outil inconnu : {name}")
        res = fn(**args)
        if name in ACTIONS_ECRITURE:
            self.store.journaliser(name, args)
        return json.dumps(res, ensure_ascii=False)

    # --- tableau de bord ---------------------------------------------------
    def g_tableau_de_bord(self, jours: int) -> dict:
        jours = max(1, min(int(jours), 366))
        now = self.now()
        depuis = (now - timedelta(days=jours)).date().isoformat()
        aujourd_hui = now.date()
        demain = aujourd_hui + timedelta(days=1)
        rdv_stats = self.store.compter(
            "SELECT statut, COUNT(*) n FROM rendez_vous WHERE debut >= ? GROUP BY statut", (depuis,))
        rdv_jour = self.store.rdv_periode(aujourd_hui.isoformat(), (demain + timedelta(days=1)).isoformat())
        dem_stats = self.store.compter(
            "SELECT type, statut, COUNT(*) n FROM demandes WHERE cree_le >= ? GROUP BY type, statut", (depuis,))
        non_traitees = self.store.demandes_filtre("nouveau", None, 100)
        ventes = self.store.ventes_depuis(depuis)
        ca = sum(v["prix_vente"] for v in ventes)
        remise = sum((v["prix_affiche"] or v["prix_vente"]) - v["prix_vente"] for v in ventes)
        stock = [v for v in self.stock if v.get("disponible", True)]
        ages = []
        for v in stock:
            if v.get("entree_stock"):
                ages.append((aujourd_hui - date.fromisoformat(v["entree_stock"])).days)
        a_confirmer = [r for r in self.store.rdv_periode(aujourd_hui.isoformat(), "9999")
                       if r["statut"] == "a_confirmer"]
        return {
            "periode": f"{jours} derniers jours (depuis {depuis})",
            "rendez_vous_par_statut": {r["statut"]: r["n"] for r in rdv_stats},
            "rendez_vous_aujourd_hui_et_demain": [
                {k: r[k] for k in ("id", "debut", "prestation", "nom", "telephone", "vehicule", "statut")} for r in rdv_jour],
            "rendez_vous_a_confirmer": len(a_confirmer),
            "demandes_par_type_et_statut": dem_stats,
            "demandes_non_traitees": [
                {"id": d["id"], "cree_le": d["cree_le"], "type": d["type"], "nom": d["nom"],
                 "telephone": d["telephone"], "resume": d["details"].get("resume")} for d in non_traitees],
            "ventes": {"nombre": len(ventes), "chiffre_affaires": ca, "remises_accordees": remise,
                       "detail": [{k: v[k] for k in ("date_vente", "ref", "vehicule", "prix_vente")} for v in ventes]},
            "stock": {
                "vehicules_en_vente": len(stock),
                "valeur_affichee": sum(v["prix"] for v in stock),
                "anciennete_moyenne_jours": round(sum(ages) / len(ages)) if ages else None,
                "plus_de_60_jours": [v["ref"] for v in stock
                                     if v.get("entree_stock") and (aujourd_hui - date.fromisoformat(v["entree_stock"])).days > 60],
            },
        }

    # --- rendez-vous -------------------------------------------------------
    def g_planning(self, du: str, au: str) -> dict:
        try:
            d1, d2 = date.fromisoformat(du), date.fromisoformat(au)
        except ValueError:
            raise OutilError("Dates invalides, format AAAA-MM-JJ.")
        if (d2 - d1).days > 62:
            raise OutilError("Periode trop longue (62 jours maximum).")
        rdv = self.store.rdv_periode(d1.isoformat(), (d2 + timedelta(days=1)).isoformat())
        return {"nombre": len(rdv), "rendez_vous": rdv}

    def _verifier_creneau(self, code: str, debut: datetime, forcer: bool, exclure: int | None = None) -> dict:
        p = self._prestation(code)
        if not forcer and debut not in self._creneaux_jour(debut.date(), p["duree_min"], exclure):
            raise OutilError("Creneau indisponible (ferme, complet ou trop proche). Proposez un autre horaire, "
                             "ou forcer=true si l'utilisateur le demande expressement.")
        return p

    def g_modifier_rendez_vous(self, numero: int, statut=None, nouveau_debut=None, note=None, forcer=False) -> dict:
        rdv = self.store.get("rendez_vous", numero)
        if rdv is None:
            raise OutilError(f"Rendez-vous n{numero} introuvable.")
        champs: dict[str, Any] = {}
        if statut:
            champs["statut"] = statut
        if nouveau_debut:
            try:
                d = datetime.fromisoformat(nouveau_debut)
            except ValueError:
                raise OutilError("Horaire invalide, format AAAA-MM-JJTHH:MM.")
            p = self._verifier_creneau(rdv["prestation"], d, forcer, exclure=numero)
            champs["debut"] = d.isoformat(timespec="minutes")
            champs["fin"] = (d + timedelta(minutes=p["duree_min"])).isoformat(timespec="minutes")
        if note:
            champs["note"] = f"{rdv['note']}\n{note}" if rdv.get("note") else note
        if not champs:
            raise OutilError("Rien a modifier.")
        self.store.maj("rendez_vous", numero, **champs)
        return {"ok": True, "rendez_vous": self.store.get("rendez_vous", numero)}

    def g_creer_rendez_vous(self, prestation: str, debut: str, nom: str, telephone: str,
                            vehicule=None, immatriculation=None, note=None, forcer=False) -> dict:
        try:
            d = datetime.fromisoformat(debut)
        except ValueError:
            raise OutilError("Horaire invalide, format AAAA-MM-JJTHH:MM.")
        p = self._verifier_creneau(prestation, d, forcer)
        rid = self.store.ajouter_rdv(
            debut=d.isoformat(timespec="minutes"),
            fin=(d + timedelta(minutes=p["duree_min"])).isoformat(timespec="minutes"),
            prestation=p["code"], nom=nom.strip(), telephone=telephone.strip(), email=None,
            vehicule=vehicule, immatriculation=immatriculation, commentaire=None, note=note,
            statut="confirme",
        )
        return {"ok": True, "numero_rdv": rid}

    # --- demandes ----------------------------------------------------------
    def g_lister_demandes(self, statut=None, type=None) -> dict:
        d = self.store.demandes_filtre(statut, type)
        return {"nombre": len(d), "demandes": d}

    def g_traiter_demande(self, numero: int, statut=None, note=None) -> dict:
        dem = self.store.get("demandes", numero)
        if dem is None:
            raise OutilError(f"Demande n{numero} introuvable.")
        champs: dict[str, Any] = {}
        if statut:
            champs["statut"] = statut
        if note:
            horo = self.now().strftime("%d/%m %H:%M")
            champs["note"] = f"{dem['note']}\n[{horo}] {note}" if dem.get("note") else f"[{horo}] {note}"
        if not champs:
            raise OutilError("Rien a modifier.")
        self.store.maj("demandes", numero, **champs)
        return {"ok": True, "demande": self.store.get("demandes", numero)}

    # --- stock -------------------------------------------------------------
    def _trouver(self, stock: list[dict], ref: str) -> dict:
        for v in stock:
            if v["ref"].lower() == ref.strip().lower():
                return v
        raise OutilError(f"Aucun vehicule avec la reference {ref}.")

    def g_stock_lister(self, inclure_vendus: bool) -> dict:
        stock = [v for v in self.stock if inclure_vendus or not v.get("vendu")]
        return {"nombre": len(stock), "vehicules": stock}

    def g_stock_ajouter(self, **v) -> dict:
        with _ECRITURE_LOCK:
            stock = self.stock
            nums = [int(m.group(1)) for x in stock if (m := re.match(r"AK-(\d+)$", x["ref"]))]
            ref = f"AK-{(max(nums) + 1) if nums else 1:03d}"
            vehicule = {"ref": ref, **{k: val for k, val in v.items() if val is not None},
                        "disponible": True, "entree_stock": self.now().date().isoformat()}
            vehicule.setdefault("places", 5)
            stock.append(vehicule)
            _ecrire_json(self.stock_path, stock)
        return {"ok": True, "ref": ref, "vehicule": vehicule}

    def g_stock_modifier(self, ref: str, prix=None, km=None, prix_achat=None, disponible=None, options=None) -> dict:
        with _ECRITURE_LOCK:
            stock = self.stock
            v = self._trouver(stock, ref)
            for k, val in (("prix", prix), ("km", km), ("prix_achat", prix_achat),
                           ("disponible", disponible), ("options", options)):
                if val is not None:
                    v[k] = val
            _ecrire_json(self.stock_path, stock)
        return {"ok": True, "vehicule": v}

    def g_stock_vendre(self, ref: str, prix_vente: int, client=None, date_vente=None, note=None) -> dict:
        jour = date_vente or self.now().date().isoformat()
        try:
            date.fromisoformat(jour)
        except ValueError:
            raise OutilError("Date de vente invalide, format AAAA-MM-JJ.")
        with _ECRITURE_LOCK:
            stock = self.stock
            v = self._trouver(stock, ref)
            if v.get("vendu"):
                raise OutilError(f"{v['ref']} est deja enregistre comme vendu.")
            v["disponible"] = False
            v["vendu"] = True
            _ecrire_json(self.stock_path, stock)
        vid = self.store.ajouter_vente(
            date_vente=jour, ref=v["ref"], vehicule=f"{v['marque']} {v['modele']} {v.get('version', '')}".strip(),
            prix_affiche=v.get("prix"), prix_vente=int(prix_vente), client=client, note=note)
        marge = int(prix_vente) - v["prix_achat"] if v.get("prix_achat") is not None else None
        return {"ok": True, "numero_vente": vid, "ref": v["ref"], "prix_vente": prix_vente,
                "remise_sur_prix_affiche": (v.get("prix") or prix_vente) - int(prix_vente), "marge_brute": marge}

    # --- configuration -----------------------------------------------------
    def g_modifier_infos_garage(self, champ: str, valeur: str) -> dict:
        valeur = valeur.strip()
        with _ECRITURE_LOCK:
            cfg = self.config
            if champ.startswith("horaires."):
                jour = champ.split(".", 1)[1]
                if not _HORAIRE_RE.match(valeur.lower()):
                    raise OutilError("Format d'horaire attendu : '08:30-12:00, 14:00-18:30' ou 'ferme'.")
                ancien = cfg["horaires"].get(jour)
                cfg["horaires"][jour] = valeur.lower() if valeur.lower() == "ferme" else valeur
            else:
                ancien = cfg.get(champ)
                cfg[champ] = valeur
            _ecrire_json(self.config_path, cfg)
        return {"ok": True, "champ": champ, "ancienne_valeur": ancien, "nouvelle_valeur": valeur}

    def g_modifier_prestation(self, code: str, prix_indicatif=None, duree_min=None) -> dict:
        with _ECRITURE_LOCK:
            cfg = self.config
            for p in cfg["prestations_atelier"]:
                if p["code"] == code:
                    if prix_indicatif is not None:
                        p["prix_indicatif"] = prix_indicatif
                    if duree_min is not None:
                        if not 15 <= int(duree_min) <= 480:
                            raise OutilError("Duree entre 15 et 480 minutes.")
                        p["duree_min"] = int(duree_min)
                    _ecrire_json(self.config_path, cfg)
                    return {"ok": True, "prestation": p}
        raise OutilError(f"Prestation inconnue '{code}'.")
