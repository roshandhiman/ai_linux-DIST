"""Doing the simple requests without the language model.

Each handler goes through the same :class:`~mineos_agent.os_api.OsApi` the
model's code uses -- the fast path is a shortcut past the *model*, never past
the safeguards. A handler returns ``None`` when it cannot finish (an app name
it cannot resolve, say), and the request then goes to the model with nothing
lost but a few milliseconds.
"""

from dataclasses import dataclass

from .os_api import FOLDERS, SITES, ApiError, OsApi
from .router import Route

__all__ = ["FastResult", "run_fast"]


@dataclass(frozen=True, slots=True)
class FastResult:
    answer: str
    action: str


def run_fast(route: Route, api: OsApi) -> FastResult | None:
    handler = _HANDLERS.get(route.intent)
    if handler is None:
        return None
    try:
        return handler(route.slots, api)
    except ApiError:
        return None


_TLDS = frozenset("com org net io dev in ai edu gov co app me uk de info tv gg".split())


def _open(slots: dict[str, str], api: OsApi) -> FastResult | None:
    target = slots.get("target", "").strip()
    low = target.lower()
    if not target:
        return None
    looks_like_site = " " not in low and low.split("/")[0].rpartition(".")[2] in _TLDS
    if low in SITES or looks_like_site:
        return FastResult(api.open_url(target).capitalize(), "open_url")
    if low in FOLDERS:
        return FastResult(api.open_path(low).capitalize(), "open_path")
    try:
        return FastResult(api.open_app(target).capitalize(), "open_app")
    except ApiError:
        return None


def _search(slots: dict[str, str], api: OsApi) -> FastResult | None:
    query = slots.get("query", "").strip()
    if not query:
        return None
    said = api.web_search(query, slots.get("site"))
    where = f" on {slots['site'].capitalize()}" if slots.get("site") else ""
    return FastResult(said.capitalize() + where + ".", "web_search")


def _volume(slots: dict[str, str], api: OsApi) -> FastResult | None:
    if "mute" in slots:
        return FastResult(api.mute(slots["mute"] == "on").capitalize() + ".", "mute")
    if "level" in slots:
        return FastResult(api.set_volume(slots["level"]).capitalize() + ".", "set_volume")
    return None


def _status(slots: dict[str, str], api: OsApi) -> FastResult | None:
    status = api.system_status()
    parts = []
    if "cpu_percent" in status:
        parts.append(f"CPU {status['cpu_percent']}%")
    if "memory" in status:
        m = status["memory"]
        parts.append(f"memory {m['used_mb']} of {m['total_mb']} MB ({m['percent']}%)")
    if "disk_home" in status:
        d = status["disk_home"]
        parts.append(f"{d['free_gb']} GB free on disk")
    if "battery" in status:
        b = status["battery"]
        parts.append(f"battery {b['percent']}% ({b['status'].lower()})")
    if "uptime" in status:
        parts.append(f"up {status['uptime']}")
    if not parts:
        return None
    return FastResult("; ".join(parts) + ".", "system_status")


def _time(slots: dict[str, str], api: OsApi) -> FastResult | None:
    return FastResult(f"It's {api.now()}.", "now")


def _remember(slots: dict[str, str], api: OsApi) -> FastResult | None:
    said = api.memory.remember(slots["subject"], slots["relation"], slots["object"])
    return FastResult(said.replace("remembered:", "Got it, I'll remember:"), "remember")


def _recall(slots: dict[str, str], api: OsApi) -> FastResult | None:
    facts = api.memory.recall(slots.get("query", ""), limit=5)
    if not facts:
        # Not "I don't know" -- the model may still answer it (e.g. "what's my
        # IP address" is a question about the computer, not about memory).
        return None
    return FastResult("Here's what I have: " + "; ".join(str(f) for f in facts) + ".", "recall")


_HANDLERS = {
    "OPEN": _open,
    "SEARCH": _search,
    "VOLUME": _volume,
    "STATUS": _status,
    "TIME": _time,
    "REMEMBER": _remember,
    "RECALL": _recall,
}
