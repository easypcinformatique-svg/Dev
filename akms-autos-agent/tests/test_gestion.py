import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["AKMS_NO_AUTOSTART"] = "1"

from agent import GestionAgent  # noqa: E402
from gestion_tools import GESTION_TOOLS, GestionTools  # noqa: E402
from store import Store  # noqa: E402
from tools import GarageTools, OutilError  # noqa: E402

NOW = datetime(2026, 11, 4, 8, 0)  # mercredi


@pytest.fixture
def env(tmp_path):
    cfg, stk = tmp_path / "garage.json", tmp_path / "vehicules.json"
    shutil.copy(ROOT / "config" / "garage.json", cfg)
    shutil.copy(ROOT / "data" / "vehicules.json", stk)
    store = Store(":memory:")
    g = GestionTools(cfg, stk, store, now=lambda: NOW)
    c = GarageTools(cfg, stk, store, now=lambda: NOW)
    return g, c


def run(t, name, **a):
    return json.loads(t.run(name, a))


def test_schemas_strict():
    for t in GESTION_TOOLS:
        s = t["input_schema"]
        assert t["strict"] is True and s["additionalProperties"] is False
        assert set(s["required"]) == set(s["properties"]), t["name"]


def test_cycle_rdv(env):
    g, c = env
    rid = run(c, "prendre_rendez_vous", prestation="vidange", debut="2026-11-05T09:00", nom="Dupont",
              telephone="0612345678", email=None, vehicule=None, immatriculation=None, commentaire=None)["numero_rdv"]
    r = run(g, "modifier_rendez_vous", numero=rid, statut="confirme", nouveau_debut="2026-11-05T10:00",
            note="client prevenu", forcer=False)["rendez_vous"]
    assert r["statut"] == "confirme" and r["debut"] == "2026-11-05T10:00" and r["fin"] == "2026-11-05T11:00"
    with pytest.raises(OutilError):  # dimanche ferme
        run(g, "modifier_rendez_vous", numero=rid, statut=None, nouveau_debut="2026-11-08T10:00", note=None, forcer=False)
    assert run(g, "modifier_rendez_vous", numero=rid, statut=None, nouveau_debut="2026-11-08T10:00",
               note=None, forcer=True)["ok"]
    p = run(g, "planning", du="2026-11-08", au="2026-11-08")
    assert p["nombre"] == 1
    assert g.store.lister("journal")[0]["action"] == "modifier_rendez_vous"


def test_rdv_annule_libere_le_creneau(env):
    g, c = env
    base = dict(prestation="vidange", debut="2026-11-05T09:00", nom="A", telephone="0612345678",
                vehicule=None, immatriculation=None, note=None, forcer=False)
    a = run(g, "creer_rendez_vous", **base)["numero_rdv"]
    run(g, "creer_rendez_vous", **{**base, "nom": "B"})
    with pytest.raises(OutilError):
        run(g, "creer_rendez_vous", **{**base, "nom": "C"})
    run(g, "modifier_rendez_vous", numero=a, statut="annule", nouveau_debut=None, note=None, forcer=False)
    assert run(g, "creer_rendez_vous", **{**base, "nom": "C"})["ok"]


def test_demandes(env):
    g, c = env
    did = run(c, "enregistrer_demande", type="reprise", nom="Ali", telephone="0611223344", email=None,
              resume="308 de 2017", vehicule=None)["numero_demande"]
    assert run(g, "lister_demandes", statut="nouveau", type=None)["nombre"] == 1
    d = run(g, "traiter_demande", numero=did, statut="en_cours", note="rappele, offre 6500")["demande"]
    assert d["statut"] == "en_cours" and "offre 6500" in d["note"]
    assert run(g, "lister_demandes", statut="nouveau", type=None)["nombre"] == 0


def test_stock_et_vente_cache_aux_clients(env):
    g, c = env
    ref = run(g, "stock_ajouter", marque="Renault", modele="Megane", version="1.5 dCi 110", annee=2017, km=120000,
              carburant="diesel", boite="manuelle", prix=9900, prix_achat=7000, couleur=None, places=None,
              critair=2, options=[])["ref"]
    assert ref == "AK-008"
    fiche = run(c, "details_vehicule", ref=ref)
    assert "prix_achat" not in fiche and "entree_stock" not in fiche
    run(g, "stock_modifier", ref=ref, prix=9500, km=None, prix_achat=None, disponible=None, options=None)
    v = run(g, "stock_vendre", ref=ref, prix_vente=9300, client="M. Durand", date_vente=None, note=None)
    assert v["remise_sur_prix_affiche"] == 200 and v["marge_brute"] == 2300
    with pytest.raises(OutilError):
        run(g, "stock_vendre", ref=ref, prix_vente=9300, client=None, date_vente=None, note=None)
    with pytest.raises(OutilError):
        run(c, "details_vehicule", ref=ref)
    tb = run(g, "tableau_de_bord", jours=7)
    assert tb["ventes"]["chiffre_affaires"] == 9300 and tb["ventes"]["nombre"] == 1
    assert tb["stock"]["vehicules_en_vente"] == 6


def test_infos_et_prestation(env):
    g, c = env
    run(g, "modifier_infos_garage", champ="horaires.samedi", valeur="ferme")
    assert run(c, "infos_garage")["horaires"]["samedi"] == "ferme"
    with pytest.raises(OutilError):
        run(g, "modifier_infos_garage", champ="horaires.lundi", valeur="le matin")
    run(g, "modifier_infos_garage", champ="telephone", valeur="04 90 00 00 00")
    assert run(c, "infos_garage")["telephone"] == "04 90 00 00 00"
    p = run(g, "modifier_prestation", code="vidange", prix_indicatif="a partir de 95 EUR TTC", duree_min=None)
    assert p["prestation"]["prix_indicatif"].endswith("95 EUR TTC")


def test_agent_gestion_utilise_ses_outils(env):
    g, _ = env
    reps = [NS(stop_reason="end_turn", content=[NS(type="text", text="ok")])]
    appels = []
    fake = NS(beta=NS(messages=NS(create=lambda **kw: (appels.append(kw), reps.pop(0))[1])))
    r = GestionAgent(g, client=fake).repondre("abcdefgh", "Tableau de bord")
    assert r["reponse"] == "ok"
    noms = {t["name"] for t in appels[0]["tools"]}
    assert "stock_vendre" in noms and "prendre_rendez_vous" not in noms
    assert "gestion interne" in appels[0]["system"][0]["text"]
