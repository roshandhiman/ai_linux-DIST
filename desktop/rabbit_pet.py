import json
from functools import lru_cache
from pathlib import Path

from gi.repository import Gdk, GdkPixbuf

ASSETS = Path(__file__).resolve().parent / "assets" / "pockito-rabbit"
with (ASSETS / "animations.json").open() as manifest:
    data = json.load(manifest)
FPS = data["fps"]
BODY_SIZE = data["bodySize"]
WIDTH = data["width"]
HEIGHT = data["height"]
LEFT_PAD = data["leftPad"]
TOP_PAD = data["topPad"]
COLUMNS = data["columns"]
CLIPS = data["clips"]
RECTS = data["rects"]


def viewport(size):
    scale = size / BODY_SIZE
    return round(WIDTH * scale), round(HEIGHT * scale), round(LEFT_PAD * scale), round(TOP_PAD * scale)


def pointer_rect(size):
    x, y, width, height = RECTS["idle"]
    scale = size / BODY_SIZE
    return (round((x - 12) * scale), round((y - 30) * scale),
            round((width + 24) * scale), round((height + 30) * scale))


@lru_cache(maxsize=3)
def sheet(name):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(ASSETS / f"{name}.png"))
    return Gdk.cairo_surface_create_from_pixbuf(pixbuf, 1, None)


def draw(cr, size, name="idle", frame=0, mirrored=False):
    frame %= CLIPS[name]
    row, column = divmod(frame, COLUMNS)
    x, y, width, height = RECTS[name]
    cr.save()
    cr.scale(size / BODY_SIZE, size / BODY_SIZE)
    if mirrored:
        cr.translate(WIDTH, 0)
        cr.scale(-1, 1)
    cr.rectangle(x, y, width, height)
    cr.clip()
    cr.set_source_surface(sheet(name), x - column * width, y - row * height)
    cr.paint()
    cr.restore()


def draw_preview(cr, size):
    _, _, left, top = viewport(size)
    cr.save()
    cr.translate(-left, -top)
    draw(cr, size)
    cr.restore()
