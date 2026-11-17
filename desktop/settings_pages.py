import ipaddress
import os
import shutil
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

import preferences
import settings_services as system

BLUEZ_ADAPTER = "org.bluez.Adapter1"
BLUEZ_DEVICE = "org.bluez.Device1"


class SystemPages:
    def register_system_pages(self):
        pages = [
            ("about", "About", "help-about-symbolic", self.about, "general"),
            ("updates", "Software Update", "software-update-available-symbolic", self.updates, "general"),
            ("storage", "Storage", "drive-harddisk-symbolic", self.storage, "general"),
            ("date_time", "Date & Time", "preferences-system-time-symbolic", self.date_time, "general"),
            ("region", "Language & Region", "preferences-desktop-locale-symbolic", self.region, "general"),
            ("startup", "Login Items", "system-run-symbolic", self.startup, "general"),
            ("default_apps", "Default Apps", "application-x-executable-symbolic", self.default_apps, "general"),
            ("color_profiles", "Color Profiles", "preferences-color-symbolic", self.color_profiles, "display"),
        ]
        for key, title, icon, build, parent in pages:
            self.pages[key] = (title, icon, "", build, parent)

    def action(self, text, callback):
        widget = Gtk.Button(label=text)
        widget.get_style_context().add_class("glass-control")
        widget.connect("clicked", callback)
        return widget

    def combo(self, options, active, change):
        control = Gtk.ComboBoxText()
        for key, title in options:
            control.append(str(key), str(title))
        control.set_active_id(str(active))
        control.change_handler = control.connect("changed", lambda widget: change(widget) if widget.get_active_id() is not None else None)
        return control

    def async_content(self, page, load, render, callback=False):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        page.pack_start(box, False, False, 0)

        def replace():
            for child in box.get_children():
                child.destroy()

        def loaded(result):
            replace()
            render(box, result, refresh)
            box.show_all()

        def failed(error):
            replace()
            group = self.group(box)
            self.row(group, str(error), self.action("Retry", refresh))
            box.show_all()

        def refresh(*_):
            replace()
            pending = Gtk.Spinner()
            self.row(self.group(box), "Loading…", pending)
            pending.start()
            box.show_all()
            if callback:
                load(loaded, failed)
            else:
                self.task(load, loaded, failed)

        refresh()
        return box

    def embed(self, page, executable):
        if not shutil.which(executable):
            self.note(self.group(page), "This system component is unavailable.")
            return
        socket = Gtk.Socket(height_request=385)
        page.pack_start(socket, True, True, 0)

        def embed_ready(widget):
            if widget in self.embeds:
                return
            try:
                self.embeds[widget] = subprocess.Popen(
                    [executable, "--socket-id", str(widget.get_id())],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except OSError as error:
                self.report(error)
                return

            def check():
                process = self.embeds.get(widget)
                if process and not widget.get_plug_window():
                    group = self.group(page)
                    self.note(group, "This panel did not load. Reopen Settings to try again.")
                    group.show_all()
                    if process.poll() is None:
                        process.terminate()
                    widget.hide()
                return GLib.SOURCE_REMOVE

            GLib.timeout_add_seconds(6, check)

        def plug_added(*_):
            plug = socket.get_plug_window()
            if plug:
                try:
                    height = plug.get_height()
                    if height > 385:
                        socket.set_size_request(-1, height)
                except TypeError:
                    pass

        socket.connect("realize", embed_ready)
        socket.connect("plug-added", plug_added)
        socket.connect("plug-removed", lambda *_: True)

    def close_panels(self, *_):
        for process in self.embeds.values():
            if process.poll() is None:
                process.terminate()
        self.embeds.clear()

    def general(self, page):
        information = self.group(page)
        self.route(information, "About", "about")
        self.route(information, "Software Update", "updates")
        self.route(information, "Storage", "storage")
        preferences_group = self.group(page)
        self.route(preferences_group, "Date & Time", "date_time")
        self.route(preferences_group, "Language & Region", "region")
        self.route(preferences_group, "Login Items", "startup")
        self.route(preferences_group, "Default Apps", "default_apps")

    def about(self, page):
        group = self.group(page)
        for title, display in system.machine_info():
            self.row(group, title, self.value(display))

    def updates(self, page):
        group = self.group(page)
        if not shutil.which("pkcon"):
            self.note(group, "Software Update requires the PackageKit service.")
            return
        output = Gtk.Label(xalign=0, selectable=True, wrap=True)
        output.set_max_width_chars(70)

        def check(widget):
            widget.set_sensitive(False)
            output.set_text("Checking for updates…")

            def load():
                system.command("pkcon", "--plain", "refresh", timeout=180)
                return system.command("pkcon", "--plain", "get-updates", timeout=120, allowed=(0, 5))

            def show(result):
                details = result.partition("Results:")[2].strip()
                packages = [line.strip() for line in details.splitlines() if ";" in line]
                output.set_text("\n".join(packages) if packages else (details or "Your system is up to date."))
                widget.set_sensitive(True)
                install.set_sensitive(bool(packages))

            def fail(error):
                output.set_text(str(error))
                widget.set_sensitive(True)

            install.set_sensitive(False)
            self.task(load, show, fail)

        def apply(widget):
            widget.set_sensitive(False)
            output.set_text("Installing available updates…")

            def installed(_):
                check(check_button)

            def fail(error):
                output.set_text(str(error))
                widget.set_sensitive(True)

            self.task(lambda: system.command("pkcon", "--plain", "--noninteractive", "update", timeout=1800),
                      installed, fail)

        check_button = self.action("Check Now", check)
        install = self.action("Install Updates", apply)
        install.get_style_context().add_class("suggested-action")
        install.set_sensitive(False)
        controls = Gtk.Box(spacing=7)
        controls.add(check_button)
        controls.add(install)
        self.row(group, "System updates", controls)
        self.row(group, "Status", output, "Check to see available updates.")

    def storage(self, page):
        for path, disk in system.mounts():
            group = self.group(page)
            bar = Gtk.LevelBar(min_value=0, max_value=1, value=disk.used / disk.total)
            bar.set_size_request(190, -1)
            self.row(group, "System volume" if path == "/" else "Home volume", bar,
                     f"{disk.used / 2**30:.1f} GiB used of {disk.total / 2**30:.1f} GiB")
            metrics = Gtk.Box(spacing=8, homogeneous=True)
            metrics.get_style_context().add_class("metric-line")
            for label, amount in (("Used", disk.used), ("Available", disk.free), ("Capacity", disk.total)):
                metrics.pack_start(self.metric(label, f"{amount / 2**30:.1f} GiB"), True, True, 0)
            group.pack_start(metrics, False, False, 0)

    def date_time(self, page):
        def load():
            fields = system.command("timedatectl", "show", "--property=Timezone", "--property=NTP")
            current = dict(line.split("=", 1) for line in fields.splitlines() if "=" in line)
            return current, system.command("timedatectl", "list-timezones").splitlines()

        def render(box, result, refresh):
            current, zones = result
            group = self.group(box)
            zone = Gtk.Entry(text=current.get("Timezone", ""), width_chars=23)
            store = Gtk.ListStore(str)
            for item in zones:
                store.append([item])
            completion = Gtk.EntryCompletion(model=store, text_column=0)
            zone.set_completion(completion)

            def apply(widget):
                name = zone.get_text().strip()
                if name not in zones:
                    self.report("Choose a time zone from the list.")
                    return
                self.bind(widget, lambda: system.command("timedatectl", "set-timezone", name),
                          lambda: zone.set_text(current.get("Timezone", "")))

            control = Gtk.Box(spacing=7)
            control.add(zone)
            control.add(self.action("Apply", apply))
            self.row(group, "Time zone", control)
            self.toggle(group, "Set time automatically", current.get("NTP") == "yes",
                        lambda active: system.command("timedatectl", "set-ntp", str(active).lower()))

        self.async_content(page, load, render)

    def region(self, page):
        def render(box, locales, refresh):
            group = self.group(box)
            active = os.environ.get("LANG", "C.UTF-8")
            if active not in locales:
                locales.insert(0, active)
            control = self.combo([(locale, locale) for locale in locales], active, lambda _: None)

            def apply(widget):
                selected = control.get_active_id()
                self.bind(widget, lambda: system.command("localectl", "set-locale", f"LANG={selected}"), lambda: None)

            fields = Gtk.Box(spacing=7)
            fields.add(control)
            fields.add(self.action("Apply", apply))
            self.row(group, "System locale", fields, "Applies to new sessions.")

        self.async_content(page, lambda: system.command("localectl", "list-locales").splitlines(), render)

    def startup(self, page):
        config = preferences.CONFIG / "autostart"

        def render(box, items, refresh):
            group = self.group(box)
            if not items:
                self.note(group, "No optional login items are installed.")
            for name, path, data, active in items:
                def save(enabled, target=path, entry=data):
                    entry.set_boolean("Desktop Entry", "Hidden", not enabled)
                    preferences.write(target, entry.to_data()[0])
                self.toggle(group, name, active, save)

        self.async_content(page, lambda: system.startup_items(config), render)

    def default_apps(self, page):
        self.embed(page, "xfce4-mime-settings")

    def color_profiles(self, page):
        self.embed(page, "xfce4-color-settings")

    def display(self, page):
        scale = self.group(page)
        self.choices(scale, "Interface scale", "ui_scale", [("1", "100%"), ("2", "200% · HiDPI")])
        self.note(scale, "Reopen applications after changing scale. Choose the display resolution below.")
        self.route(self.group(page), "Color Profiles", "color_profiles")
        self.embed(page, "xfce4-display-settings")

    def keyboard(self, page):
        self.embed(page, "xfce4-keyboard-settings")

    def mouse(self, page):
        self.embed(page, "xfce4-mouse-settings")

    def power(self, page):
        channel = "xfce4-power-manager"
        prefix = "/xfce4-power-manager/"
        group = self.group(page)

        def get(key, default):
            result = subprocess.run(["xfconf-query", "-c", channel, "-p", prefix + key],
                                    capture_output=True, text=True, timeout=4)
            return result.stdout.strip() if result.returncode == 0 else default

        self.toggle(group, "Display power management", get("dpms-enabled", "true") == "true",
                    lambda enabled: preferences.xfce(channel, prefix + "dpms-enabled", "bool", str(enabled).lower()))
        battery_available = any(
            path.read_text().strip() == "Battery" for path in Path("/sys/class/power_supply").glob("*/type")
        )
        sources = [("ac", "Plugged in", 15, 14)]
        if battery_available:
            sources.append(("battery", "On battery", 5, 14))
        for suffix, title, display_default, sleep_default in sources:
            settings = self.group(page)
            settings.add(Gtk.Label(label=title, xalign=0, margin=12))
            self.power_timer(settings, "Turn display off after", f"dpms-on-{suffix}-off",
                             get(f"dpms-on-{suffix}-off", str(display_default)), 0)
            self.power_timer(settings, "Put computer to sleep after", f"inactivity-on-{suffix}",
                             get(f"inactivity-on-{suffix}", str(sleep_default)), 14)

    def power_timer(self, group, title, key, current, never):
        choices = [never, 15, 20, 30, 45, 60, 120]
        if never == 0:
            choices[1:1] = [1, 5, 10]
        if int(current) not in choices:
            choices.append(int(current))
        options = [(minutes, "Never" if minutes == never else f"{minutes} minutes") for minutes in choices]
        def changed(widget):
            value = widget.get_active_id()
            self.bind(widget, lambda: preferences.xfce("xfce4-power-manager", "/xfce4-power-manager/" + key, "uint", value),
                      lambda: self.restore_combo(widget, current))
        self.row(group, title, self.combo(options, current, changed))

    def notifications(self, page):
        self.embed(page, "xfce4-notifyd-config")

    def accessibility(self, page):
        self.embed(page, "xfce4-accessibility-settings")

    def menu_bar(self, page):
        group = self.group(page)
        self.slider(group, "Opacity", "panel_opacity", 0, 100)
        self.switch(group, "24-hour clock", "clock_24h")
        self.switch(group, "Show seconds", "clock_seconds")

    def toggle(self, group, label, active, change):
        control = Gtk.Switch(active=bool(active))
        state = {"active": bool(active)}

        def changed(widget, _):
            next_value = widget.get_active()
            if next_value == state["active"]:
                return
            widget.set_sensitive(False)

            def success(_):
                state["active"] = next_value
                widget.set_sensitive(True)

            def failure(error):
                widget.set_active(state["active"])
                widget.set_sensitive(True)
                self.report(error)

            self.task(lambda: change(next_value), success, failure)

        control.connect("notify::active", changed)
        self.row(group, label, control)

    def sound(self, page):
        def render(box, audio, refresh):
            for kind, title, (devices, default) in audio:
                group = self.group(box)
                if not devices:
                    self.note(group, f"No {title.lower()} devices found.")
                    continue
                device = next((device for device in devices if device["name"] == default), devices[0])
                def set_default(widget, direction=kind, previous=default):
                    selected = widget.get_active_id()
                    widget.set_sensitive(False)
                    def failed(error):
                        self.restore_combo(widget, previous)
                        widget.set_sensitive(True)
                        self.report(error)
                    self.task(lambda: system.command("pactl", f"set-default-{direction}", selected),
                              lambda _: refresh(), failed)
                options = [(item["name"], item["description"]) for item in devices]
                self.row(group, f"{title} device", self.combo(options, default, set_default))
                self.toggle(group, f"Mute {title.lower()}", device["mute"],
                            lambda muted, direction=kind, name=device["name"]: system.command(
                                "pactl", f"set-{direction}-mute", name, str(int(muted))))
                self.audio_level(group, kind, device)

        self.async_content(page, lambda: [("sink", "Output", system.audio_devices("sink")),
                                          ("source", "Input", system.audio_devices("source"))], render)

    def restore_combo(self, widget, value):
        handler_id = getattr(widget, "change_handler", None)
        if handler_id:
            widget.handler_block(handler_id)
        widget.set_active_id(value)
        if handler_id:
            widget.handler_unblock(handler_id)

    def audio_level(self, group, kind, device):
        control = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        control.set_size_request(165, -1)
        control.set_value(min(system.volume(device), 100))
        control.set_value_pos(Gtk.PositionType.RIGHT)
        control.connect("format-value", lambda _, value: f"{value:.0f}%")
        pending = 0
        prior = control.get_value()

        def change(widget):
            nonlocal pending, prior
            value = round(widget.get_value())
            if pending:
                GLib.source_remove(pending)
            if value == prior:
                pending = 0
                return

            def commit():
                nonlocal pending, prior
                pending = 0
                def saved(_):
                    nonlocal prior
                    prior = value
                self.task(lambda: system.command("pactl", f"set-{kind}-volume", device["name"], f"{value}%"), saved)
                return GLib.SOURCE_REMOVE

            pending = GLib.timeout_add(180, commit)

        control.connect("value-changed", change)
        self.row(group, "Volume" if kind == "sink" else "Input level", control)

    def network(self, page):
        def load():
            return [(device, kind, state, name, system.ethernet_details(device) if kind == "ethernet" else "")
                    for device, kind, state, name in system.network_devices()]

        def render(box, devices, refresh):
            for device, kind, state, name, details in devices:
                group = self.group(box)
                self.row(group, name or device, self.value(state.title()), f"{kind.title()} · {device}")
                for key, title in (("IP4.ADDRESS", "IPv4 address"), ("IP4.GATEWAY", "Router"),
                                   ("IP4.DNS", "DNS"), ("IP6.ADDRESS", "IPv6 address")):
                    matches = [line.split(":", 1)[1].strip() for line in details.splitlines() if line.startswith(key)]
                    if matches:
                        self.row(group, title, self.value(", ".join(matches).replace("\\:", ":")))
                uuid = next((line.partition(":")[2] for line in details.splitlines()
                             if line.startswith("GENERAL.CON-UUID:")), "")
                if kind == "ethernet" and uuid and uuid != "--":
                    self.row(group, "IPv4 & DNS", self.action("Configure…", lambda _, profile=uuid:
                                                              self.ethernet_editor(profile)))
            if not devices:
                self.note(self.group(box), "No network interfaces found.")
            box.pack_start(self.action("Refresh", refresh), False, False, 0)

        self.async_content(page, load, render)

    def ethernet_editor(self, uuid):
        def load():
            fields = ["ipv4.method", "ipv4.addresses", "ipv4.gateway", "ipv4.dns"]
            return [system.command("nmcli", "-g", field, "connection", "show", "uuid", uuid) for field in fields]

        def loaded(values):
            dialog = Gtk.Dialog(title="IPv4 & DNS", transient_for=self, modal=True)
            dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Save", Gtk.ResponseType.OK)
            content = dialog.get_content_area()
            content.set_border_width(16)
            group = self.group(content)
            method = self.combo([("auto", "Automatic (DHCP)"), ("manual", "Manual")], values[0], lambda _: None)
            self.row(group, "IPv4 configuration", method)
            fields = [Gtk.Entry(text=value, width_chars=23) for value in values[1:]]
            for title, field in zip(("Address / prefix", "Gateway", "DNS servers"), fields):
                self.row(group, title, field)
            dialog.show_all()
            response = dialog.run()
            selected = method.get_active_id()
            address, gateway, dns = [entry.get_text().strip() for entry in fields]
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return
            if selected not in ("auto", "manual"):
                self.report("Choose an IPv4 configuration.")
                return
            try:
                if selected == "manual":
                    if "/" not in address:
                        raise ValueError("Enter the address with a prefix, for example 192.168.1.5/24.")
                    ipaddress.IPv4Interface(address)
                    if gateway:
                        ipaddress.IPv4Address(gateway)
                dns = ",".join(str(ipaddress.IPv4Address(item.strip())) for item in dns.split(",") if item.strip())
            except ValueError as error:
                self.report(error)
                return
            def saved(_):
                message = Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.CLOSE,
                                            text="Network settings saved", secondary_text="They apply when the connection next activates.")
                message.connect("response", lambda widget, __: widget.destroy())
                message.show()
            self.task(lambda: system.command(
                "nmcli", "connection", "modify", "uuid", uuid, "ipv4.method", selected,
                "ipv4.addresses", address if selected == "manual" else "",
                "ipv4.gateway", gateway if selected == "manual" else "",
                "ipv4.dns", dns, "ipv4.ignore-auto-dns", "yes" if dns else "no",
            ), saved)

        self.task(load, loaded)

    def wifi(self, page):
        def render(box, result, refresh):
            nm, client, devices = result
            group = self.group(box)
            if not devices:
                self.note(group, "No Wi-Fi adapter found.")
                return
            radio = client.wireless_get_enabled()

            def set_radio(widget, _):
                enabled = widget.get_active()
                widget.set_sensitive(False)

                def finished(_):
                    refresh()

                def failed(error):
                    self.report(error)
                    refresh()

                self.task(lambda: system.command("nmcli", "radio", "wifi", "on" if enabled else "off"), finished, failed)

            control = Gtk.Switch(active=radio)
            control.connect("notify::active", set_radio)
            self.row(group, "Wi-Fi", control)
            if not radio:
                return
            seen = set()
            for device in devices:
                active = device.get_active_access_point()
                points = sorted(device.get_access_points(), key=lambda point: point.get_strength(), reverse=True)
                for point in points:
                    name = point.get_ssid()
                    if not name or name.get_data() in seen:
                        continue
                    seen.add(name.get_data())
                    label = name.get_data().decode(errors="replace")
                    if active and active.get_ssid() and active.get_ssid().equal(name):
                        self.row(group, label, self.value("Connected"), f"Signal {point.get_strength()}%")
                    else:
                        action = self.action("Join…", lambda _, ap=point, adapter=device, ssid=label:
                                             self.join_wifi(nm, client, adapter, ap, ssid, refresh))
                        self.row(group, label, action, f"Signal {point.get_strength()}%")
            def scan(widget):
                widget.set_sensitive(False)
                self.task(lambda: system.command("nmcli", "--wait", "8", "device", "wifi", "rescan"),
                          lambda _: GLib.timeout_add(1300, lambda: (refresh(), GLib.SOURCE_REMOVE)[1]),
                          lambda error: (self.report(error), refresh()))
            self.row(group, "Available networks", self.action("Scan", scan))

        self.async_content(page, system.wifi_client, render, callback=True)

    def join_wifi(self, nm, client, device, point, name, refresh):
        compatible = point.filter_connections(client.get_connections())
        connection = compatible[0] if compatible else None
        new = connection is None
        if new and (point.get_flags() & nm.APFlags.PRIVACY):
            flags = point.get_rsn_flags() | point.get_wpa_flags()
            if not flags & (nm.APFlagsSec.KEY_MGMT_PSK | nm.APFlagsSec.KEY_MGMT_SAE):
                self.report("Joining a new enterprise or WEP network is unavailable.")
                return
            dialog = Gtk.Dialog(title=f"Join {name}", transient_for=self, modal=True)
            dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Join", Gtk.ResponseType.OK)
            password = Gtk.Entry(visibility=False, placeholder_text="Wi-Fi password", margin=16, activates_default=True)
            dialog.get_content_area().add(password)
            dialog.set_default_response(Gtk.ResponseType.OK)
            dialog.show_all()
            response = dialog.run()
            secret = password.get_text()
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return
            if not secret:
                self.report("Enter the Wi-Fi password to join this network.")
                return
            connection = nm.SimpleConnection.new()
            wireless = nm.SettingWireless.new()
            wireless.set_property("ssid", point.get_ssid())
            security = nm.SettingWirelessSecurity.new()
            method = "wpa-psk" if flags & nm.APFlagsSec.KEY_MGMT_PSK else "sae"
            security.set_property("key-mgmt", method)
            security.set_property("psk", secret)
            connection.add_setting(wireless)
            connection.add_setting(security)

        def complete(source, result, *_):
            try:
                if new:
                    source.add_and_activate_connection_finish(result)
                else:
                    source.activate_connection_finish(result)
            except GLib.Error as error:
                self.report(error)
            GLib.timeout_add_seconds(2, lambda: (refresh(), GLib.SOURCE_REMOVE)[1])

        activate = client.add_and_activate_connection_async if new else client.activate_connection_async
        activate(connection, device, point.get_path(), None, complete, None)

    def bluetooth(self, page):
        def load():
            try:
                return system.bluez_objects()
            except GLib.Error as error:
                names = ("ServiceUnknown", "NameHasNoOwner", "Spawn.ChildExited")
                if any(name in str(error) for name in names):
                    return {}
                raise

        def render(box, objects, refresh):
            adapters = [(path, data[BLUEZ_ADAPTER]) for path, data in objects.items() if BLUEZ_ADAPTER in data]
            group = self.group(box)
            if not adapters:
                self.note(group, "No Bluetooth adapter found.")
                return
            path, adapter = adapters[0]

            def power(widget, _):
                active = widget.get_active()
                widget.set_sensitive(False)
                args = GLib.Variant("(ssv)", (BLUEZ_ADAPTER, "Powered", GLib.Variant("b", active)))
                def failed(error):
                    self.report(error)
                    refresh()
                self.task(lambda: system.bluez_call(path, "org.freedesktop.DBus.Properties", "Set", args),
                          lambda _: refresh(), failed)

            radio = Gtk.Switch(active=adapter["Powered"])
            radio.connect("notify::active", power)
            self.row(group, "Bluetooth", radio)
            if not adapter["Powered"]:
                return

            def scan(widget):
                widget.set_sensitive(False)
                def started(_):
                    def stop():
                        self.task(lambda: system.bluez_call(path, BLUEZ_ADAPTER, "StopDiscovery"), lambda _: refresh())
                        return GLib.SOURCE_REMOVE
                    GLib.timeout_add_seconds(5, stop)
                self.bind_scan(widget, lambda: system.bluez_call(path, BLUEZ_ADAPTER, "StartDiscovery"), started)

            self.row(group, "Nearby devices", self.action("Scan", scan))
            for device_path, interfaces in objects.items():
                if BLUEZ_DEVICE not in interfaces or not device_path.startswith(path + "/"):
                    continue
                device = interfaces[BLUEZ_DEVICE]
                paired = device.get("Paired", False)
                connected = device.get("Connected", False)
                title = device.get("Alias", device.get("Address", "Bluetooth device"))
                method = "Disconnect" if connected else "Connect" if paired else "Pair"

                def operate(widget, target=device_path, action=method):
                    widget.set_sensitive(False)
                    self.bind_scan(widget, lambda: system.bluez_call(target, BLUEZ_DEVICE, action),
                                   lambda _: refresh())

                self.row(group, title, self.action(method, operate),
                         "Connected" if connected else "Paired" if paired else None)

        self.async_content(page, load, render)

    def bind_scan(self, widget, action, done):
        def fail(error):
            widget.set_sensitive(True)
            self.report(error)
        self.task(action, done, fail)
