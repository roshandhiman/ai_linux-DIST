"""Previewable desktop actions with fixed scope and no model-generated commands."""

from dataclasses import dataclass
from pathlib import Path
import os
import re
import stat
import subprocess
import time

from gi.repository import Gio, GLib


GROUPS = {
    "Images": ".jpg .jpeg .png .gif .svg .webp .bmp .heic .avif",
    "Documents": ".txt .md .pdf .odt .doc .docx .csv .xls .xlsx .ods .ppt .pptx",
    "Code": ".py .js .ts .tsx .jsx .html .css .c .cpp .h .rs .go .java .sh .json .yaml .yml",
    "Media": ".mp3 .wav .flac .ogg .m4a .mp4 .mov .mkv .webm",
    "Archives": ".zip .tar .gz .xz .bz2 .7z .rar",
}
FILE_GROUP = {suffix: name for name, extensions in GROUPS.items() for suffix in extensions.split()}
EDITORS = {"mousepad", "kate", "kwrite"}
MAX_OPERATIONS = 400
MAX_EDITOR_TEXT = 200_000


@dataclass(frozen=True)
class Change:
    source: Path
    version: tuple
    destination: Path | None = None

    @property
    def size(self):
        return self.version[-1]


def file_version(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        return None
    return info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size


def desktop_folder():
    directory = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP)
    folder = Path(directory) if directory else Path.home() / "Desktop"
    if folder.resolve() == Path.home().resolve():
        raise ValueError("Configure a dedicated Desktop folder before organizing it.")
    return folder


def organization_plan(folder):
    result = []
    if not folder.is_dir() or folder.is_symlink():
        return result
    for source in sorted(folder.iterdir(), key=lambda path: path.name.casefold()):
        if source.name.startswith(".") or source.suffix.lower() not in FILE_GROUP:
            continue
        group = folder / FILE_GROUP[source.suffix.lower()]
        target = group / source.name
        if group.is_symlink() or (group.exists() and not group.is_dir()) or os.path.lexists(target):
            continue
        version = file_version(source)
        if version:
            result.append(Change(source, version, target))
        if len(result) == MAX_OPERATIONS:
            break
    return result


def cache_plan(cache):
    result = []
    cutoff = time.time_ns() - 7 * 24 * 60 * 60 * 1_000_000_000
    thumbnails = cache / "thumbnails"
    # Only generated thumbnail files. Other app caches, browser data and models
    # have different retention rules and are outside this action.
    if cache.is_symlink() or thumbnails.is_symlink():
        return result
    for size in ("normal", "large", "x-large", "xx-large"):
        folder = thumbnails / size
        if not folder.is_dir() or folder.is_symlink():
            continue
        for source in sorted(folder.iterdir()):
            if not re.fullmatch(r"[0-9a-f]{32}\.png", source.name):
                continue
            version = file_version(source)
            if version and version[2] < cutoff:
                result.append(Change(source, version))
            if len(result) == MAX_OPERATIONS:
                return result
    return result


def apply_plan(changes):
    done = 0
    skipped = []
    for change in changes:
        try:
            source = change.source
            if source.parent.is_symlink() or source.parent.parent.is_symlink() or file_version(source) != change.version:
                raise ValueError("file changed since review")
            if change.destination:
                destination = change.destination
                if destination.parent.is_symlink():
                    raise ValueError("the destination folder changed")
                destination.parent.mkdir(exist_ok=True)
                Gio.File.new_for_path(str(source)).move(
                    Gio.File.new_for_path(str(destination)), Gio.FileCopyFlags.NOFOLLOW_SYMLINKS, None, None,
                )
            else:
                source.unlink()
            done += 1
        except (OSError, ValueError, GLib.Error) as error:
            skipped.append(f"{change.source.name}: {error}")
    return done, skipped


def editor_pid(target):
    if target is None:
        return None
    try:
        pid = int(subprocess.check_output(["xdotool", "getwindowpid", str(target.xid)],
                                          text=True, stderr=subprocess.DEVNULL, timeout=1))
        binary = Path(os.readlink(f"/proc/{pid}/exe")).name
        return pid if binary in EDITORS else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def focused_editor(atspi, pid):
    desktop = atspi.get_desktop(0)
    for index in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(index)
        if app is None or app.get_process_id() != pid:
            continue
        queue = [app]
        for _ in range(350):
            if not queue:
                break
            node = queue.pop()
            state = node.get_state_set()
            if (
                node.get_role() in (atspi.Role.TEXT, atspi.Role.DOCUMENT_TEXT)
                and state.contains(atspi.StateType.FOCUSED)
                and state.contains(atspi.StateType.EDITABLE)
                and node.get_text_iface() and node.get_editable_text_iface()
            ):
                return node
            for child in reversed(range(min(node.get_child_count(), 80))):
                item = node.get_child_at_index(child)
                if item is not None:
                    queue.append(item)
    return None


def update_editor(target, replacement, selected=None):
    import gi

    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi

    pid = editor_pid(target)
    if pid is None:
        raise ValueError("The original editor is unavailable. Use Copy text to paste it yourself.")
    subprocess.run(["xdotool", "windowactivate", "--sync", str(target.xid)], check=True, timeout=3,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    Atspi.init()
    Atspi.set_timeout(800, 800)
    editor = focused_editor(Atspi, pid)
    if editor is None:
        raise ValueError("Focus the document in Mousepad, Kate, or KWrite first, then try again.")
    text = editor.get_text_iface()
    length = Atspi.Text.get_character_count(text)
    if length > MAX_EDITOR_TEXT:
        raise ValueError("This document is too large for direct editing. Use Copy text.")
    if selected is not None:
        if Atspi.Text.get_n_selections(text) != 1:
            raise ValueError("Select the same text in the original editor first.")
        selection = Atspi.Text.get_selection(text, 0)
        start, end = selection.start_offset, selection.end_offset
        if Atspi.Text.get_text(text, start, end) != selected:
            raise ValueError("The selection changed since review. Capture it again.")
    else:
        start = end = Atspi.Text.get_caret_offset(text)
    if start < 0 or end < start or end > length:
        raise ValueError("The editor did not report a valid cursor position.")
    active = subprocess.check_output(["xdotool", "getactivewindow"], text=True, timeout=1)
    if int(active) != target.xid:
        raise ValueError("The active editor changed. Open the original document before applying.")
    if selected is None:
        inserted = editor.get_editable_text_iface().insert_text(start, replacement, len(replacement.encode("utf-8")))
        if not inserted:
            raise ValueError("The editor declined the insertion. Use Copy text.")
    else:
        original = Atspi.Text.get_text(text, 0, length)
        if original[start:end] != selected:
            raise ValueError("The content changed since review. Capture it again.")
        edited = original[:start] + replacement + original[end:]
        if not editor.get_editable_text_iface().set_text_contents(edited):
            raise ValueError("The editor declined the edit. Use Copy text.")
        Atspi.Text.set_caret_offset(text, start + len(replacement))
