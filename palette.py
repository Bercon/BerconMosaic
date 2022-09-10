#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

import os
import sys
from glob import glob
from PIL import Image
import time
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

def palette_remove(palette, tile):
    for i in range(len(palette)):
        if (palette[i]['filename'] == tile['filename']):
            del palette[i]
            return

def get_pixels(img, box, resolution):
    img = img.crop(box)
    img = img.resize(resolution, Image.BICUBIC)
    img = img.convert('RGB')
    size = img.size
    pixels = []
    for x in range(size[0]):
        for y in range(size[1]):
            color = img.getpixel((x, y))
            pixels.append(list(color))
    return pixels

def get_pixels(img):
    img = utils.crop_to_square(img)
    img = img.resize(INDEX_SIZE, Image.BICUBIC)
    img = img.convert('RGB')


    utils.crop(img, left(img), resolution),
    crop(img, center(img), resolution),
    crop(img, right(img), resolution)

    size = img.size
    pixels = []
    pixels_hsv = []
    for x in range(size[0]):
        for y in range(size[1]):
            color = img.getpixel((x, y))
            pixels.append(list(color))
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
    'Done!'

    elapsed_time = time.time() - start_time
    print
    'Processing palette took %s' % elapsed_time
