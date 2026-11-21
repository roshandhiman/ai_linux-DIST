"""Mino's command entry point."""

import argparse
import json
import os
import subprocess
import sys
import shutil
from pathlib import Path

from .config import LANGUAGES, SIZES, Settings, load
from .service import client, serve


def session_start():
    names = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "XDG_CURRENT_DESKTOP",
             "XDG_SESSION_TYPE", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS")
    present = [name for name in names if name in os.environ]
    if present:
        subprocess.run(["systemctl", "--user", "import-environment", *present], check=True, timeout=5)
    subprocess.run(["systemctl", "--user", "start", "mino.service"], check=True, timeout=10)


def approve_cli(title, detail):
    if not sys.stdin.isatty():
        return False
    print(f"{title}\n{detail}", file=sys.stderr)
    return input("Confirm [y/N]? ").strip().casefold() == "y"


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "code":
        binary = shutil.which("mino-code")
        if not binary:
            print("Install Mino Code with scripts/install-mino-code.sh.", file=sys.stderr)
            return 1
        os.execv(binary, [binary, *sys.argv[2:]])
    p = argparse.ArgumentParser(prog="mino", description="Speak to your MineOS assistant.")
    p.add_argument("--once", action="store_true", help="Run a text request in this process")
    p.add_argument("--speak", action="store_true", help="Speak the response in the desktop service")
    p.add_argument("--json", action="store_true", help="Return a JSON response")
    p.add_argument("request", nargs="*")
    args = p.parse_args()
    request = args.request
    if not request:
        p.print_help()
        return 0
    mode = request[0]
    try:
        if mode == "daemon":
            serve()
            return 0
        if mode == "session-start":
            session_start()
            return 0
        if mode == "models":
            from .models import download
            settings, issue = load()
            if issue:
                print(issue, file=sys.stderr)
            size = next((x for x in request[1:] if x in SIZES[1:]), None)
            # Use 'kokoro' as an optional positional selection.
            download(settings, size, kokoro="kokoro" in request[1:])
            return 0
        if mode == "transcribe" and len(request) == 2:
            from .voice import RATE, Recognizer
            import wave
            with wave.open(request[1]) as audio:
                if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (RATE, 1, 2):
                    raise ValueError("Use 16 kHz mono 16-bit PCM WAV.")
                print(Recognizer(load()[0]).transcribe(audio.readframes(RATE * 12)))
            return 0
        if args.once:
            from .agent import Mino
            from .desk import Desktop
            settings, _ = load()
            reply, tool = Mino(Desktop(Path.home(), settings, approve_cli), settings).respond(" ".join(request))
            result = {"reply": reply, "tool": tool}
        elif mode in ("listen", "release", "stop", "status", "settings") and len(request) == 1:
            result = client({"action": mode})
        else:
            result = client({"action": "text", "text": " ".join(request), "speak": args.speak})
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        elif mode == "status" and "echo_cancellation" in result:
            print(f"{result['reply']} Model: {result['model']}. "
                  f"Wake word: {'on' if result['wake_word'] else 'off'}. "
                  f"Echo cancellation: {'on' if result['echo_cancellation'] else 'off'}.")
        else:
            print(result.get("reply", result.get("error", "")))
        return int("error" in result)
    except (ConnectionRefusedError, FileNotFoundError) as error:
        print("Mino is unavailable. Start it in your desktop session or use mino --once.", file=sys.stderr)
        return 1
    except (OSError, ValueError, ImportError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Mino: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
