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
from pixel_pet import draw as draw_pet
from wallpaper_cache import playback_copy


def surface(window):
    visual = window.get_screen().get_rgba_visual()
    if visual:
        window.set_visual(visual)
    window.set_app_paintable(True)
    window.set_decorated(False)
    window.set_skip_taskbar_hint(True)
    window.set_skip_pager_hint(True)


class Pet(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        surface(self)
        self.set_title("MineOS Companion")
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.set_tooltip_text("Chat with the assistant")
        self.connect("draw", self.paint)
        self.connect("button-press-event", self.press)
        self.connect("button-release-event", self.release)
        self.connect("motion-notify-event", self.drag)
        self.connect("enter-notify-event", self.hover, True)
        self.connect("leave-notify-event", self.hover, False)
        self.connect("map-event", self.place)
        self.connect("size-allocate", self.shape)
        self.origin = None
        self.held = None
        self.moved = False
        self.motion = True
        self.size = preferences.DEFAULTS["pet_size"]
        self.position = None
        self.hovered = False
        self.direction = 1
        self.walking = False
        self.frame = None
        self.started = time.monotonic()
        GLib.timeout_add(100, self.animate)

    def area(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        return monitor.get_workarea()

    def place(self, *_):
        self.reposition(0)
        window = self.get_window()
        if window:
            cursor = Gdk.Cursor.new_from_name(window.get_display(), "pointer")
            window.set_cursor(cursor)
        return False

    def shape(self, _, size):
        if self.get_window():
            side = min(size.width, size.height)
            pixel = max(1, side // 26)
            inset = (side - 20 * pixel) // 2
            top = (side - 25 * pixel) // 2
            self.input_shape_combine_region(cairo.Region(cairo.RectangleInt(inset, top, 20 * pixel, 24 * pixel)))

    def hover(self, _, __, hovered):
        self.hovered = hovered
        self.queue_draw()
        return False

    def reposition(self, offset):
        area = self.area()
        x, y = self.origin or (area.x + area.width - self.size - 34, area.y + area.height - self.size - 82)
        x = max(area.x, min(x + offset, area.x + area.width - self.size))
        y = max(area.y, min(y, area.y + area.height - self.size))
        position = (int(x), int(y))
        if position != self.position:
            self.move(*position)
            self.position = position

    def animate(self):
        if not self.get_visible() or not self.motion:
            return GLib.SOURCE_CONTINUE
        elapsed = time.monotonic() - self.started
        phase = elapsed % 16
        self.walking = not self.hovered and not self.held and phase < 9
        if self.walking:
            self.direction = -1 if phase < 4.5 else 1
            travel = phase if phase < 4.5 else 9 - phase
            self.reposition(-travel * 11)
        elif not self.hovered and not self.held:
            self.reposition(0)
        frame = (self.direction, self.walking, elapsed % 4.9 > 4.72,
                 (int(elapsed * 7) % 2, int(elapsed * 5) % 2) if self.walking else None)
        if self.frame != frame:
            self.frame = frame
            self.queue_draw()
        return GLib.SOURCE_CONTINUE

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
        if event.button != 1:
            return False
        self.held = (event.x, event.y)
        self.moved = False
        return True

    def drag(self, _, event):
        if self.held and (abs(event.x - self.held[0]) > 5 or abs(event.y - self.held[1]) > 5):
            self.moved = True
            self.origin = (int(event.x_root - self.held[0]), int(event.y_root - self.held[1]))
            self.reposition(0)
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
        elapsed = time.monotonic() - self.started if self.motion else 0
        draw_pet(cr, min(self.get_allocated_width(), self.get_allocated_height()), elapsed,
                 self.direction, self.walking and self.motion, self.hovered)
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
        if values["pet"] and (not previous or not self.pet.motion or values["pet_size"] != previous["pet_size"]):
            self.pet.reposition(0)
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
            if current[0] and (current[1] or current[2]):
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
            self.live = LiveWallpaper(video, Path(current[2]))
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
