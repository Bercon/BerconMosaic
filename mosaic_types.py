from PIL import Image
from dataclasses import dataclass, field
import math

@dataclass
class Tile:
    filename: str
    size: tuple[int, int]
    rgb: list
    hsv: list
    index: int

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


class Painting:
    tiles_unoredered: list[PaintingTile] = []
    tiles: list[PaintingTile] = []
    def __init__(self, widthInTiles, heightInTiles):
        self.widthInTiles = widthInTiles
        self.heightInTiles = heightInTiles

    def getNeighbouringTiles(self, tileIndex: int, radius: float) -> list[int]:
        radiusCeiled = math.ceil(radius)
        neighbours = []
        curX = tileIndex % self.widthInTiles
        curY = math.floor(tileIndex / self.widthInTiles)
        for x in range(-radiusCeiled, radiusCeiled):
            for y in range(-radiusCeiled, radiusCeiled):
                print(x)
                px = curX + x
                py = curY + y
                if px < 0 or py < 0 or px >= self.widthInTiles or py >= self.heightInTiles:
                    continue
                neighbour = self.tiles[px + py * self.widthInTiles]
                if neighbour.match == None:
                    continue
                neighbours.append(neighbour.match.index)
        return neighbours

