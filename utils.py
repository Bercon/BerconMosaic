import math
from PIL import Image

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

