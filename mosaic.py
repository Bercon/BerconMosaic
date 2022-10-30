#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import os
import sys
from glob import glob
from PIL import Image, ImageOps
import time
import colorsys
import numpy
import random
import json
import utils
import argparse
import yaml
import multiprocessing
from mosaic_types import *
from dataclasses import asdict


parser = argparse.ArgumentParser()
parser.add_argument("--config", help="Configuration YAML", default="./config.yaml")
parser.add_argument("--reset", help="Resets palette", action="store_true")
args = parser.parse_args()

config = None
with open(args.config, "r") as stream:
    config = yaml.safe_load(stream)


def crop_to_square(img):
    d = min(img.size)
    # left, upper, right, and lower
    left = (img.size[0] - d) / 2
    upper = (img.size[1] - d) / 2
    box = (
        left,
        upper,
        left + d,
        upper + d
    )
    return img.crop(box)


def palette_remove(palette: Palette, tile: Tile):
    for i in range(len(palette)):
        if (palette[i]['filename'] == tile['filename']):
            del palette[i]
            return


# Distance in Hue coordinates i.e. looping 0..1 normalized to 0..1 range
def hue_distance(a, b):
    return min((
        abs(a - b),
        abs(a - b - 1),
        abs(a - b + 1)
    )) * 2.0


def hsv(color):
    return colorsys.rgb_to_hsv(color[0] / 255., color[1] / 255., color[2] / 255.)


def get_pixels(img: Image):
    img = utils.crop_to_square(img)
    img = img.resize(config["tileIndexSize"], Image.Resampling.BICUBIC)
    img = img.convert('RGB')
    size = img.size
    pixels = []
    pixels_hsv = []
    for x in range(size[0]):
        for y in range(size[1]):
            color = img.getpixel((x, y))
            pixels.append(list(color))
            pixels_hsv.append(list(hsv(color)))
    return {
        'rgb': pixels,
        'hsv': pixels_hsv
    }


def index_image(filename: str) -> Tile:
    try:
        img = Image.open(filename, 'r')
        size = img.size
        pixels = get_pixels(img)
        return Tile(
            filename = filename,
            size = size,
            rgb = pixels['rgb'],
            hsv = pixels['hsv'],
            index = -1
        )
    except:
        print('Couldn\'t index %s' % filename)
        return None


def index_photo(filename: str) -> Painting:
    img = Image.open(filename, 'r')
    img = utils.crop_to_square(img)
    tileCount = config["photoResolutionInTiles"]
    tileSize = config["tileIndexSize"]
    res = (tileCount[0] * tileSize[0], tileCount[1] * tileSize[1])
    img = img.resize(res, Image.Resampling.BICUBIC)
    painting = Painting(config["photoResolutionInTiles"][0], config["photoResolutionInTiles"][1])
    index = 0
    for j in range(tileCount[1]):
        for i in range(tileCount[0]):
            tile = []
            tile_hsv = []
            x_base = i * tileSize[0]
            y_base = j * tileSize[1]
            for x_off in range(tileSize[0]):
                for y_off in range(tileSize[1]):
                    color = img.getpixel((x_base + x_off, y_base + y_off))
                    tile.append(list(color))
                    tile_hsv.append(list(hsv(color)))
            painting.tiles.append(PaintingTile(
                index = index,
                rgb = tile,
                hsv = tile_hsv,
                x = i,
                y = j
            ))
            index += 1
    return painting


def update_palette_multi(filename: str, palette: Palette):
    existing_palette = {}
    for tile in palette.index:
        existing_palette[tile.filename] = True
    files = [y for x in os.walk(filename) for y in glob(os.path.join(x[0], '*.jpg'))]
    filtered = []
    for filename in files:
        if filename not in existing_palette:
            filtered.append(filename)

    newImages = len(filtered)
    if newImages > 0:
        print("Adding {} new images to index".format(newImages))
        results = None
        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            results = pool.map(index_image, filtered)
        for new_pixel in results:
            new_pixel.index = len(palette.index)
            palette.index.append(new_pixel)


def find_closest_match(palette: Palette, tile: PaintingTile):
    closest_value = None
    closest_tile = None
    for index_tile in palette.index:
        value = utils.distance_value(index_tile, tile)
        if closest_value is None or value < closest_value:
            closest_value = value
            closest_tile = index_tile
    return closest_tile


def rank_tiles(params):
    tile = params["tile"]
    palette = params["palette"]
    ranks = []
    for i in range(len(palette.index)):
        index_tile = palette.index[i]
        value = utils.distance_value(index_tile, tile)
        ranks.append((value, i))
    ranks.sort(key=lambda pair: pair[0])
    return (tile.index, ranks)


# For each pixel, compute rank for each tile i.e. you get array dim: pixel*tiles
def rank_tiles_for_each_pixel(palette, picture):
    tiles = []
    for i in range(len(picture.tiles_unordered)):
        tiles.append({
            "tile": picture.tiles_unordered[i],
            "palette": palette
        })
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.map(rank_tiles, tiles)
        for res in results:
            picture.tiles[res[0]].ranks = res[1]


def find_tiles(palette: Palette, picture: Painting):
    rank_tiles_for_each_pixel(palette, picture)


    for i in range(len(picture.tiles_unordered)):
        tile = picture.tiles_unordered[i]
        sys.stdout.write('\rFinding tiles %d%%' % (100.0 * i / len(picture.tiles_unordered)))
        sys.stdout.flush()
        SEARCH_RADIUS = 5
        neighbours = picture.getNeighbouringTiles(i, SEARCH_RADIUS)
        # print(neighbours)
        if (len(neighbours) >= len(palette.index)):
            raise Exception("Neibhbourhood size is bigger than palette size, can't find acceptable tiles")
        j = 0
        matchingTile = tile.ranks[j][1]
        while matchingTile in neighbours:
            j += 1
            matchingTile = tile.ranks[j][1]
        # print(matchingTile)
        closest_tile = palette.index[matchingTile]
        # if not config["reuseTiles"]:
        #     palette_remove(palette.index, closest_tile)
        tile.match = closest_tile
    sys.stdout.write('\rFinding tiles 100%!\n')


# Done for each tile, modify colors etc. here
def render_mosaic_worker(params) -> RenderTile:
    tile = params["tile"]
    tile_size = params["size"]
    # print("Index", index, "length", len(picture))
    # tile = picture[index]
    tile_img = crop_to_square(Image.open(tile.match.filename))
    tile_img = tile_img.resize(tile_size)

    if (config["colorizeTiles"]):
        avgColor = utils.average_rgb_color(tile)
        tile_img = ImageOps.grayscale(tile_img)
        tile_img = ImageOps.colorize(tile_img, [0,0,0], [255,255,255], avgColor) # mid=None, blackpoint=0, whitepoint=255, midpoint=127
    return RenderTile(
        x = tile.x,
        y = tile.y,
        img = tile_img
    )


def render_mosaic_multi(picture: Painting):
    tile_size = (
        config["photoResolutionInPixels"][0] // config["photoResolutionInTiles"][0],
        config["photoResolutionInPixels"][1] // config["photoResolutionInTiles"][1]
    )
    tiles = []
    for i in range(len(picture.tiles_unordered)):
        tiles.append({
            "tile": picture.tiles_unordered[i],
            "size": tile_size
        })
    renderTiles = None
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        renderTiles = pool.map(render_mosaic_worker, tiles)
    img = Image.new('RGB', config["photoResolutionInPixels"])
    for tile in renderTiles:
        # print("pasting", tile.x, tile.y, tile.img)
        img.paste(tile.img, (tile.x * tile_size[0], tile.y * tile_size[1]))
    return img


def save_palette(filename: str, palette: Palette):
    with open(filename, 'w') as data_file:
        dicts = list(map(lambda tile: asdict(tile), palette.index))
        data = json.dumps(dicts)
        data_file.write(data)


def load_palette(filename, palette) -> Palette:
    try:
        with open(filename, 'r') as data_file:
            index = json.load(data_file)
            for tile in index:
                palette.index.append(Tile(
                    filename = tile["filename"],
                    size = tile["size"],
                    rgb = tile['rgb'],
                    hsv = tile['hsv'],
                    index = len(palette.index)
                ))
            return palette
    except:
        pass


def processPhoto(photoPath: str, palette: Palette):
    print("Indexing photo [{}]...".format(photoPath), flush=True)
    picture = index_photo(photoPath)

    print("Finding tiles...", flush=True)
    # random.shuffle(picture)
    picture.tiles_unordered = random.sample(picture.tiles, len(picture.tiles))
    find_tiles(palette, picture)

    print("Rendering mosaic...", flush=True)
    # img = render_mosaic(picture)
    img = render_mosaic_multi(picture)

    print("Done!", flush=True)
    # img.show()
    os.makedirs(config["outputFolder"], exist_ok=True)
    img.save(config["outputFolder"] + "/" + time.strftime("%Y-%m-%d-%H-%M-%S") + ".png")


if __name__ == '__main__':
    start_time = time.time()
    random.seed(config["randomSeed"])

    palette = Palette([])
    if args.reset:
        try:
            os.remove(config["tilePalettePath"])
        except OSError:
            pass
    else:
        print("Loading palette...", flush=True)
        load_palette(config["tilePalettePath"], palette)

    print("Updating palette...", flush=True)
    update_palette_multi(config["tilesFolder"], palette)

    print("Saving palette for future runs...", flush=True)
    save_palette(config["tilePalettePath"], palette)

    photoPaths = config["photoPath"]
    if type(photoPaths) is str:
        processPhoto(photoPaths, palette)
    else:
        for path in photoPaths: processPhoto(path, palette)

    elapsed_time = time.time() - start_time
    print("Processing took %s" % elapsed_time)
