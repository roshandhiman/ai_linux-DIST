import json
import os
import re
import signal
import subprocess
import tempfile
from pathlib import Path

import glass_theme
import native_wallpaper

DESKTOP = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
PREFS = CONFIG / "mineos" / "appearance.json"
PET_POSITION = PREFS.with_name("companion-position.json")
PET_SIZES = {120: "Medium", 166: "Large"}
DOCK = "net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/"
DEFAULTS = {
    "appearance": "dark", "backdrop": str(DESKTOP / "assets" / "graphite.svg"), "background_color": "#171717",
    "ui_scale": "1",
    "wallpaper_fit": "5", "video": "", "video_fit": "fill", "live": False,
    "dock_style": "mineos", "dock_size": 52, "dock_opacity": glass_theme.DOCK_REST_OPACITY, "dock_position": "bottom",
    "dock_hide": True, "dock_zoom": True, "dock_roundness": 19,
    "panel_opacity": 92, "clock_24h": True, "clock_seconds": False, "blur": True, "shadows": True, "animations": True,
    "pet": True, "pet_motion": True, "pet_size": 120, "model": "",
}


def read():
    try:
        data = json.loads(PREFS.read_text())
        if not isinstance(data, dict):
            return DEFAULTS.copy()
    except (OSError, ValueError):
        return DEFAULTS.copy()
    values = {**DEFAULTS, **{key: data[key] for key in DEFAULTS if key in data and type(data[key]) is type(DEFAULTS[key])}}
    if values["pet_size"] not in PET_SIZES:
        # Map custom sizes from the previous companion to the two presets.
        values["pet_size"] = 166 if values["pet_size"] >= 110 else DEFAULTS["pet_size"]
    if "ui_scale" not in data:
        try:
            scale = run("xfconf-query", "-c", "xsettings", "-p", "/Gdk/WindowScalingFactor").strip()
            if scale in ("1", "2"):
                values["ui_scale"] = scale
        except (OSError, subprocess.SubprocessError):
            pass
    if values["backdrop"] == str(DESKTOP / "assets" / "wallpaper.jpg"):
        values["backdrop"] = DEFAULTS["backdrop"]
    if values["backdrop"] == str(DESKTOP / "assets" / "dunes.png"):
        values["backdrop"] = ""
    return values


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, mode="w", delete=False) as file:
        file.write(text)
    os.replace(file.name, path)


def terminal_defaults():
    from gi.repository import GLib

    path = CONFIG / "xfce4/terminal/terminalrc"
    group = "Configuration"
    settings = GLib.KeyFile()
    if path.exists():
        settings.load_from_file(str(path), GLib.KeyFileFlags.KEEP_COMMENTS)
    else:
        defaults = {
            "FontName": "DejaVu Sans Mono 10",
            "MiscMenubarDefault": "FALSE",
            "MiscBordersDefault": "TRUE",
            "ColorForeground": "#e9e9e9",
            "ColorBackground": "#252525",
            "ColorCursor": "#ffffff",
            "BackgroundMode": "TERMINAL_BACKGROUND_SOLID",
        }
        for key, value in defaults.items():
            settings.set_string(group, key, value)
    if settings.has_group(group):
        keys = settings.get_keys(group)[0]
        if "MiscToolbarDefault" in keys and settings.get_value(group, "MiscToolbarDefault") == "FALSE":
            return
    settings.set_string(group, "MiscToolbarDefault", "FALSE")
    write(path, settings.to_data()[0])


def run(*argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=10).stdout


def theme(values):
    dark = values["appearance"] == "dark"
    theme_name = "Arc-Dark" if dark else "Arc"
    css_name = "gtk-dark.css" if dark else "gtk.css"
    write(CONFIG / "gtk-3.0" / "gtk.css", (DESKTOP / css_name).read_text())
    run("xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-n", "-t", "string", "-s", theme_name)
    run("xfconf-query", "-c", "xsettings", "-p", "/Net/IconThemeName", "-n", "-t", "string", "-s", "Papirus-Dark" if dark else "Papirus")
    xfce("xfwm4", "/general/theme", "string", theme_name)


def xfce(channel, property_name, kind, value):
    run("xfconf-query", "-c", channel, "-p", property_name, "-n", "-t", kind, "-s", str(value))


def wallpaper(values):
    channel = "xfce4-desktop"
    image = values["backdrop"]
    if not image or not Path(image).is_file():
        image = ""
    color = values["background_color"]
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        color = DEFAULTS["background_color"]
    channels = [str(int(color[index:index + 2], 16) / 255) for index in (1, 3, 5)]
    properties = run("xfconf-query", "-c", channel, "-l").splitlines()
    prefixes = {prop.rsplit("/", 1)[0] for prop in properties if re.match(r"/backdrop/screen[0-9]+/monitor[^/]+/workspace[0-9]+/", prop)}
    prefixes.update(
        f"/backdrop/screen0/monitor{line.split()[0]}/workspace0"
        for line in run("xrandr", "--query").splitlines()
        if len(line.split()) > 1 and line.split()[1] == "connected"
    )
    xfce(channel, "/backdrop/single-workspace-mode", "bool", "true")
    xfce(channel, "/backdrop/single-workspace-number", "int", 0)
    for prefix in sorted(prefixes):
        xfce(channel, prefix + "/color-style", "int", 0)
        args = [option for component in (*channels, "1") for option in ("-t", "double", "-s", component)]
        run("xfconf-query", "-c", channel, "-p", prefix + "/rgba1", "-n", "-a", *args)
        xfce(channel, prefix + "/last-image", "string", image)
        xfce(channel, prefix + "/image-style", "int", values["wallpaper_fit"] if image else 0)


def replace_setting(text, key, value):
    lines = text.splitlines()
    return "\n".join(f"{key}={value}" if line.startswith(f"{key}=") else line for line in lines) + "\n"


def dock(values):
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    theme_name = "Docky" if values["dock_style"] == "docky" else "MineOS"
    theme_path = data / "plank" / "themes" / theme_name / "dock.theme"
    write(theme_path, glass_theme.plank_theme(values))
    trash = data / "applications/org.mineos.Trash.desktop"
    if trash.is_file():
        icon_name = "trash-" + values["dock_position"] + ".svg"
        icon_path = data / "mineos/icons" / icon_name
        write(icon_path, glass_theme.trash_icon(values["dock_position"]))
        text = trash.read_text()
        updated = re.sub(r"(?m)^Icon=.*$", lambda _: f"Icon={icon_path}", text)
        if updated != text:
            write(trash, updated)
    dock_size = values["dock_size"]
    if run("systemd-detect-virt", "--vm").strip() == "parallels":
        dock_size = min(dock_size, 48)
    settings = {
        "icon-size": str(dock_size), "position": "'" + values["dock_position"] + "'",
        "hide-mode": "'intelligent'" if values["dock_hide"] else "'none'",
        "zoom-enabled": str(values["dock_zoom"]).lower(), "zoom-percent": str(glass_theme.DOCK_ZOOM),
        "theme": f"'{theme_name}'",
    }
    for key, value in settings.items():
        run("gsettings", "set", DOCK, key, value)


def reload_process(name):
    display = os.environ.get("DISPLAY", "").removesuffix(".0")
    matches = subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", name], capture_output=True, text=True)
    for pid in matches.stdout.split():
        try:
            environment = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
            displays = [entry[8:].decode().removesuffix(".0") for entry in environment if entry.startswith(b"DISPLAY=")]
            if display in displays:
                os.kill(int(pid), signal.SIGUSR1)
        except OSError:
            continue


def panel(values):
    template = (DESKTOP / "tint2rc").read_text()
    path = CONFIG / "tint2" / "tint2rc"
    template = template.replace("background_color = #202020 88", f"background_color = #202020 {values['panel_opacity']}", 1)
    time = "%H:%M" if values["clock_24h"] else "%I:%M"
    if values["clock_seconds"]:
        time += ":%S"
    if not values["clock_24h"]:
        time += " %p"
    # tint2 uses physical pixels, unlike GTK's logical pixel coordinates.
    scale = int(values["ui_scale"]) if values["ui_scale"] in ("1", "2") else 1
    dimensions = {"panel_size", "panel_margin", "panel_padding", "button_max_icon_size",
                  "button_padding", "taskbar_padding", "task_maximum_size", "task_padding",
                  "systray_padding", "systray_icon_size", "clock_padding", "rounded"}
    lines = []
    for line in template.splitlines():
        key, separator, value = line.partition(" = ")
        if key in dimensions:
            value = " ".join(str(int(part) * scale) if part.isdigit() else part for part in value.split())
            line = key + separator + value
        elif scale > 1 and key in {"task_font", "time1_font"}:
            family, size = value.rsplit(" ", 1)
            line = key + separator + family + " " + str(int(size) * scale)
        lines.append(line)
    template = "\n".join(lines) + "\n"
    write(path, template.replace("time1_format = %a %d %b  %H:%M", f"time1_format = %a %d %b  {time}"))
    reload_process("tint2")


def compositor(values):
    path = CONFIG / "picom" / "picom.conf"
    template = glass_theme.compositor_config(values["ui_scale"])
    if values["blur"]:
        template = template.replace('blur-method = "none"', 'blur-method = "dual_kawase"')
    if not values["shadows"]:
        template = template.replace("shadow = true", "shadow = false")
    if not values["animations"]:
        template = re.sub(r"        animations = \(.*?\);\n", "", template, flags=re.S)
    write(path, template)
    write(path.with_name("mineos-parallels.conf"), glass_theme.parallels_compositor_config(values["shadows"]))
    reload_process("picom")


def apply(values, old=None):
    old = old or {}
    if old.get("ui_scale") != values["ui_scale"]:
        scale = int(values["ui_scale"]) if values["ui_scale"] in ("1", "2") else 1
        xfce("xsettings", "/Gdk/WindowScalingFactor", "int", scale)
        xfce("xsettings", "/Xft/DPI", "int", 96)
        xfce("xsettings", "/Gtk/CursorThemeSize", "int", 24 * scale)
    if old.get("appearance") != values["appearance"]:
        theme(values)
    if native_wallpaper.available():
        if any(old.get(key) != values[key] for key in native_wallpaper.NATIVE_KEYS):
            native_wallpaper.apply(values, old)
    elif any(old.get(key) != values[key] for key in native_wallpaper.NATIVE_KEYS[:3]):
        wallpaper(values)
    if any(old.get(key) != value for key, value in values.items() if key.startswith("dock_") or key in ("appearance", "blur")):
        dock(values)
    if any(old.get(key) != values[key] for key in ("panel_opacity", "clock_24h", "clock_seconds", "ui_scale")):
        panel(values)
    if any(old.get(key) != values[key] for key in ("blur", "shadows", "animations", "ui_scale")):
        compositor(values)
    write(PREFS, json.dumps(values, indent=2) + "\n")
    if old and old.get("dock_position") != values["dock_position"]:
        subprocess.Popen([str(DESKTOP / "launch-session.sh"), "--restart-dock"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)


if __name__ == "__main__":
    terminal_defaults()
    apply(read())
