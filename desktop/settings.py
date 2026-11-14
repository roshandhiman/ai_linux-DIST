import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

import preferences

CSS = b"""
.settings-navigation { padding: 12px; background-color: alpha(currentColor, 0.045); }
.settings-navigation row { margin: 2px 0; border-radius: 7px; }
.settings-navigation row:selected { background: alpha(currentColor, 0.13); }
.settings-section { font-size: 24px; font-weight: 700; }
.settings-group { border: 1px solid alpha(currentColor, 0.12); border-radius: 10px; }
.settings-row { padding: 12px 15px; }
.settings-value { opacity: 0.65; }
.settings-preview { border-radius: 10px; }
.settings-body separator { min-width: 1px; background-color: alpha(currentColor, 0.12); }
"""


def button(text, action):
    widget = Gtk.Button(label=text)
    widget.connect("clicked", action)
    return widget


class Settings(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Settings")
        self.set_wmclass("mineos-settings", "MineOSSettings")
        self.set_default_size(780, 565)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.values = preferences.read()
        self.timer = 0
        self.set_titlebar(Gtk.HeaderBar(title="Settings", show_close_button=True))
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        body = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        body.get_style_context().add_class("settings-body")
        self.add(body)
        nav = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        nav.get_style_context().add_class("settings-navigation")
        nav.set_size_request(204, -1)
        body.pack1(nav, resize=False, shrink=False)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=150)
        body.pack2(self.stack, resize=True, shrink=False)
        sections = [
            ("Appearance", "preferences-desktop-theme", self.appearance),
            ("Wallpaper", "preferences-desktop-wallpaper", self.wallpaper),
            ("Desktop & Dock", "video-display", self.dock),
            ("Assistant", "system-search", self.assistant),
            ("Desktop Companion", "face-smile", self.companion),
            ("Network", "network-wired", self.network),
            ("Sound", "audio-volume-high", self.sound),
            ("About", "help-about", self.about),
        ]
        for title, icon, populate in sections:
            label = Gtk.Label(label=title, xalign=0)
            row = Gtk.Box(spacing=10, margin=9)
            row.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU), False, False, 0)
            row.pack_start(label, True, True, 0)
            nav.add(row)
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin=24)
            heading = Gtk.Label(label=title, xalign=0)
            heading.get_style_context().add_class("settings-section")
            page.pack_start(heading, False, False, 0)
            populate(page)
            scroll.add(page)
            self.stack.add_named(scroll, title)
        nav.connect("row-selected", lambda _, row: self.stack.set_visible_child_name(sections[row.get_index()][0]) if row else None)
        nav.select_row(nav.get_row_at_index(0))
        self.connect("delete-event", self.flush)
        self.refresh_style()

    def group(self, page):
        group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        group.get_style_context().add_class("settings-group")
        page.pack_start(group, False, False, 0)
        return group

    def row(self, group, title, control, info=None):
        if group.get_children():
            group.pack_start(Gtk.Separator(), False, False, 0)
        row = Gtk.Box(spacing=14)
        row.get_style_context().add_class("settings-row")
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        labels.pack_start(Gtk.Label(label=title, xalign=0), False, False, 0)
        if info:
            caption = Gtk.Label(label=info, xalign=0)
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

    def choices(self, group, title, key, options):
        control = Gtk.ComboBoxText()
        for value, label in options:
            control.append(value, label)
        control.set_active_id(self.values[key])
        control.connect("changed", lambda widget: self.change(key, widget.get_active_id()))
        self.row(group, title, control)

    def change(self, key, value):
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
            if old["appearance"] != self.values["appearance"]:
                self.refresh_style()
        except (OSError, subprocess.SubprocessError, GLib.Error) as error:
            dialog = Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.CLOSE, text="Could not apply settings", secondary_text=str(error))
            dialog.run()
            dialog.destroy()
        return GLib.SOURCE_REMOVE

    def refresh_style(self):
        dark = self.values["appearance"] == "dark"
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", dark)
        provider = Gtk.CssProvider()
        provider.load_from_path(str(preferences.DESKTOP / ("gtk-dark.css" if dark else "gtk.css")))
        screen = Gdk.Screen.get_default()
        if getattr(self, "mode_provider", None):
            Gtk.StyleContext.remove_provider_for_screen(screen, self.mode_provider)
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
        self.mode_provider = provider

    def appearance(self, page):
        group = self.group(page)
        self.choices(group, "Appearance", "appearance", [("light", "Light"), ("dark", "Dark")])
        self.switch(group, "Blur translucent surfaces", "blur")
        self.slider(group, "Menu bar opacity", "panel_opacity", 0, 100)

    def computer_preview(self):
        image = Path(self.values["backdrop"])
        if not image.is_file():
            image = Path(preferences.DEFAULTS["backdrop"])
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(str(image), 468, 168, False)

    def wallpaper(self, page):
        self.preview = Gtk.Image()
        self.preview.get_style_context().add_class("settings-preview")
        try:
            self.preview.set_from_pixbuf(self.computer_preview())
        except GLib.Error:
            pass
        page.pack_start(self.preview, False, False, 0)
        group = self.group(page)
        self.row(group, "Picture", button("Choose…", lambda _: self.pick(False)))
        self.switch(group, "Live wallpaper", "live")
        self.row(group, "Video", button("Choose…", lambda _: self.pick(True)), "Built-in motion" if not self.values["video"] else Path(self.values["video"]).name)
        self.row(group, "Wallpaper defaults", button("Restore", self.reset_wallpaper))

    def pick(self, video):
        dialog = Gtk.FileChooserDialog(title="Choose video" if video else "Choose picture", transient_for=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Choose", Gtk.ResponseType.OK)
        rule = Gtk.FileFilter()
        rule.set_name("Video files" if video else "Pictures")
        for mime in (["video/mp4", "video/webm", "video/quicktime", "video/x-matroska"] if video else ["image/png", "image/jpeg", "image/webp"]):
            rule.add_mime_type(mime)
        dialog.add_filter(rule)
        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            if video:
                self.values["video"] = path
            else:
                self.values["backdrop"] = path
        dialog.destroy()
        if not video:
            try:
                self.preview.set_from_pixbuf(self.computer_preview())
            except GLib.Error:
                pass
        self.flush()
        self.refresh_wallpaper_page()

    def reset_wallpaper(self, *_):
        for key in ("backdrop", "video", "live"):
            self.values[key] = preferences.DEFAULTS[key]
        self.flush()
        self.refresh_wallpaper_page()

    def refresh_wallpaper_page(self):
        scroll = self.stack.get_child_by_name("Wallpaper")
        page = scroll.get_child().get_child()
        for child in page.get_children()[1:]:
            child.destroy()
        self.wallpaper(page)
        page.show_all()

    def dock(self, page):
        group = self.group(page)
        self.choices(group, "Position", "dock_position", [("bottom", "Bottom"), ("left", "Left"), ("right", "Right")])
        self.slider(group, "Icon size", "dock_size", 26, 72)
        self.slider(group, "Opacity", "dock_opacity", 0, 100)
        self.slider(group, "Corner radius", "dock_roundness", 0, 24)
        self.switch(group, "Magnify icons", "dock_zoom")
        self.switch(group, "Hide when a window overlaps", "dock_hide")

    def companion(self, page):
        group = self.group(page)
        self.switch(group, "Show on desktop", "pet")
        self.switch(group, "Animate companion", "pet_motion")
        self.slider(group, "Size", "pet_size", 72, 144)

    def assistant(self, page):
        group = self.group(page)
        self.row(group, "Assistant", button("Open", lambda _: subprocess.Popen(["python3", "/opt/ai/jarvis_gui.py"])))
        model = Gtk.Entry(text=self.values["model"], placeholder_text="Ollama default", width_chars=17)
        model.connect("activate", lambda widget: self.change("model", widget.get_text().strip()))
        model.connect("focus-out-event", self.model_changed)
        self.row(group, "Local model", model)
        self.row(group, "Internet research", Gtk.Label(label="Web mode"))

    def model_changed(self, widget, _):
        self.change("model", widget.get_text().strip())
        return False

    def network(self, page):
        self.row(self.group(page), "Network connections", button("Open", lambda _: subprocess.Popen(["nm-connection-editor"])))

    def sound(self, page):
        self.row(self.group(page), "Volume and devices", button("Open", lambda _: subprocess.Popen(["pavucontrol"])))

    def about(self, page):
        group = self.group(page)
        self.row(group, "Operating system", Gtk.Label(label="MineOS"))
        self.row(group, "Base system", Gtk.Label(label="Debian 13"))
        self.row(group, "Startup animation", button("Preview", lambda _: subprocess.Popen(["python3", "/opt/ai/desktop/boot_preview.py"])))


class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.mineos.Settings")

    def do_activate(self):
        window = self.get_active_window() or Settings(self)
        window.show_all()
        window.present()


if __name__ == "__main__":
    Application().run(None)
