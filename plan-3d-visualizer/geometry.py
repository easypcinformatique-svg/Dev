"""Modèle de données géométrique partagé entre l'extraction (Claude) et le rendu 3D.

Toutes les coordonnées sont en mètres, vues en plan :
  - X : vers la droite
  - Y : vers le haut de la feuille (profondeur)
  - Z : hauteur (ajoutée lors de l'extrusion 3D)
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class Point(BaseModel):
    x: float = Field(description="Coordonnée X en mètres")
    y: float = Field(description="Coordonnée Y en mètres")


class Wall(BaseModel):
    """Un segment de mur, du point (x1, y1) au point (x2, y2)."""

    x1: float
    y1: float
    x2: float
    y2: float
    thickness: float = Field(description="Épaisseur du mur en mètres (ex: 0.2)")
    height: float = Field(description="Hauteur du mur en mètres (ex: 2.5)")


class Opening(BaseModel):
    """Une ouverture (porte ou fenêtre) positionnée par son centre."""

    kind: Literal["door", "window"]
    center_x: float = Field(description="X du centre de l'ouverture, en mètres")
    center_y: float = Field(description="Y du centre de l'ouverture, en mètres")
    width: float = Field(description="Largeur de l'ouverture en mètres")
    height: float = Field(description="Hauteur de l'ouverture en mètres")
    sill_height: float = Field(
        description="Hauteur d'allège (bas de l'ouverture depuis le sol) en mètres. "
        "0 pour une porte."
    )


class Room(BaseModel):
    """Une pièce, décrite par le polygone fermé de son sol."""

    name: str = Field(description="Nom de la pièce, ex: 'Chambre 1', 'Cuisine'")
    polygon: List[Point] = Field(description="Sommets du sol dans l'ordre, en mètres")
    area_m2: float = Field(description="Surface en m² indiquée sur le plan (0 si absente)")


class PlanGeometry(BaseModel):
    """Géométrie complète extraite d'un plan d'intérieur."""

    notes: str = Field(
        description="Notes sur l'échelle, les hypothèses ou les ambiguïtés rencontrées"
    )
    ceiling_height: float = Field(
        description="Hauteur sous plafond par défaut en mètres (ex: 2.5)"
    )
    walls: List[Wall]
    rooms: List[Room]
    openings: List[Opening]
