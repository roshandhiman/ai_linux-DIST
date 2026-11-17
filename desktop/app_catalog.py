import os
from dataclasses import dataclass
from pathlib import Path

import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

import preferences

ASSETS = Path(__file__).resolve().parent / "assets" / "icons"
LAUNCHERS = preferences.CONFIG / "plank/dock1/launchers"
DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
APPS = DATA / "applications"
DOCK_SHORTCUT = "mineos-apps.dockitem"

CUSTOM_APPS = {
    "thunar.desktop": "Files",
    "firefox-esr.desktop": "Firefox",
    "xfce4-terminal.desktop": "Terminal",
    "org.xfce.mousepad.desktop": "Text Editor",
    "xfce4-taskmanager.desktop": "Task Manager",
    "org.gnome.SystemMonitor.desktop": "System Monitor",
}
FAVORITES = (
    "thunar.dockitem", DOCK_SHORTCUT, "firefox-esr.dockitem", "xfce4-terminal.dockitem",
    "mineos-assistant.dockitem", "mineos-settings.dockitem", "org.xfce.mousepad.dockitem",
    "trash.dockitem",
)
PANEL_ROUTES = {
    "xfce4-accessibility-settings.desktop", "xfce-display-settings.desktop",
    "xfce-keyboard-settings.desktop", "xfce-mouse-settings.desktop",
    "xfce-session-settings.desktop", "xfce4-power-manager-settings.desktop",
    "xfce4-color-settings.desktop", "xfce4-mime-settings.desktop",
    "xfce4-notifyd-config.desktop", "xfce4-about.desktop", "nm-connection-editor.desktop",
    "org.pulseaudio.pavucontrol.desktop", "xfce4-terminal-emulator.desktop",
    "xfce4-file-manager.desktop", "xfce4-web-browser.desktop", "xfce4-mail-reader.desktop",
    "xfce4-appfinder.desktop", "xfce4-run.desktop", "xfce4-settings-editor.desktop",
}
GROUPS = (
    ("Internet", {"Network", "WebBrowser", "Email", "Chat", "InstantMessaging"}),
    ("Productivity", {"Office", "Finance", "Calendar", "Education"}),
    ("Developer", {"Development", "IDE", "TerminalEmulator"}),
    ("Media", {"AudioVideo", "Audio", "Video", "Graphics", "Photography"}),
    ("Utilities", {"Utility", "System", "Settings", "FileTools"}),
    ("Games", {"Game"}),
)
PRIVATE_LAUNCHERS = {"org.mineos.Companion.desktop", "org.mineos.Trash.desktop", "org.mineos.Apps.desktop"}


@dataclass(frozen=True)
class App:
    info: Gio.DesktopAppInfo
    name: str
    group: str
    search: str


def installed_apps():
    apps = []
    for info in Gio.AppInfo.get_all():
        if not isinstance(info, Gio.DesktopAppInfo) or not info.should_show():
            continue
        app_id = info.get_id()
        if app_id in PANEL_ROUTES or app_id in PRIVATE_LAUNCHERS:
            continue
        name = CUSTOM_APPS.get(app_id, info.get_display_name())
        categories = set((info.get_categories() or "").split(";"))
        group = next((title for title, tags in GROUPS if tags & categories), "Other")
        search = " ".join([name, info.get_display_name(), info.get_generic_name() or "",
                           info.get_executable() or "", group, *(info.get_keywords() or [])]).casefold()
        apps.append(App(info, name, group, search))
    return sorted(apps, key=lambda item: (item.name.casefold(), item.info.get_id()))


def pinned(settings, apps):
    by_id = {item.info.get_id(): item for item in apps}
    matches = []
    for name in settings.get_strv("dock-items"):
        item = GLib.KeyFile()
        try:
            item.load_from_file(str(LAUNCHERS / Path(name).name), GLib.KeyFileFlags.NONE)
            uri = item.get_string("PlankDockItemPreferences", "Launcher")
            app_file = Gio.File.new_for_uri(uri)
            app = by_id.get(app_file.get_basename()) if app_file.get_path() else None
            if app and app not in matches:
                matches.append(app)
        except GLib.Error:
            continue
    return matches[:7]


def set_up_dock(defaults=False):
    settings = Gio.Settings.new_with_path("net.launchpad.plank.dock.settings", "/net/launchpad/plank/docks/dock1/")
    for app_id, name in CUSTOM_APPS.items():
        try:
            app = Gio.DesktopAppInfo.new(app_id)
        except TypeError:
            # Missing optional desktop entries raise in PyGObject.
            continue
        if not app:
            continue
        desktop_file = APPS / app_id
        source = Path(app.get_filename())
        entry = GLib.KeyFile()
        entry.load_from_file(str(source), GLib.KeyFileFlags.KEEP_TRANSLATIONS | GLib.KeyFileFlags.KEEP_COMMENTS)
        if source == desktop_file and "X-MineOS-Icon" not in entry.get_keys("Desktop Entry")[0]:
            continue
        if source == desktop_file:
            roots = GLib.get_system_data_dirs()
            packaged = next((Path(root) / "applications" / app_id for root in roots
                             if (Path(root) / "applications" / app_id).is_file()), None)
            if packaged:
                entry.load_from_file(str(packaged), GLib.KeyFileFlags.KEEP_TRANSLATIONS | GLib.KeyFileFlags.KEEP_COMMENTS)
        entry.set_string("Desktop Entry", "Name", name)
        entry.set_boolean("Desktop Entry", "X-MineOS-Icon", True)
        preferences.write(desktop_file, entry.to_data()[0])
        if app_id in ("thunar.desktop", "firefox-esr.desktop", "xfce4-terminal.desktop", "org.xfce.mousepad.desktop"):
            write_dockitem(app_id[:-8] + ".dockitem", desktop_file)
    write_dockitem(DOCK_SHORTCUT, APPS / "org.mineos.Apps.desktop")
    if defaults:
        settings.set_strv("dock-items", [name for name in FAVORITES if (LAUNCHERS / name).is_file()])
    elif not (preferences.CONFIG / "mineos/dock-apps-v1").exists():
        items = settings.get_strv("dock-items")
        if DOCK_SHORTCUT not in items:
            position = items.index("thunar.dockitem") + 1 if "thunar.dockitem" in items else 0
            settings.set_strv("dock-items", [*items[:position], DOCK_SHORTCUT, *items[position:]])
    preferences.write(preferences.CONFIG / "mineos/dock-apps-v1", "")


def write_dockitem(name, desktop_file):
    preferences.write(LAUNCHERS / name, f"[PlankDockItemPreferences]\nLauncher={desktop_file.as_uri()}\n")


if __name__ == "__main__":
    import sys
    set_up_dock("--defaults" in sys.argv[1:])
