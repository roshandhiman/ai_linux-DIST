import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango
import threading
import requests
import json
import subprocess
import os
import sys
import socket

LOCK_FILE = "/tmp/ai_hud.lock"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:1.5b"
SYSTEM_PROMPT = (
    "You are an AI operating system agent for MineOS. "
    "RULES: 1) Always reply ONLY in English. 2) Be concise. "
    "3) When the user says open/launch/go to X, call the tool. "
    "4) Never show the model name."
)

COMMON_SITES = {
    "youtube": "https://youtube.com",
    "whatsapp": "https://web.whatsapp.com",
    "google": "https://google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "twitter": "https://twitter.com",
    "instagram": "https://instagram.com",
    "reddit": "https://reddit.com",
    "netflix": "https://netflix.com",
    "spotify": "https://open.spotify.com",
    "maps": "https://maps.google.com",
    "translate": "https://translate.google.com",
    "linkedin": "https://linkedin.com",
    "chatgpt": "https://chat.openai.com",
}

COMMON_APPS = {
    "terminal": ["xfce4-terminal"],
    "files": ["thunar"],
    "settings": ["xfce4-settings-manager"],
    "text editor": ["mousepad"],
    "task manager": ["xfce4-taskmanager"],
    "calculator": ["galculator"],
}

def _env():
    e = os.environ.copy()
    e["DISPLAY"] = ":0"
    e["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1000/bus"
    return e

def open_url(url):
    subprocess.Popen(["xdg-open", url], env=_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def handle_action(text):
    low = text.lower()
    for site, url in COMMON_SITES.items():
        if site in low and any(w in low for w in ["open", "search", "go", "launch", "firefox", "browser", "show"]):
            open_url(url)
            return f"Opening {site.capitalize()} in Firefox."
    for app, cmd in COMMON_APPS.items():
        if app in low and any(w in low for w in ["open", "launch", "start", "show"]):
            subprocess.Popen(cmd, env=_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Launching {app.title()}."
    if "search" in low:
        query = low.replace("search", "").strip()
        if "youtube" in low:
            query = query.replace("on youtube", "").replace("youtube", "").strip()
            open_url(f"https://youtube.com/results?search_query={query.replace(' ', '+')}")
            return f"Searching YouTube for: {query}"
        query = query.replace("on google", "").replace("google", "").strip()
        open_url(f"https://google.com/search?q={query.replace(' ', '+')}")
        return f"Searching Google for: {query}"
    if "volume" in low or "mute" in low:
        if "mute" in low:
            subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"], env=_env())
            return "Toggled mute."
        elif "up" in low or "increase" in low:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"], env=_env())
            return "Volume increased."
        elif "down" in low or "decrease" in low:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"], env=_env())
            return "Volume decreased."
    return None

def ask_ollama(history):
    payload = {"model": MODEL, "messages": history, "stream": False, "options": {"temperature": 0.1}}
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=60)
        return r.json()["message"]["content"].strip()
    except Exception as e:
        return f"Error: {e}"

CSS = b"""
* { font-family: "Inter", "Cantarell", sans-serif; }
window {
    background-color: #0a0a0f;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
}
#titlebar {
    background-color: #0d0d14;
    border-bottom: 1px solid #1e1e2e;
    border-radius: 12px 12px 0 0;
    padding: 10px 14px;
}
#title-label {
    color: #e8e8f0;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
#dot-green { color: #2ecc71; font-size: 11px; }
#dot-yellow { color: #f39c12; font-size: 11px; }
#dot-red { color: #e74c3c; font-size: 11px; }
#close-btn {
    background: none;
    border: none;
    color: #e74c3c;
    font-size: 15px;
    padding: 0 2px;
    min-width: 20px;
    min-height: 20px;
    border-radius: 50%;
}
#close-btn:hover { background-color: #2a0a0a; }
#scroll { background-color: #0a0a0f; }
#chat-box { background-color: #0a0a0f; padding: 8px 10px; }
.bubble-user {
    background-color: #1a1f35;
    border-radius: 12px 12px 4px 12px;
    padding: 8px 12px;
    color: #e8e8f0;
    font-size: 13px;
}
.bubble-ai {
    background-color: #14141c;
    border-radius: 12px 12px 12px 4px;
    border: 1px solid #1e1e2e;
    padding: 8px 12px;
    color: #e8e8f0;
    font-size: 13px;
}
.bubble-status {
    background: none;
    color: #3d84f5;
    font-size: 11px;
    padding: 2px 4px;
}
#input-box {
    background-color: #111118;
    border-top: 1px solid #1e1e2e;
    padding: 8px 10px;
    border-radius: 0 0 12px 12px;
}
#entry {
    background-color: #1a1a24;
    color: #e8e8f0;
    border: 1px solid #2a2a3e;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    caret-color: #3d84f5;
}
#entry:focus { border-color: #3d84f5; }
#send-btn {
    background-color: #3d84f5;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 15px;
    font-weight: 600;
    min-width: 48px;
}
#send-btn:hover { background-color: #5a99ff; }
#send-btn:active { background-color: #2a6fe0; }
#thinking-label {
    color: #3d84f5;
    font-size: 11px;
    padding: 2px 10px;
    font-style: italic;
}
"""

class AiHUD(Gtk.Window):
    def __init__(self):
        super().__init__(title="AI Assistant")
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.set_default_size(360, 580)
        self.set_resizable(True)
        self.set_keep_above(True)
        self.set_decorated(False)
        self.set_app_paintable(True)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        if monitor:
            geo = monitor.get_geometry()
            self.move(geo.x + geo.width - 380, geo.y + 50)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self._build_ui()
        self.connect("delete-event", Gtk.main_quit)
        self.connect("key-press-event", self._on_key)
        self._drag_start = None
        self._titlebar.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON1_MOTION_MASK)
        self._titlebar.connect("button-press-event", self._drag_begin)
        self._titlebar.connect("motion-notify-event", self._drag_motion)

    def _build_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        self._titlebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._titlebar.set_name("titlebar")

        dots = Gtk.Box(spacing=5)
        for did, lbl in [("dot-red", "●"), ("dot-yellow", "●"), ("dot-green", "●")]:
            l = Gtk.Label(label=lbl)
            l.set_name(did)
            dots.pack_start(l, False, False, 0)
        self._titlebar.pack_start(dots, False, False, 0)

        title = Gtk.Label(label="  AI Assistant")
        title.set_name("title-label")
        title.set_halign(Gtk.Align.START)
        self._titlebar.pack_start(title, True, True, 0)

        close_btn = Gtk.Button(label="✕")
        close_btn.set_name("close-btn")
        close_btn.connect("clicked", lambda _: Gtk.main_quit())
        self._titlebar.pack_end(close_btn, False, False, 0)

        vbox.pack_start(self._titlebar, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_name("scroll")
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        self._chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._chat_box.set_name("chat-box")
        self._chat_box.set_valign(Gtk.Align.END)
        scroll.add(self._chat_box)
        vbox.pack_start(scroll, True, True, 0)
        self._scroll = scroll

        self._thinking = Gtk.Label(label="")
        self._thinking.set_name("thinking-label")
        self._thinking.set_halign(Gtk.Align.START)
        self._thinking.set_no_show_all(True)
        vbox.pack_start(self._thinking, False, False, 0)

        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_box.set_name("input-box")

        self._entry = Gtk.Entry()
        self._entry.set_name("entry")
        self._entry.set_placeholder_text("Ask anything...")
        self._entry.set_hexpand(True)
        self._entry.connect("activate", self._on_send)
        input_box.pack_start(self._entry, True, True, 0)

        send_btn = Gtk.Button(label="→")
        send_btn.set_name("send-btn")
        send_btn.connect("clicked", self._on_send)
        input_box.pack_start(send_btn, False, False, 0)

        vbox.pack_start(input_box, False, False, 0)

        self._add_bubble("ai", "Hello! How can I help you today?")

    def _add_bubble(self, role, text):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        label = Gtk.Label(label=text)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_max_width_chars(32)
        label.set_selectable(True)
        label.set_xalign(0)

        if role == "user":
            row.set_halign(Gtk.Align.END)
            label.get_style_context().add_class("bubble-user")
            row.set_name("msg-row-user")
        else:
            row.set_halign(Gtk.Align.START)
            label.get_style_context().add_class("bubble-ai")
            row.set_name("msg-row-ai")

        row.pack_start(label, False, False, 0)
        self._chat_box.pack_start(row, False, False, 0)
        row.show_all()
        GLib.idle_add(self._scroll_bottom)

    def _scroll_bottom(self):
        adj = self._scroll.get_vadjustment()
        adj.set_value(adj.get_upper())
        return False

    def _on_send(self, *_):
        text = self._entry.get_text().strip()
        if not text:
            return
        self._entry.set_text("")
        self._add_bubble("user", text)
        self._thinking.set_text("thinking...")
        self._thinking.show()

        def worker():
            action_reply = handle_action(text)
            if action_reply:
                self.history.append({"role": "user", "content": text})
                self.history.append({"role": "assistant", "content": action_reply})
                GLib.idle_add(self._reply, action_reply)
                return
            self.history.append({"role": "user", "content": text})
            reply = ask_ollama(self.history)
            self.history.append({"role": "assistant", "content": reply})
            GLib.idle_add(self._reply, reply)

        threading.Thread(target=worker, daemon=True).start()

    def _reply(self, text):
        self._thinking.hide()
        self._add_bubble("ai", text)
        return False

    def _on_key(self, _, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def _drag_begin(self, widget, event):
        if event.button == 1:
            self._drag_start = (event.x_root, event.y_root, *self.get_position())

    def _drag_motion(self, widget, event):
        if self._drag_start:
            dx = event.x_root - self._drag_start[0]
            dy = event.y_root - self._drag_start[1]
            self.move(int(self._drag_start[2] + dx), int(self._drag_start[3] + dy))

def acquire_lock():
    try:
        import socket
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind("\0ai_hud_lock")
        return s
    except OSError:
        sys.exit(0)

if __name__ == "__main__":
    lock = acquire_lock()
    win = AiHUD()
    win.show_all()
    Gtk.main()
