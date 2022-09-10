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


def palette_remove(palette, tile):
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


def get_pixels(img):
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


def index_image(filename):
    try:
        img = Image.open(filename, 'r')
        size = img.size
        pixels = get_pixels(img)
        return {
            'filename': filename,
            'size': size,
            'rgb': pixels['rgb'],
            'hsv': pixels['hsv']
        }
    except:
        print('Couldn\'t index %s' % filename)


def index_photo(filename):
    img = Image.open(filename, 'r')
    img = utils.crop_to_square(img)
    tileCount = config["photoResolutionInTiles"]
    tileSize = config["tileIndexSize"]
    res = (tileCount[0] * tileSize[0], tileCount[1] * tileSize[1])
    img = img.resize(res, Image.Resampling.BICUBIC)
    tiles = []
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
            tiles.append({
                'index': index,
                'rgb': tile,
                'hsv': tile_hsv
            })
            index += 1
    return tiles


def update_palette_multi(filename, palette):
    existing_palette = {}
    for tile in palette:
        existing_palette[tile['filename']] = True
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
            palette.append(new_pixel)


def find_closest_match(palette, tile):
    closest_value = None
    closest_tile = None
    for index_tile in palette:
        value = utils.distance_value(index_tile, tile)
        if closest_value is None or value < closest_value:
            closest_value = value
            closest_tile = index_tile
    return closest_tile


def find_tiles(palette, picture):
    for i in range(len(picture)):
        tile = picture[i]
        sys.stdout.write('\rFinding tiles %d%%' % (100.0 * i / len(picture)))
        sys.stdout.flush()
        closest_tile = find_closest_match(palette, tile)
        if not config["reuseTiles"]:
            palette_remove(palette, closest_tile)
        tile['match'] = closest_tile
    sys.stdout.write('\rFinding tiles 100%!\n')


# Done for each tile, modify colors etc. here
def render_mosaic_worker(params):
    tile = params["tile"]
    tile_size = params["size"]
    # print("Index", index, "length", len(picture))
    # tile = picture[index]
    i = tile['index']
    x = i % config["photoResolutionInTiles"][0]
    y = i // config["photoResolutionInTiles"][0]  # // is floor division
    tile_img = crop_to_square(Image.open(tile['match']['filename']))
    tile_img = tile_img.resize(tile_size)

    if (config["colorizeTiles"]):
        avgColor = utils.average_rgb_color(tile)
        tile_img = ImageOps.grayscale(tile_img)
        tile_img = ImageOps.colorize(tile_img, [0,0,0], [255,255,255], avgColor) # mid=None, blackpoint=0, whitepoint=255, midpoint=127

    return {
        "x": x,
        "y": y,
        "img": tile_img
    }


def render_mosaic_multi(picture):
    tile_size = (
        config["photoResolutionInPixels"][0] // config["photoResolutionInTiles"][0],
        config["photoResolutionInPixels"][1] // config["photoResolutionInTiles"][1]
    )
    count = len(picture)
    tiles = []
    for i in range(count):
        tiles.append({
            "tile": picture[i],
            "size": tile_size
        })
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.map(render_mosaic_worker, tiles)
    img = Image.new('RGB', config["photoResolutionInPixels"])
    for tile in results:
        img.paste(tile["img"], (tile["x"] * tile_size[0], tile["y"] * tile_size[1]))
    return img


def save_palette(filename, palette):
    with open(filename, 'w') as data_file:
        data = json.dumps(palette)
        data_file.write(data)


def load_palette(filename):
    try:
        with open(filename, 'r') as data_file:
            return json.load(data_file)
    except:
        return []


if __name__ == '__main__':
    start_time = time.time()
    random.seed(config["randomSeed"])

    print("Indexing photo...", flush=True)
    picture = index_photo(config["photoPath"])

    palette = []
    if args.reset:
        try:
            os.remove(config["tilePalettePath"])
        except OSError:
            pass
    else:
        print("Loading palette...", flush=True)
        palette = load_palette(config["tilePalettePath"])

    print("Updating palette...", flush=True)
    update_palette_multi(config["tilesFolder"], palette)

    print("Saving palette for future runs...", flush=True)
    save_palette(config["tilePalettePath"], palette)

    print("Finding tiles...", flush=True)
    random.shuffle(picture)
    find_tiles(palette, picture)

    print("Rendering mosaic...", flush=True)
    # img = render_mosaic(picture)
    img = render_mosaic_multi(picture)

    print("Done!", flush=True)
    # img.show()
    os.makedirs(config["outputFolder"], exist_ok=True)
    img.save(config["outputFolder"] + "/" + time.strftime("%Y-%m-%d-%H-%M-%S") + ".png")

    elapsed_time = time.time() - start_time
    print("Processing took %s" % elapsed_time)
