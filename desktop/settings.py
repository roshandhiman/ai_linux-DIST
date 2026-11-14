import subprocess
from threading import Thread
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

import preferences
from settings_pages import SystemPages
from pixel_pet import draw as draw_pet

PALETTES = {
    "dark": {
        "surface": "rgba(29,29,29,.90)", "nav": "alpha(#000,.16)", "card": "alpha(#fff,.07)", "line": "alpha(#fff,.17)",
        "text": "#f2f2f2", "muted": "#bdbdbd", "hover": "#393939", "selected": "#474747",
    },
    "light": {
        "surface": "rgba(245,245,245,.95)", "nav": "alpha(#000,.04)", "card": "alpha(#fff,.65)", "line": "alpha(#000,.16)",
        "text": "#222222", "muted": "#575757", "hover": "#e9e9e9", "selected": "#dcdcdc",
    },
}

SECTIONS = [
    ("Wi-Fi", "network-wireless-symbolic", "wifi", "wireless internet", "connect"),
    ("Bluetooth", "bluetooth-symbolic", "bluetooth", "pair devices wireless", "connect"),
    ("Network", "network-wired-symbolic", "network", "ethernet ip address dns gateway", "connect"),
    ("Power", "battery-symbolic", "power", "battery sleep screen dpms", "hardware"),
    ("General", "preferences-system-symbolic", "general", "about storage update time language startup", ""),
    ("Accessibility", "preferences-desktop-accessibility-symbolic", "accessibility", "sticky slow bounce keys high contrast", ""),
    ("Appearance", "weather-clear-night-symbolic", "appearance", "dark light effects shadows blur animations", "personal"),
    ("Assistant", "face-smile-symbolic", "assistant", "ollama local model pixel pet companion", "personal"),
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
    widget.connect("clicked", action)
    return widget


class Settings(SystemPages, Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Settings")
        self.set_wmclass("mineos-settings", "MineOSSettings")
        bounds = self.get_display().get_monitor_at_point(0, 0).get_workarea()
        self.set_default_size(min(1060, bounds.width - 48), min(760, bounds.height - 72))
        self.set_position(Gtk.WindowPosition.CENTER)
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            self.get_style_context().add_class("mineos-translucent")
        self.get_style_context().add_class("mineos-settings")
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
        body.pack_start(sidebar, False, False, 0)
        self.search = Gtk.SearchEntry(placeholder_text="Search settings")
        self.search.get_style_context().add_class("settings-search")
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
        self.stack = Gtk.Stack(transition_duration=120, hhomogeneous=False, vhomogeneous=False)
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
        if tone:
            image.get_style_context().add_class(tone)
        image.set_halign(Gtk.Align.CENTER)
        return image

    def icon_button(self, icon, hint, action):
        control = Gtk.Button(image=Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
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
        self.stack.set_visible_child_name(key)
        self.back.set_sensitive(bool(self.back_stack))
        self.forward.set_sensitive(bool(self.forward_stack))

    def select_parent(self, parent):
        self.nav.handler_block_by_func(self.selected)
        self.nav.select_row(self.nav_rows[parent])
        self.nav.handler_unblock_by_func(self.selected)

    def build_page(self, key, title, icon, tone, populate):
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22, margin=28)
        hero = Gtk.Box(spacing=16)
        hero.get_style_context().add_class("settings-hero")
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

    def choices(self, group, title, key, options):
        control = Gtk.ComboBoxText()
        for value, label in options:
            control.append(value, label)
        control.set_active_id(self.values[key])
        control.connect("changed", lambda widget: self.change(key, widget.get_active_id()))
        self.row(group, title, control)

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
            if old["appearance"] != self.values["appearance"]:
                self.refresh_style()
        except (OSError, subprocess.SubprocessError, GLib.Error) as error:
            dialog = Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.CLOSE, text="Could not apply settings", secondary_text=str(error))
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
        palette = PALETTES["dark" if dark else "light"]
        colors = "".join(f"@define-color mineos_{name} {value};\n" for name, value in palette.items())
        provider.load_from_data((colors + (preferences.DESKTOP / "settings.css").read_text()).encode())
        screen = Gdk.Screen.get_default()
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
        self.switch(effects, "Blur behind the app launcher", "blur")

    def wallpaper_preview(self, widget, cr):
        width, height = widget.get_allocated_width(), widget.get_allocated_height()
        color = Gdk.RGBA()
        color.parse(self.values["background_color"])
        Gdk.cairo_set_source_rgba(cr, color)
        cr.paint()
        if self.wallpaper_image:
            image = self.wallpaper_image
            scale = max(width / image.get_width(), height / image.get_height())
            cr.translate((width - image.get_width() * scale) / 2, (height - image.get_height() * scale) / 2)
            cr.scale(scale, scale)
            Gdk.cairo_set_source_pixbuf(cr, image, 0, 0)
            cr.paint()
        return True

    def wallpaper(self, page):
        frame = Gtk.Box()
        frame.get_style_context().add_class("settings-preview")
        preview = Gtk.DrawingArea(height_request=136)
        self.wallpaper_image = None
        backdrop = self.values["backdrop"]
        if backdrop:
            try:
                self.wallpaper_image = GdkPixbuf.Pixbuf.new_from_file_at_scale(backdrop, 594, 360, True)
            except GLib.Error:
                pass
        preview.connect("draw", self.wallpaper_preview)
        frame.pack_start(preview, True, True, 0)
        page.pack_start(frame, False, False, 0)
        options = self.group(page)
        color = Gdk.RGBA()
        color.parse(self.values["background_color"])
        pick_color = Gtk.ColorButton(rgba=color, title="Background color")
        pick_color.connect("color-set", self.change_color, preview)
        self.row(options, "Background color", pick_color)
        self.row(options, "Picture", button("Choose…", lambda _: self.pick(False)), Path(backdrop).name if backdrop else None)
        self.choices(options, "Picture fit", "wallpaper_fit", [("5", "Fill"), ("4", "Fit"), ("3", "Stretch"), ("1", "Center")])
        media = self.group(page)
        video = self.values["video"]
        self.row(media, "Video", button("Choose…", lambda _: self.pick(True)), Path(video).name if video else None)
        if video or backdrop:
            self.switch(media, "Live wallpaper", "live")
        self.row(media, "Reset wallpaper", button("Reset", self.reset_wallpaper))

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
        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            self.values["video" if video else "backdrop"] = path
            if video:
                self.values["live"] = True
            else:
                self.values["live"] = False
            dialog.destroy()
            self.flush()
            self.refresh_wallpaper_page()
        else:
            dialog.destroy()

    def reset_wallpaper(self, *_):
        for key in ("backdrop", "background_color", "wallpaper_fit", "video", "live"):
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
        self.switch(companion, "Desktop companion", "pet")
        self.switch(companion, "Animate companion", "pet_motion")
        self.slider(companion, "Companion size", "pet_size", 52, 130)
        sprite = Gtk.DrawingArea(width_request=82, height_request=82)
        sprite.set_halign(Gtk.Align.CENTER)
        sprite.connect("draw", self.draw_companion)
        companion.pack_start(sprite, False, False, 6)

    def draw_companion(self, widget, cr):
        draw_pet(cr, widget.get_allocated_width(), 0, hovered=True)
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
