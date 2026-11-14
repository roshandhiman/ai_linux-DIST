from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

FRAMES = Path("/usr/share/plymouth/themes/mineos")


class Preview(Gtk.Window):
    def __init__(self):
        super().__init__(title="Startup Animation")
        self.set_default_size(820, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.frames = [GdkPixbuf.Pixbuf.new_from_file(str(FRAMES / f"frame-{index}.png")) for index in range(24)]
        self.index = 0
        self.full = False
        bar = Gtk.HeaderBar(title="Startup Animation", show_close_button=True)
        button = Gtk.Button.new_from_icon_name("view-fullscreen-symbolic", Gtk.IconSize.BUTTON)
        button.set_tooltip_text("Full Screen")
        button.connect("clicked", self.toggle)
        bar.pack_end(button)
        self.set_titlebar(bar)
        drawing = Gtk.DrawingArea()
        drawing.connect("draw", self.paint)
        self.add(drawing)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.key)
        GLib.timeout_add(80, self.tick)

    def toggle(self, *_):
        self.full = not self.full
        if self.full:
            self.fullscreen()
        else:
            self.unfullscreen()

    def key(self, _, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close()

    def tick(self):
        self.index = (self.index + 1) % len(self.frames)
        self.queue_draw()
        return True

    def paint(self, area, cr):
        cr.set_source_rgb(0.045, 0.047, 0.05)
        cr.paint()
        frame = self.frames[self.index]
        x = (area.get_allocated_width() - frame.get_width()) // 2
        y = (area.get_allocated_height() - frame.get_height()) // 2
        Gdk.cairo_set_source_pixbuf(cr, frame, x, y)
        cr.paint()


if __name__ == "__main__":
    Preview().show_all()
    Gtk.main()
