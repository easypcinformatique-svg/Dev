"""Outils metier que l'agent IA peut appeler : infos garage, stock, planning, demandes."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from store import Store

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


CHAMPS_INTERNES = {"prix_achat", "vendu", "entree_stock"}


class OutilError(Exception):
    """Erreur renvoyee au modele comme tool_result is_error (message lisible)."""


def _strict(schema: dict) -> dict:
    schema.setdefault("additionalProperties", False)
    return schema


TOOLS: list[dict] = [
    {
        "name": "infos_garage",
        "description": "Renvoie les informations du garage AKMS AUTOS : adresse, telephone, email, horaires d'ouverture, prestations atelier avec duree et prix indicatif, services a la vente. A utiliser pour toute question pratique ou tarifaire.",
        "input_schema": _strict({"type": "object", "properties": {}, "required": []}),
    },
    {
        "name": "rechercher_vehicules",
        "description": "Cherche dans le stock de vehicules d'occasion en vente. Tous les filtres sont optionnels ; passer null pour ignorer un filtre. Renvoie au plus 10 vehicules disponibles, du moins cher au plus cher.",
        "input_schema": _strict({
            "type": "object",
            "properties": {
                "marque": {"type": ["string", "null"], "description": "Ex : Peugeot"},
                "modele": {"type": ["string", "null"], "description": "Ex : 208"},
                "carburant": {"type": ["string", "null"], "enum": ["essence", "diesel", "hybride", "electrique", "gpl", None]},
                "boite": {"type": ["string", "null"], "enum": ["manuelle", "automatique", None]},
                "prix_max": {"type": ["integer", "null"], "description": "Budget maximum en euros TTC"},
                "km_max": {"type": ["integer", "null"]},
                "annee_min": {"type": ["integer", "null"]},
                "places_min": {"type": ["integer", "null"]},
            },
            "required": ["marque", "modele", "carburant", "boite", "prix_max", "km_max", "annee_min", "places_min"],
        }),
    },
    {
        "name": "details_vehicule",
        "description": "Renvoie la fiche complete d'un vehicule du stock a partir de sa reference (ex : AK-001).",
        "input_schema": _strict({
            "type": "object",
            "properties": {"ref": {"type": "string"}},
            "required": ["ref"],
        }),
    },
    {
        "name": "creneaux_disponibles",
        "description": "Liste les creneaux libres pour une prestation atelier ou un essai de vehicule, a partir d'une date. Toujours appeler cet outil avant de proposer un horaire au client.",
        "input_schema": _strict({
            "type": "object",
            "properties": {
                "prestation": {"type": "string", "description": "Code prestation renvoye par infos_garage (ex : vidange, revision, essai)"},
                "a_partir_du": {"type": "string", "description": "Date AAAA-MM-JJ"},
                "nb_jours": {"type": "integer", "description": "Nombre de jours a explorer (1 a 7)"},
            },
            "required": ["prestation", "a_partir_du", "nb_jours"],
        }),
    },
    {
        "name": "prendre_rendez_vous",
        "description": "Enregistre un rendez-vous atelier ou un essai. Ne l'appeler qu'apres avoir obtenu l'accord explicite du client sur le creneau ET son nom et son telephone. Le rendez-vous est enregistre 'a confirmer' par le garage.",
        "input_schema": _strict({
            "type": "object",
            "properties": {
                "prestation": {"type": "string"},
                "debut": {"type": "string", "description": "Date et heure AAAA-MM-JJTHH:MM, issue de creneaux_disponibles"},
                "nom": {"type": "string"},
                "telephone": {"type": "string"},
                "email": {"type": ["string", "null"]},
                "vehicule": {"type": ["string", "null"], "description": "Marque/modele du vehicule client, ou reference du vehicule a essayer"},
                "immatriculation": {"type": ["string", "null"]},
                "commentaire": {"type": ["string", "null"]},
            },
            "required": ["prestation", "debut", "nom", "telephone", "email", "vehicule", "immatriculation", "commentaire"],
        }),
    },
    {
        "name": "enregistrer_demande",
        "description": "Transmet une demande a l'equipe AKMS AUTOS qui rappellera le client : devis atelier, estimation de reprise, interet pour un vehicule, financement, ou simple demande de rappel. Exige nom et telephone du client.",
        "input_schema": _strict({
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["devis", "reprise", "achat_vehicule", "financement", "rappel", "autre"]},
                "nom": {"type": "string"},
                "telephone": {"type": "string"},
                "email": {"type": ["string", "null"]},
                "resume": {"type": "string", "description": "Resume clair de la demande pour l'equipe"},
                "vehicule": {"type": ["string", "null"], "description": "Vehicule concerne (marque, modele, annee, km, immatriculation ou reference stock)"},
            },
            "required": ["type", "nom", "telephone", "email", "resume", "vehicule"],
        }),
    },
]
for _t in TOOLS:
    _t["strict"] = True


_TEL_RE = re.compile(r"^\+?[0-9 .\-()]{9,20}$")


def _check_tel(tel: str) -> str:
    tel = (tel or "").strip()
    if not _TEL_RE.match(tel) or sum(c.isdigit() for c in tel) < 9:
        raise OutilError("Numero de telephone invalide : demandez au client de le verifier.")
    return tel


def _plages(horaire: str) -> list[tuple[int, int]]:
    """'08:30-12:00, 14:00-18:30' -> [(510, 720), (840, 1110)] en minutes."""
    if not horaire or horaire.strip().lower() == "ferme":
        return []
    out = []
    for plage in horaire.split(","):
        a, b = plage.strip().split("-")
        ha, ma = map(int, a.split(":"))
        hb, mb = map(int, b.split(":"))
        out.append((ha * 60 + ma, hb * 60 + mb))
    return out


class GarageTools:
    def __init__(self, config_path: Path, stock_path: Path, store: Store,
                 now: Callable[[], datetime] = datetime.now):
        self.config_path = Path(config_path)
        self.stock_path = Path(stock_path)
        self.store = store
        self.now = now

    # Relu a chaque appel : le garage peut modifier les JSON sans redemarrer.
    @property
    def config(self) -> dict:
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    @property
    def stock(self) -> list[dict]:
        return json.loads(self.stock_path.read_text(encoding="utf-8"))

    def _prestation(self, code: str) -> dict:
        for p in self.config["prestations_atelier"]:
            if p["code"] == code:
                return p
        codes = ", ".join(p["code"] for p in self.config["prestations_atelier"])
        raise OutilError(f"Prestation inconnue '{code}'. Codes valides : {codes}")

    # --- dispatch ----------------------------------------------------------
    def run(self, name: str, args: dict[str, Any]) -> str:
        fn = getattr(self, f"t_{name}", None)
        if fn is None:
            raise OutilError(f"Outil inconnu : {name}")
        return json.dumps(fn(**args), ensure_ascii=False)

    # --- outils ------------------------------------------------------------
    def t_infos_garage(self) -> dict:
        cfg = {k: v for k, v in self.config.items() if not k.startswith("_") and k != "planning"}
        return cfg

    def t_rechercher_vehicules(self, marque=None, modele=None, carburant=None, boite=None,
                               prix_max=None, km_max=None, annee_min=None, places_min=None) -> dict:
        def ok(v: dict) -> bool:
            if not v.get("disponible", True) or v.get("vendu"):
                return False
            if marque and marque.lower() not in v["marque"].lower():
                return False
            if modele and modele.lower() not in v["modele"].lower():
                return False
            if carburant and v["carburant"] != carburant:
                return False
            if boite and v["boite"] != boite:
                return False
            if prix_max is not None and v["prix"] > prix_max:
                return False
            if km_max is not None and v["km"] > km_max:
                return False
            if annee_min is not None and v["annee"] < annee_min:
                return False
            if places_min is not None and v.get("places", 5) < places_min:
                return False
            return True

        res = sorted((v for v in self.stock if ok(v)), key=lambda v: v["prix"])
        champs = ("ref", "marque", "modele", "version", "annee", "km", "carburant", "boite", "prix")
        return {
            "nb_resultats": len(res),
            "vehicules": [{k: v[k] for k in champs} for v in res[:10]],
        }

    def t_details_vehicule(self, ref: str) -> dict:
        for v in self.stock:
            if v["ref"].lower() == ref.strip().lower():
                if v.get("vendu"):
                    raise OutilError(f"Le vehicule {ref} a ete vendu.")
                return {k: val for k, val in v.items() if not k.startswith("_") and k not in CHAMPS_INTERNES}
        raise OutilError(f"Aucun vehicule avec la reference {ref}.")

    def _creneaux_jour(self, jour: date, duree: int, exclure_rdv: int | None = None) -> list[datetime]:
        cfg = self.config
        planning = cfg.get("planning", {})
        pas = int(planning.get("pas_creneau_min", 30))
        postes = int(planning.get("postes_atelier", 1))
        plages = _plages(cfg["horaires"].get(JOURS[jour.weekday()], "ferme"))
        maintenant = self.now()
        debut_jour = datetime.combine(jour, datetime.min.time())
        pris = [r for r in self.store.rdv_entre(debut_jour, debut_jour + timedelta(days=1)) if r["id"] != exclure_rdv]
        libres = []
        for a, b in plages:
            m = a
            while m + duree <= b:
                debut = debut_jour + timedelta(minutes=m)
                fin = debut + timedelta(minutes=duree)
                # au moins 2 h de prevenance
                if debut >= maintenant + timedelta(hours=2):
                    occupes = sum(
                        1 for r in pris
                        if datetime.fromisoformat(r["debut"]) < fin and datetime.fromisoformat(r["fin"]) > debut
                    )
                    if occupes < postes:
                        libres.append(debut)
                m += pas
        return libres

    def t_creneaux_disponibles(self, prestation: str, a_partir_du: str, nb_jours: int) -> dict:
        p = self._prestation(prestation)
        try:
            depart = date.fromisoformat(a_partir_du)
        except ValueError:
            raise OutilError("Date invalide, format attendu AAAA-MM-JJ.")
        aujourd_hui = self.now().date()
        horizon = aujourd_hui + timedelta(days=int(self.config.get("planning", {}).get("jours_reservables_a_l_avance", 30)))
        depart = max(depart, aujourd_hui)
        nb_jours = max(1, min(int(nb_jours), 7))
        jours = []
        for i in range(nb_jours):
            j = depart + timedelta(days=i)
            if j > horizon:
                break
            libres = self._creneaux_jour(j, p["duree_min"])
            if libres:
                jours.append({
                    "date": j.isoformat(),
                    "jour": JOURS[j.weekday()],
                    "creneaux": [d.strftime("%Y-%m-%dT%H:%M") for d in libres],
                })
        return {"prestation": p["libelle"], "duree_min": p["duree_min"], "jours": jours,
                "remarque": None if jours else "Aucun creneau libre sur cette periode."}

    def t_prendre_rendez_vous(self, prestation: str, debut: str, nom: str, telephone: str,
                              email=None, vehicule=None, immatriculation=None, commentaire=None) -> dict:
        p = self._prestation(prestation)
        if not nom.strip():
            raise OutilError("Nom du client manquant.")
        telephone = _check_tel(telephone)
        try:
            d = datetime.fromisoformat(debut)
        except ValueError:
            raise OutilError("Horaire invalide, format attendu AAAA-MM-JJTHH:MM.")
        if d not in self._creneaux_jour(d.date(), p["duree_min"]):
            raise OutilError("Ce creneau n'est plus disponible : rappelez creneaux_disponibles et proposez-en un autre.")
        rid = self.store.ajouter_rdv(
            debut=d.isoformat(timespec="minutes"),
            fin=(d + timedelta(minutes=p["duree_min"])).isoformat(timespec="minutes"),
            prestation=p["code"], nom=nom.strip(), telephone=telephone, email=email,
            vehicule=vehicule, immatriculation=immatriculation, commentaire=commentaire,
        )
        return {"ok": True, "numero_rdv": rid, "prestation": p["libelle"],
                "debut": d.strftime("%Y-%m-%dT%H:%M"), "statut": "a_confirmer",
                "message": "Rendez-vous enregistre ; le garage le confirmera par telephone ou SMS."}

    def t_enregistrer_demande(self, type: str, nom: str, telephone: str, resume: str,
                              email=None, vehicule=None) -> dict:
        if not nom.strip():
            raise OutilError("Nom du client manquant.")
        telephone = _check_tel(telephone)
        did = self.store.ajouter_demande(type, nom.strip(), telephone, email,
                                         {"resume": resume, "vehicule": vehicule})
        return {"ok": True, "numero_demande": did,
                "message": "Demande transmise a l'equipe, qui rappellera le client."}
