"""User-session voice service with a private Unix socket."""

import concurrent.futures
import json
import os
import signal
import socket
import socketserver
import sys
import threading
from pathlib import Path

from .agent import Mino, WAKE
from .config import load
from .desk import Desktop
from .voice import Capture, Echo, Recognizer, Speaker

MAX_PACKET = 16384


def endpoint():
    runtime = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    return Path(runtime) / "mineos-mino.sock"


class Runtime:
    def __init__(self, ui, settings):
        self.ui = ui
        self.settings = settings
        self.activity = threading.Lock()
        self.audio_jobs = threading.BoundedSemaphore(2)
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="mino")
        self.echo = Echo()
        self.echo.start()
        self.recognizer = Recognizer(settings)
        self.desk = Desktop(Path.home(), settings, ui.approve)
        self.agent = Mino(self.desk, settings)
        self.start_voice()

    def start_voice(self):
        self.speaker = Speaker(self.settings, self.echo, self.ui.show, self.warn)
        self.capture = Capture(self.settings, self.echo, self.submit_audio, self.ui.show,
                               self.speaker.speaking.is_set, self.speaker.cancel, self.warn,
                               self.activity.locked)
        self.capture.thread.start()

    def warn(self, message):
        print(message, file=sys.stderr, flush=True)
        self.ui.show("error", message)

    def reload(self, settings):
        if not self.activity.acquire(blocking=False):
            self.warn("Settings saved. They will apply when Mino next starts.")
            return
        try:
            self.capture.close()
            self.speaker.close()
            self.settings = settings
            self.desk.settings = settings
            self.recognizer = Recognizer(settings)
            self.agent = Mino(self.desk, settings)
            self.start_voice()
        finally:
            self.activity.release()

    def listen(self, held=False):
        self.capture.arm(held)

    def release(self):
        self.capture.release()

    def cancel(self):
        self.capture.cancel()
        self.speaker.cancel()
        self.ui.show("idle")

    def submit_audio(self, pcm):
        if self.audio_jobs.acquire(blocking=False):
            self.pool.submit(self.voice_request, pcm)

    def voice_request(self, pcm):
        try:
            with self.activity:
                self.ui.show("thinking")
                text = self.recognizer.transcribe(pcm)
                if not WAKE.sub("", text).strip():
                    self.ui.show("idle")
                    return
                self.answer(text, True)
        except Exception as exc:
            self.warn(f"Couldn't process speech: {exc}")
            self.speaker.say("I couldn't process that. Check Mino's microphone and model settings.",
                             self.speaker.generation)
        finally:
            self.audio_jobs.release()

    def answer(self, text, speak=False):
        generation = self.speaker.generation
        emitted = False
        self.ui.show("thinking")
        def say(reply):
            nonlocal emitted
            if speak and generation != self.speaker.generation:
                return False
            if speak and reply:
                emitted = True
                self.speaker.say(reply, generation)
            return True
        reply, tool = self.agent.respond(text, say)
        if not emitted and generation == self.speaker.generation:
            self.ui.show("idle")
        return {"reply": reply, "tool": tool}

    def request(self, message):
        action = message.get("action")
        if action == "status":
            return {"reply": "Mino is running.", "wake_word": self.settings.wake_word,
                    "model": self.recognizer.model_path().name.removeprefix("whisper-"), "echo_cancellation": bool(self.echo.source)}
        if action == "listen":
            self.listen()
            return {"reply": "Listening."}
        if action == "release":
            self.release()
            return {"reply": "Released."}
        if action == "stop":
            self.cancel()
            return {"reply": "Stopped audio."}
        if action == "settings":
            self.ui.settings(self)
            return {"reply": "Opened Mino Voice Settings."}
        if action != "text" or type(message.get("text")) != str:
            return {"error": "Unrecognized Mino request."}
        if not self.activity.acquire(blocking=False):
            return {"error": "Mino is busy. Try again in a moment."}
        try:
            return self.answer(message["text"], message.get("speak") is True)
        finally:
            self.activity.release()

    def close(self):
        self.capture.close()
        self.speaker.close()
        self.echo.close()
        self.pool.shutdown(wait=False, cancel_futures=True)


class SocketHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(5)
        try:
            raw = self.rfile.readline(MAX_PACKET + 1)
            message = json.loads(raw) if len(raw) <= MAX_PACKET else None
            if not isinstance(message, dict):
                raise ValueError("invalid request")
            reply = self.server.runtime.request(message)
        except (OSError, ValueError):
            reply = {"error": "Invalid Mino request."}
        self.wfile.write(json.dumps(reply, ensure_ascii=False).encode() + b"\n")


class UserServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True


def client(message):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(58)
        connection.connect(str(endpoint()))
        connection.sendall(json.dumps(message).encode() + b"\n")
        with connection.makefile("rb") as stream:
            return json.loads(stream.readline(MAX_PACKET))


def serve():
    from .ui import Overlay, hotkey
    ui = Overlay()
    path = endpoint()
    if path.exists():
        try:
            client({"action": "status"})
        except ConnectionRefusedError:
            path.unlink()
        else:
            raise RuntimeError("Mino is already running.")
    old = os.umask(0o077)
    try:
        server = UserServer(str(path), SocketHandler)
    finally:
        os.umask(old)
    config, issue = load()
    worker = Runtime(ui, config)
    server.runtime = worker
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="mino-ipc")
    thread.start()
    if issue:
        worker.warn(issue)
    if os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        def listen_hotkey():
            try:
                hotkey(worker)
            except Exception as exc:
                worker.warn(f"Push-to-talk shortcut is unavailable: {exc}")
        threading.Thread(target=listen_hotkey, daemon=True, name="mino-hotkey").start()
    signal.signal(signal.SIGTERM, lambda *_: ui.GLib.idle_add(ui.Gtk.main_quit))
    signal.signal(signal.SIGINT, lambda *_: ui.GLib.idle_add(ui.Gtk.main_quit))
    try:
        ui.Gtk.main()
    finally:
        worker.close()
        server.shutdown()
        server.server_close()
        path.unlink(missing_ok=True)
