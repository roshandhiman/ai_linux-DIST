import json
import subprocess
from threading import Thread
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

import native_wallpaper
import preferences
import glass_theme
from settings_pages import SystemPages
from companion_art import draw as draw_pet

SECTIONS = [
    ("Wi-Fi", "network-wireless-symbolic", "wifi", "wireless internet", "connect"),
    ("Bluetooth", "bluetooth-symbolic", "bluetooth", "pair devices wireless", "connect"),
    ("Network", "network-wired-symbolic", "network", "ethernet ip address dns gateway", "connect"),
    ("Power", "battery-symbolic", "power", "battery sleep screen dpms", "hardware"),
    ("General", "preferences-system-symbolic", "general", "about storage update time language startup", ""),
    ("Accessibility", "preferences-desktop-accessibility-symbolic", "accessibility", "sticky slow bounce keys high contrast", ""),
    ("Appearance", "weather-clear-night-symbolic", "appearance", "dark light effects shadows blur animations", "personal"),
    ("Assistant", "face-smile-symbolic", "assistant", "local model mino pet companion", "personal"),
    ("Desktop & Dock", "user-desktop-symbolic", "dock", "opacity position icons corner radius magnification", ""),
    ("Displays", "video-display-symbolic", "display", "resolution scale monitors refresh color profiles", "hardware"),
    ("Menu Bar", "view-list-symbolic", "menu_bar", "top panel opacity transparency clock", ""),
    ("Wallpaper", "image-x-generic-symbolic", "wallpaper", "picture video wallpaper background color live", "personal"),
    ("Notifications", "preferences-system-notifications-symbolic", "notifications", "alerts do not disturb", "audio"),
    ("Sound", "audio-volume-high-symbolic", "sound", "output input microphone volume mute", "audio"),
    ("Keyboard", "input-keyboard-symbolic", "keyboard", "shortcuts repeat layout", "hardware"),
    ("Mouse & Touchpad", "input-mouse-symbolic", "mouse", "pointer acceleration scrolling", "hardware"),
]


def button(text, action):
    widget = Gtk.Button(label=text)
    widget.get_style_context().add_class("glass-control")
    widget.connect("clicked", action)
    return widget


class Settings(SystemPages, Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Settings")
        self.set_wmclass("mineos-settings", "MineOSSettings")
        display = self.get_display()
        pointer = display.get_default_seat().get_pointer()
        _, x, y = pointer.get_position()
        monitor = display.get_monitor_at_point(x, y) or display.get_monitor(0)
        bounds = monitor.get_workarea()
        width = min(980, max(320, bounds.width - 112))
        height = min(620, max(260, bounds.height - 172))
        self.set_default_size(width, height)
        self.set_position(Gtk.WindowPosition.CENTER)
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.get_style_context().add_class("mineos-settings")
        self.get_style_context().add_class("glass-panel")
        self.values = preferences.read()
        self.timer = 0
        self.current = None
        self.back_stack = []
        self.forward_stack = []
        self.pages = {}
        self.nav_rows = {}
        self.embeds = {}
        self.toolbar = Gtk.HeaderBar(title="Settings", show_close_button=True)
        self.toolbar.get_style_context().add_class("mineos-toolbar")
        self.set_titlebar(self.toolbar)
        arrows = Gtk.Box()
        arrows.get_style_context().add_class("linked")
        self.back = self.icon_button("go-previous-symbolic", "Back", lambda _: self.travel(self.back_stack, self.forward_stack))
        self.forward = self.icon_button("go-next-symbolic", "Forward", lambda _: self.travel(self.forward_stack, self.back_stack))
        arrows.add(self.back)
        arrows.add(self.forward)
        self.toolbar.pack_start(arrows)
        body = Gtk.Box()
        self.add(body)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.set_size_request(246, -1)
        sidebar.get_style_context().add_class("mineos-sidebar")
        sidebar.get_style_context().add_class("glass-card")
        body.pack_start(sidebar, False, False, 0)
        self.search = Gtk.SearchEntry(placeholder_text="Search settings")
        self.search.get_style_context().add_class("settings-search")
        self.search.get_style_context().add_class("pill-search")
        self.search.get_accessible().set_name("Search settings")
        sidebar.pack_start(self.search, False, False, 0)
        account = Gtk.Box(spacing=10)
        account.get_style_context().add_class("settings-account")
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        name = Gtk.Label(label=GLib.get_real_name() or GLib.get_user_name(), xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=22)
        name.get_style_context().add_class("settings-account-name")
        labels.add(name)
        account.pack_start(self.badge("avatar-default-symbolic", "", 27), False, False, 0)
        account.pack_start(labels, True, True, 0)
        sidebar.pack_start(account, False, False, 0)
        navigation = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        sidebar.pack_start(navigation, True, True, 0)
        self.nav = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.nav.get_style_context().add_class("settings-navigation")
        navigation.add(self.nav)
        self.stack = Gtk.Stack(transition_duration=glass_theme.MOTION_MS, hhomogeneous=False, vhomogeneous=False)
        self.update_transition()
        body.pack_start(self.stack, True, True, 0)
        for title, icon, key, keywords, tone in SECTIONS:
            self.add_navigation_item(key, title, icon, tone, keywords)
            self.pages[key] = (title, icon, tone, getattr(self, key), key)
        self.register_system_pages()
        for key, (title, icon, tone, _, parent) in self.pages.items():
            if key != parent:
                self.add_navigation_item(key, title, icon, tone, search_only=True)
        self.nav.connect("row-selected", self.selected)
        self.nav.set_filter_func(self.match_search)
        self.search.connect("search-changed", self.filter_navigation)
        self.search.connect("activate", self.activate_search)
        self.connect("delete-event", self.flush)
        self.connect("destroy", self.close_panels)
        self.connect("key-press-event", self.keys)
        self.refresh_style()
        self.navigate("general", remember=False)

    def add_navigation_item(self, key, title, icon, tone, keywords="", search_only=False):
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("glass-row")
        row.key = key
        row.terms = f"{title} {keywords}".casefold()
        row.search_only = search_only
        item = Gtk.Box(spacing=9, margin=4)
        item.pack_start(self.badge(icon, tone, 18), False, False, 0)
        item.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
        row.add(item)
        self.nav.add(row)
        self.nav_rows[key] = row

    def badge(self, icon, tone, size):
        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)
        image.set_pixel_size(size)
        image.get_style_context().add_class("settings-icon")
        image.get_style_context().add_class("glass-icon")
        if tone:
            image.get_style_context().add_class(tone)
        image.set_halign(Gtk.Align.CENTER)
        return image

    def icon_button(self, icon, hint, action):
        control = Gtk.Button(image=Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        control.get_style_context().add_class("glass-control")
        control.set_tooltip_text(hint)
        control.get_accessible().set_name(hint)
        control.connect("clicked", action)
        return control

    def selected(self, _, row):
        if row and row.key != self.current:
            self.navigate(row.key)

    def match_search(self, row):
        query = self.search.get_text().casefold().split()
        return (bool(query) or not row.search_only) and all(term in row.terms for term in query)

    def filter_navigation(self, *_):
        self.nav.invalidate_filter()

    def activate_search(self, *_):
        matches = [row for row in self.nav.get_children() if row.get_child_visible()]
        query = self.search.get_text().strip().casefold()
        match = next((row for row in matches if self.pages[row.key][0].casefold() == query), None)
        if not match and matches:
            match = matches[0]
        if match:
            self.navigate(match.key)

    def keys(self, _, event):
        if event.state & Gdk.ModifierType.CONTROL_MASK and event.keyval == Gdk.KEY_f:
            self.search.grab_focus()
            return True
        if event.state & Gdk.ModifierType.MOD1_MASK and event.keyval in (Gdk.KEY_Left, Gdk.KEY_Right):
            if event.keyval == Gdk.KEY_Left:
                self.travel(self.back_stack, self.forward_stack)
            else:
                self.travel(self.forward_stack, self.back_stack)
            return True
        return False

    def travel(self, source, destination):
        if source:
            destination.append(self.current)
            self.navigate(source.pop(), remember=False)

    def navigate(self, key, remember=True):
        if key not in self.pages or key == self.current:
            return
        if remember and self.current:
            self.back_stack.append(self.current)
            self.forward_stack.clear()
        self.current = key
        title, icon, tone, populate, parent = self.pages[key]
        target = key if self.search.get_text().strip() and self.nav_rows[key].get_child_visible() else parent
        if self.nav.get_selected_row() is not self.nav_rows[target]:
            self.select_parent(target)
        if not self.stack.get_child_by_name(key):
            self.build_page(key, title, icon, tone, populate)
        elif key == "wallpaper":
            self.refresh_wallpaper_page()
        self.stack.set_visible_child_name(key)
        self.back.set_sensitive(bool(self.back_stack))
        self.forward.set_sensitive(bool(self.forward_stack))

    def select_parent(self, parent):
        self.nav.handler_block_by_func(self.selected)
        self.nav.select_row(self.nav_rows[parent])
        self.nav.handler_unblock_by_func(self.selected)

    def build_page(self, key, title, icon, tone, populate):
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.AUTOMATIC)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22, margin=28)
        hero = Gtk.Box(spacing=16)
        hero.get_style_context().add_class("settings-hero")
        hero.get_style_context().add_class("glass-card")
        hero.pack_start(self.badge(icon, tone, 34), False, False, 0)
        heading = Gtk.Label(label=title, xalign=0)
        heading.get_style_context().add_class("settings-section")
        hero.pack_start(heading, False, False, 0)
        page.pack_start(hero, False, False, 0)
        scroll.add(page)
        self.stack.add_named(scroll, key)
        populate(page)
        scroll.show_all()

    def route(self, group, title, key, note=None):
        if group.get_children():
            group.add(Gtk.Separator())
        control = Gtk.Button()
        control.get_style_context().add_class("settings-link")
        control.get_style_context().add_class("glass-row")
        row = Gtk.Box(spacing=12)
        row.get_style_context().add_class("settings-row")
        _, icon, tone, _, _ = self.pages[key]
        row.add(self.badge(icon, tone, 18))
        row.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
        if note:
            row.pack_start(self.value(note), False, False, 0)
        row.add(Gtk.Image.new_from_icon_name("go-next-symbolic", Gtk.IconSize.MENU))
        control.add(row)
        control.connect("clicked", lambda _: self.navigate(key))
        group.add(control)

    def value(self, text):
        label = Gtk.Label(label=str(text), xalign=0)
        label.set_line_wrap(True)
        label.get_style_context().add_class("settings-value")
        return label

    def note(self, group, text):
        self.row(group, text, Gtk.Label())

    def report(self, error):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.CLOSE,
                                   text="Could not complete the change", secondary_text=str(error))
        dialog.connect("response", lambda window, _: window.destroy())
        dialog.show()

    def task(self, action, done=None, failed=None):
        def worker():
            try:
                result = action()
            except (GLib.Error, OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
                GLib.idle_add(failed or self.report, error)
            else:
                if done:
                    GLib.idle_add(done, result)
        Thread(target=worker, daemon=True).start()

    def bind(self, control, callback, reset):
        control.set_sensitive(False)
        def finished(_):
            control.set_sensitive(True)
        def failed(error):
            reset()
            control.set_sensitive(True)
            self.report(error)
        self.task(callback, finished, failed)

    def metric(self, title, value):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.get_style_context().add_class("metric-chip")
        name = Gtk.Label(label=title)
        name.get_style_context().add_class("metric-label")
        amount = Gtk.Label(label=value)
        amount.get_style_context().add_class("metric-value")
        box.add(name)
        box.add(amount)
        return box

    def group(self, page):
        group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        group.get_style_context().add_class("settings-group")
        group.get_style_context().add_class("glass-card")
        page.pack_start(group, False, False, 0)
        return group

    def row(self, group, title, control, info=None):
        if group.get_children():
            group.pack_start(Gtk.Separator(), False, False, 0)
        row = Gtk.Box(spacing=14)
        row.get_style_context().add_class("settings-row")
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        labels.pack_start(Gtk.Label(label=title, xalign=0, wrap=True), False, False, 0)
        if info:
            caption = self.value(info)
            caption.get_style_context().add_class("settings-value")
            labels.pack_start(caption, False, False, 0)
        row.pack_start(labels, True, True, 0)
        control.set_valign(Gtk.Align.CENTER)
        row.pack_end(control, False, False, 0)
        group.pack_start(row, False, False, 0)
        return row

    def switch(self, group, title, key):
        toggle = Gtk.Switch(active=self.values[key])
        toggle.connect("notify::active", lambda widget, _: self.change(key, widget.get_active()))
        self.row(group, title, toggle)

    def slider(self, group, title, key, low, high):
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, low, high, 1)
        scale.set_size_request(155, -1)
        scale.set_value(self.values[key])
        scale.set_draw_value(True)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.connect("value-changed", lambda widget: self.change(key, int(widget.get_value())))
        self.row(group, title, scale)

    def choices(self, group, title, key, options, info=None):
        control = Gtk.ComboBoxText()
        values = {str(value): value for value, _ in options}
        for value, label in options:
            control.append(str(value), label)
        control.set_active_id(str(self.values[key]))
        def changed(widget):
            active_id = widget.get_active_id()
            if active_id in values:
                self.change(key, values[active_id])

        control.connect("changed", changed)
        self.row(group, title, control, info)
        return control

    def change(self, key, value):
        if self.values[key] == value:
            return
        self.values[key] = value
        if self.timer:
            GLib.source_remove(self.timer)
        self.timer = GLib.timeout_add(200, self.flush)

    def flush(self, *_):
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = 0
        try:
            old = preferences.read()
            preferences.apply(self.values, old)
            if old["animations"] != self.values["animations"]:
                self.update_transition()
            if any(old[key] != self.values[key] for key in ("appearance", "blur", "animations")):
                self.refresh_style()
        except (OSError, ValueError, subprocess.SubprocessError, GLib.Error) as error:
            detail = (getattr(error, "stderr", None) or str(error)).strip()
            dialog = Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.CLOSE, text="Could not apply settings", secondary_text=detail)
            dialog.run()
            dialog.destroy()
        return GLib.SOURCE_REMOVE

    def update_transition(self):
        self.stack.set_transition_type(
            Gtk.StackTransitionType.CROSSFADE if self.values["animations"] else Gtk.StackTransitionType.NONE
        )

    def refresh_style(self):
        dark = self.values["appearance"] == "dark"
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", dark)
        provider = Gtk.CssProvider()
        screen = self.get_screen()
        provider.load_from_data(glass_theme.style(self.values, "settings", screen.is_composited()))
        if getattr(self, "mode_provider", None):
            Gtk.StyleContext.remove_provider_for_screen(screen, self.mode_provider)
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
        self.mode_provider = provider
        for mode, widget in getattr(self, "appearance_swatches", {}).items():
            style = widget.get_style_context()
            if mode == self.values["appearance"]:
                style.add_class("selected")
            else:
                style.remove_class("selected")

    def appearance(self, page):
        group = self.group(page)
        swatches = Gtk.Box(spacing=8)
        self.appearance_swatches = {}
        for mode, icon in (("light", "weather-clear-symbolic"), ("dark", "weather-clear-night-symbolic")):
            control = button(mode.title(), lambda _, value=mode: self.change("appearance", value))
            control.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
            control.set_always_show_image(True)
            control.get_style_context().add_class("settings-swatch")
            swatches.add(control)
            self.appearance_swatches[mode] = control
            if mode == self.values["appearance"]:
                control.get_style_context().add_class("selected")
        self.row(group, "Color scheme", swatches)
        effects = self.group(page)
        self.switch(effects, "Window animations", "animations")
        self.switch(effects, "Window shadows", "shadows")
        self.switch(effects, "Glass blur", "blur")

    def wallpaper_preview(self, widget, cr):
        width, height = widget.get_allocated_width(), widget.get_allocated_height()
        color = Gdk.RGBA()
        color.parse(self.values["background_color"])
        Gdk.cairo_set_source_rgba(cr, color)
        cr.paint()
        image = self.wallpaper_image
        if image:
            scale_x, scale_y = width / image.get_width(), height / image.get_height()
            fit = self.values["video_fit"] if self.values["live"] and self.values["video"] else {
                "1": "center", "3": "stretch", "4": "fit", "5": "fill"
            }.get(self.values["wallpaper_fit"], "fill")
            if fit != "stretch":
                scale = min(scale_x, scale_y) if fit in ("fit", "center") else max(scale_x, scale_y)
                scale_x = scale_y = scale
            cr.translate((width - image.get_width() * scale_x) / 2, (height - image.get_height() * scale_y) / 2)
            cr.scale(scale_x, scale_y)
            Gdk.cairo_set_source_pixbuf(cr, image, 0, 0)
            cr.paint()
        return True

    def wallpaper(self, page):
        if native_wallpaper.available():
            try:
                native = native_wallpaper.selection()
                saved = preferences.read()
                if any(saved[key] != value for key, value in native.items()):
                    preferences.write(preferences.PREFS, json.dumps({**saved, **native}, indent=2) + "\n")
                self.values.update(native)
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
        frame = Gtk.Box()
        frame.get_style_context().add_class("settings-preview")
        frame.get_style_context().add_class("glass-card")
        monitor = self.get_display().get_monitor_at_window(self.get_window()) if self.get_window() else None
        monitor = monitor or self.get_display().get_primary_monitor()
        bounds = monitor.get_geometry() if monitor else None
        dimensions = (bounds.width, bounds.height) if bounds else (16, 9)
        preview = Gtk.DrawingArea(width_request=min(320, round(180 * dimensions[0] / dimensions[1])),
                                  height_request=min(180, round(320 * dimensions[1] / dimensions[0])),
                                  halign=Gtk.Align.CENTER)
        self.wallpaper_image = None
        self.wallpaper_preview_widget = preview
        backdrop = self.values["backdrop"]
        video = self.values["video"]
        if backdrop:
            try:
                self.wallpaper_image = GdkPixbuf.Pixbuf.new_from_file_at_scale(backdrop, 594, 360, True)
            except GLib.Error:
                pass
        preview.connect("draw", self.wallpaper_preview)
        frame.pack_start(preview, True, True, 0)
        page.pack_start(frame, False, False, 0)
        media = self.group(page)
        toggle = Gtk.Switch(active=bool(video and self.values["live"]), sensitive=bool(video))
        toggle.connect("notify::active", self.toggle_live_wallpaper)
        self.row(media, "Live wallpaper", toggle, "Video plays muted behind your desktop icons.")
        file_row = self.row(media, "Video", button("Choose…", lambda _: self.pick(True)),
                            Path(video).name if video else "Select a local video file")
        if native_wallpaper.available():
            fit = self.choices(media, "Video fit", "video_fit", [
                ("fill", "Fill screen"), ("fit", "Fit entire video"), ("stretch", "Stretch")
            ])
            fit.set_sensitive(bool(video))
            fit.connect("changed", lambda *_: preview.queue_draw())
        if video:
            labels = file_row.get_children()[0]
            resolution = self.value("")
            resolution.get_style_context().add_class("settings-value")
            labels.pack_start(resolution, False, False, 0)
            Thread(target=self.load_wallpaper_video_preview,
                   args=(video, preview, resolution, self.values["live"]), daemon=True).start()
        options = self.group(page)
        color = Gdk.RGBA()
        color.parse(self.values["background_color"])
        pick_color = Gtk.ColorButton(rgba=color, title="Background color")
        pick_color.connect("color-set", self.change_color, preview)
        self.row(options, "Background color", pick_color)
        self.row(options, "Picture", button("Choose…", lambda _: self.pick(False)), Path(backdrop).name if backdrop else None)
        fit = self.choices(options, "Picture fit", "wallpaper_fit", [("5", "Fill"), ("4", "Fit"), ("3", "Stretch"), ("1", "Center")])
        fit.connect("changed", lambda *_: preview.queue_draw())
        self.row(options, "Reset wallpaper", button("Reset", self.reset_wallpaper))

    def toggle_live_wallpaper(self, toggle, _):
        self.values["live"] = toggle.get_active()
        self.flush()
        GLib.idle_add(self.refresh_wallpaper_page)

    def load_wallpaper_video_preview(self, video, preview, resolution, live):
        try:
            dimensions = self.wallpaper_video_dimensions(video)
            data = subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-threads", "2", "-i", video, "-frames:v", "1",
                 "-vf", "scale=480:-2", "-f", "image2pipe", "-vcodec", "png", "-threads:v", "1", "pipe:1"],
                check=True, capture_output=True, timeout=8,
            ).stdout if live else b""
        except (OSError, ValueError, subprocess.SubprocessError):
            dimensions, data = None, b""
        GLib.idle_add(self.apply_wallpaper_video_preview, preview, resolution, dimensions, data)

    def apply_wallpaper_video_preview(self, preview, resolution, dimensions, data):
        if preview is not self.wallpaper_preview_widget or not resolution.get_parent():
            return GLib.SOURCE_REMOVE
        resolution.set_text(f"{dimensions[0]} × {dimensions[1]}" if dimensions else "Video unavailable")
        if data:
            try:
                loader = GdkPixbuf.PixbufLoader.new_with_type("png")
                loader.write(data)
                loader.close()
                self.wallpaper_image = loader.get_pixbuf()
                preview.queue_draw()
            except GLib.Error:
                pass
        return GLib.SOURCE_REMOVE

    def wallpaper_video_dimensions(self, path):
        raw = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
             "-of", "json", path],
            check=True, capture_output=True, timeout=5,
        ).stdout
        streams = json.loads(raw).get("streams", [])
        if not streams or not all(streams[0].get(axis) for axis in ("width", "height")):
            raise ValueError("Choose a file containing a supported video track.")
        return streams[0]["width"], streams[0]["height"]

    def change_color(self, widget, preview):
        color = widget.get_rgba()
        value = "#" + "".join(f"{round(channel * 255):02x}" for channel in (color.red, color.green, color.blue))
        self.change("background_color", value)
        preview.queue_draw()

    def pick(self, video):
        dialog = Gtk.FileChooserDialog(title="Choose video" if video else "Choose picture", transient_for=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Choose", Gtk.ResponseType.OK)
        rule = Gtk.FileFilter()
        rule.set_name("Video files" if video else "Pictures")
        for mime in (["video/mp4", "video/webm", "video/quicktime", "video/x-matroska"] if video else ["image/png", "image/jpeg", "image/webp"]):
            rule.add_mime_type(mime)
        dialog.add_filter(rule)
        folder = Path.home() / "Wallpapers" if video else Path.home() / "Pictures"
        if folder.is_dir():
            dialog.set_current_folder(str(folder))
        path = dialog.get_filename() if dialog.run() == Gtk.ResponseType.OK else None
        dialog.destroy()
        if not path:
            return
        if video:
            try:
                self.wallpaper_video_dimensions(path)
            except (OSError, ValueError, subprocess.SubprocessError):
                error = Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.CLOSE,
                                          text="Could not open this video",
                                          secondary_text="Choose a local MP4, WebM, MOV, or MKV with a readable video track.")
                error.run()
                error.destroy()
                return
        self.values["video" if video else "backdrop"] = path
        self.values["live"] = video
        self.flush()
        self.refresh_wallpaper_page()

    def reset_wallpaper(self, *_):
        for key in native_wallpaper.NATIVE_KEYS:
            self.values[key] = preferences.DEFAULTS[key]
        self.flush()
        self.refresh_wallpaper_page()

    def refresh_wallpaper_page(self):
        scroll = self.stack.get_child_by_name("wallpaper")
        page = scroll.get_child().get_child()
        for child in page.get_children()[1:]:
            child.destroy()
        self.wallpaper(page)
        page.show_all()

    def dock(self, page):
        group = self.group(page)
        self.choices(group, "Style", "dock_style", [("mineos", "MineOS"), ("docky", "Docky")])
        self.choices(group, "Position", "dock_position", [("bottom", "Bottom"), ("left", "Left"), ("right", "Right")])
        self.slider(group, "Icon size", "dock_size", 26, 72)
        self.slider(group, "Opacity", "dock_opacity", 0, 100)
        self.slider(group, "Corner radius", "dock_roundness", 0, 24)
        self.switch(group, "Magnify icons", "dock_zoom")
        self.switch(group, "Hide when a window overlaps", "dock_hide")

    def assistant(self, page):
        group = self.group(page)
        model = Gtk.Entry(placeholder_text="Default model", width_chars=17)
        model.set_text(self.values["model"])
        model.connect("activate", lambda widget: self.change("model", widget.get_text().strip()))
        model.connect("focus-out-event", self.model_changed)
        self.row(group, "Local model", model)
        companion = self.group(page)
        self.switch(companion, "Show Mino on the desktop", "pet")
        self.switch(companion, "Animate Mino", "pet_motion")
        self.choices(companion, "Companion size", "pet_size", list(preferences.PET_SIZES.items()),
                     "Drag Mino to move it. Click to open chat.")
        sprite = Gtk.DrawingArea(width_request=82, height_request=82)
        sprite.set_halign(Gtk.Align.CENTER)
        sprite.connect("draw", self.draw_companion)
        companion.pack_start(sprite, False, False, 6)

    def draw_companion(self, widget, cr):
        draw_pet(cr, min(widget.get_allocated_width(), widget.get_allocated_height()))
        return True

    def model_changed(self, widget, _):
        self.change("model", widget.get_text().strip())
        return False


class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.mineos.Settings", flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()
        window = self.get_active_window() or Settings(self)
        if len(args) > 1:
            window.navigate(args[1])
        window.show_all()
        window.present()
        return 0


if __name__ == "__main__":
    import sys
    Application().run(sys.argv)
