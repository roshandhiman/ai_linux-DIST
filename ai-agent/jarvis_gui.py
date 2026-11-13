#!/usr/bin/env python3
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib, Pango
from pathlib import Path
from urllib.parse import quote_plus
import requests
import subprocess
import threading
import sys
import os
import re

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = os.environ.get("MINEOS_MODEL", "qwen2.5:1.5b")
SYSTEM_PROMPT = (
    "You are Mine AI, the helpful assistant built into MineOS, a Debian Linux desktop. "
    "Always respond only in English. Keep answers concise and useful. "
    "Do not claim to have performed system actions unless the application supplied a tool result. "
    "Do not reveal internal model names unless explicitly asked."
)
COMMON_SITES = {"youtube": "https://youtube.com", "whatsapp": "https://web.whatsapp.com", "google": "https://google.com", "github": "https://github.com", "gmail": "https://mail.google.com", "spotify": "https://open.spotify.com", "maps": "https://maps.google.com", "reddit": "https://reddit.com", "chatgpt": "https://chatgpt.com"}
COMMON_APPS = {"terminal": ["xfce4-terminal"], "files": ["thunar"], "file manager": ["thunar"], "settings": ["xfce4-settings-manager"], "text editor": ["mousepad"], "task manager": ["xfce4-taskmanager"], "calculator": ["galculator"], "browser": ["firefox-esr"], "firefox": ["firefox-esr"], "this pc": ["thunar", "computer:///"], "control center": ["xfce4-settings-manager"]}


def launch(command):
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def handle_action(text):
    low = text.strip().lower().rstrip(".!?")
    match = re.fullmatch(r"(?:please\s+)?(?:open|launch|start|show|go to)\s+(?:the\s+)?(.+)", low)
    if match:
        target = match.group(1)
        if target in COMMON_APPS:
            launch(COMMON_APPS[target])
            return f"Opened {target}."
        if target in COMMON_SITES:
            launch(["xdg-open", COMMON_SITES[target]])
            return f"Opened {target.title()} in your browser."
        folders = {"home": Path.home(), "downloads": GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD), "documents": GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS), "pictures": GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)}
        if target in folders and folders[target]:
            launch(["thunar", str(folders[target])])
            return f"Opened your {target} folder."
    search = re.match(r"(?:please\s+)?search\s+(?:for\s+)?(.+)", text.strip(), re.IGNORECASE)
    if search:
        query = search.group(1)
        youtube = re.search(r"\s+on youtube$", query, re.IGNORECASE)
        query = re.sub(r"\s+(?:on|in|using) (?:google|youtube|firefox|browser)$", "", query, flags=re.IGNORECASE).strip()
        url = "https://youtube.com/results?search_query=" if youtube else "https://google.com/search?q="
        launch(["xdg-open", url + quote_plus(query)])
        return f"Searching the web for “{query}”."
    volume_actions = {"mute": ["set-sink-mute", "@DEFAULT_SINK@", "1"], "unmute": ["set-sink-mute", "@DEFAULT_SINK@", "0"], "volume up": ["set-sink-volume", "@DEFAULT_SINK@", "+5%"], "volume down": ["set-sink-volume", "@DEFAULT_SINK@", "-5%"]}
    if low in volume_actions:
        subprocess.run(["pactl"] + volume_actions[low], check=True, capture_output=True, timeout=5)
        return {"mute": "Audio muted.", "unmute": "Audio unmuted.", "volume up": "Volume increased by 5%.", "volume down": "Volume decreased by 5%."}[low]
    return None


def ask_ollama(history):
    response = requests.post(OLLAMA_URL, json={"model": MODEL, "messages": history, "stream": False, "options": {"temperature": 0.2, "num_predict": 384}}, timeout=(4, 120))
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


class AssistantWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Assistant")
        self.set_wmclass("mine-ai", "MineAI")
        self.set_default_size(420, 510)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.busy = False
        header = Gtk.HeaderBar(title="Assistant", show_close_button=True)
        header.set_decoration_layout(":minimize,maximize,close")
        self.set_titlebar(header)
        self.spinner = Gtk.Spinner()
        header.pack_end(self.spinner)
        clear = Gtk.Button.new_from_icon_name("document-new-symbolic", Gtk.IconSize.BUTTON)
        clear.get_style_context().add_class("flat")
        clear.set_tooltip_text("New conversation")
        clear.connect("clicked", self.clear)
        header.pack_start(clear)
        self.clear_button = clear
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(layout)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        self.messages = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.messages.set_border_width(18)
        self.messages.set_valign(Gtk.Align.END)
        scroll.add(self.messages)
        layout.pack_start(scroll, True, True, 0)
        self.scroll = scroll
        layout.pack_start(Gtk.Separator(), False, False, 0)
        row = Gtk.Box(spacing=8)
        row.set_border_width(12)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Message")
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self.send_message)
        row.pack_start(self.entry, True, True, 0)
        self.send = Gtk.Button.new_from_icon_name("mail-send-symbolic", Gtk.IconSize.BUTTON)
        self.send.set_tooltip_text("Send")
        self.send.connect("clicked", self.send_message)
        row.pack_end(self.send, False, False, 0)
        layout.pack_end(row, False, False, 0)
        self.connect("key-press-event", self.on_key)

    def on_key(self, _, event):
        if event.keyval == 65307:
            self.close()

    def clear(self, *_):
        if self.busy:
            return
        self.history = self.history[:1]
        for child in self.messages.get_children():
            child.destroy()
        self.entry.grab_focus()

    def add_message(self, role, text):
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        role_label = Gtk.Label(label="You" if role == "user" else "Assistant")
        role_label.set_xalign(0)
        attributes = Pango.AttrList()
        attributes.insert(Pango.attr_weight_new(Pango.Weight.SEMIBOLD))
        role_label.set_attributes(attributes)
        row.pack_start(role_label, False, False, 0)
        message = Gtk.Label(label=text)
        message.set_xalign(0)
        message.set_line_wrap(True)
        message.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        message.set_max_width_chars(44)
        message.set_selectable(True)
        row.pack_start(message, False, False, 0)
        self.messages.pack_start(row, False, False, 0)
        row.show_all()
        GLib.idle_add(self.scroll_bottom)

    def scroll_bottom(self):
        adjustment = self.scroll.get_vadjustment()
        adjustment.set_value(max(0, adjustment.get_upper() - adjustment.get_page_size()))
        return False

    def send_message(self, *_):
        text = self.entry.get_text().strip()
        if self.busy or not text:
            return
        self.busy = True
        self.entry.set_text("")
        self.entry.set_sensitive(False)
        self.send.set_sensitive(False)
        self.clear_button.set_sensitive(False)
        self.spinner.start()
        self.add_message("user", text)
        self.history.append({"role": "user", "content": text})
        snapshot = [dict(message) for message in self.history]
        threading.Thread(target=self.worker, args=(text, snapshot), daemon=True).start()

    def worker(self, text, history):
        try:
            reply = handle_action(text)
            if reply is None:
                reply = ask_ollama(history)
        except requests.Timeout:
            reply = "The request timed out. Please try again."
        except requests.RequestException:
            reply = "Could not connect to the local model."
        except (OSError, subprocess.SubprocessError, KeyError, ValueError) as error:
            reply = f"Could not complete the request: {error}"
        GLib.idle_add(self.finish, reply)

    def finish(self, reply):
        self.history.append({"role": "assistant", "content": reply})
        if len(self.history) > 21:
            self.history = self.history[:1] + self.history[-20:]
        self.add_message("assistant", reply)
        self.spinner.stop()
        self.busy = False
        self.entry.set_sensitive(True)
        self.send.set_sensitive(True)
        self.clear_button.set_sensitive(True)
        self.entry.grab_focus()
        return False


class Assistant(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.mineos.Assistant")
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = AssistantWindow(self)
            self.window.connect("destroy", self.reset)
            self.window.show_all()
        self.window.present()
        self.window.entry.grab_focus()

    def reset(self, *_):
        self.window = None


if __name__ == "__main__":
    Assistant().run(sys.argv)
