import sys

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango

import app_catalog as catalog
import preferences

DARK = {
    "surface": "rgba(28,28,28,.80)", "text": "#f2f2f2", "muted": "#bdbdbd",
    "border": "alpha(#fff,.17)", "control": "alpha(#fff,.08)", "hover": "alpha(#fff,.14)",
    "selected": "#4a4a4a", "selected_border": "#717171",
}
LIGHT = {
    "surface": "rgba(246,246,246,.88)", "text": "#222222", "muted": "#575757",
    "border": "alpha(#000,.16)", "control": "#e8e8e8", "hover": "#e1e1e1",
    "selected": "#d6d6d6", "selected_border": "#a9a9a9",
}


def styled(widget, name):
    widget.get_style_context().add_class(name)
    return widget


class Launcher(Gtk.ApplicationWindow):
    def __init__(self, app, prefill=False):
        super().__init__(application=app, title="Applications")
        self.set_wmclass("mineos-applications", "MineOSApplications")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_resizable(False)
        self.set_app_paintable(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        styled(self, "mineos-launcher")
        palette = DARK if preferences.read()["appearance"] == "dark" else LIGHT
        if not visual or not screen.is_composited():
            palette = {**palette, "surface": "#222222" if palette is DARK else "#f2f2f2"}
        css = "".join(f"@define-color apps_{key} {color};\n" for key, color in palette.items())
        provider = Gtk.CssProvider()
        provider.load_from_data((css + (catalog.ASSETS.parent.parent / "launcher.css").read_text()).encode())
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 10)
        self.connect("destroy", lambda *_: Gtk.StyleContext.remove_provider_for_screen(screen, provider))

        display = self.get_display()
        pointer = display.get_default_seat().get_pointer()
        _, x, y = pointer.get_position()
        monitor = display.get_monitor_at_point(x, y) or display.get_monitor(0)
        bounds = monitor.get_workarea()
        self.width = min(960, max(320, bounds.width - 72))
        self.height = min(660, max(280, bounds.height - 66))
        self.set_default_size(self.width, self.height)
        self.move(bounds.x + max(0, (bounds.width - self.width) // 2), bounds.y + max(0, (bounds.height - self.height) // 2))
        self.columns = max(2, min(7, (self.width - 56) // 120))
        self.catalog = catalog.installed_apps()
        self.active_group = "All Apps"
        self.switching_group = False
        self.grids = []
        self.search_timer = 0
        self.dock_settings = Gio.Settings.new_with_path(
            "net.launchpad.plank.dock.settings", "/net/launchpad/plank/docks/dock1/"
        )
        surface = styled(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "launcher-surface")
        self.add(surface)
        header = styled(Gtk.Box(spacing=10), "launcher-toolbar")
        icon = Gtk.Image()
        icon.set_from_gicon(Gio.FileIcon.new(Gio.File.new_for_path(str(catalog.ASSETS / "apps.svg"))), Gtk.IconSize.DND)
        icon.set_pixel_size(32)
        header.pack_start(icon, False, False, 0)
        title = styled(Gtk.Label(label="Applications", xalign=0), "launcher-title")
        header.pack_start(title, True, True, 0)
        self.search = styled(Gtk.SearchEntry(), "launcher-search")
        self.search.set_placeholder_text("Search apps")
        self.search.set_size_request(min(255, self.width // 3), -1)
        header.pack_start(self.search, False, False, 0)
        dismiss = styled(Gtk.Button(image=Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)), "launcher-dismiss")
        dismiss.set_tooltip_text("Close")
        dismiss.get_accessible().set_name("Close Applications")
        dismiss.connect("clicked", lambda *_: self.destroy())
        header.pack_end(dismiss, False, False, 0)
        surface.pack_start(header, False, False, 0)
        ribbon = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.AUTOMATIC, vscrollbar_policy=Gtk.PolicyType.NEVER)
        chips = styled(Gtk.Box(spacing=6), "launcher-chips")
        ribbon.add(chips)
        categories = {item.group for item in self.catalog}
        labels = ["All Apps", *(name for name, _ in catalog.GROUPS if name in categories)]
        if "Other" in categories:
            labels.append("Other")
        for label in labels:
            chip = styled(Gtk.ToggleButton(label=label, active=label == self.active_group), "launcher-chip")
            chip.connect("clicked", self.select_group, label, chips)
            chips.pack_start(chip, False, False, 0)
        surface.pack_start(ribbon, False, False, 0)
        surface.pack_start(styled(Gtk.Separator(), "launcher-divider"), False, False, 0)
        self.scroll = styled(Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER), "launcher-scroll")
        self.listing = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        self.listing.set_border_width(15)
        self.scroll.add(self.listing)
        surface.pack_start(self.scroll, True, True, 0)
        self.search.connect("changed", self.queue_search)
        self.search.connect("activate", self.search_activate)
        self.connect("key-press-event", self.key)
        self.connect("destroy", self.cancel_search)
        self.render()
        self.show_all()
        if prefill:
            self.search.grab_focus()
        else:
            self.set_focus(None)

    def select_group(self, chip, label, chips):
        if self.switching_group:
            return
        self.switching_group = True
        try:
            self.active_group = label
            for button in chips.get_children():
                button.set_active(button is chip)
        finally:
            self.switching_group = False
        self.render()

    def cancel_search(self, *_):
        if self.search_timer:
            GLib.source_remove(self.search_timer)
            self.search_timer = 0

    def queue_search(self, *_):
        self.cancel_search()
        self.search_timer = GLib.timeout_add(55, self.apply_search)

    def apply_search(self):
        self.search_timer = 0
        self.render()
        return GLib.SOURCE_REMOVE

    def matching(self):
        terms = self.search.get_text().casefold().split()
        if terms:
            matches = [item for item in self.catalog if all(term in item.search for term in terms)]
            return sorted(matches, key=lambda item: not item.name.casefold().startswith(" ".join(terms)))
        return [item for item in self.catalog if self.active_group == "All Apps" or item.group == self.active_group]

    def render(self):
        for widget in self.listing.get_children():
            widget.destroy()
        self.grids.clear()
        query = self.search.get_text().strip()
        apps = self.matching()
        if not query and self.active_group == "All Apps":
            favorites = catalog.pinned(self.dock_settings, self.catalog)[:self.columns]
            if favorites:
                self.section("Pinned", favorites)
                self.listing.add(styled(Gtk.Separator(), "launcher-divider"))
        if apps:
            self.section("Search Results" if query else self.active_group, apps)
        else:
            self.listing.add(styled(Gtk.Label(label="No matching applications"), "launcher-empty"))
        self.listing.show_all()
        self.scroll.get_vadjustment().set_value(0)

    def section(self, title, apps):
        heading = styled(Gtk.Label(label=title, xalign=0, margin_start=5), "launcher-section")
        self.listing.pack_start(heading, False, False, 0)
        grid = styled(Gtk.FlowBox(selection_mode=Gtk.SelectionMode.SINGLE, homogeneous=True,
                                 column_spacing=4, row_spacing=6, activate_on_single_click=True,
                                 min_children_per_line=self.columns, max_children_per_line=self.columns), "launcher-grid")
        grid.connect("child-activated", lambda _, child: self.launch(child.app))
        for app in apps:
            child = styled(Gtk.FlowBoxChild(), "launcher-tile")
            child.app = app
            child.set_tooltip_text(app.name)
            child.get_accessible().set_name(app.name)
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            cell.set_size_request(87, -1)
            icon = app.info.get_icon() or Gio.ThemedIcon.new("application-x-executable")
            image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG)
            image.set_pixel_size(48)
            well = Gtk.Box()
            well.set_size_request(64, 64)
            well.set_halign(Gtk.Align.CENTER)
            if isinstance(icon, Gio.FileIcon) and icon.get_file().get_parent().get_path() == str(catalog.ASSETS):
                image.set_pixel_size(64)
            else:
                styled(well, "launcher-icon-well")
            well.pack_start(image, True, False, 0)
            cell.add(well)
            name = styled(Gtk.Label(label=app.name, ellipsize=Pango.EllipsizeMode.END, max_width_chars=14), "launcher-app-name")
            cell.add(name)
            child.add(cell)
            grid.add(child)
        self.grids.append(grid)
        self.listing.pack_start(grid, False, False, 0)

    def key(self, _, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.search.get_text():
                self.search.set_text("")
            else:
                self.destroy()
            return True
        if event.keyval == Gdk.KEY_f and event.state & Gdk.ModifierType.CONTROL_MASK:
            self.search.grab_focus()
            return True
        if event.keyval == Gdk.KEY_Down and self.search.is_focus() and self.grids:
            self.grids[-1].get_child_at_index(0).grab_focus()
            return True
        if not self.search.is_focus() and not event.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.SUPER_MASK):
            ch = Gdk.keyval_to_unicode(event.keyval)
            if ch and chr(ch).isprintable() and not chr(ch).isspace():
                self.search.grab_focus()
                self.search.set_text(self.search.get_text() + chr(ch))
                self.search.set_position(-1)
                return True
        return False

    def search_activate(self, *_):
        apps = self.matching()
        if apps and self.search.get_text().strip():
            self.launch(apps[0])

    def launch(self, app):
        context = self.get_display().get_app_launch_context()
        context.set_timestamp(Gtk.get_current_event_time())
        try:
            if not app.info.launch([], context):
                raise RuntimeError("The application did not start.")
        except (GLib.Error, RuntimeError) as error:
            dialog = Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.CLOSE,
                                       text=f"Could not open {app.name}", secondary_text=str(error))
            dialog.run()
            dialog.destroy()
        else:
            self.destroy()


class Applications(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.mineos.Apps", flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    def do_command_line(self, invocation):
        window = self.get_active_window()
        search = "--search" in invocation.get_arguments()[1:]
        if window:
            if search:
                window.search.grab_focus()
                window.present()
            else:
                window.destroy()
        else:
            Launcher(self, prefill=search).present()
        return 0


if __name__ == "__main__":
    Applications().run(sys.argv)
