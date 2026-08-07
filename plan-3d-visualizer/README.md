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
python main.py /chemin/vers/Plan_interieur.pdf building.json
```

Ou étape par étape :

```bash
python extract_plan.py Plan_interieur.pdf plan.json        # 1. Claude lit le plan
python build_3d.py plan.json apercu.png building.json      # 2. construit la 3D
```

## Niveaux (R+1) et toiture

Le code gère plusieurs niveaux et une toiture à deux pentes.

- **Niveaux** : Claude affecte un `level` (0 = RDC, 1 = étage…) à chaque mur,
  pièce et ouverture, et renseigne `num_levels`. Les niveaux sont empilés selon
  `level_height`.
- **Toiture / hauteurs** : ces valeurs ne se lisent pas sur le plan d'intérieur ;
  elles se règlent dans `building.json` (issu des coupes / façades du permis) :

```json
{
  "level_height": 2.8,        // hauteur plancher-à-plancher
  "ground_offset": 0.5,       // surélévation du RDC (zone inondable)
  "roof": { "kind": "gable", "slope_percent": 25.0, "overhang": 0.3 }
}
```

> Le `building.json` fourni correspond au projet Manossian (R+1, toiture 2 pentes
> à 25 %, faîtage ≈ 6,2 m, RDC surélevé de 0,50 m). Mettez `"kind": "flat"` pour
> un toit plat.

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
