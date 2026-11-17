import json
import os
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

PLUGIN = "org.mineos.video"
PLUGIN_PATH = Path("/usr/share/plasma/wallpapers") / PLUGIN
VIDEO_FITS = ("fill", "fit", "stretch")
NATIVE_KEYS = ("backdrop", "background_color", "wallpaper_fit", "video", "video_fit", "live")


def available():
    return "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "").split(":")


def evaluate(script):
    result = subprocess.run(
        ["busctl", "--user", "--json=short", "call", "org.kde.plasmashell", "/PlasmaShell",
         "org.kde.PlasmaShell", "evaluateScript", "s", script],
        check=True, capture_output=True, text=True, timeout=5,
    )
    return json.loads(result.stdout)["data"][0]


def local_uri(filename):
    path = Path(filename).expanduser()
    return path.resolve().as_uri() if filename and path.is_file() else ""


def apply(values, old):
    picture_changed = any(old.get(key) != values[key] for key in NATIVE_KEYS[:3])
    live_video = bool(values["live"] and values["video"])
    if not live_video and not picture_changed and not old.get("live"):
        return
    settings = {
        "plugin": PLUGIN,
        "live": live_video,
        "video": local_uri(values["video"]) if live_video else "",
        "picture": local_uri(values["backdrop"]),
        "pictureChanged": picture_changed,
        "color": values["background_color"],
        "pictureFit": {"1": 6, "3": 0, "4": 1, "5": 2}.get(values["wallpaper_fit"], 2),
        "fit": values["video_fit"] if values["video_fit"] in VIDEO_FITS else "fill",
    }
    if live_video and not (PLUGIN_PATH / "metadata.json").is_file():
        raise ValueError("The MineOS live wallpaper plugin is unavailable.")
    if live_video and not settings["video"]:
        raise ValueError("The selected wallpaper video could not be found.")
    script = "const settings = " + json.dumps(settings, ensure_ascii=True) + ";\n" + (
        Path(__file__).with_name("native-wallpaper.js").read_text()
    )
    if evaluate(script).strip() != "ok":
        raise ValueError("The desktop could not apply the wallpaper.")


def local_path(value):
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme == "file" and parsed.netloc in ("", "localhost"):
        return unquote(parsed.path)
    return value if Path(value).is_absolute() else ""


def selection():
    result = evaluate("""
const desktop = desktops().find(item => item.screen === 0);
if (desktop) {
    const plugin = desktop.wallpaperPlugin;
    const live = plugin === "org.mineos.video";
    desktop.currentConfigGroup = ["Wallpaper", plugin, "General"];
    print(JSON.stringify({
        plugin,
        live,
        video: live ? desktop.readConfig("Video", "") : "",
        video_fit: live ? desktop.readConfig("Fit", "fill") : "",
        picture: desktop.readConfig(live ? "Picture" : "Image", ""),
        pictureFit: desktop.readConfig("FillMode", 2)
    }));
}
""")
    if not result:
        return {}
    state = json.loads(result)
    values = {"live": bool(state["live"] and local_path(state["video"]))}
    if values["live"]:
        values["video"] = local_path(state["video"])
        if state["video_fit"] in VIDEO_FITS:
            values["video_fit"] = state["video_fit"]
    picture = local_path(state["picture"])
    if picture:
        values["backdrop"] = picture
    if state["plugin"] == "org.kde.image":
        values["wallpaper_fit"] = {0: "3", 1: "4", 2: "5", 6: "1"}.get(state["pictureFit"], "5")
    return values
