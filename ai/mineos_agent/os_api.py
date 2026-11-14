"""The ``mine`` API: every way the model's code can touch the computer.

This is the whitelist. Code in the sandbox calls ``mine.open_app("firefox")``;
that becomes a JSON message to the agent process, which looks the name up
*here* and nowhere else. There is no generic "call any function" path, so the
list below is the complete set of powers the model has.

Two kinds of function:

* **immediate** -- reversible or read-only (open an app, read a file in your
  home, check the battery). They just run.
* **asks the user** -- anything that writes, deletes, runs a program or talks
  to hardware. The agent stops and shows the *exact* action ("run: rm notes.txt",
  not "run a command") and does it only on a "y". The approval is bound to that
  exact action by construction: the call is paused mid-flight, so there is no
  second call in which the model could swap the content. (clarkeAgent needed a
  hashed confirmation code for this because its writes were two separate turns.)

Ported and fixed from the old ``tools/system_ctrl.py``: nothing here goes
through a shell, URLs and app names are never pasted into command strings, and
file access is fenced to the user's home with the private parts carved out.
"""

import fnmatch
import json
import os
import shlex
import shutil
import subprocess
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Final

from .memory import GraphMemory

__all__ = ["ApiError", "ApiFunction", "OsApi"]


class ApiError(Exception):
    """A refusal or a failure, phrased as the next thing to try."""


#: ``approver(action, detail) -> bool``. The CLI asks y/N; tests script it.
Approver = Callable[[str, str], bool]
#: ``spawn(argv) -> None``. Starts a desktop program detached.
Spawner = Callable[[list[str]], None]


@dataclass(frozen=True, slots=True)
class ApiFunction:
    name: str
    signature: str
    doc: str
    gated: bool
    method: str
    #: Changes something visible (opens a window, sets volume, writes memory).
    #: A block that called one of these and then failed is still history.
    effect: bool


#: Friendly names -> the executables this ISO actually ships.
APP_ALIASES: Final[dict[str, str]] = {
    "browser": "firefox-esr", "firefox": "firefox-esr", "web browser": "firefox-esr",
    "internet": "firefox-esr", "chrome": "firefox-esr",
    "files": "thunar", "file manager": "thunar", "explorer": "thunar",
    "folders": "thunar", "thunar": "thunar",
    "terminal": "xfce4-terminal", "console": "xfce4-terminal", "shell": "xfce4-terminal",
    "editor": "mousepad", "text editor": "mousepad", "notepad": "mousepad",
    "notes": "mousepad", "mousepad": "mousepad",
    "task manager": "xfce4-taskmanager", "system monitor": "xfce4-taskmanager",
    "processes": "xfce4-taskmanager",
    "volume": "pavucontrol", "sound": "pavucontrol", "audio settings": "pavucontrol",
    "archive manager": "file-roller", "calculator": "galculator",
}

#: Sites a request is likely to name without a URL.
SITES: Final[dict[str, str]] = {
    "youtube": "https://www.youtube.com", "google": "https://www.google.com",
    "github": "https://github.com", "gmail": "https://mail.google.com",
    "wikipedia": "https://en.wikipedia.org", "maps": "https://maps.google.com",
    "reddit": "https://www.reddit.com", "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com", "linkedin": "https://www.linkedin.com",
    "whatsapp": "https://web.whatsapp.com", "chatgpt": "https://chatgpt.com",
}

#: Folder words -> paths under home.
FOLDERS: Final[dict[str, str]] = {
    "home": "", "downloads": "Downloads", "download": "Downloads",
    "documents": "Documents", "docs": "Documents", "desktop": "Desktop",
    "pictures": "Pictures", "photos": "Pictures", "music": "Music",
    "videos": "Videos", "templates": "Templates", "public": "Public",
}

#: Inside home, but not the agent's business: keys, browser profiles, and the
#: agent's own config (which can hold the user's API key) and memory.
PRIVATE: Final[tuple[str, ...]] = (
    ".ssh", ".gnupg", ".pki", ".mozilla", ".password-store", ".local/share/keyrings",
    ".config/mineos", ".local/share/mineos", ".netrc", ".git-credentials",
)

#: Never run, even with a yes: the agent does not hold or ask for root.
NO_ROOT: Final[frozenset[str]] = frozenset({"sudo", "su", "pkexec", "doas", "run0"})

_API: list[ApiFunction] = []


def api(signature: str, doc: str, *, gated: bool = False, effect: bool = False):
    def register(func: Callable[..., Any]) -> Callable[..., Any]:
        _API.append(ApiFunction(func.__name__, signature, doc, gated, func.__name__,
                                effect or gated))
        return func
    return register


def _default_spawn(argv: list[str]) -> None:
    env = dict(os.environ)
    if "DISPLAY" not in env and Path("/tmp/.X11-unix/X0").exists():
        env["DISPLAY"] = ":0"
    subprocess.Popen(  # noqa: S603 - argv list, never a shell
        argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True, env=env,
    )


def _cli_deny(action: str, detail: str) -> bool:
    return False


@dataclass(slots=True)
class OsApi:
    home: Path
    memory: GraphMemory
    approver: Approver = _cli_deny
    spawn: Spawner = _default_spawn
    #: Records every action actually taken, for the trace.
    actions: list[str] = field(default_factory=list)
    app_dirs: tuple[Path, ...] = (
        Path("/usr/share/applications"), Path("/usr/local/share/applications"),
    )

    # -- registry ---------------------------------------------------------

    @staticmethod
    def functions() -> list[ApiFunction]:
        return list(_API)

    @staticmethod
    def names() -> list[str]:
        return [f.name for f in _API]

    @staticmethod
    def changed_something(calls: list[str]) -> bool:
        """Whether any of these (successful) calls had a visible effect."""
        effects = {f.name for f in _API if f.effect}
        return any(name in effects for name in calls)

    def dispatch(self, name: str, args: list, kwargs: dict) -> tuple[bool, object]:
        """The only entry point from the sandbox. Never raises."""
        spec = next((f for f in _API if f.name == name), None)
        if spec is None:
            return False, f"there is no mine.{name}; see the API list"
        try:
            value = getattr(self, spec.method)(*args, **kwargs)
        except ApiError as exc:
            return False, str(exc)
        except TypeError as exc:
            return False, f"wrong arguments; the signature is mine.{spec.signature} ({exc})"
        except OSError as exc:
            return False, f"{exc.strerror or exc}"
        except Exception as exc:  # noqa: BLE001 - one boundary
            return False, f"{type(exc).__name__}: {exc}"
        return True, value

    def _approve(self, action: str, detail: str) -> None:
        if not self.approver(action, detail):
            raise ApiError(f"the user declined ({action}); tell them it was not done")

    # -- paths --------------------------------------------------------------

    def _path(self, path: str, *, must_exist: bool = True) -> Path:
        text = str(path).strip()
        if text.lower() in FOLDERS:
            text = "~/" + FOLDERS[text.lower()]
        if text in ("~", ""):
            candidate = self.home
        elif text.startswith("~/"):
            candidate = self.home / text[2:]
        elif text.startswith("~"):
            raise ApiError("only your own home folder is reachable; use ~/...")
        else:
            candidate = Path(text)
            if not candidate.is_absolute():
                candidate = self.home / candidate
        home = self.home.resolve()
        resolved = candidate.resolve()
        if not resolved.is_relative_to(home):
            raise ApiError(f"{path} is outside the home folder; only ~/ is reachable")
        relative = resolved.relative_to(home).as_posix()
        for private in PRIVATE:
            if relative == private or relative.startswith(private + "/"):
                raise ApiError(f"{path} is private (keys, passwords or agent settings)")
        if must_exist and not resolved.exists():
            raise ApiError(f"{path} does not exist; try mine.find_files to locate it")
        return resolved

    def _show(self, path: Path) -> str:
        try:
            return "~/" + path.relative_to(self.home.resolve()).as_posix()
        except ValueError:
            return str(path)

    # -- desktop ----------------------------------------------------------

    def _desktop_entries(self) -> list[tuple[str, str, list[str]]]:
        """(name, file stem, argv) for every launchable application."""
        found = []
        dirs = (*self.app_dirs, self.home / ".local/share/applications")
        for folder in dirs:
            if not folder.is_dir():
                continue
            for file in sorted(folder.glob("*.desktop")):
                entry = _parse_desktop(file)
                if entry:
                    found.append(entry)
        return found

    @api("open_app(name) -> str", "open an installed app: browser, files, terminal, editor, settings, task manager...", effect=True)
    def open_app(self, name: str) -> str:
        wanted = " ".join(str(name).lower().split())
        if not wanted:
            raise ApiError("say which app, e.g. mine.open_app('browser')")
        # Only the alias table and real menu entries can be opened. A bare
        # "any executable on PATH" fallback would make open_app("reboot") an
        # un-asked-for reboot: logind lets the desktop user do that silently.
        exe = APP_ALIASES.get(wanted)
        if exe and shutil.which(exe):
            self.spawn([exe])
            self.actions.append(f"opened {exe}")
            return f"opened {exe}"
        entries = self._desktop_entries()
        for label, stem, argv in entries:
            if wanted in (label.lower(), stem.lower(), stem.lower().rpartition(".")[2]):
                self.spawn(argv)
                self.actions.append(f"opened {label}")
                return f"opened {label}"
        for label, stem, argv in entries:
            if len(wanted) >= 3 and (wanted in label.lower() or wanted in stem.lower()):
                self.spawn(argv)
                self.actions.append(f"opened {label}")
                return f"opened {label}"
        known = sorted({label for label, _, _ in entries})[:12]
        hint = ", ".join(known) if known else ", ".join(sorted(set(APP_ALIASES))[:12])
        raise ApiError(f"no app called '{name}' is installed; available: {hint}")

    @api("open_url(url) -> str", "open an http(s) link in the browser", effect=True)
    def open_url(self, url: str) -> str:
        text = str(url).strip()
        if text.lower() in SITES:
            text = SITES[text.lower()]
        if "://" not in text and "." in text and " " not in text:
            text = "https://" + text
        parsed = urllib.parse.urlparse(text)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ApiError("only http:// and https:// links can be opened")
        self.spawn(["xdg-open", text])
        self.actions.append(f"opened {text}")
        return f"opened {text}"

    @api("web_search(query, site=None) -> str", "search the web (or youtube/github/wikipedia) in the browser", effect=True)
    def web_search(self, query: str, site: str | None = None) -> str:
        q = urllib.parse.quote_plus(str(query).strip())
        if not q:
            raise ApiError("the search query is empty")
        targets = {
            None: f"https://duckduckgo.com/?q={q}",
            "youtube": f"https://www.youtube.com/results?search_query={q}",
            "github": f"https://github.com/search?q={q}",
            "wikipedia": f"https://en.wikipedia.org/w/index.php?search={q}",
            "google": f"https://www.google.com/search?q={q}",
        }
        key = str(site).lower().strip() if site else None
        if key not in targets:
            raise ApiError(f"site must be one of: {', '.join(k for k in targets if k)}")
        url = targets[key]
        self.spawn(["xdg-open", url])
        self.actions.append(f"searched {query}")
        return f"searching for {query}"

    @api("open_path(path) -> str", "open a file or folder from home in its default app (e.g. 'downloads')", effect=True)
    def open_path(self, path: str) -> str:
        target = self._path(path)
        self.spawn(["xdg-open", str(target)])
        self.actions.append(f"opened {self._show(target)}")
        return f"opened {self._show(target)}"

    @api("set_volume(percent) -> str", "set speaker volume 0-100, or '+10' / '-10' to change it", effect=True)
    def set_volume(self, percent: int | float | str) -> str:
        raw = str(percent).strip().rstrip("%")
        relative = raw[:1] in "+-" and len(raw) > 1
        try:
            amount = int(float(raw))
        except ValueError:
            raise ApiError("percent must be a number from 0 to 100, or like '+10'") from None
        level = max(-100, min(100, amount)) if relative else max(0, min(100, amount))
        if shutil.which("pactl"):
            _quiet(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])
            _quiet(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level:+d}%" if relative else f"{level}%"])
        elif shutil.which("wpctl"):
            value = f"{abs(level) / 100:.2f}" + (("+" if level > 0 else "-") if relative else "")
            _quiet(["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", value])
        else:
            raise ApiError("no sound control (pactl or wpctl) is installed")
        said = f"volume {'up' if level > 0 else 'down'} {abs(level)}%" if relative else f"volume set to {level}%"
        self.actions.append(said)
        return said

    @api("mute(on=True) -> str", "mute or unmute the speakers", effect=True)
    def mute(self, on: bool = True) -> str:
        if shutil.which("pactl"):
            _quiet(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if on else "0"])
        elif shutil.which("wpctl"):
            _quiet(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if on else "0"])
        else:
            raise ApiError("no sound control (pactl or wpctl) is installed")
        self.actions.append("muted" if on else "unmuted")
        return "muted" if on else "unmuted"

    @api("notify(title, message='') -> str", "show a desktop notification", effect=True)
    def notify(self, title: str, message: str = "") -> str:
        if not shutil.which("notify-send"):
            raise ApiError("desktop notifications are not available; print the message instead")
        self.spawn(["notify-send", "--app-name=MineOS", str(title)[:80], str(message)[:300]])
        return "notification shown"

    # -- information ------------------------------------------------------

    @api("system_status() -> dict", "cpu %, memory, disk, battery, uptime")
    def system_status(self) -> dict[str, Any]:
        return system_status(self.home)

    @api("now() -> str", "current local date and time")
    def now(self) -> str:
        return datetime.now().strftime("%A %d %B %Y, %H:%M")

    @api("list_dir(path='~') -> list", "names in a folder under home; folders end with /")
    def list_dir(self, path: str = "~") -> list[str]:
        folder = self._path(path)
        if not folder.is_dir():
            raise ApiError(f"{path} is a file, not a folder")
        names = []
        for child in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            if child.name.startswith("."):
                continue
            names.append(child.name + ("/" if child.is_dir() else ""))
        if len(names) > 60:
            names = names[:60] + [f"... and {len(names) - 60} more"]
        return names

    @api("read_file(path, max_chars=3000) -> str", "read a text file under home")
    def read_file(self, path: str, max_chars: int = 3000) -> str:
        target = self._path(path)
        if target.is_dir():
            raise ApiError(f"{path} is a folder; use mine.list_dir")
        if target.stat().st_size > 2_000_000:
            raise ApiError(f"{path} is larger than 2 MB; it is not read whole")
        data = target.read_bytes()
        if b"\x00" in data[:4096]:
            raise ApiError(f"{path} is a binary file, not text")
        limit = max(100, min(int(max_chars), 8000))
        text = data.decode("utf-8", "replace")
        return text if len(text) <= limit else text[:limit] + f"\n[... {len(text) - limit} more characters]"

    @api("file_info(path) -> dict", "size and date of a file or folder under home: {'bytes', 'size', 'modified', 'is_folder'}")
    def file_info(self, path: str) -> dict[str, Any]:
        target = self._path(path)
        stat = target.stat()
        return {
            "path": self._show(target),
            "bytes": stat.st_size,
            "size": _human(stat.st_size),
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "is_folder": target.is_dir(),
        }

    @api("find_files(name, folder='~') -> list", "find files by name or *.ext pattern under home; returns paths like ~/Downloads/a.pdf")
    def find_files(self, name: str, folder: str = "~") -> list[str]:
        root = self._path(folder)
        pattern = str(name).strip().lower()
        if not pattern:
            raise ApiError("give part of a file name, or a pattern like *.pdf")
        wildcard = any(ch in pattern for ch in "*?[")
        found: list[str] = []
        base_depth = len(root.parts)
        deadline = time.monotonic() + 5
        for current, dirs, files in os.walk(root):
            here = Path(current)
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
            if len(here.parts) - base_depth >= 5:
                dirs[:] = []
            for entry in files + dirs:
                low = entry.lower()
                if (fnmatch.fnmatch(low, pattern) if wildcard else pattern in low):
                    found.append(self._show(here / entry))
                    if len(found) >= 25:
                        return found
            if time.monotonic() > deadline:
                break
        return found

    # -- memory -----------------------------------------------------------

    @api("remember(subject, relation, obj) -> str", "store a fact, e.g. remember('user', 'favourite editor', 'mousepad')", effect=True)
    def remember(self, subject: str, relation: str, obj: str) -> str:
        try:
            return self.memory.remember(subject, relation, obj, source="agent")
        except ValueError as exc:
            raise ApiError(str(exc)) from None

    @api("recall(query) -> list", "facts you stored that relate to the query")
    def recall(self, query: str) -> list[str]:
        return [str(f) for f in self.memory.recall(str(query))]

    @api("forget(name) -> str", "delete everything stored about a person or thing", effect=True)
    def forget(self, name: str) -> str:
        removed = self.memory.forget(str(name))
        return f"forgot {removed} fact(s) about {name}" if removed else f"nothing stored about {name}"

    # -- gated: these stop and ask the user --------------------------------

    @api("write_file(path, text, append=False) -> str", "write a text file under home", gated=True)
    def write_file(self, path: str, text: str, append: bool = False) -> str:
        target = self._path(path, must_exist=False)
        body = str(text)
        if len(body) > 200_000:
            raise ApiError("the text is over 200,000 characters; write less")
        if target.is_dir():
            raise ApiError(f"{path} is a folder")
        verb = "append to" if append else ("overwrite" if target.exists() else "create")
        preview = body if len(body) <= 160 else body[:160] + f"... ({len(body)} chars)"
        self._approve(f"{verb} {self._show(target)}", preview)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a" if append else "w", encoding="utf-8") as handle:
            handle.write(body)
        self.actions.append(f"{verb} {self._show(target)}")
        return f"wrote {len(body)} characters to {self._show(target)}"

    @api("trash(path) -> str", "move a file or folder under home to the Trash", gated=True)
    def trash(self, path: str) -> str:
        target = self._path(path)
        if target == self.home.resolve():
            raise ApiError("the home folder itself cannot be trashed")
        self._approve(f"move {self._show(target)} to the Trash", "")
        if shutil.which("gio"):
            result = subprocess.run(["gio", "trash", str(target)], capture_output=True,
                                    text=True, timeout=30)
            if result.returncode != 0:
                raise ApiError(f"could not trash it: {result.stderr.strip()[:120]}")
        else:
            bin_dir = self.home / ".local/share/Trash/files"
            info_dir = self.home / ".local/share/Trash/info"
            bin_dir.mkdir(parents=True, exist_ok=True)
            info_dir.mkdir(parents=True, exist_ok=True)
            dest = bin_dir / target.name
            n = 1
            while dest.exists():
                n += 1
                dest = bin_dir / f"{target.stem}.{n}{target.suffix}"
            (info_dir / (dest.name + ".trashinfo")).write_text(
                "[Trash Info]\nPath={}\nDeletionDate={}\n".format(
                    urllib.parse.quote(str(target)), datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                encoding="utf-8")
            shutil.move(str(target), str(dest))
        self.actions.append(f"trashed {self._show(target)}")
        return f"moved {self._show(target)} to the Trash"

    @api("run(command) -> str", "run a terminal command (no shell, no sudo) and return its output", gated=True)
    def run(self, command: str) -> str:
        try:
            argv = shlex.split(str(command))
        except ValueError as exc:
            raise ApiError(f"could not split the command: {exc}") from None
        if not argv:
            raise ApiError("the command is empty")
        if Path(argv[0]).name in NO_ROOT:
            raise ApiError("the agent does not run anything as root; ask the user to run it themselves")
        if any(token in ("|", "&&", "||", ";", ">", ">>", "<") for token in argv):
            raise ApiError("pipes and redirects need a shell, which is not used; run one command "
                           "and process its output in Python")
        if not shutil.which(argv[0]):
            raise ApiError(f"{argv[0]} is not installed")
        self._approve(f"run: {shlex.join(argv)}", "")
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=60,
                                    cwd=self.home, stdin=subprocess.DEVNULL,
                                    encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            raise ApiError("the command ran for over 60 seconds and was stopped") from None
        self.actions.append(f"ran {shlex.join(argv)}")
        output = (result.stdout + result.stderr).strip()
        if len(output) > 4000:
            output = output[:4000] + "\n[output cut]"
        return f"exit {result.returncode}\n{output}" if result.returncode else output or "(no output)"

    @api("device_send(text, port=None) -> str", "send one line to an ESP32/Arduino on USB serial", gated=True)
    def device_send(self, text: str, port: str | None = None) -> str:
        try:
            import serial  # type: ignore[import-not-found]
        except ImportError:
            raise ApiError("serial support (python3-serial) is not installed") from None
        if port is None:
            ports = sorted(str(p) for pattern in ("ttyUSB*", "ttyACM*") for p in Path("/dev").glob(pattern))
            if not ports:
                raise ApiError("no USB serial device is plugged in")
            port = ports[0]
        if not str(port).startswith("/dev/tty"):
            raise ApiError("port must be a /dev/tty... device")
        line = str(text).replace("\n", " ")[:200]
        self._approve(f"send '{line}' to {port}", "")
        with serial.Serial(str(port), 115200, timeout=1) as device:
            device.write((line + "\n").encode("utf-8"))
            reply = device.readline().decode("utf-8", "replace").strip()
        self.actions.append(f"sent to {port}")
        return reply or "sent (no reply)"


def _human(size: float) -> str:
    for unit in ("bytes", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "bytes" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _quiet(argv: list[str]) -> None:
    result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise ApiError(f"{argv[0]} failed: {result.stderr.strip()[:120] or 'no sound server?'}")


def _parse_desktop(file: Path) -> tuple[str, str, list[str]] | None:
    try:
        lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    fields: dict[str, str] = {}
    in_entry = False
    for line in lines:
        line = line.strip()
        if line.startswith("["):
            in_entry = line == "[Desktop Entry]"
            continue
        if in_entry and "=" in line:
            key, _, value = line.partition("=")
            fields.setdefault(key.strip(), value.strip())
    if fields.get("Type") != "Application" or fields.get("Hidden") == "true":
        return None
    if fields.get("NoDisplay") == "true" or not fields.get("Exec") or not fields.get("Name"):
        return None
    exec_line = fields["Exec"]
    for code in ("%f", "%F", "%u", "%U", "%d", "%D", "%n", "%N", "%i", "%c", "%k", "%v", "%m"):
        exec_line = exec_line.replace(code, "")
    exec_line = exec_line.replace("%%", "%")
    try:
        argv = shlex.split(exec_line)
    except ValueError:
        return None
    if not argv:
        return None
    return fields["Name"], file.stem, argv


def _read(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _cpu_percent() -> float | None:
    def sample() -> tuple[int, int] | None:
        line = _read("/proc/stat").splitlines()[:1]
        if not line:
            return None
        values = [int(v) for v in line[0].split()[1:]]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        return idle, sum(values)
    first = sample()
    if first is None:
        return None
    time.sleep(0.25)
    second = sample()
    if second is None or second[1] == first[1]:
        return None
    return round(100 * (1 - (second[0] - first[0]) / (second[1] - first[1])), 1)


def system_status(home: Path) -> dict[str, Any]:
    status: dict[str, Any] = {}
    cpu = _cpu_percent()
    if cpu is not None:
        status["cpu_percent"] = cpu
    if hasattr(os, "getloadavg"):
        status["load_1m"] = round(os.getloadavg()[0], 2)
    meminfo = {}
    for line in _read("/proc/meminfo").splitlines():
        key, _, value = line.partition(":")
        if value.strip().split():
            meminfo[key] = int(value.split()[0])
    if "MemTotal" in meminfo and "MemAvailable" in meminfo:
        total, avail = meminfo["MemTotal"] / 1024, meminfo["MemAvailable"] / 1024
        status["memory"] = {"used_mb": round(total - avail), "total_mb": round(total),
                            "percent": round(100 * (total - avail) / total, 1)}
    usage = shutil.disk_usage(home)
    status["disk_home"] = {"free_gb": round(usage.free / 2**30, 1),
                           "total_gb": round(usage.total / 2**30, 1),
                           "percent_used": round(100 * usage.used / usage.total, 1)}
    for battery in sorted(Path("/sys/class/power_supply").glob("BAT*")):
        capacity = _read(str(battery / "capacity"))
        if capacity:
            status["battery"] = {"percent": int(capacity),
                                 "status": _read(str(battery / "status")) or "unknown"}
            break
    uptime = _read("/proc/uptime").split()
    if uptime:
        minutes = int(float(uptime[0]) // 60)
        status["uptime"] = f"{minutes // 60}h {minutes % 60}m"
    return status


def api_reference() -> str:
    """The API as the model reads it. Built from the registry, so it can't drift."""
    lines = []
    for spec in _API:
        mark = " [asks user]" if spec.gated else ""
        lines.append(f"  mine.{spec.signature}{mark}: {spec.doc}")
    return "\n".join(lines)


def to_json(value: object) -> str:
    return json.dumps(value, default=str)
