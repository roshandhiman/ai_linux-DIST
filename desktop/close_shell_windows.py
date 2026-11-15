import os
import time
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
gi.require_version("Wnck", "3.0")
from gi.repository import Gdk, GdkX11, GLib, Wnck

SHELL_WINDOWS = {"mineos-settings", "mineos-applications"}


def belongs_to_user(window):
    pid = window.get_pid()
    if pid <= 0:
        return False
    try:
        return (Path("/proc") / str(pid)).stat().st_uid == os.getuid()
    except OSError:
        return False


def close_windows(classes=SHELL_WINDOWS):
    if not Gdk.init_check([])[0]:
        return True
    display = Gdk.Display.get_default()
    if not isinstance(display, GdkX11.X11Display):
        return True
    screen = Wnck.Screen.get_default()
    if screen is None:
        return True
    screen.force_update()
    windows = [window for window in screen.get_windows()
               if window.get_class_instance_name() in classes and belongs_to_user(window)]
    if not windows:
        return True
    pending = {window.get_xid() for window in windows}
    timestamp = GdkX11.x11_get_server_time(display.get_default_screen().get_root_window())
    for window in windows:
        window.close(timestamp)

    context = GLib.MainContext.default()
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        screen.force_update()
        if pending.isdisjoint(window.get_xid() for window in screen.get_windows()):
            return True
        time.sleep(.025)
    return False


if __name__ == "__main__":
    raise SystemExit(0 if close_windows() else 1)
