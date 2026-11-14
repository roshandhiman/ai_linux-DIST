"""Resolution-independent companion drawing, shared by desktop and Settings."""
import math

import cairo


def rounded(cr, x, y, width, height, radius):
    cr.new_sub_path()
    for cx, cy, start in (
        (x + width - radius, y + radius, -math.pi / 2),
        (x + width - radius, y + height - radius, 0),
        (x + radius, y + height - radius, math.pi / 2),
        (x + radius, y + radius, math.pi),
    ):
        cr.arc(cx, cy, radius, start, start + math.pi / 2)
    cr.close_path()


def draw(cr, size, elapsed, direction=1, moving=False, hovered=False):
    cr.save()
    cr.set_antialias(cairo.ANTIALIAS_BEST)
    cr.scale(size / 100, size / 100)
    cr.save()
    cr.translate(50, 88)
    cr.scale(1, .2)
    cr.arc(0, 0, 30, 0, math.tau)
    cr.set_source_rgba(0, 0, 0, .24)
    cr.fill()
    cr.restore()
    bob = math.sin(elapsed * (7 if moving else 2)) * (2 if moving else .8)
    cr.translate(0, bob)
    shell = cairo.LinearGradient(15, 15, 80, 78)
    shell.add_color_stop_rgb(0, .94, .94, .94)
    shell.add_color_stop_rgb(.45, .68, .68, .68)
    shell.add_color_stop_rgb(1, .34, .34, .34)
    rounded(cr, 34, 66, 32, 19, 9)
    cr.set_source(shell)
    cr.fill()
    rounded(cr, 14, 23, 72, 48, 21)
    cr.set_source(shell)
    cr.fill_preserve()
    cr.set_source_rgba(1, 1, 1, .55)
    cr.set_line_width(1)
    cr.stroke()
    rounded(cr, 21, 31, 58, 32, 14)
    face = cairo.LinearGradient(0, 30, 0, 65)
    face.add_color_stop_rgb(0, .055, .055, .055)
    face.add_color_stop_rgb(1, .15, .15, .15)
    cr.set_source(face)
    cr.fill()
    shift = 2 * direction if moving else 0
    blink = elapsed % 5 > 4.82 and not hovered
    for x in (34, 59):
        rounded(cr, x + shift, 42 if blink else 39, 7, 3 if blink else 12, 1.5 if blink else 3.5)
        cr.set_source_rgb(.91, .91, .91)
        cr.fill()
    cr.set_source_rgb(.96, .96, .96)
    cr.set_line_width(2)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.arc(50 + shift, 49, 5, .25, math.pi - .25)
    cr.stroke()
    cr.move_to(50, 23)
    cr.line_to(50, 16)
    cr.set_source_rgb(.8, .8, .8)
    cr.stroke()
    cr.arc(50, 13, 3.5, 0, math.tau)
    cr.set_source_rgb(.95, .95, .95)
    cr.fill()
    cr.arc(50, 75, 3, 0, math.tau)
    cr.set_source_rgb(.94, .94, .94)
    cr.fill()
    cr.restore()
