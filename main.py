import os
import sys
from glob import glob
from PIL import Image
import time
import colorsys
import numpy
import random

RANDOM_SEED = 34632354
PICTURE_PATH = 'S:/Projects/Mosaic/jerry.jpg'
TILE_PATH = 'S:/Projects/Mosaic/resized2'
OUTPUT_PATH = 'S:/Projects/Mosaic/output_%s.png' % time.strftime("%Y-%m-%d-%H-%M-%S")

INDEX_SIZE = (3,3)
PICTURE_TILES = (20, 20)
OUTPUT_SIZE = (1300, 1300)


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
        abs(a-b),
        abs(a-b-1),
        abs(a-b+1)
    )) * 2.0;


def hsv(color):
    return colorsys.rgb_to_hsv(color[0] / 255., color[1] / 255., color[2] / 255.)


def get_pixels(img):
    img = crop_to_square(img)
    img = img.resize(INDEX_SIZE, Image.BICUBIC)
    img = img.convert('RGB')
    size = img.size
    pixels = []
    pixels_hsv = []
    for x in range(size[0]):
        for y in range(size[1]):
            color = img.getpixel((x, y))
            pixels.append(to_array(color))
            pixels_hsv.append(to_array(hsv(color)))
    return {'rgb': pixels, 'hsv': pixels_hsv}


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
    img = crop_to_square(img)
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
                    tile.append(to_array(color))
                    tile_hsv.append(to_array(hsv(color)))
            tiles.append({
                'index': index,
                'rgb': tile,
                'hsv': tile_hsv
            })
            print tile_hsv
            index += 1
    return tiles


def index_folder(filename):
    files = [y for x in os.walk(filename) for y in glob(os.path.join(x[0], '*.jpg'))]
    images = map(index_image, files)
    return images


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
        #value = value + compare_color(a[i], b[i])
        value += numpy.linalg.norm(a[i] - b[i])
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
    for tile in picture:
        i = tile['index']
        x = i % PICTURE_TILES[0]
        y = i // PICTURE_TILES[0] # // is floor division
        tile_img = crop_to_square(Image.open(tile['match']['filename']))
        tile_img = tile_img.resize(tile_size)
        img.paste(tile_img, (x * tile_size[0], y * tile_size[1]))
    return img


if __name__ == '__main__':
    random.seed(RANDOM_SEED)
    print 'Indexing picture...'
    picture = index_picture(PICTURE_PATH)
    print 'Indexing...'
    palette = index_folder(TILE_PATH)
    print 'Finding tiles...'
    random.shuffle(picture)
    find_tiles(palette, picture)
    print 'Rendering mosaic...'
    img = render_mosaic(picture)
    print 'Done!'
    #img.show()
    img.save(OUTPUT_PATH)
