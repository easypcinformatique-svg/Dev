"""Étape 2 : transforme la géométrie JSON en modèle 3D multi-niveaux.

- Empile les niveaux (R+1) selon `level`.
- Génère une toiture (deux pentes / gable) par-dessus le niveau supérieur.
- Affiche un rendu 3D (ou l'enregistre en PNG) et exporte un fichier .obj.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np

from geometry import BuildingSpec, PlanGeometry, Roof, Wall

Vec3 = Tuple[float, float, float]
Quad = Tuple[int, ...]  # indices de sommets (1-based pour OBJ)


def _wall_box(wall: Wall, z0: float) -> Tuple[List[Vec3], List[Quad]]:
    """Extrude un mur en boîte entre z0 et z0+hauteur : 8 sommets, 6 faces."""
    dx, dy = wall.x2 - wall.x1, wall.y2 - wall.y1
    length = float(np.hypot(dx, dy))
    if length < 1e-6:
        return [], []

    nx, ny = -dy / length, dx / length
    h = wall.thickness / 2.0
    base = [
        (wall.x1 + nx * h, wall.y1 + ny * h),
        (wall.x2 + nx * h, wall.y2 + ny * h),
        (wall.x2 - nx * h, wall.y2 - ny * h),
        (wall.x1 - nx * h, wall.y1 - ny * h),
    ]
    z1 = z0 + wall.height
    verts: List[Vec3] = [(x, y, z0) for x, y in base] + [(x, y, z1) for x, y in base]
    faces: List[Quad] = [
        (1, 2, 3, 4), (5, 6, 7, 8),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 4, 8, 7), (4, 1, 5, 8),
    ]
    return verts, faces


def _level_z0(level: int, spec: BuildingSpec) -> float:
    """Cote du plancher d'un niveau."""
    return spec.ground_offset + level * spec.level_height


def _footprint_bbox(geometry: PlanGeometry, level: int) -> Tuple[float, float, float, float]:
    xs = [c for w in geometry.walls if w.level == level for c in (w.x1, w.x2)]
    ys = [c for w in geometry.walls if w.level == level for c in (w.y1, w.y2)]
    if not xs:  # repli sur l'ensemble si le niveau n'a pas de murs propres
        xs = [c for w in geometry.walls for c in (w.x1, w.x2)]
        ys = [c for w in geometry.walls for c in (w.y1, w.y2)]
    return min(xs), min(ys), max(xs), max(ys)


def _gable_roof(
    geometry: PlanGeometry, spec: BuildingSpec, eaves_z: float
) -> Tuple[List[Vec3], List[Quad]]:
    """Toiture à deux pentes au-dessus de l'empreinte du niveau supérieur.

    Le faîtage suit le plus grand côté de la boîte englobante ; les deux pans
    descendent vers les deux côtés opposés (les plus courts).
    """
    top = geometry.num_levels - 1
    minx, miny, maxx, maxy = _footprint_bbox(geometry, top)
    o = spec.roof.overhang
    minx, miny, maxx, maxy = minx - o, miny - o, maxx + o, maxy + o

    span_x, span_y = maxx - minx, maxy - miny
    slope = spec.roof.slope_percent / 100.0

    if span_x >= span_y:  # faîtage parallèle à X, pentes selon Y
        ridge_z = eaves_z + (span_y / 2.0) * slope
        ridge_y = (miny + maxy) / 2.0
        verts: List[Vec3] = [
            (minx, miny, eaves_z), (maxx, miny, eaves_z),       # 1,2 égout sud
            (maxx, maxy, eaves_z), (minx, maxy, eaves_z),       # 3,4 égout nord
            (minx, ridge_y, ridge_z), (maxx, ridge_y, ridge_z),  # 5,6 faîtage
        ]
        faces: List[Quad] = [
            (1, 2, 6, 5),  # pan sud
            (4, 3, 6, 5),  # pan nord
            (1, 5, 4),     # pignon ouest
            (2, 3, 6),     # pignon est
        ]
    else:  # faîtage parallèle à Y, pentes selon X
        ridge_z = eaves_z + (span_x / 2.0) * slope
        ridge_x = (minx + maxx) / 2.0
        verts = [
            (minx, miny, eaves_z), (minx, maxy, eaves_z),
            (maxx, maxy, eaves_z), (maxx, miny, eaves_z),
            (ridge_x, miny, ridge_z), (ridge_x, maxy, ridge_z),
        ]
        faces = [
            (1, 2, 6, 5),
            (4, 3, 6, 5),
            (1, 5, 4),
            (2, 3, 6),
        ]
    return verts, faces


# --------------------------------------------------------------------------- #
# Export OBJ
# --------------------------------------------------------------------------- #

def export_obj(geometry: PlanGeometry, spec: BuildingSpec, obj_path: Path) -> None:
    lines: List[str] = ["# Modèle 3D généré depuis un plan d'intérieur"]
    offset = 0

    def emit(name: str, verts: List[Vec3], faces: List[Quad]) -> None:
        nonlocal offset
        if not verts:
            return
        lines.append(f"o {name}")
        for x, y, z in verts:
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
        for f in faces:
            lines.append("f " + " ".join(str(v + offset) for v in f))
        offset += len(verts)

    for i, wall in enumerate(geometry.walls):
        emit(f"mur_n{wall.level}_{i}", *_wall_box(wall, _level_z0(wall.level, spec)))

    if spec.roof.kind == "gable":
        eaves_z = _level_z0(geometry.num_levels - 1, spec) + _top_wall_height(geometry)
        emit("toiture", *_gable_roof(geometry, spec, eaves_z))

    obj_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _top_wall_height(geometry: PlanGeometry) -> float:
    top = geometry.num_levels - 1
    hs = [w.height for w in geometry.walls if w.level == top]
    if not hs:
        hs = [w.height for w in geometry.walls]
    return max(hs) if hs else geometry.ceiling_height


# --------------------------------------------------------------------------- #
# Rendu matplotlib
# --------------------------------------------------------------------------- #

def render(
    geometry: PlanGeometry, spec: BuildingSpec, png_path: Path | None = None
) -> None:
    import matplotlib

    if png_path is not None:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(111, projection="3d")

    # Murs, teinte par niveau
    level_colors = ["#cdd6e0", "#d9cfe0", "#cfe0d6", "#e0dccd"]
    for lvl in sorted({w.level for w in geometry.walls}):
        quads: List[List[Vec3]] = []
        for wall in (w for w in geometry.walls if w.level == lvl):
            verts, faces = _wall_box(wall, _level_z0(lvl, spec))
            for f in faces:
                quads.append([verts[i - 1] for i in f])
        if quads:
            ax.add_collection3d(
                Poly3DCollection(
                    quads, facecolors=level_colors[lvl % len(level_colors)],
                    edgecolors="#41506b", linewidths=0.3, alpha=0.9,
                )
            )

    # Sols + étiquettes des pièces
    floors = [
        [(p.x, p.y, _level_z0(room.level, spec)) for p in room.polygon]
        for room in geometry.rooms if len(room.polygon) >= 3
    ]
    if floors:
        ax.add_collection3d(
            Poly3DCollection(floors, facecolors="#f0e6d2", edgecolors="#b9a77f",
                             alpha=0.5)
        )
    for room in geometry.rooms:
        if room.polygon:
            cx = sum(p.x for p in room.polygon) / len(room.polygon)
            cy = sum(p.y for p in room.polygon) / len(room.polygon)
            label = room.name + (f"\n{room.area_m2:g} m²" if room.area_m2 else "")
            ax.text(cx, cy, _level_z0(room.level, spec) + 0.05, label,
                    fontsize=6.5, ha="center", color="#5a4a2a")

    # Ouvertures
    for op in geometry.openings:
        color = "#7fb069" if op.kind == "door" else "#5bc0de"
        base = _level_z0(op.level, spec) + op.sill_height
        z0, z1 = base, base + op.height
        hw = op.width / 2.0
        panel = [
            (op.center_x - hw, op.center_y, z0), (op.center_x + hw, op.center_y, z0),
            (op.center_x + hw, op.center_y, z1), (op.center_x - hw, op.center_y, z1),
        ]
        ax.add_collection3d(Poly3DCollection([panel], facecolors=color, alpha=0.85))

    # Toiture
    roof_top = _level_z0(geometry.num_levels - 1, spec) + _top_wall_height(geometry)
    if spec.roof.kind == "gable":
        verts, faces = _gable_roof(geometry, spec, roof_top)
        ax.add_collection3d(
            Poly3DCollection(
                [[verts[i - 1] for i in f] for f in faces],
                facecolors="#a0522d", edgecolors="#5c2e18", linewidths=0.3, alpha=0.9,
            )
        )

    _set_equal_aspect(ax, geometry, spec)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    ax.set_title(f"Visuel 3D — {geometry.num_levels} niveau(x)"
                 + (" + toiture" if spec.roof.kind == "gable" else ""))
    ax.view_init(elev=28, azim=-60)

    if png_path is not None:
        fig.savefig(png_path, dpi=150, bbox_inches="tight")
        print(f"✓ Rendu enregistré → {png_path}")
    else:
        plt.show()


def _set_equal_aspect(ax, geometry: PlanGeometry, spec: BuildingSpec) -> None:
    xs = [c for w in geometry.walls for c in (w.x1, w.x2)]
    ys = [c for w in geometry.walls for c in (w.y1, w.y2)]
    if not xs:
        return
    roof_top = _level_z0(geometry.num_levels - 1, spec) + _top_wall_height(geometry)
    minx, miny, maxx, maxy = _footprint_bbox(geometry, geometry.num_levels - 1)
    span = max(maxx - minx, maxy - miny)
    zmax = roof_top + (span / 2.0) * (spec.roof.slope_percent / 100.0
                                      if spec.roof.kind == "gable" else 0)
    rx, ry = max(xs) - min(xs), max(ys) - min(ys)
    ax.set_box_aspect((max(rx, 1e-3), max(ry, 1e-3), max(zmax, 1e-3)))
    ax.set_xlim(min(xs), max(xs))
    ax.set_ylim(min(ys), max(ys))
    ax.set_zlim(0, zmax)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def load_spec(path: Path | None) -> BuildingSpec:
    """Charge une BuildingSpec depuis un JSON, ou renvoie les valeurs par défaut."""
    if path is not None and path.is_file():
        return BuildingSpec.model_validate_json(path.read_text("utf-8"))
    return BuildingSpec()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python build_3d.py <geometrie.json> [sortie.png] [building.json]")
        raise SystemExit(2)

    geometry = PlanGeometry.model_validate_json(Path(sys.argv[1]).read_text("utf-8"))
    png_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    spec = load_spec(Path(sys.argv[3]) if len(sys.argv) > 3 else None)

    obj_path = Path(sys.argv[1]).with_suffix(".obj")
    export_obj(geometry, spec, obj_path)
    print(f"✓ Modèle 3D exporté → {obj_path}")

    render(geometry, spec, png_path)


if __name__ == "__main__":
    main()
