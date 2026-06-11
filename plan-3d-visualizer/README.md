# Plan → Visuel 3D

Transforme un plan d'intérieur (PDF) en modèle 3D, en utilisant l'API Claude
pour **lire et comprendre le plan**, puis Python pour **construire la 3D**.

```
PDF du plan ──▶ Claude (vision + sortie structurée) ──▶ géométrie JSON ──▶ modèle 3D (.obj + aperçu .png)
```

> ⚠️ Claude ne dessine pas l'image 3D lui-même : c'est un modèle texte+vision.
> Il extrait la **géométrie** (murs, pièces, portes/fenêtres, dimensions) ;
> le code Python (`build_3d.py`) l'extrude en volume et l'exporte au format 3D.

## Installation

```bash
cd plan-3d-visualizer
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Utilisation

Pipeline complet (PDF → JSON → OBJ + PNG) :

```bash
python main.py /chemin/vers/Plan_interieur.pdf
```

Ou étape par étape :

```bash
python extract_plan.py Plan_interieur.pdf plan.json   # 1. Claude lit le plan
python build_3d.py plan.json apercu.png               # 2. construit la 3D
```

## Fichiers produits

| Fichier      | Contenu                                                        |
|--------------|---------------------------------------------------------------|
| `*.json`     | Géométrie extraite (murs, pièces, ouvertures) — éditable       |
| `*.obj`      | Modèle 3D — ouvrable dans Blender, Windows 3D Viewer, etc.     |
| `*.png`      | Aperçu du rendu 3D                                             |

## Affiner le résultat

La précision dépend de la lisibilité des cotes sur le plan. Le champ `notes`
du JSON indique les hypothèses faites par Claude. Le JSON étant lisible et
modifiable, vous pouvez corriger une épaisseur de mur ou une dimension à la
main, puis relancer uniquement `build_3d.py`.

## Structure

| Module            | Rôle                                                       |
|-------------------|------------------------------------------------------------|
| `geometry.py`     | Modèle Pydantic partagé (murs, pièces, ouvertures, points) |
| `extract_plan.py` | Appel Claude : PDF → géométrie validée                     |
| `build_3d.py`     | Géométrie → extrusion 3D, rendu matplotlib, export OBJ     |
| `main.py`         | Orchestre le pipeline complet                              |
