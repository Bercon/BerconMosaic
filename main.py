import os
import sys
from glob import glob
from PIL import Image

PICTURE_PATH = 'S:/Projects/Mosaic/jerry.jpg'
TILE_PATH = 'S:/Projects/Mosaic/resized'
INDEX_SIZE = (3,3)
PICTURE_TILES = (60, 60)
OUTPUT_SIZE = (900, 900)

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


def get_pixels(img):
    img = crop_to_square(img)
    img = img.resize(INDEX_SIZE, Image.BICUBIC)
    img = img.convert('RGB')
    size = img.size
    pixels = []
    for x in range(size[0]):
        for y in range(size[1]):
            pixels.append(img.getpixel((x, y)))
    return pixels


def index_image(filename):
    try:
        img = Image.open(filename, 'r')
        size = img.size
        return {
            'filename': filename,
            'size': size,
            'pixels': get_pixels(img)
        }
    except:
        print('Couldn\'t index %s' % filename)


def index_picture(filename):
    img = Image.open(filename, 'r')
    img = crop_to_square(img)
    res = (PICTURE_TILES[0] * INDEX_SIZE[0], PICTURE_TILES[1] * INDEX_SIZE[1])
    img = img.resize(res, Image.BICUBIC)
    tiles = []
    for j in range(PICTURE_TILES[1]):
        for i in range(PICTURE_TILES[0]):
            tile = []
            x_base = i * INDEX_SIZE[0]
            y_base = j * INDEX_SIZE[1]
            for x_off in range(INDEX_SIZE[0]):
                for y_off in range(INDEX_SIZE[1]):
                    tile.append(img.getpixel((x_base + x_off, y_base + y_off)))
            tiles.append(tile)
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
def compare(a, b):
    value = 0
    for i in range(len(a)):
        value = value + compare_color(a[i], b[i])
    return value


def find_closest_match(palette, tile):
    closest_value = sys.maxint
    closest_tile = None
    for index_tile in palette:
        value = compare(index_tile['pixels'], tile)
        if value < closest_value:
            closest_value = value
            closest_tile = index_tile
    return closest_tile


def find_tiles(palette, picture):
    tiles = []
    for i in range(len(picture)):
        sys.stdout.write('\rFinding tiles %d' % (100.0 * i / len(picture)))
        closest_tile = find_closest_match(palette, picture[i])
        tiles.append(closest_tile)
    print
    return tiles


def render_mosaic(tiles):
    img = Image.new('RGB', OUTPUT_SIZE)
    tile_size = (OUTPUT_SIZE[0] / PICTURE_TILES[0], OUTPUT_SIZE[1] / PICTURE_TILES[1])
    for i in range(len(tiles)):
        x = i % PICTURE_TILES[0]
        y = i // PICTURE_TILES[0] # // is floor division
        tile_img = crop_to_square(Image.open(tiles[i]['filename']))
        tile_img = tile_img.resize(tile_size)
        img.paste(tile_img, (x * tile_size[0], y * tile_size[1]))
    return img


if __name__ == '__main__':
    print 'Indexing picture...'
    picture = index_picture(PICTURE_PATH)
    print 'Indexing...'
    palette = index_folder(TILE_PATH)
    print 'Finding tiles...'
    tiles = find_tiles(palette, picture)
    print 'Rendering mosaic...'
    img = render_mosaic(tiles)
    print 'Done!'
    img.show()
