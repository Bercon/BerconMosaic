#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import os
import sys
from glob import glob
from PIL import Image
import time
import colorsys
import numpy
import random
import json
import io
import utils

from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

RANDOM_SEED = 34632354
PICTURE_PATH = 'S:/Projects/Mosaic/input/pluto.png'
TILE_PATH = 'S:/Projects/Mosaic/Valokuvat'
OUTPUT_PATH = 'S:/Projects/Mosaic/output/output_%s.png' % time.strftime("%Y-%m-%d-%H-%M-%S")
PALETTE_PATH = 'S:/Projects/Mosaic/palette4.json'

# INDEX_SIZE = (4,4)
# PICTURE_TILES = (25, 25)
# OUTPUT_SIZE = (3000, 3000)

INDEX_SIZE = (4, 4)
PICTURE_TILES = (24, 26)
OUTPUT_SIZE = (3600, 3900)

WEIGHTS = numpy.array([1.0, 1.0, 1.0])


def to_array(tuple):
    return numpy.array(list(tuple))


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
    img = img.resize(INDEX_SIZE, Image.BICUBIC)
    img = img.convert('RGB')
    size = img.size
    pixels = []
    pixels_hsv = []
    for x in range(size[0]):
        for y in range(size[1]):
            color = img.getpixel((x, y))
            pixels.append(list(color))
            pixels_hsv.append(list(hsv(color)))
    return {'rgb': pixels, 'hsv': pixels_hsv}



# {
#     'filename': filename,
#     'size': size,
#     'rgb': [
#       {
#           crop: []
#           tile: []
#       }
#     ],
#     'hsv': pixels['hsv']
# }

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


def index_picture(filename):
    img = Image.open(filename, 'r')
    img = utils.crop_to_square(img)
    res = (PICTURE_TILES[0] * INDEX_SIZE[0], PICTURE_TILES[1] * INDEX_SIZE[1])
    img = img.resize(res, Image.BICUBIC)
    tiles = []
    index = 0
    for j in range(PICTURE_TILES[1]):
        for i in range(PICTURE_TILES[0]):
            tile = []
            tile_hsv = []
            x_base = i * INDEX_SIZE[0]
            y_base = j * INDEX_SIZE[1]
            for x_off in range(INDEX_SIZE[0]):
                for y_off in range(INDEX_SIZE[1]):
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


def update_palette(filename, palette):
    existing_palette = {}
    for tile in palette:
        existing_palette[tile['filename']] = True
    files = [y for x in os.walk(filename) for y in glob(os.path.join(x[0], '*.jpg'))]
    i = 0

    for filename in files:
        sys.stdout.write('\rUpdating palette %d' % (100.0 * i / len(files)))
        if filename not in existing_palette:
            palette.append(index_image(filename))
        i += 1
    print


def update_palette_multi(filename, palette):
    existing_palette = {}
    for tile in palette:
        existing_palette[tile['filename']] = True
    files = [y for x in os.walk(filename) for y in glob(os.path.join(x[0], '*.jpg'))]
    filtered = []
    for filename in files:
        if filename not in existing_palette:
            filtered.append(filename)
    pool = ThreadPool()
    results = pool.map(index_image, filtered)
    pool.close()
    pool.join()
    for new_pixel in results:
        palette.append(new_pixel)


# 0 = indentical, >0 = different
def compare_color(a, b):
    value = 0
    for i in range(3):
        value = value + abs(a[i] - b[i])
    return value


# 0 = indentical, >0 = different
def compare_rgb(tile_a, tile_b):
    a = tile_a['rgb']
    b = tile_b['rgb']
    value = 0
    for i in range(len(a)):
        # value = value + compare_color(a[i], b[i])
        value += abs(a[i][0] - b[i][0]) + abs(a[i][1] - b[i][1]) * 1.2 + abs(a[i][2] - b[i][2]) * .8
        # value += numpy.linalg.norm((numpy.array(a[i]) * WEIGHTS) - (numpy.array(b[i]) * WEIGHTS))
    return value


def compare_hsv(tile_a, tile_b):
    a = tile_a['hsv']
    b = tile_b['hsv']
    value = 0
    for i in range(len(a)):
        # Hue, Saturation, Value
        value = value + hue_distance(a[i][0], b[i][0])
        value = value + abs(a[i][1] - b[i][1])
        value = value + abs(a[i][2] - b[i][2]) * 1.0
    return value


def find_closest_match(palette, tile):
    closest_value = sys.maxint
    closest_tile = None
    for index_tile in palette:
        value = compare_rgb(index_tile, tile)
        if value < closest_value:
            closest_value = value
            closest_tile = index_tile
    return closest_tile


def find_tiles(palette, picture):
    for i in range(len(picture)):
        tile = picture[i]
        sys.stdout.write('\rFinding tiles %d' % (100.0 * i / len(picture)))
        closest_tile = find_closest_match(palette, tile)
        palette_remove(palette, closest_tile)
        tile['match'] = closest_tile
    print


def render_mosaic(picture):
    img = Image.new('RGB', OUTPUT_SIZE)
    tile_size = (OUTPUT_SIZE[0] / PICTURE_TILES[0], OUTPUT_SIZE[1] / PICTURE_TILES[1])
    count = len(picture)
    for index in range(count):
        # for tile in picture:
        tile = picture[index]
        i = tile['index']
        x = i % PICTURE_TILES[0]
        y = i // PICTURE_TILES[0]  # // is floor division
        tile_img = crop_to_square(Image.open(tile['match']['filename']))
        tile_img = tile_img.resize(tile_size)
        img.paste(tile_img, (x * tile_size[0], y * tile_size[1]))
        sys.stdout.write('\rRendering %d' % (100.0 * index / count))
    return img


def render_mosaic_worker(index, picture, tile_size, img):
    tile = picture[index]
    i = tile['index']
    x = i % PICTURE_TILES[0]
    y = i // PICTURE_TILES[0]  # // is floor division
    tile_img = crop_to_square(Image.open(tile['match']['filename']))
    tile_img = tile_img.resize(tile_size)
    img.paste(tile_img, (x * tile_size[0], y * tile_size[1]))


def render_mosaic_multi(picture):
    img = Image.new('RGB', OUTPUT_SIZE)
    tile_size = (OUTPUT_SIZE[0] / PICTURE_TILES[0], OUTPUT_SIZE[1] / PICTURE_TILES[1])
    count = len(picture)

    worker = lambda x: render_mosaic_worker(x, picture, tile_size, img)
    pool = ThreadPool()
    results = pool.map(worker, range(count))
    pool.close()
    pool.join()

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


# def convert_to_numpy(array):
#    for tile in array:
#        for
#        'rgb': tile,
#        'hsv': tile_hsv


if __name__ == '__main__':
    start_time = time.time()
    random.seed(RANDOM_SEED)
    print
    'Indexing picture...'
    picture = index_picture(PICTURE_PATH)
    print
    'Loading palette...'
    palette = load_palette(PALETTE_PATH)
    print
    'Updating palette...'
    # update_palette(TILE_PATH, palette)
    update_palette_multi(TILE_PATH, palette)
    print
    'Saving palette for future runs...'
    save_palette(PALETTE_PATH, palette)
    print
    'Finding tiles...'
    random.shuffle(picture)
    find_tiles(palette, picture)
    print
    'Rendering mosaic...'
    # img = render_mosaic(picture)
    img = render_mosaic_multi(picture)

    print
    'Done!'
    # img.show()
    img.save(OUTPUT_PATH)

    elapsed_time = time.time() - start_time
    print
    'Processing took %s' % elapsed_time
