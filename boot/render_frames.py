import random
import sys
from pathlib import Path

import cairo

WIDTH, HEIGHT = 520, 180


def wordmark():
    canvas = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    cr = cairo.Context(canvas)
    cr.set_source_rgb(0.93, 0.935, 0.925)
    cr.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(70)
    text = "MineOS"
    extents = cr.text_extents(text)
    cr.move_to((WIDTH - extents.width) / 2 - extents.x_bearing, 102)
    cr.show_text(text)
    return canvas


def render(output):
    output.mkdir(parents=True, exist_ok=True)
    mark = wordmark()
    for frame in range(24):
        canvas = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
        cr = cairo.Context(canvas)
        cr.set_source_surface(mark)
        cr.paint()
        rng = random.Random(frame)
        if frame in (0, 1, 2, 10, 11, 18):
            for _ in range(9):
                y = rng.randrange(39, 110)
                height = rng.randrange(1, 7)
                dx = rng.choice((-15, -7, 6, 17, 22))
                cr.save()
                cr.rectangle(116, y, 288, height)
                cr.clip()
                cr.set_operator(cairo.OPERATOR_SOURCE)
                cr.set_source_surface(mark, dx)
                cr.paint()
                cr.set_operator(cairo.OPERATOR_OVER)
                cr.set_source_rgba(*rng.choice(((0.25, 0.88, 0.67, 0.44), (0.97, 0.54, 0.33, 0.38))))
                cr.rectangle(126 + rng.randrange(230), y, rng.randrange(5, 44), 1)
                cr.fill()
                cr.restore()
        for segment in range(16):
            distance = (frame - segment) % 16
            cr.set_source_rgba(0.66, 0.90, 0.78, 0.75 - 0.13 * min(distance, 4))
            cr.rectangle(197 + segment * 8, 128, 4, 2)
            cr.fill()
        canvas.write_to_png(str(output / f"frame-{frame}.png"))


if __name__ == "__main__":
    render(Path(sys.argv[1]))
