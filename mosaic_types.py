from PIL import Image
from dataclasses import dataclass, field

@dataclass
class Tile:
    filename: str
    size: tuple[int, int]
    rgb: list
    hsv: list

@dataclass
class Palette:
    index: list[Tile]

@dataclass
class PaintingTile:
    index: int
    rgb: list
    hsv: list
    x: int
    y: int
    ranks: list[tuple[float, int]] = field(default_factory=list)
    match: Tile = None

@dataclass
class RenderTile:
    x: int
    y: int
    img: Image = None

@dataclass
class Painting:
    tiles_unoredered: list[PaintingTile] = field(default_factory=list)
    tiles: list[PaintingTile] = field(default_factory=list)

