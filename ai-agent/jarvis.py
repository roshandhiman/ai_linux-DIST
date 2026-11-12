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
You have direct execution control over this OS, files, and connected hardware.

CRITICAL RULES:
1. When asked to create, write, or generate a file, you MUST use action "create_file". Provide the target path and complete file content. Default paths: ~/Documents, ~/Desktop, or current folder.
2. When asked to open apps, use action "open_app".
3. When asked to run bash commands, use action "run_command".
4. When asked to control volume, status, or hardware, use the corresponding action.

Output STRICT JSON only:
{
  "thought": "brief thought",
  "action": "create_file" | "open_app" | "run_command" | "set_volume" | "system_status" | "esp32_cmd" | "bluetooth_scan" | "switch_model" | "chat",
  "params": { ... },
  "response": "short friendly response"
}

Params specifications:
- "create_file": {"path": "~/Documents/script.py", "content": "..."}
- "open_app": {"app": "firefox" | "thunar" | "terminal" | "settings" | "calculator"}
- "run_command": {"cmd": "shell command"}
- "set_volume": {"percentage": 0 to 100}
- "system_status": {}
- "esp32_cmd": {"command": "LIGHT_ON" | "LIGHT_OFF" | "FAN_ON"}
- "bluetooth_scan": {}
- "switch_model": {"model": "model_name"}
- "chat": {}

Never output conversational text outside the JSON.
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

def execute_action(action_data: dict) -> dict:
    action = action_data.get("action", "chat")
    params = action_data.get("params", {})
    response = action_data.get("response", "")

    result_detail = None
    if action == "create_file":
        path = params.get("path", "~/Documents/untitled.txt")
        content = params.get("content", "")
        result_detail = system_ctrl.create_file(path, content)
    elif action == "open_app":
        app = params.get("app", "")
        result_detail = system_ctrl.open_app(app)
    elif action == "run_command":
        cmd = params.get("cmd", "")
        result_detail = system_ctrl.run_cmd(cmd)
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
        result_detail = f"Found {len(devices)} device(s)"
    elif action == "switch_model":
        model = params.get("model", "")
        result_detail = model_mgr.set_active_model(model, CONFIG_FILE)

    return {
        "response": response,
        "detail": result_detail,
        "action": action
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: ai <instruction>")
        sys.exit(0)

    prompt = " ".join(sys.argv[1:])
    action_data = query_llm(prompt)
    res = execute_action(action_data)
    print(f"\nAI: {res['response']}")
    if res.get("detail"):
        print(f"   ↳ {res['detail']}")

if __name__ == "__main__":
    main()
