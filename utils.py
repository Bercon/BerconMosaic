import math
from PIL import Image
from mosaic_types import *

def center(img):
    d = min(img.size)
    # left, upper, right, and lower
    left = (img.size[0] - d) / 2
    upper = (img.size[1] - d) / 2
    return (
        left,
        upper,
        left + d,
        upper + d
    )

def left(img):
    d = min(img.size)
    # left, upper, right, and lower
    return (
        0,
        0,
        d,
        d
    )

def right(img):
    d = min(img.size)
    # left, upper, right, and lower
    return (
        img.size[0] - d,
        img.size[1] - d,
        img.size[0],
        img.size[1]
    )

def crop(img, box, resolution):
    img = img.crop(box)
    img = img.resize(resolution, Image.BICUBIC)
    img = img.convert('RGB')
    return img


def crops(img, resolution):
    return (
        crop(img, left(img), resolution),
        crop(img, center(img), resolution),
        crop(img, right(img), resolution)
    )


def crop_to_square(img):
    width = img.width
    height = img.height
    newSize = min(width, height)
    xOffset = (width - newSize) // 2
    yOffset = (height - newSize) // 2
    return img.crop((
        xOffset, yOffset,
        xOffset + newSize, yOffset + newSize
    ))


def average_hue(pixels, tile_b):
    value = 0
    for i in range(len(pixels)):
        # value = value + compare_color(a[i], b[i])
        value += abs(a[i][0] - b[i][0]) + abs(a[i][1] - b[i][1]) * 1.2 + abs(a[i][2] - b[i][2]) * .8
        # value += numpy.linalg.norm((numpy.array(a[i]) * WEIGHTS) - (numpy.array(b[i]) * WEIGHTS))
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


def distance_value(tile_a, tile_b):
    a = tile_a.hsv
    b = tile_b.hsv
    value = 0
    for i in range(len(a)):
        # Hue, Saturation, Value
        value += abs(a[i][2] - b[i][2])
    return value


# 0 = indentical, >0 = different
def compare_color(a, b):
    value = 0
    for i in range(3):
        value = value + abs(a[i] - b[i])
    return value


# 0 = indentical, >0 = different
def average_rgb_color(tile: PaintingTile):
    rgbs = tile.rgb
    total = [0,0,0]
    for rgb in rgbs:
        for i in range(3):
            total[i] += rgb[i]
    count = len(rgbs)
    return [total[0] / count, total[1] / count, total[2] / count]
