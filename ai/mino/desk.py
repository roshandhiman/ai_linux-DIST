"""Local desktop and project actions. Screens stay on this machine."""

import difflib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote_plus, urlsplit

from mineos_agent.coding import CodingApi
from mineos_agent.os_api import ApiError, NO_ROOT

SOURAV_CHANNEL = "https://www.youtube.com/@souravjoshivlogs7028"
VISION = Path("/usr/share/mineos/models/screen-vision")


def accomplish(argv, timeout, *, data=None):
    try:
        return subprocess.run(argv, input=data, capture_output=True, timeout=timeout, check=True).stdout
    except FileNotFoundError as exc:
        raise ApiError(f"{argv[0]} is missing. Run the Mino installer.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ApiError(f"{Path(argv[0]).name} took too long.") from exc
    except subprocess.CalledProcessError as exc:
        raise ApiError(f"{Path(argv[0]).name} could not complete the request.") from exc


class Desktop(CodingApi):
    """Reuse MineOS paths, diff review, reads, URL opening and Trash."""

    __slots__ = ("last_app", "settings", "allow_launch")

    def __init__(self, home, settings, approve, *, allow_launch=True):
        super().__init__(home=home, memory=None, approver=approve)
        self.last_app = ""
        self.settings = settings
        self.allow_launch = allow_launch

    def spawn_app(self, argv):
        if self.allow_launch:
            self.spawn(argv)

    def app(self, name):
        wanted = re.sub(r"[^a-z0-9]+", "", name.casefold())
        aliases = {"vscode": ("mineoside", "visualstudiocode", "vscodium", "codium", "codeoss", "code"),
                   "code": ("mineoside", "visualstudiocode", "vscodium", "codium", "codeoss"),
                   "browser": ("firefox", "firefoxesr", "chromium"),
                   "files": ("dolphin", "thunar", "nautilus"),
                   "terminal": ("terminal", "xfce4terminal", "konsole", "gnometerminal")}
        terms = aliases.get(wanted, (wanted,))
        entries = self._desktop_entries()
        best = None
        best_score = .72
        for label, stem, argv in entries:
            keys = [re.sub(r"[^a-z0-9]+", "", part.casefold())
                    for part in (label, stem, stem.rpartition(".")[2], Path(argv[0]).stem)]
            for rank, term in enumerate(terms):
                score = max((1.05 if term == key else difflib.SequenceMatcher(
                    None, term, key).ratio()) for key in keys) - rank * .012
                if score > best_score:
                    best, best_score = (label, stem, argv), score
        if not best:
            raise ApiError(f"I couldn't find an installed app named {name}.")
        label, stem, argv = best
        self.spawn_app(argv)
        # These are matched against the window class, not the title of an arbitrary window.
        self.last_app = " ".join((stem, argv[0], label))
        return f"Opening {label}."

    def close(self):
        if not self.last_app:
            raise ApiError("I don't have a recently opened app to close.")
        words = set(re.findall(r"[a-z0-9-]{4,}", self.last_app.casefold()))
        if words & {"code", "mineos-ide", "codium", "vscodium", "code-oss"}:
            words.update(("code", "codium", "vscodium", "mineos-ide", "code-oss"))
        matches = []
        for line in accomplish(["wmctrl", "-lx"], 1).decode(errors="replace").splitlines():
            fields = line.split(maxsplit=4)
            if len(fields) >= 3 and re.fullmatch(r"0x[\da-fA-F]+", fields[0]):
                classes = set(fields[2].casefold().split("."))
                if words & classes:
                    matches.append(fields[0])
        if not matches:
            raise ApiError("I couldn't find that app's window in the X11 session.")
        target = matches[0]
        if len(matches) > 1:
            active = accomplish(["xdotool", "getactivewindow"], .3).decode().strip()
            target = next((xid for xid in matches if active.isdecimal() and int(xid, 16) == int(active)), None)
            if not target:
                raise ApiError("Focus the window you want to close and try again.")
        accomplish(["wmctrl", "-ic", target], 1)
        self.last_app = ""
        return "I asked the app to close. It can still prompt to save."

    def file_name(self, path):
        # Bare filenames are placed in Documents. Explicit relative folders are home-relative.
        p = Path(path)
        if not p.is_absolute() and len(p.parts) == 1 and not path.startswith("~"):
            folder = self.home / "Documents"
            return str(folder / p)
        return path

    def create(self, path, text=""):
        target = self._path(self.file_name(path), must_exist=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._commit(target, text)
        return f"Created {target.name} in {target.parent.name}."

    def open_file(self, path):
        target = self._path(self.file_name(path))
        self.spawn_app(["xdg-open", str(target)])
        return f"Opening {target.name}."

    def read(self, path):
        target = self._path(self.file_name(path))
        if not stat.S_ISREG(target.stat().st_mode) or target.stat().st_size > 2_000_000:
            raise ApiError("Choose a text file smaller than 2 MB.")
        return super().read_file(str(target), line_count=60)

    def write(self, path, text):
        target = self._path(self.file_name(path))
        if not target.is_file() or target.stat().st_size > 2_000_000:
            raise ApiError("Choose a text file smaller than 2 MB.")
        original = self._source(target)
        if original == text:
            return f"{target.name} already has that content."
        changes = "".join(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
                                              f"a/{target.name}", f"b/{target.name}"))
        self._approve(f"Overwrite {target.name}", changes[:12000])
        if self._path(self.file_name(path)) != target or self._source(target) != original:
            raise ApiError("The file changed during review. Try again.")
        self._commit(target, text, mode=stat.S_IMODE(target.stat().st_mode))
        return f"Wrote {target.name}."

    def edit(self, path, old, new):
        return super().replace_text(self.file_name(path), old, new)

    def remove(self, path):
        return self.delete_file(self.file_name(path))

    def move(self, path, destination):
        source = self._path(self.file_name(path))
        target = self._path(self.file_name(destination), must_exist=False)
        if not source.is_file() or target.exists():
            raise ApiError("Choose one file and a destination that doesn't exist.")
        if not target.parent.is_dir():
            raise ApiError("Create the destination folder first.")
        # link is exclusive, so an intervening destination can never be overwritten.
        os.link(source, target)
        try:
            source.unlink()
        except OSError:
            target.unlink()
            raise
        return f"Moved {source.name} to {target.name}."

    def search(self, query, folder="~", content=False):
        directory = self._path(folder)
        if not directory.is_dir():
            raise ApiError("Choose a folder to search.")
        excludes = ["node_modules", ".git", ".venv", "*.key", "*.pem", ".env*"]
        if content:
            argv = ["rg", "--files-with-matches", "--fixed-strings", "--max-filesize", "2M"]
            argv += [arg for pattern in excludes for arg in ("-g", "!" + pattern)]
            argv += ["--", query, "."]
        else:
            fd = shutil.which("fd") or shutil.which("fdfind")
            if not fd:
                return "\n".join(self.find_files(query, folder)[:20]) or "No matching files."
            argv = [fd, "--fixed-strings", "--max-results", "20"]
            argv += [arg for pattern in excludes for arg in ("--exclude", pattern)]
            argv += ["--", query, "."]
        result = subprocess.run(argv, cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=3, text=True)
        if result.returncode not in (0, 1):
            raise ApiError("Search did not finish. Try a smaller folder.")
        return "\n".join(result.stdout.splitlines()[:20]) or "No matching files."

    def url(self, url):
        parsed = urlsplit(url)
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username:
            raise ApiError("Use an HTTP or HTTPS website.")
        self.spawn_app(["xdg-open", url])
        return f"Opening {parsed.hostname}."

    def web(self, query):
        self.url("https://www.google.com/search?q=" + quote_plus(query))
        return "Opening browser search results."

    def media(self, query):
        # Use the channel's uploads feed, which is already newest first.
        known = re.search(r"sourav\s+joshi", query, re.IGNORECASE) or "सौरव जोशी" in query
        mode = SOURAV_CHANNEL + "/videos" if known else f"ytsearch5:{query}"
        try:
            data = json.loads(accomplish(
                ["yt-dlp", "--ignore-config", "--flat-playlist", "--playlist-end", "5",
                 "--dump-single-json", "--skip-download", "--socket-timeout", "5", "--", mode], 12))
            entries = data.get("entries", []) if isinstance(data, dict) else []
            match = next((item for item in entries if isinstance(item, dict) and
                          re.fullmatch(r"[A-Za-z0-9_-]{11}", str(item.get("id", ""))) and
                          item.get("live_status") != "is_upcoming"), None)
        except (ApiError, ValueError, TypeError):
            match = None
        if match:
            self.url("https://www.youtube.com/watch?v=" + match["id"])
            return f"Opening {match.get('title') or 'the latest video'}."
        self.url(mode if known else "https://www.youtube.com/results?search_query=" + quote_plus(query))
        return "YouTube lookup is unavailable. I opened the uploads page." if known else "I opened YouTube search results."

    def terminal(self, command, folder="~/Documents"):
        argv = shlex.split(command)
        if not argv or Path(argv[0]).name in NO_ROOT or "/" in argv[0]:
            raise ApiError("Use a command name without sudo or an absolute executable path.")
        directory = self._path(folder)
        if directory == self.home or not directory.is_dir():
            raise ApiError("Choose a project folder under your home directory.")
        self._approve("Run a read-only sandbox command", f"{shlex.join(argv)}\nFolder: {directory}")
        wrapper = ["prlimit", "--fsize=262144", "--as=805306368", "--cpu=8", "--",
                   "bwrap", "--die-with-parent", "--new-session", "--unshare-all",
                   "--ro-bind", "/usr", "/usr", "--ro-bind", str(directory), "/work",
                   "--tmpfs", "/tmp", "--proc", "/proc", "--dev", "/dev",
                   "--clearenv", "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp",
                   "--chdir", "/work"]
        for path in ("/bin", "/lib", "/lib64", "/sbin"):
            if Path(path).is_symlink():
                wrapper += ["--symlink", os.readlink(path), path]
        for path in ("/etc/ld.so.cache", "/etc/alternatives"):
            if Path(path).exists():
                wrapper += ["--ro-bind", path, path]
        with tempfile.TemporaryFile() as out:
            result = subprocess.run([*wrapper, "--", *argv], stdout=out, stderr=out,
                                    stdin=subprocess.DEVNULL, timeout=10)
            out.seek(0)
            return f"Exit {result.returncode}\n" + out.read(5000).decode(errors="replace")

    def read_screen(self, region=False):
        # A locked session must never be used as context.
        lock = subprocess.run(["gdbus", "call", "--session", "--dest", "org.freedesktop.ScreenSaver",
                               "--object-path", "/ScreenSaver", "--method",
                               "org.freedesktop.ScreenSaver.GetActive"], timeout=.35, capture_output=True)
        if b"true" in lock.stdout:
            raise ApiError("Unlock the desktop before reading the screen.")
        if os.environ.get("WAYLAND_DISPLAY"):
            args = ["grim", "-"]
            if region:
                area = accomplish(["slurp"], 20).decode().strip()
                args[1:1] = ["-g", area]
            png = accomplish(args, 1)
        else:
            args = ["maim", "-u"]
            if region:
                args.append("-s")
            elif shutil.which("xdotool"):
                try:
                    xid = accomplish(["xdotool", "getactivewindow"], .25).decode().strip()
                    if xid.isdecimal():
                        args += ["-i", xid]
                except ApiError:
                    pass
            png = accomplish(args, 20 if region else .9)
        text = ocr(png)
        if not text and self.settings.local_vision:
            return vision(png)
        if not text:
            raise ApiError("I couldn't read text on the focused window. Focus the error and try again.")
        return text


def ocr(png):
    from io import BytesIO
    from PIL import Image, ImageOps
    with Image.open(BytesIO(png)) as image:
        image.thumbnail((1600, 1100))
        gray = ImageOps.grayscale(image)
        if gray.resize((1, 1)).getpixel((0, 0)) < 112:
            gray = ImageOps.invert(gray)
        image_data = BytesIO()
        gray.save(image_data, format="PPM")
    return accomplish(["env", "OMP_THREAD_LIMIT=2", "tesseract", "stdin", "stdout", "--psm", "11"],
                      1.25, data=image_data.getvalue()).decode(errors="replace").strip()[:3600]


def vision(png):
    with tempfile.TemporaryDirectory(prefix="mino-vision-") as temp:
        path = Path(temp) / "screen.png"
        path.write_bytes(png)
        return accomplish(
            ["/opt/llama.cpp/llama-mtmd-cli", "-m", str(VISION / "model.gguf"),
             "--mmproj", str(VISION / "projector.gguf"), "--image", str(path), "--no-warmup",
             "-p", "Describe the visible problem in a short sentence.", "-n", "64", "-t", "2"],
            32).decode(errors="replace")[-1500:].strip()
