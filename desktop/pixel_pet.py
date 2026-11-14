import math

import cairo

PALETTE = {
    "o": (0.055, 0.095, 0.20),
    "d": (0.15, 0.32, 0.68),
    "b": (0.20, 0.48, 0.94),
    "a": (0.35, 0.65, 1.00),
    "c": (0.60, 0.85, 1.00),
    "w": (0.85, 0.96, 1.00),
    "s": (0.08, 0.17, 0.34),
    "p": (0.47, 0.68, 1.00),
}

HEAD = (
    ".......oo...........",
    ".......owoo.........",
    "........oo..........",
    "...oooooooooooooo...",
    "..ocaaaaaaaaaaabdo..",
    ".ocaaaaaaaaaaaaabdo.",
    ".oaaaaaabbbbbbbabdo.",
    "oaaaasssssssssssbddo",
    "oaabssssssssssssbddo",
    "oaabssssssssssssbddo",
    "oaabssssssssssssbddo",
    "oaabssssssssssssbddo",
    "oaabssssssssssssbddo",
    "oaabssssssssssssbddo",
    "oabbssssssssssssbddo",
    ".odbbddddddddddbddo.",
    ".oddbbbbbbbbbbbdddo.",
    "..oddddddddddddddo..",
    "...oooooooooooooo...",
)

BODY = (
    "......oooooooo......",
    ".....oaaaaabbdo.....",
    "...oodabccabbddoo...",
    "...obbabccabbdddo...",
    "....oodddddddooo....",
    ".....oooooooooo.....",
)


def draw(cr, size, elapsed, direction=1, moving=False, hovered=False):
    pixel = max(1, math.floor(size / 26))
    cr.set_antialias(cairo.ANTIALIAS_NONE)
    cr.translate(math.floor((size - pixel * 20) / 2), math.floor((size - pixel * 25) / 2))
    cr.scale(pixel, pixel)
    for y, x, width, alpha in ((23, 3, 14, 0.13), (24, 5, 10, 0.26)):
        cr.set_source_rgba(0, 0, 0, alpha)
        cr.rectangle(x, y, width, 1)
        cr.fill()
    if direction < 0:
        cr.translate(20, 0)
        cr.scale(-1, 1)
    stride = int(elapsed * 7) % 2 if moving else 0

    def block(x, y, w, h, color):
        cr.set_source_rgb(*PALETTE[color])
        cr.rectangle(x, y, w, h)
        cr.fill()

    for x, offset in ((5, stride), (12, 1 - stride if moving else 0)):
        block(x, 21 + offset, 4, 3, "o")
        block(x + 1, 21 + offset, 2, 2, "d")

    bob = (int(elapsed * 5) % 2) if moving else 0
    for sprite, top in ((BODY, 17), (HEAD, bob)):
        for y, row in enumerate(sprite):
            for x, color in enumerate(row):
                if color != ".":
                    block(x, y + top, 1, 1, color)

    blink = elapsed % 4.9 > 4.72 and not hovered
    for x in (7, 12):
        if blink:
            block(x, 11 + bob, 2, 1, "c")
        else:
            block(x, 9 + bob, 2, 3, "c")
            block(x, 9 + bob, 1, 1, "w")
    block(5, 12 + bob, 2, 1, "p")
    block(14, 12 + bob, 2, 1, "p")
    block(9, 13 + bob, 3, 1, "c")
    if hovered:
        block(10, 12 + bob, 1, 1, "c")
