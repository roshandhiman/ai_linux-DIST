import json
import os
import subprocess
import tempfile
from pathlib import Path

DESKTOP = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
PREFS = CONFIG / "mineos" / "appearance.json"
DOCK = "net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/"
DEFAULTS = {
    "appearance": "light", "backdrop": str(DESKTOP / "assets" / "dunes.png"),
    "video": "", "live": False, "dock_size": 42, "dock_opacity": 68,
    "dock_position": "bottom", "dock_hide": True, "dock_zoom": True,
    "dock_roundness": 14, "panel_opacity": 88, "blur": False,
    "pet": True, "pet_motion": True, "pet_size": 104, "model": "",
}


def read():
    try:
        data = json.loads(PREFS.read_text())
        return {**DEFAULTS, **{key: data[key] for key in DEFAULTS if key in data}}
    except (OSError, ValueError, TypeError):
        return DEFAULTS.copy()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, mode="w", delete=False) as file:
        file.write(text)
    os.replace(file.name, path)


def run(*argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=10).stdout


def theme(values):
    dark = values["appearance"] == "dark"
    theme_name = "Arc-Dark" if dark else "Arc"
    css_name = "gtk-dark.css" if dark else "gtk.css"
    write(CONFIG / "gtk-3.0" / "gtk.css", (DESKTOP / css_name).read_text())
    run("xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-n", "-t", "string", "-s", theme_name)
    run("xfconf-query", "-c", "xsettings", "-p", "/Net/IconThemeName", "-n", "-t", "string", "-s", "Papirus-Dark" if dark else "Papirus")
    run("xfconf-query", "-c", "xfwm4", "-p", "/general/theme", "-s", theme_name)


def wallpaper(values):
    path = Path(values["backdrop"])
    if not path.is_file():
        path = DESKTOP / "assets" / "dunes.png"
    properties = run("xfconf-query", "-c", "xfce4-desktop", "-l").splitlines()
    for prop in properties:
        if prop.endswith("/last-image"):
            run("xfconf-query", "-c", "xfce4-desktop", "-p", prop, "-s", str(path))


def replace_setting(text, key, value):
    lines = text.splitlines()
    return "\n".join(f"{key}={value}" if line.startswith(f"{key}=") else line for line in lines) + "\n"


def dock(values):
    dark = values["appearance"] == "dark"
    tint = "30;;30;;32" if dark else "225;;225;;225"
    alpha = round(values["dock_opacity"] * 255 / 100)
    template = (DESKTOP / "dock.theme").read_text()
    for field in ("FillStartColor", "FillEndColor"):
        template = replace_setting(template, field, f"{tint};;{alpha}")
    for field in ("TopRoundness", "BottomRoundness"):
        template = replace_setting(template, field, values["dock_roundness"])
    theme_path = Path.home() / ".local/share/plank/themes/MineOS/dock.theme"
    write(theme_path, template)
    settings = {
        "icon-size": str(values["dock_size"]), "position": "'" + values["dock_position"] + "'",
        "hide-mode": "'intelligent'" if values["dock_hide"] else "'none'",
        "zoom-enabled": str(values["dock_zoom"]).lower(), "zoom-percent": "120",
        "theme": "'MineOS'",
    }
    for key, value in settings.items():
        run("gsettings", "set", DOCK, key, value)


def panel(values):
    template = (DESKTOP / "tint2rc").read_text()
    path = CONFIG / "tint2" / "tint2rc"
    write(path, template.replace("background_color = #202020 88", f"background_color = #202020 {values['panel_opacity']}", 1))
    subprocess.run(["pkill", "-USR1", "-u", str(os.getuid()), "-x", "tint2"], check=False)


def compositor(values):
    path = CONFIG / "picom" / "picom.conf"
    template = (DESKTOP / "picom.conf").read_text()
    if values["blur"]:
        template = template.replace('blur-method = "none"', 'blur-method = "dual_kawase"').replace("blur-background = false", "blur-background = true")
    write(path, template)


def apply(values, old=None):
    old = old or {}
    if old.get("appearance") != values["appearance"]:
        theme(values)
    if old.get("backdrop") != values["backdrop"]:
        wallpaper(values)
    if any(old.get(key) != value for key, value in values.items() if key.startswith("dock_") or key == "appearance"):
        dock(values)
    if old.get("panel_opacity") != values["panel_opacity"]:
        panel(values)
    if old.get("blur") != values["blur"]:
        compositor(values)
    write(PREFS, json.dumps(values, indent=2) + "\n")


if __name__ == "__main__":
    apply(read())
