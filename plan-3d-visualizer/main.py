"""Pipeline complet : PDF du plan -> géométrie (Claude) -> modèle 3D.

    python main.py <plan.pdf> [building.json]

Produit, à côté du PDF :
  <plan>.json   géométrie extraite par Claude
  <plan>.obj    modèle 3D (ouvrable dans Blender / Windows 3D Viewer)
  <plan>.png    aperçu du rendu 3D

`building.json` (optionnel) fixe les hauteurs et la toiture (voir building.json).
Nécessite la variable d'environnement ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import sys
from pathlib import Path

from build_3d import export_obj, load_spec, render
from extract_plan import extract_geometry


def main() -> None:
    if not 2 <= len(sys.argv) <= 3:
        print("Usage: python main.py <plan.pdf> [building.json]")
        raise SystemExit(2)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.is_file():
        print(f"Fichier introuvable : {pdf_path}")
        raise SystemExit(1)
    spec = load_spec(Path(sys.argv[2]) if len(sys.argv) > 2 else None)

    print(f"1/3  Lecture du plan par Claude : {pdf_path.name} …")
    geometry = extract_geometry(pdf_path)
    print(f"     {geometry.num_levels} niveau(x), {len(geometry.walls)} murs, "
          f"{len(geometry.rooms)} pièces, {len(geometry.openings)} ouvertures.")
    if geometry.notes:
        print(f"     Notes : {geometry.notes}")

    json_path = pdf_path.with_suffix(".json")
    json_path.write_text(geometry.model_dump_json(indent=2), encoding="utf-8")
    print(f"2/3  Géométrie enregistrée → {json_path}")

    obj_path = pdf_path.with_suffix(".obj")
    export_obj(geometry, spec, obj_path)
    png_path = pdf_path.with_suffix(".png")
    render(geometry, spec, png_path)
    print(f"3/3  Terminé → {obj_path}, {png_path}")


if __name__ == "__main__":
    main()
