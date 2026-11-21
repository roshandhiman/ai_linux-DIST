import json
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

import companion_art
import native_wallpaper
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


class Pet(Gtk.Window):
    MIC_SIZE = 32

    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        surface(self)
        self.set_title("MineOS Companion")
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.get_accessible().set_name("Mino, MineOS Companion")
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.connect("draw", self.paint)
        self.connect("button-press-event", self.press)
        self.connect("button-release-event", self.release)
        self.connect("motion-notify-event", self.drag)
        self.connect("enter-notify-event", self.hover, True)
        self.connect("leave-notify-event", self.hover, False)
        self.connect("map-event", self.place)
        self.connect("size-allocate", self.shape)
        screen = self.get_screen()
        self.screen_signals = [screen.connect(signal, self.reposition) for signal in ("monitors-changed", "size-changed")]
        self.connect("destroy", self.dispose)
        self.controls = Gtk.Fixed()
        self.add(self.controls)
        self.controls.show()
        self.mic = Gtk.Button.new_from_icon_name("audio-input-microphone-symbolic", Gtk.IconSize.MENU)
        self.mic.set_name("mino-mic")
        self.mic.set_size_request(self.MIC_SIZE, self.MIC_SIZE)
        self.mic.set_focus_on_click(False)
        self.mic.set_tooltip_text("Talk to Mino")
        self.mic.get_accessible().set_name("Talk to Mino")
        self.mic.connect("clicked", self.open_voice)
        self.controls.put(self.mic, 0, 0)
        self.mic.show()
        style = Gtk.CssProvider()
        style.load_from_data(b"""
            #mino-mic {
                min-width: 0; min-height: 0; padding: 0; border-radius: 16px;
                color: #bae9c4; background: #293647; border: 1px solid #826072;
                box-shadow: none;
            }
            #mino-mic:hover { color: #fff1d2; background: #3c5360; }
            #mino-mic:active { color: #293647; background: #bae9c4; }
        """)
        self.mic.get_style_context().add_provider(style, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.voice_command = None
        self.origin = self.load_position()
        self.position = None
        self.held = None
        self.moved = False
        self.hovered = False
        self.motion = False
        self.size = 0
        self.animation = 0
        self.greet_until = 0
        self.drawn_face = None
        self.started = time.monotonic()

    @staticmethod
    def load_position():
        try:
            value = json.loads(preferences.PET_POSITION.read_text())
            if isinstance(value, list) and len(value) == 2 and all(type(n) is int for n in value):
                return tuple(value)
        except (OSError, ValueError):
            pass
        return None

    def save_position(self):
        try:
            preferences.write(preferences.PET_POSITION, json.dumps(self.origin) + "\n")
        except OSError as error:
            print(f"Could not save the companion position: {error}", flush=True)

    def area(self):
        display = self.get_display()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        return monitor.get_workarea()

    def reposition(self, *_):
        area = self.area()
        if self.origin:
            monitor = self.get_display().get_monitor_at_point(*self.origin)
            if monitor:
                area = monitor.get_workarea()
            x, y = self.origin
        else:
            x = area.x + area.width - self.size - 30
            y = area.y + area.height - self.size - 24
        position = (max(area.x, min(x, area.x + area.width - self.size)),
                    max(area.y, min(y, area.y + area.height - self.size)))
        if position != self.position:
            self.position = position
            self.move(*position)

    def place(self, *_):
        self.reposition()
        window = self.get_window()
        window.set_cursor(Gdk.Cursor.new_from_name(window.get_display(), "grab"))
        self.shape()
        return False

    def shape(self, *_):
        if self.get_window():
            region = cairo.Region()
            for box in companion_art.hit_boxes(self.size):
                region.union(cairo.RectangleInt(*box))
            x, y = self.mic_position()
            region.union(cairo.RectangleInt(x, y, self.MIC_SIZE, self.MIC_SIZE))
            self.input_shape_combine_region(region)
            if not self.get_screen().is_composited():
                self.shape_combine_region(region)

    def mic_position(self):
        tile, inset = companion_art.dimensions(self.size)
        return self.size - self.MIC_SIZE, max(0, inset + 6 * tile - self.MIC_SIZE)

    def configure(self, visible, motion, size):
        self.motion = motion
        if self.size != size:
            self.size = size
            self.controls.move(self.mic, *self.mic_position())
            self.resize(size, size)
            self.shape()
        self.reposition()
        self.set_visible(visible)
        if visible and motion and not self.animation:
            self.animation = GLib.timeout_add(50, self.redraw)
        elif self.animation and not (visible and motion):
            GLib.source_remove(self.animation)
            self.animation = 0
        self.queue_draw()

    def dispose(self, *_):
        if self.animation:
            GLib.source_remove(self.animation)
        for handler in self.screen_signals:
            self.get_screen().disconnect(handler)

    def face(self):
        now = time.monotonic()
        phase = now - self.started if self.motion and not self.held else 0
        return companion_art.expression(phase, self.hovered, self.motion and now < self.greet_until)

    def redraw(self):
        if self.face() != self.drawn_face:
            self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def hover(self, _, __, hovered):
        self.hovered = hovered
        self.queue_draw()
        return False

    def press(self, _, event):
        if event.button == 3:
            menu = Gtk.Menu()
            for title, action in (
                ("Talk to Mino", self.open_voice),
                ("Open Assistant", self.open_chat),
                ("Companion Settings", self.open_settings),
                ("Reset Position", self.reset_position),
            ):
                item = Gtk.MenuItem(label=title)
                item.connect("activate", action)
                menu.append(item)
            menu.connect("selection-done", lambda widget: widget.destroy())
            menu.show_all()
            menu.popup_at_pointer(event)
            return True
        if event.button != 1:
            return False
        self.held = (event.x_root, event.y_root, *self.position)
        self.moved = False
        return True

    def drag(self, _, event):
        if self.held:
            start_x, start_y, x, y = self.held
            dx = event.x_root - start_x
            dy = event.y_root - start_y
            if self.moved or abs(dx) > 5 or abs(dy) > 5:
                self.moved = True
                self.origin = (round(x + dx), round(y + dy))
                self.reposition()
        return True

    def release(self, _, event):
        if event.button != 1 or not self.held:
            return False
        self.held = None
        if self.moved:
            self.origin = self.position
            self.save_position()
        else:
            self.greet_until = time.monotonic() + 0.45
            self.queue_draw()
            self.open_chat()
        return True

    def open_chat(self, *_):
        chat = Path(__file__).resolve().parent.parent / "jarvis_gui.py"
        subprocess.Popen(["python3", str(chat)])

    def open_voice(self, *_):
        if self.voice_command is not None:
            return
        try:
            self.voice_command = Gio.Subprocess.new(
                ["mino", "listen"], Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_PIPE
            )
            self.voice_command.communicate_utf8_async(None, None, self.voice_finished)
        except GLib.Error:
            self.voice_error("Install the Mino voice assistant to use the mic button.")

    def voice_finished(self, process, result):
        self.voice_command = None
        try:
            _, _, error = process.communicate_utf8_finish(result)
            if process.get_successful():
                return
            message = (error or "").strip()
        except GLib.Error:
            message = ""
        self.voice_error(message or "Start the Mino voice service and try again.")

    def voice_error(self, message):
        dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                                   text="Could not start Mino voice")
        dialog.format_secondary_text(message)
        dialog.connect("response", lambda window, _: window.destroy())
        dialog.show()

    def open_settings(self, *_):
        settings = Path(__file__).with_name("settings.py")
        subprocess.Popen(["python3", str(settings), "assistant"])

    def reset_position(self, *_):
        self.origin = None
        self.save_position()
        self.reposition()

    def paint(self, _, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        self.drawn_face = self.face()
        companion_art.draw(cr, self.size, self.drawn_face)
        return False


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
        self.pet.configure(values["pet"], values["pet_motion"], values["pet_size"])
        current = (values["live"] and not native_wallpaper.available(), values["video"], values["backdrop"])
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
