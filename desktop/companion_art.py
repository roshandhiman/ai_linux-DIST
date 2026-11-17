"""Mino's hand-placed pixel art, shared by the desktop, Settings, and chat."""

from functools import lru_cache
from itertools import groupby

import cairo


# The cabinet, screen, and tiny hardware details share this fixed palette.
PALETTE = {
    "o": 0x342B43,  # Ink outline
    "l": 0xA18DAB,  # Cabinet edge in shadow
    "h": 0xFFF1D2,  # Cabinet highlight
    "c": 0xE7CBA1,  # Warm plastic
    "s": 0xB38372,  # Side panel
    "d": 0x826072,  # Recess, feet, vents
    "n": 0x293647,  # CRT glass
    "b": 0x3C5360,  # Bottom of the glass
    "m": 0xBAE9C4,  # Green phosphor and power LED
    "p": 0xF0A68B,  # Button and cheeks
}

CABINET = (
    "........................",
    ".............oo.........",
    "............ommo........",
    ".............oo.........",
    "............ol..........",
    "...........ol...........",
    "...oooooooooooooooo.....",
    "..ohhhhhhhhhhhhhhclo....",
    ".ohccccccccccccchcslo...",
    ".ohcooooooooooocccsdo...",
    ".ohconnnnnnnnnocccsdo...",
    ".ohconnnnnnnnnocposdo...",
    ".ohconnnnnnnnnocpcsdo...",
    ".ohconnnnnnnnnoccdddo...",
    ".ohcobbbbbbbbbochsddo...",
    ".ohccooooooooocmcsddo...",
    ".ochccccccccccccssldo...",
    "..occcccccccccccsldo....",
    "...ooooooooooooooo......",
    "....oddo.....oddo.......",
    ".....oo.......oo........",
    "........................",
    "........................",
    "........................",
)

# The face frames replace only the picture on the CRT.
FACES = {
    "idle": (
        "nnnnnnnnn",
        "nnmnnnmnn",
        "nnmnnnmnn",
        "pnnnmnnnp",
        "bbbbbbbbb",
    ),
    "blink": (
        "nnnnnnnnn",
        "nnnnnnnnn",
        "nmmnnmmnn",
        "pnnnmnnnp",
        "bbbbbbbbb",
    ),
    "happy": (
        "nnnnnnnnn",
        "nnmnnnmnn",
        "nmnmnmnmn",
        "pnnmnmnnp",
        "bbbbmbbbb",
    ),
}

GRID_SIZE = len(CABINET)


def dimensions(size):
    """Return whole logical pixels per tile and center the sprite in its window."""
    tile = max(1, int(size) // GRID_SIZE)
    return tile, (int(size) - GRID_SIZE * tile) // 2


def hit_boxes(size):
    tile, inset = dimensions(size)
    for y, row in enumerate(CABINET):
        x = 0
        for opaque, run in groupby(row, lambda symbol: symbol != "."):
            width = sum(1 for _ in run)
            if opaque:
                yield inset + x * tile, inset + y * tile, width * tile, tile
            x += width


@lru_cache(maxsize=len(FACES))
def frame(face):
    # Paint unscaled, then copy the finished sprite with nearest-neighbor filtering.
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, GRID_SIZE, GRID_SIZE)
    cr = cairo.Context(surface)
    cr.set_antialias(cairo.ANTIALIAS_NONE)
    image = list(CABINET)
    for y, pixels in enumerate(FACES[face], start=10):
        image[y] = image[y][:5] + pixels + image[y][14:]
    for y, row in enumerate(image):
        for x, symbol in enumerate(row):
            if symbol == ".":
                continue
            rgb = PALETTE[symbol]
            cr.set_source_rgb((rgb >> 16) / 255, ((rgb >> 8) & 255) / 255, (rgb & 255) / 255)
            cr.rectangle(x, y, 1, 1)
            cr.fill()
    return surface


def expression(phase, hovered, greeting):
    if hovered or greeting:
        return "happy"
    if 4.5 < phase % 4.8 < 4.68:
        return "blink"
    return "idle"


def draw(cr, size, face="idle"):
    tile, inset = dimensions(size)
    cr.save()
    cr.translate(inset, inset)
    cr.scale(tile, tile)
    cr.set_source_surface(frame(face))
    cr.get_source().set_filter(cairo.FILTER_NEAREST)
    cr.paint()
    cr.restore()
