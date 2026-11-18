import json
import os
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["AKMS_NO_AUTOSTART"] = "1"

from agent import AkmsAgent  # noqa: E402
from store import Store  # noqa: E402
from tools import TOOLS, GarageTools, OutilError  # noqa: E402

# Mercredi 2026-11-04 08:00
NOW = datetime(2026, 11, 4, 8, 0)


@pytest.fixture
def tools():
    return GarageTools(ROOT / "config" / "garage.json", ROOT / "data" / "vehicules.json",
                       Store(":memory:"), now=lambda: NOW)


def test_schemas_strict():
    for t in TOOLS:
        s = t["input_schema"]
        assert t["strict"] is True and s["additionalProperties"] is False
        assert set(s["required"]) == set(s["properties"])


def test_recherche_filtre_et_tri(tools):
    r = json.loads(tools.run("rechercher_vehicules", {
        "marque": None, "modele": None, "carburant": "diesel", "boite": None,
        "prix_max": 18000, "km_max": None, "annee_min": None, "places_min": None}))
    refs = [v["ref"] for v in r["vehicules"]]
    assert refs == ["AK-005", "AK-003", "AK-006"]  # tri prix, AK-007 indisponible exclu


def test_infos_garage_masque_champs_internes(tools):
    r = json.loads(tools.run("infos_garage", {}))
    assert "_a_completer" not in r and "planning" not in r and r["nom"] == "AKMS AUTOS"


def test_creneaux_respectent_horaires_et_prevenance(tools):
    r = json.loads(tools.run("creneaux_disponibles", {"prestation": "vidange", "a_partir_du": "2026-11-04", "nb_jours": 7}))
    jours = {j["date"]: j for j in r["jours"]}
    assert "2026-11-08" not in jours  # dimanche ferme
    mer = jours["2026-11-04"]["creneaux"]
    assert mer[0] == "2026-11-04T10:00"  # 2 h de prevenance
    assert "2026-11-04T11:00" in mer and "2026-11-04T11:30" not in mer  # 60 min avant 12:00
    sam = jours["2026-11-07"]["creneaux"]
    assert sam == ["2026-11-07T09:00", "2026-11-07T09:30", "2026-11-07T10:00", "2026-11-07T10:30", "2026-11-07T11:00"]


def test_rdv_capacite_postes(tools):
    args = {"prestation": "vidange", "debut": "2026-11-05T09:00", "nom": "Dupont", "telephone": "06 12 34 56 78",
            "email": None, "vehicule": "Clio", "immatriculation": None, "commentaire": None}
    assert json.loads(tools.run("prendre_rendez_vous", args))["ok"]
    assert json.loads(tools.run("prendre_rendez_vous", {**args, "nom": "Martin"}))["ok"]  # 2 postes
    with pytest.raises(OutilError):
        tools.run("prendre_rendez_vous", {**args, "nom": "Durand"})
    with pytest.raises(OutilError):
        tools.run("prendre_rendez_vous", {**args, "debut": "2026-11-05T09:00", "telephone": "abc"})


def test_demande_enregistree(tools):
    r = json.loads(tools.run("enregistrer_demande", {"type": "reprise", "nom": "Ali", "telephone": "+33 6 11 22 33 44",
                                                       "email": None, "resume": "Estimation", "vehicule": "308 2017 120000 km"}))
    assert r["ok"]
    d = tools.store.lister("demandes")[0]
    assert d["type"] == "reprise" and d["details"]["vehicule"].startswith("308")


# --- boucle agent avec client factice --------------------------------------
class FakeClient:
    def __init__(self, reponses):
        self.reponses = list(reponses)
        self.appels = []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kw):
        self.appels.append({**kw, "messages": list(kw["messages"])})
        return self.reponses.pop(0)


def txt(t):
    return NS(type="text", text=t)


def test_boucle_outils(tools):
    fake = FakeClient([
        NS(stop_reason="tool_use", content=[txt("Je regarde."), NS(type="tool_use", id="tu1", name="infos_garage", input={})]),
        NS(stop_reason="end_turn", content=[txt("Nous sommes ouverts du lundi au samedi.")]),
    ])
    agent = AkmsAgent(tools, client=fake)
    r = agent.repondre("session-123", "Vos horaires ?")
    assert r["reponse"] == "Nous sommes ouverts du lundi au samedi."
    assert len(fake.appels) == 2
    kw = fake.appels[0]
    assert kw["model"] == "claude-opus-5-5" and kw["fallbacks"] == "default"
    assert "tool_choice" not in kw and "thinking" not in kw
    res = fake.appels[1]["messages"][-1]["content"][0]
    assert res["tool_use_id"] == "tu1" and "AKMS AUTOS" in res["content"]


def test_refus_retire_le_tour(tools):
    fake = FakeClient([NS(stop_reason="refusal", content=[])])
    agent = AkmsAgent(tools, client=fake)
    r = agent.repondre("session-123", "...")
    assert "ne peux pas" in r["reponse"]
    assert agent._session("session-123").messages == []


def test_action_rdv_remontee(tools):
    rdv = {"prestation": "essai", "debut": "2026-11-05T14:00", "nom": "Lea", "telephone": "0612345678",
           "email": None, "vehicule": "AK-004", "immatriculation": None, "commentaire": None}
    fake = FakeClient([
        NS(stop_reason="tool_use", content=[NS(type="tool_use", id="t", name="prendre_rendez_vous", input=rdv)]),
        NS(stop_reason="end_turn", content=[txt("C'est note !")]),
    ])
    r = AkmsAgent(tools, client=fake).repondre("session-123", "oui je confirme")
    assert r["actions"][0]["outil"] == "prendre_rendez_vous"
    assert r["actions"][0]["resultat"]["numero_rdv"] == 1
