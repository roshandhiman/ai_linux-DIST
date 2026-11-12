#!/usr/bin/env python3
import sys
import json
import os
import urllib.request
import urllib.parse
from tools import system_ctrl, iot_ctrl, model_mgr

OLLAMA_API = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:1.5b"
CONFIG_FILE = os.path.expanduser("~/.config/ai/config.json")

def get_active_model() -> str:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f).get("active_model", DEFAULT_MODEL)
        except Exception:
            pass
    return DEFAULT_MODEL

SYSTEM_PROMPT = """You are an AI Operating System Agent embedded in an AI-powered Linux Distro.
You have direct control over this OS and connected hardware (ESP32 / Arduino / Bluetooth).

When the user asks you to do something, determine if you need to execute an OS/hardware action.
If an action is needed, return a STRICT JSON object in this format:
{
  "thought": "brief explanation",
  "action": "open_app" | "set_volume" | "system_status" | "esp32_cmd" | "bluetooth_scan" | "switch_model" | "run_command" | "chat",
  "params": { ... },
  "response": "short friendly response"
}

Actions & Params:
- "open_app": {"app": "firefox" | "terminal" | "files" | "settings" | "calculator"}
- "set_volume": {"percentage": 0 to 100}
- "system_status": {}
- "esp32_cmd": {"command": "LIGHT_ON" | "LIGHT_OFF" | "FAN_ON"}
- "bluetooth_scan": {}
- "switch_model": {"model": "model_name"}
- "run_command": {"cmd": "safe bash command"}
- "chat": {}

Output ONLY valid JSON.
"""

def query_llm(prompt: str) -> dict:
    model = get_active_model()
    payload = {
        "model": model,
        "prompt": f"{SYSTEM_PROMPT}\nUser: {prompt}\nAI JSON:",
        "stream": False,
        "format": "json"
    }
    req = urllib.request.Request(
        OLLAMA_API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return json.loads(data.get("response", "{}"))
    except Exception as e:
        return {
            "action": "chat",
            "response": f"AI Engine Offline ({e})"
        }

def execute_action(action_data: dict) -> str:
    action = action_data.get("action", "chat")
    params = action_data.get("params", {})
    response = action_data.get("response", "")

    print(f"\nAI: {response}")

    result_detail = None
    if action == "open_app":
        app = params.get("app", "")
        result_detail = system_ctrl.open_app(app)
    elif action == "set_volume":
        vol = params.get("percentage", 50)
        result_detail = system_ctrl.set_volume(vol)
    elif action == "system_status":
        status = system_ctrl.get_system_status()
        result_detail = f"RAM: {status['memory_used']} | Disk: {status['disk_used']}"
    elif action == "esp32_cmd":
        cmd = params.get("command", "")
        result_detail = iot_ctrl.control_esp32_serial(cmd)
    elif action == "bluetooth_scan":
        devices = iot_ctrl.scan_bluetooth()
        result_detail = f"Found {len(devices)} device(s): {devices}"
    elif action == "switch_model":
        model = params.get("model", "")
        result_detail = model_mgr.set_active_model(model, CONFIG_FILE)
    elif action == "run_command":
        cmd = params.get("cmd", "")
        result_detail = system_ctrl.run_cmd(cmd)

    if result_detail:
        print(f"   ↳ {result_detail}")

    return response

def main():
    if len(sys.argv) < 2:
        print("Usage: ai <instruction>")
        sys.exit(0)

    prompt = " ".join(sys.argv[1:])
    action_data = query_llm(prompt)
    execute_action(action_data)

if __name__ == "__main__":
    main()
