import math
import subprocess
import threading
import time
from pathlib import Path

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Gst", "1.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gst, Gtk

import preferences
from wallpaper_cache import playback_copy


def surface(window):
    visual = window.get_screen().get_rgba_visual()
    if visual:
        window.set_visual(visual)
    window.set_app_paintable(True)
    window.set_decorated(False)
    window.set_skip_taskbar_hint(True)
    window.set_skip_pager_hint(True)


def ellipse(cr, x, y, width, height, color):
    cr.save()
    cr.translate(x, y)
    cr.scale(width, height)
    cr.arc(0, 0, 1, 0, math.tau)
    cr.set_source_rgba(*color)
    cr.fill()
    cr.restore()


def sphere(cr, x, y, rx, ry, color):
    cr.save()
    cr.translate(x, y)
    cr.scale(rx, ry)
    light = cairo.RadialGradient(-0.33, -0.5, 0.03, 0.05, 0.12, 1.02)
    light.add_color_stop_rgb(0, *(min(1, component * 0.64 + 0.41) for component in color))
    light.add_color_stop_rgb(0.47, *color)
    light.add_color_stop_rgb(1, *(component * 0.53 for component in color))
    cr.set_source(light)
    cr.arc(0, 0, 1, 0, math.tau)
    cr.fill()
    cr.restore()


class Pet(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        surface(self)
        self.set_title("MineOS Companion")
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.set_tooltip_text("Chat with the assistant")
        self.connect("draw", self.paint)
        self.connect("button-press-event", self.press)
        self.connect("button-release-event", self.release)
        self.connect("motion-notify-event", self.drag)
        self.origin = None
        self.held = None
        self.moved = False
        self.motion = True
        self.size = 104
        self.position = None
        GLib.timeout_add(66, self.animate)

    def area(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        return monitor.get_workarea()

    def animate(self):
        if self.get_visible() and self.motion:
            area = self.area()
            offset = math.sin(time.monotonic() * 0.27) * 18
            x, y = self.origin or (area.x + area.width - self.size - 34, area.y + area.height - self.size - 96)
            if not self.held:
                x = max(area.x, min(x + offset, area.x + area.width - self.size))
                y = max(area.y, min(y, area.y + area.height - self.size))
                position = (int(x), int(y))
                if position != self.position:
                    self.move(*position)
                    self.position = position
            self.queue_draw()
        return True

    def press(self, _, event):
        if event.button == 3:
            menu = Gtk.Menu()
            for title, path in [("Chat", "/opt/ai/jarvis_gui.py"), ("Settings", "/opt/ai/desktop/settings.py")]:
                item = Gtk.MenuItem(label=title)
                item.connect("activate", lambda _, target=path: subprocess.Popen(["python3", target]))
                menu.append(item)
            menu.show_all()
            menu.popup_at_pointer(event)
            return True
        self.held = (event.x, event.y)
        self.moved = False
        return True

    def drag(self, _, event):
        if self.held and (abs(event.x - self.held[0]) > 5 or abs(event.y - self.held[1]) > 5):
            self.moved = True
            self.origin = (int(event.x_root - self.held[0]), int(event.y_root - self.held[1]))
            self.move(*self.origin)
        return True

    def release(self, _, event):
        if event.button == 1 and self.held and not self.moved:
            subprocess.Popen(["python3", "/opt/ai/jarvis_gui.py"])
        self.held = None
        return True

    def paint(self, _, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        size = self.get_allocated_width()
        cr.scale(size / 104, size / 104)
        t = time.monotonic() if self.motion else 0
        turn = math.sin(t * 1.18) * 0.66
        bob = math.sin(t * 2.35) * 3.6
        ellipse(cr, 52, 94, 24 - bob / 2, 3.3, (0, 0, 0, 0.22))
        cr.translate(0, bob)
        sin_turn, cos_turn = math.sin(turn), math.cos(turn)
        parts = [
            (-16, 78, 3, 8, 9, (0.56, 0.45, 0.34)),
            (16, 78, 3, 8, 9, (0.56, 0.45, 0.34)),
            (0, 69, 0, 22, 18, (0.88, 0.72, 0.53)),
            (0, 70, 19, 5, 4, (0.42, 0.83, 0.66)),
            (-28, 37, -2, 10, 13, (0.71, 0.55, 0.42)),
            (28, 37, -2, 10, 13, (0.71, 0.55, 0.42)),
            (0, 36, 0, 33, 28, (0.91, 0.82, 0.67)),
            (0, 37, 24, 25 * cos_turn, 15, (0.13, 0.17, 0.18)),
        ]
        parts.sort(key=lambda part: part[2] * cos_turn - part[0] * sin_turn)
        for x, y, z, width, height, color in parts:
            sphere(cr, 52 + x * cos_turn + z * sin_turn, y, width, height, color)
        eye_height = 1.2 if t % 5.4 > 5.2 else 3.1
        for offset in (-9, 9):
            ellipse(cr, 52 + offset * cos_turn + 29 * sin_turn, 36, 3.1, eye_height, (0.58, 0.98, 0.77, 1))
        ellipse(cr, 52 + 29 * sin_turn, 43, 3.2, 1.0, (0.58, 0.98, 0.77, 0.57))
        return True


class LiveWallpaper(Gtk.Window):
    def __init__(self, video, image):
        super().__init__()
        surface(self)
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.set_keep_below(True)
        self.set_accept_focus(False)
        self.player = None
        self.bus = None
        self.started = time.monotonic()
        display = Gdk.Display.get_default()
        bounds = (display.get_primary_monitor() or display.get_monitor(0)).get_geometry()
        self.move(bounds.x, bounds.y)
        self.set_default_size(bounds.width, bounds.height)
        self.connect("destroy", self.stop)
        self.paused = False
        if video:
            Gst.init(None)
            self.player = Gst.ElementFactory.make("playbin")
            sink = Gst.ElementFactory.make("gtksink")
            audio = Gst.ElementFactory.make("fakesink")
            if not all((self.player, sink, audio)):
                raise RuntimeError("The video playback plugin is unavailable.")
            sink.set_property("force-aspect-ratio", False)
            self.add(sink.get_property("widget"))
            self.player.set_property("uri", Path(video).resolve().as_uri())
            self.player.set_property("video-sink", sink)
            self.player.set_property("audio-sink", audio)
            self.player.set_property("mute", True)
            self.bus = self.player.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect("message", self.message)
            self.player.set_state(Gst.State.PLAYING)
        else:
            self.picture = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(image), 1280, 900, True)
            self.connect("draw", self.paint)
            GLib.timeout_add(120, self.tick)
        self.connect("map-event", self.place_window)

    def place_window(self, *_):
        self.input_shape_combine_region(cairo.Region())
        return False

    def tick(self):
        if not self.get_visible():
            return GLib.SOURCE_REMOVE
        if not self.paused:
            self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def paint(self, _, cr):
        width, height = self.get_allocated_width(), self.get_allocated_height()
        iw, ih = self.picture.get_width(), self.picture.get_height()
        t = time.monotonic() - self.started
        scale = max(width / iw, height / ih) * (1.11 + 0.035 * math.sin(t * 0.12))
        cr.translate((width - iw * scale) * (0.5 + 0.33 * math.sin(t * 0.12)), (height - ih * scale) / 2)
        cr.scale(scale, scale)
        Gdk.cairo_set_source_pixbuf(cr, self.picture, 0, 0)
        cr.paint()
        return True

    def pause(self, paused):
        if self.paused != paused:
            self.paused = paused
            if self.player:
                self.player.set_state(Gst.State.PAUSED if paused else Gst.State.PLAYING)

    def message(self, _, message):
        if message.type == Gst.MessageType.EOS:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0)
        elif message.type == Gst.MessageType.ERROR:
            error, _ = message.parse_error()
            print(error.message, flush=True)
            self.destroy()

    def stop(self, *_):
        if self.player:
            self.player.set_state(Gst.State.NULL)
        if self.bus:
            self.bus.remove_signal_watch()


class DesktopCompanion(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.mineos.Companion")
        self.pet = None
        self.live = None
        self.last_wallpaper = None

    def do_activate(self):
        if self.pet is not None:
            return
        self.hold()
        self.pet = Pet()
        self.prepare_timer = 0
        self.preparing = False
        self.values = None
        preferences.PREFS.parent.mkdir(parents=True, exist_ok=True)
        self.monitor = Gio.File.new_for_path(str(preferences.PREFS.parent)).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        self.monitor.connect("changed", self.preferences_changed)
        self.pref_timer = 0
        self.refresh()
        GLib.timeout_add(750, self.update_visibility)

    def preferences_changed(self, _, changed, other, event):
        if all(file is None or file.get_basename() != preferences.PREFS.name for file in (changed, other)):
            return
        if self.pref_timer:
            GLib.source_remove(self.pref_timer)
        self.pref_timer = GLib.timeout_add(160, self.refresh)

    def refresh(self):
        self.pref_timer = 0
        values = preferences.read()
        previous = self.values or {}
        self.values = values
        if self.pet.size != values["pet_size"] or not previous:
            self.pet.size = values["pet_size"]
            self.pet.resize(self.pet.size, self.pet.size)
        self.pet.motion = values["pet_motion"]
        self.pet.set_visible(values["pet"])
        if not previous and values["pet"]:
            area = self.pet.area()
            self.pet.move(area.x + area.width - self.pet.size - 34, area.y + area.height - self.pet.size - 96)
        self.pet.queue_draw()
        current = (values["live"], values["video"], values["backdrop"])
        if current != self.last_wallpaper:
            self.last_wallpaper = current
            if self.prepare_timer:
                GLib.source_remove(self.prepare_timer)
                self.prepare_timer = 0
            if self.live:
                self.live.destroy()
                self.live = None
            if current[0]:
                self.prepare_timer = GLib.timeout_add_seconds(3 if not previous else 1, self.prepare, current)
        return GLib.SOURCE_REMOVE

    def prepare(self, current):
        self.prepare_timer = 0
        if self.preparing:
            self.prepare_timer = GLib.timeout_add_seconds(1, self.prepare, current)
        elif current[1]:
            self.preparing = True
            threading.Thread(target=self.prepare_video, args=(current,), daemon=True).start()
        else:
            self.show_wallpaper(current, None)
        return GLib.SOURCE_REMOVE

    def prepare_video(self, current):
        try:
            path = playback_copy(current[1])
        except (OSError, subprocess.SubprocessError) as error:
            print(f"Could not prepare wallpaper: {error}", flush=True)
            path = None
        GLib.idle_add(self.video_ready, current, path)

    def video_ready(self, current, path):
        self.preparing = False
        if path:
            self.show_wallpaper(current, path)
        return GLib.SOURCE_REMOVE

    def show_wallpaper(self, current, video):
        if current != self.last_wallpaper:
            return
        try:
            image = Path(current[2])
            if not image.is_file():
                image = Path(preferences.DEFAULTS["backdrop"])
            self.live = LiveWallpaper(video, image)
            self.live.connect("destroy", self.wallpaper_closed)
            self.live.show_all()
            self.update_visibility()
        except (OSError, GLib.Error, RuntimeError) as error:
            print(error, flush=True)

    def wallpaper_closed(self, wallpaper):
        if self.live is wallpaper:
            self.live = None

    def update_visibility(self):
        if self.live:
            active = Gdk.Screen.get_default().get_active_window()
            monitor = self.pet.area()
            covered = False
            if active and active.get_window_type() == Gdk.WindowType.FOREIGN:
                _, _, width, height = active.get_geometry()
                covered = width >= monitor.width * 0.96 and height >= monitor.height * 0.96
            self.live.pause(covered)
        return GLib.SOURCE_CONTINUE


if __name__ == "__main__":
    DesktopCompanion().run(None)
