"""GTK status, settings, and file approvals."""

import threading

from .config import LANGUAGES, SIZES, VOICES, Settings, save

LABELS = {"listening": "Listening…", "thinking": "Thinking…", "speaking": "Speaking…",
          "error": "Mino needs attention"}


class Overlay:
    def __init__(self):
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk, GLib, Gtk
        if not Gtk.init_check()[0]:
            raise RuntimeError("No graphical session is available.")
        self.Gtk, self.GLib = Gtk, GLib
        self.last_detail = ""
        self.state = "idle"
        self.generation = 0
        self.on_stop = lambda: self._show("idle", "")
        self.expiry = 0
        self.window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.window.set_decorated(False)
        self.window.set_accept_focus(False)
        self.window.set_keep_above(True)
        self.window.set_resizable(False)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_name("mino")
        box = Gtk.Box(spacing=10)
        box.set_border_width(12)
        label = self.label = Gtk.Label(xalign=0, yalign=.5)
        label.set_name("mino-status")
        label.set_line_wrap(True)
        label.set_max_width_chars(42)
        box.pack_start(label, True, True, 0)
        self.stop_button = Gtk.Button.new_from_icon_name("process-stop-symbolic", Gtk.IconSize.MENU)
        self.stop_button.set_name("mino-stop")
        self.stop_button.set_tooltip_text("Stop Mino")
        self.stop_button.get_accessible().set_name("Stop Mino")
        self.stop_button.set_focus_on_click(False)
        self.stop_button.connect("clicked", lambda *_: self.on_stop())
        box.pack_start(self.stop_button, False, False, 0)
        self.window.add(box)
        css = Gtk.CssProvider()
        css.load_from_data(b"""
            #mino {background: #20252e; color: #f1f3f7; border: 1px solid #526474;
                   border-radius: 12px; min-width: 0; min-height: 0;}
            #mino-status {color: #f1f3f7; padding: 0; margin: 0; min-height: 0;}
            #mino-stop {color: #bae9c4; background: #303b48; border-radius: 16px;
                        padding: 6px; margin: 0; min-width: 16px; min-height: 16px;}
            #mino-stop:hover {background: #4a596c;}
        """)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.window.connect("size-allocate", self.place)
        self.last_settings = None

    def show(self, state, detail=""):
        self.GLib.idle_add(self._show, state, detail)

    def _show(self, state, detail):
        self.state = state
        self.generation += 1
        generation = self.generation
        if self.expiry:
            self.GLib.source_remove(self.expiry)
            self.expiry = 0
        if state == "idle":
            self.window.hide()
            return False
        self.label.set_text(f"Mino  ·  {LABELS.get(state, state)}" + (f"\n{detail[:430]}" if detail else ""))
        self.window.show_all()
        self.window.resize(1, 1)
        self.place()
        if state in ("listening", "thinking", "speaking"):
            self.expiry = self.GLib.timeout_add_seconds(
                {"listening": 14, "thinking": 25, "speaking": 60}[state],
                self.expire, generation)
        elif state == "error":
            self.expiry = self.GLib.timeout_add_seconds(7, self.expire, generation)
        return False

    def expire(self, generation):
        self.expiry = 0
        if generation == self.generation:
            if self.state == "error":
                self._show("idle", "")
            else:
                self.on_stop()
        return False

    def place(self, *_):
        display = self.window.get_display()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        if monitor:
            bounds = monitor.get_workarea()
            width, height = self.window.get_size()
            self.window.move(bounds.x + (bounds.width - width) // 2, bounds.y + bounds.height - height - 24)
        return False

    def approve(self, title, detail):
        ready = threading.Event()
        answer = []

        def dialog():
            if ready.is_set():
                return False
            Gtk = self.Gtk
            prompt = Gtk.Dialog(title="Mino approval", flags=Gtk.DialogFlags.MODAL)
            prompt.set_default_size(520, 280)
            prompt.add_button("Cancel", Gtk.ResponseType.CANCEL)
            prompt.add_button("Confirm", Gtk.ResponseType.OK)
            prompt.set_default_response(Gtk.ResponseType.CANCEL)
            layout = prompt.get_content_area()
            layout.set_border_width(12)
            title_label = Gtk.Label(label=title, xalign=0)
            title_label.set_line_wrap(True)
            layout.pack_start(title_label, False, False, 6)
            scrolled = Gtk.ScrolledWindow()
            view = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
            view.get_buffer().set_text(detail or "Review this action before continuing.")
            scrolled.add(view)
            layout.pack_start(scrolled, True, True, 4)
            def done(window, response):
                if not ready.is_set():
                    answer.append(response == Gtk.ResponseType.OK)
                    ready.set()
                window.destroy()
            prompt.connect("response", done)
            prompt.connect("delete-event", lambda window, event: (done(window, Gtk.ResponseType.CANCEL), True)[1])
            prompt.show_all()
            prompt.present()
            self.GLib.timeout_add_seconds(35, lambda: (prompt.response(Gtk.ResponseType.CANCEL), False)[1]
                                         if not ready.is_set() else False)
            return False

        self.GLib.idle_add(dialog)
        ready.wait(36)
        ready.set()
        return bool(answer and answer[0])

    def settings(self, runtime):
        self.GLib.idle_add(self._settings, runtime)

    def _settings(self, runtime):
        if self.last_settings:
            self.last_settings.present()
            return False
        Gtk = self.Gtk
        existing = runtime.settings
        dialog = Gtk.Dialog(title="Mino Voice Settings")
        self.last_settings = dialog
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save", Gtk.ResponseType.OK)
        dialog.set_resizable(False)
        grid = Gtk.Grid(column_spacing=18, row_spacing=10, margin=16)
        dialog.get_content_area().add(grid)
        fields = {}
        choices = {
            "language": ("Speech language", LANGUAGES),
            "model_size": ("Recognition model", SIZES),
            "en_voice": ("English voice", VOICES[:2]),
            "hi_voice": ("Hindi voice", VOICES[2:]),
            "voice_engine": ("Playback engine", ("piper", "kokoro")),
        }
        for row, (key, (title, values)) in enumerate(choices.items()):
            combo = Gtk.ComboBoxText()
            for value in values:
                combo.append(value, value)
            combo.set_active_id(getattr(existing, key))
            grid.attach(Gtk.Label(label=title, xalign=0), 0, row, 1, 1)
            grid.attach(combo, 1, row, 1, 1)
            fields[key] = combo
        speed = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, .65, 1.5, .05)
        speed.set_value(existing.speed)
        speed.set_digits(2)
        speed.set_size_request(170, -1)
        grid.attach(Gtk.Label(label="Speaking speed", xalign=0), 0, 5, 1, 1)
        grid.attach(speed, 1, 5, 1, 1)
        wake = Gtk.CheckButton(label="Listen for Mino")
        wake.set_active(existing.wake_word)
        grid.attach(wake, 0, 6, 2, 1)
        hint = Gtk.Label(label="Hold Ctrl + Alt + Space to talk on X11.", xalign=0)
        grid.attach(hint, 0, 7, 2, 1)

        def finish(window, response):
            if response == Gtk.ResponseType.OK:
                try:
                    values = {key: widget.get_active_id() for key, widget in fields.items()}
                    settings = Settings(**values, speed=speed.get_value(), wake_word=wake.get_active(),
                                        wake_model=existing.wake_model, local_vision=existing.local_vision,
                                        use_hosted_planner=existing.use_hosted_planner)
                    save(settings)
                    runtime.reload(settings)
                except (OSError, ValueError) as exc:
                    self.show("error", str(exc))
            self.last_settings = None
            window.destroy()
        dialog.connect("response", finish)
        dialog.show_all()
        return False


def hotkey(runtime):
    """Hold-to-talk on X11. Wayland can bind mino listen as a compositor shortcut."""
    from Xlib import X, XK, display
    from Xlib.error import BadAccess
    connection = display.Display()
    root = connection.screen().root
    key = connection.keysym_to_keycode(XK.string_to_keysym("space"))
    modifiers = X.ControlMask | X.Mod1Mask
    errors = []
    for locks in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
        root.grab_key(key, modifiers | locks, False, X.GrabModeAsync, X.GrabModeAsync,
                     onerror=lambda error, _: errors.append(error))
    connection.sync()
    if any(isinstance(error, BadAccess) for error in errors):
        runtime.warn("Ctrl + Alt + Space is occupied. Use mino listen or the wake word.")
        connection.close()
        return
    held = False
    while True:
        event = connection.next_event()
        if event.type == X.KeyPress and not held:
            held = True
            runtime.listen(True)
        elif event.type == X.KeyRelease:
            # X11 autorepeat emits paired release/press events for the same timestamp.
            if connection.pending_events():
                following = connection.next_event()
                if (following.type == X.KeyPress and following.detail == event.detail and
                        following.time == event.time):
                    continue
                if following.type == X.KeyPress:
                    runtime.release()
                    runtime.listen(True)
                    continue
            held = False
            runtime.release()
