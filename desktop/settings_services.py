import json
import os
import re
import shutil
from functools import lru_cache
import subprocess
from pathlib import Path

from gi.repository import Gio, GLib


def command(*args, timeout=15, allowed=(0,)):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env={**os.environ, "LC_ALL": "C.UTF-8"})
    if result.returncode not in allowed:
        detail = result.stderr.strip() or result.stdout.strip() or "The service returned an error."
        raise RuntimeError(detail.splitlines()[-1])
    return result.stdout.strip()


def audio_devices(kind):
    devices = json.loads(command("pactl", "-f", "json", "list", f"{kind}s"))
    if kind == "source":
        devices = [device for device in devices if not device["name"].endswith(".monitor")]
    default = command("pactl", f"get-default-{kind}") if devices else ""
    return devices, default


def volume(device):
    channels = [int(item["value_percent"].strip("%")) for item in device["volume"].values()]
    return round(sum(channels) / len(channels)) if channels else 0


def machine_info():
    release = {key: value.strip('"') for line in Path("/etc/os-release").read_text().splitlines()
               if "=" in line for key, value in [line.split("=", 1)]}
    memory = next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemTotal:"))
    return [
        ("Operating system", release.get("PRETTY_NAME", "MineOS")),
        ("Base system", f"Debian {release.get('VERSION_ID', '13')}"),
        ("Computer name", os.uname().nodename),
        ("Processor architecture", os.uname().machine),
        ("Memory", f"{int(memory) / 1048576:.1f} GiB"),
        ("Kernel", os.uname().release),
    ]


def mounts():
    paths = [Path("/"), Path.home()]
    result = []
    seen = set()
    for path in paths:
        disk = path.stat().st_dev
        if disk not in seen:
            seen.add(disk)
            result.append((str(path), shutil.disk_usage(path)))
    return result


def network_devices():
    def unescape(value):
        return re.sub(r"\\(.)", r"\1", value)

    lines = command("nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device").splitlines()
    return [tuple(unescape(item) for item in re.split(r"(?<!\\):", line, maxsplit=3))
            for line in lines if line and ":loopback:" not in line]


def ethernet_details(interface):
    return command("nmcli", "-t", "-f", "GENERAL,IP4,IP6", "device", "show", interface)


def wifi_client(loaded, failed):
    import gi
    try:
        gi.require_version("NM", "1.0")
        from gi.repository import NM
    except (ValueError, ImportError):
        failed("NetworkManager support is unavailable.")
        return

    def ready(_, result, *__):
        try:
            client = NM.Client.new_finish(result)
            devices = [device for device in client.get_devices() if device.get_device_type() == NM.DeviceType.WIFI]
            loaded((NM, client, devices))
        except GLib.Error as error:
            failed(error)

    NM.Client.new_async(None, ready, None)


@lru_cache(maxsize=1)
def system_bus():
    return Gio.bus_get_sync(Gio.BusType.SYSTEM, None)


def bluez_objects():
    bus = system_bus()
    answer = bus.call_sync("org.bluez", "/", "org.freedesktop.DBus.ObjectManager", "GetManagedObjects",
                           None, GLib.VariantType.new("(a{oa{sa{sv}}})"), Gio.DBusCallFlags.NONE, 4000, None)
    return answer.unpack()[0]


def bluez_call(path, interface, method, args=None, timeout=25):
    bus = system_bus()
    return bus.call_sync("org.bluez", path, interface, method, args, None,
                         Gio.DBusCallFlags.NONE, timeout * 1000, None)


def key_exists(data, group, key):
    return key in data.get_keys(group)[0]


def startup_items(override_dir):
    paths = {entry.name: entry for folder in reversed([override_dir, Path("/etc/xdg/autostart")])
             for entry in folder.glob("*.desktop")}
    items = []
    for name, path in paths.items():
        if name.startswith("mineos-") or name == "picom.desktop":
            continue
        data = GLib.KeyFile()
        try:
            data.load_from_file(str(path), GLib.KeyFileFlags.KEEP_TRANSLATIONS | GLib.KeyFileFlags.KEEP_COMMENTS)
            group = "Desktop Entry"
            if key_exists(data, group, "OnlyShowIn") and "XFCE" not in data.get_string_list(group, "OnlyShowIn"):
                continue
            if key_exists(data, group, "NotShowIn") and "XFCE" in data.get_string_list(group, "NotShowIn"):
                continue
            if not key_exists(data, group, "Exec"):
                original = Path("/etc/xdg/autostart") / name
                if path == original or not original.is_file():
                    continue
                data.load_from_file(str(original), GLib.KeyFileFlags.KEEP_TRANSLATIONS | GLib.KeyFileFlags.KEEP_COMMENTS)
                active = False
            else:
                active = not (key_exists(data, group, "Hidden") and data.get_boolean(group, "Hidden"))
            title = data.get_locale_string(group, "Name", None)
            items.append((title, override_dir / name, data, active))
        except GLib.Error:
            continue
    return sorted(items, key=lambda item: item[0].casefold())
