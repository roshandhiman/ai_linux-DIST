import shutil
import subprocess
import sys
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
from gi.repository import Gdk, GdkX11, Gio, GLib, Gtk

from glass_theme import DOCK_EDGE_GAP


class Spacer(Gtk.Window):
    def __init__(self, ready):
        super().__init__(title="MineOS Dock Spacing")
        self.ready = ready
        self.set_decorated(False)
        self.set_accept_focus(False)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_below(True)
        self.set_opacity(0)
        self.realize()
        self.get_window().input_shape_combine_region(cairo.Region(), 0, 0)
        self.screen = self.get_screen()
        self.dock = Gio.Settings.new_with_path("net.launchpad.plank.dock.settings", "/net/launchpad/plank/docks/dock1/")
        self.dock.connect("changed::position", self.update)
        self.dock.connect("changed::monitor", self.update)
        for signal in ("monitors-changed", "size-changed", "composited-changed"):
            self.screen.connect(signal, self.update)
        self.update()
        GLib.timeout_add(140, self.mark_ready)

    def mark_ready(self):
        self.ready.touch()
        return GLib.SOURCE_REMOVE

    def update(self, *_):
        if not self.screen.is_composited():
            self.hide()
            return
        selected = self.dock.get_string("monitor")
        monitor = self.screen.get_primary_monitor()
        if selected:
            for number in range(self.screen.get_n_monitors()):
                name = self.screen.get_monitor_plug_name(number) or f"PLUG_MONITOR_{number}"
                if name == selected:
                    monitor = number
                    break
        area = self.screen.get_monitor_geometry(max(0, monitor))
        side = self.dock.get_string("position")
        if (side == "left" and area.x != 0 or
            side == "right" and area.x + area.width != self.screen.get_width() or
            side == "bottom" and area.y + area.height != self.screen.get_height() or
            side == "top" and area.y != 0):
            self.hide()
            return

        sides = ("left", "right", "top", "bottom")
        if side not in sides:
            self.hide()
            return
        gap = DOCK_EDGE_GAP
        edge = sides.index(side)
        strut = [0] * 12
        strut[edge] = gap
        vertical = edge < 2
        start, length = (area.y, area.height) if vertical else (area.x, area.width)
        strut[4 + 2 * edge:6 + 2 * edge] = [start, start + length - 1]
        x = area.x + (area.width - gap if side == "right" else 0)
        y = area.y + (area.height - gap if side == "bottom" else 0)
        size = (gap, 1) if vertical else (1, gap)
        self.set_default_size(*size)
        self.resize(*size)
        self.move(x, y)
        try:
            subprocess.run(
                ["xprop", "-id", str(self.get_window().get_xid()), "-f", "_NET_WM_STRUT_PARTIAL", "32c",
                 "-set", "_NET_WM_STRUT_PARTIAL", ", ".join(map(str, strut))],
                check=True, timeout=1, capture_output=True,
            )
        except (subprocess.SubprocessError, OSError):
            self.hide()
            return
        self.show()


if __name__ == "__main__":
    ready = Path(sys.argv[1])
    if shutil.which("xprop") and isinstance(Gdk.Display.get_default(), GdkX11.X11Display):
        spacer = Spacer(ready)
        Gtk.main()
    else:
        ready.touch()
