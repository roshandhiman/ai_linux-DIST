import os
from pathlib import Path
import re
from string import Template

DESKTOP = Path(__file__).resolve().parent

MOTION_MS = 170
TOKENS = {
    "font": "Inter, sans-serif",
    "window_radius": "24px",
    "card_radius": "19px",
    "control_radius": "15px",
    "pill_radius": "999px",
    "space": "8px",
    "inset": "16px",
    "window_shadow": "0 20px 60px rgba(0,0,0,.45)",
    "transition": f"{MOTION_MS}ms",
}
PALETTES = {
    "dark": {
        "surface": "rgba(30,30,30,.55)", "solid": "#252528", "text": "#f5f4f7",
        "muted": "#c1bfc8", "line": "rgba(255,255,255,.12)", "nav": "rgba(10,10,14,.20)",
        "card": "rgba(255,255,255,.06)", "control": "rgba(255,255,255,.085)",
        "hover": "rgba(255,255,255,.14)", "selected": "rgba(156,178,255,.19)",
        "accent": "#b7c9ff", "accent_fill": "rgba(138,163,245,.20)",
        "danger": "#ffb7ba", "danger_fill": "rgba(224,84,95,.20)",
        "blue": "#a7c9ff", "violet": "#d5b8ff", "amber": "#ffcf9c", "mint": "#9be5cb",
        "dock": (30, 30, 30), "dock_top": (47, 47, 51), "dock_solid": (38, 38, 42),
    },
    "light": {
        "surface": "rgba(245,243,249,.73)", "solid": "#f3f1f6", "text": "#24232c",
        "muted": "#575362", "line": "rgba(37,34,52,.14)", "nav": "rgba(48,37,73,.065)",
        "card": "rgba(255,255,255,.63)", "control": "rgba(42,37,69,.08)",
        "hover": "rgba(42,37,69,.13)", "selected": "rgba(73,100,193,.18)",
        "accent": "#394f9b", "accent_fill": "rgba(76,102,195,.16)",
        "danger": "#9f253d", "danger_fill": "rgba(190,47,73,.16)",
        "blue": "#365c9e", "violet": "#66429e", "amber": "#795224", "mint": "#23765c",
        "dock": (238, 235, 245), "dock_top": (255, 254, 255), "dock_solid": (237, 234, 242),
    },
}
DOCK_RADIUS = 42
DOCK_EDGE_GAP = 12
DOCK_ZOOM = 116
DOCK_REST_OPACITY = 55
DOCK_FALLBACK_OPACITY = 80
DOCK_VALUES = {
    "LineWidth": 1,
    "HorizPadding": 11,
    "TopPadding": 8,
    "BottomPadding": 8,
    "ItemPadding": 7,
    "IndicatorSize": 7,
    "IconShadowSize": 2,
    "LaunchBounceHeight": .15,
    "ClickTime": 150,
    "LaunchBounceTime": 180,
    "ActiveTime": 170,
    "SlideTime": 170,
    "FadeTime": 170,
    "HideTime": 170,
    "ItemMoveTime": 170,
}
BLUR_STRENGTH = 7
WINDOW_CORNER = 24
SHADOW = {"radius": 28, "opacity": .42, "offset_x": -22, "offset_y": -12}


def capable():
    display = re.sub(r"[^a-zA-Z0-9]", "_", os.environ.get("DISPLAY", "").removesuffix(".0"))
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    try:
        pid = int((runtime / f"mineos-glass-{display}").read_text())
        proc = Path("/proc") / str(pid)
        return proc.stat().st_uid == os.getuid() and (proc / "comm").read_text().strip() == "picom"
    except (OSError, ValueError):
        return False


def style(values, component, composited):
    palette = PALETTES.get(values["appearance"], PALETTES["dark"])
    colors = {name: value for name, value in palette.items() if isinstance(value, str)}
    if not (values["blur"] and composited and capable()):
        colors["surface"] = colors["solid"]
    definitions = "".join(f"@define-color glass_{name} {value};\n" for name, value in colors.items())
    tokens = {**TOKENS, "transition": TOKENS["transition"] if values["animations"] else "0ms"}
    styles = "".join((DESKTOP / filename).read_text() for filename in ("glass.css", f"{component}.css"))
    return (definitions + Template(styles).substitute(tokens)).encode()


def rgba(color, alpha):
    return ";;".join(str(value) for value in (*color, alpha))


def plank_theme(values):
    palette = PALETTES.get(values["appearance"], PALETTES["dark"])
    blurred = values["blur"] and capable()
    opacity = values["dock_opacity"] if blurred else DOCK_FALLBACK_OPACITY + values["dock_opacity"] * (100 - DOCK_FALLBACK_OPACITY) / 100
    alpha = round(opacity * 255 / 100)
    radius = max(2, round(DOCK_RADIUS * values["dock_roundness"] / 24))
    fill = palette["dock"] if blurred else palette["dock_solid"]
    values = {
        **DOCK_VALUES,
        "TopRoundness": radius,
        "BottomRoundness": radius,
        "OuterStrokeColor": rgba((255, 255, 255), 46),
        "InnerStrokeColor": rgba((255, 255, 255), 13),
        "FillStartColor": rgba(palette["dock_top"] if blurred else fill, alpha),
        "FillEndColor": rgba(fill, alpha),
    }
    return Template((DESKTOP / "dock.theme").read_text()).substitute(values)


def trash_icon(position):
    source = (DESKTOP / "assets/icons/trash.svg").read_text().split("\n", 1)[1].split("</svg>", 1)[0]
    if position in ("left", "right"):
        offset = "7 11"
        divider = "M12 4h40"
    else:
        offset = "11 7"
        divider = "M4 12v40"
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 64 64">'
        f'<path d="{divider}" stroke="#aaaab3" stroke-opacity=".60" stroke-width="1.5" stroke-linecap="round"/>'
        f'<g transform="translate({offset}) scale(.80)">{source}</g></svg>\n'
    )


def compositor_config(ui_scale):
    scale = 2 if ui_scale == "2" else 1
    tokens = {
        "shadow_radius": SHADOW["radius"],
        "shadow_opacity": SHADOW["opacity"],
        "shadow_x": SHADOW["offset_x"],
        "shadow_y": SHADOW["offset_y"],
        "blur_strength": BLUR_STRENGTH,
        "regular_corner": 12 * scale,
        "window_corner": WINDOW_CORNER * scale,
        "motion_seconds": MOTION_MS / 1000,
    }
    return Template((DESKTOP / "picom.conf").read_text()).substitute(tokens)
