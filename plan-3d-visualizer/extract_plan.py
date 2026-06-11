"""Étape 1 : Claude lit le plan PDF (vision) et en extrait la géométrie structurée.

Claude ne génère pas d'image 3D — il *comprend* le plan et renvoie des murs,
pièces et ouvertures en JSON, que `build_3d.py` transforme ensuite en modèle 3D.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import anthropic

from geometry import PlanGeometry

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """\
Tu es un assistant spécialisé en lecture de plans d'architecture d'intérieur.
On te fournit le plan d'un logement. Extrais sa géométrie pour permettre une
reconstruction 3D.

Règles :
- Travaille en mètres. Utilise l'échelle et les cotes imprimées sur le plan pour
  convertir les distances. Place l'origine (0, 0) au coin inférieur gauche.
- Représente chaque mur comme un segment droit (x1,y1)->(x2,y2). Découpe les
  murs longs aux intersections et aux angles.
- Donne une épaisseur de mur réaliste (0.20 m pour les murs porteurs, 0.10 m
  pour les cloisons) si elle n'est pas cotée.
- Pour chaque pièce, donne le polygone fermé de son sol et la surface si elle
  est écrite sur le plan.
- Positionne les portes et fenêtres par le centre, le long d'un mur.
- Si une dimension est illisible, fais l'hypothèse la plus raisonnable et
  signale-la dans `notes`. Ne renvoie jamais de champ vide faute de certitude.
"""


def _pdf_to_base64(pdf_path: Path) -> str:
    return base64.standard_b64encode(pdf_path.read_bytes()).decode("utf-8")


def extract_geometry(pdf_path: Path) -> PlanGeometry:
    """Envoie le PDF à Claude et renvoie la géométrie validée."""
    client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans l'environnement

    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": _pdf_to_base64(pdf_path),
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extrais la géométrie complète de ce plan "
                        "(murs, pièces, ouvertures) au format demandé.",
                    },
                ],
            }
        ],
        output_format=PlanGeometry,
    )

    geometry = response.parsed_output
    if geometry is None:
        raise RuntimeError(
            f"Claude n'a pas renvoyé de géométrie exploitable "
            f"(stop_reason={response.stop_reason})."
        )
    return geometry


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python extract_plan.py <plan.pdf> <sortie.json>")
        raise SystemExit(2)

    pdf_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    geometry = extract_geometry(pdf_path)
    out_path.write_text(geometry.model_dump_json(indent=2), encoding="utf-8")

    print(f"✓ {len(geometry.walls)} murs, {len(geometry.rooms)} pièces, "
          f"{len(geometry.openings)} ouvertures → {out_path}")
    if geometry.notes:
        print(f"  Notes de Claude : {geometry.notes}")


if __name__ == "__main__":
    main()
