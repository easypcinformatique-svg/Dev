"""Étape 2 : transforme la géométrie JSON en modèle 3D.

- Affiche un rendu 3D interactif (ou l'enregistre en PNG) avec matplotlib.
- Exporte un fichier .obj ouvrable dans Blender, Windows 3D Viewer, etc.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np

from geometry import PlanGeometry, Wall

Vec3 = Tuple[float, float, float]
Quad = Tuple[int, int, int, int]  # indices de sommets (1-based pour OBJ)


def _wall_box(wall: Wall) -> Tuple[List[Vec3], List[Quad]]:
    """Extrude un mur en boîte : 8 sommets, 6 faces."""
    dx, dy = wall.x2 - wall.x1, wall.y2 - wall.y1
    length = float(np.hypot(dx, dy))
    if length < 1e-6:
        return [], []

    # Normale perpendiculaire dans le plan, demi-épaisseur
    nx, ny = -dy / length, dx / length
    h = wall.thickness / 2.0

    base = [
        (wall.x1 + nx * h, wall.y1 + ny * h),
        (wall.x2 + nx * h, wall.y2 + ny * h),
        (wall.x2 - nx * h, wall.y2 - ny * h),
        (wall.x1 - nx * h, wall.y1 - ny * h),
    ]
    z0, z1 = 0.0, wall.height
    verts: List[Vec3] = [(x, y, z0) for x, y in base] + [(x, y, z1) for x, y in base]

    # Faces (indices 1-based, convention OBJ) : bas, haut, 4 côtés
    faces: List[Quad] = [
        (1, 2, 3, 4),
        (5, 6, 7, 8),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 4, 8, 7),
        (4, 1, 5, 8),
    ]
    return verts, faces


def export_obj(geometry: PlanGeometry, obj_path: Path) -> None:
    """Écrit toutes les boîtes de murs dans un seul fichier .obj."""
    lines: List[str] = ["# Modèle 3D généré depuis un plan d'intérieur"]
    offset = 0
    for i, wall in enumerate(geometry.walls):
        verts, faces = _wall_box(wall)
        if not verts:
            continue
        lines.append(f"o mur_{i}")
        for x, y, z in verts:
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
        for quad in faces:
            lines.append("f " + " ".join(str(v + offset) for v in quad))
        offset += len(verts)
    obj_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render(geometry: PlanGeometry, png_path: Path | None = None) -> None:
    """Rendu 3D matplotlib. Affiche à l'écran, ou enregistre en PNG si fourni."""
    import matplotlib

    if png_path is not None:
        matplotlib.use("Agg")  # backend sans écran
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(111, projection="3d")

    all_quads: List[List[Vec3]] = []
    for wall in geometry.walls:
        verts, faces = _wall_box(wall)
        for quad in faces:
            all_quads.append([verts[i - 1] for i in quad])

    ax.add_collection3d(
        Poly3DCollection(
            all_quads, facecolors="#cdd6e0", edgecolors="#41506b",
            linewidths=0.3, alpha=0.92,
        )
    )

    # Sols des pièces + étiquettes
    floors = [
        [(p.x, p.y, 0.0) for p in room.polygon]
        for room in geometry.rooms
        if len(room.polygon) >= 3
    ]
    if floors:
        ax.add_collection3d(
            Poly3DCollection(floors, facecolors="#f0e6d2", edgecolors="#b9a77f",
                             alpha=0.55)
        )
    for room in geometry.rooms:
        if room.polygon:
            cx = sum(p.x for p in room.polygon) / len(room.polygon)
            cy = sum(p.y for p in room.polygon) / len(room.polygon)
            label = room.name + (f"\n{room.area_m2:g} m²" if room.area_m2 else "")
            ax.text(cx, cy, 0.05, label, fontsize=7, ha="center", color="#5a4a2a")

    # Ouvertures : petits panneaux colorés sur le mur
    for op in geometry.openings:
        color = "#7fb069" if op.kind == "door" else "#5bc0de"
        z0, z1 = op.sill_height, op.sill_height + op.height
        hw = op.width / 2.0
        panel = [
            (op.center_x - hw, op.center_y, z0),
            (op.center_x + hw, op.center_y, z0),
            (op.center_x + hw, op.center_y, z1),
            (op.center_x - hw, op.center_y, z1),
        ]
        ax.add_collection3d(Poly3DCollection([panel], facecolors=color, alpha=0.85))

    _set_equal_aspect(ax, geometry)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    ax.set_title("Visuel 3D du plan d'intérieur")
    ax.view_init(elev=35, azim=-60)

    if png_path is not None:
        fig.savefig(png_path, dpi=150, bbox_inches="tight")
        print(f"✓ Rendu enregistré → {png_path}")
    else:
        plt.show()


def _set_equal_aspect(ax, geometry: PlanGeometry) -> None:
    xs = [c for w in geometry.walls for c in (w.x1, w.x2)]
    ys = [c for w in geometry.walls for c in (w.y1, w.y2)]
    if not xs:
        return
    zmax = max((w.height for w in geometry.walls), default=geometry.ceiling_height)
    rx, ry = max(xs) - min(xs), max(ys) - min(ys)
    ax.set_box_aspect((max(rx, 1e-3), max(ry, 1e-3), max(zmax, 1e-3)))
    ax.set_xlim(min(xs), max(xs))
    ax.set_ylim(min(ys), max(ys))
    ax.set_zlim(0, zmax)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python build_3d.py <geometrie.json> [sortie.png]")
        raise SystemExit(2)

    geometry = PlanGeometry.model_validate_json(Path(sys.argv[1]).read_text("utf-8"))

    obj_path = Path(sys.argv[1]).with_suffix(".obj")
    export_obj(geometry, obj_path)
    print(f"✓ Modèle 3D exporté → {obj_path}")

    png_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    render(geometry, png_path)


if __name__ == "__main__":
    main()
