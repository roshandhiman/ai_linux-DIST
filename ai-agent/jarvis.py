#!/usr/bin/env python3
"""
Jarvis Core Agent for JarvisOS
Orchestrates offline LLM reasoning and system action execution.
"""
import sys
import json
import os
import urllib.request
import urllib.parse
from tools import system_ctrl, iot_ctrl, model_mgr

OLLAMA_API = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:1.5b"
CONFIG_FILE = os.path.expanduser("~/.config/jarvis/config.json")

def get_active_model() -> str:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f).get("active_model", DEFAULT_MODEL)
        except Exception:
            pass
    return DEFAULT_MODEL

SYSTEM_PROMPT = """You are JARVIS, an advanced AI Operating System Agent embedded in an AI-powered Linux Distro.
You have direct control over this OS and connected hardware (ESP32 / Arduino / Bluetooth).

When the user asks you to do something, determine if you need to execute an OS/hardware action.
If an action is needed, return a STRICT JSON object in this format:
{
  "thought": "brief explanation of what you are doing",
  "action": "open_app" | "set_volume" | "system_status" | "esp32_cmd" | "bluetooth_scan" | "switch_model" | "run_command" | "chat",
  "params": { ... },
  "response": "friendly Jarvis-style response to the user"
}

Actions & Params:
- "open_app": {"app": "firefox" | "terminal" | "files" | "settings" | "calculator" | ...}
- "set_volume": {"percentage": 0 to 100}
- "system_status": {}
- "esp32_cmd": {"command": "LIGHT_ON" | "LIGHT_OFF" | "FAN_ON" | ...}
- "bluetooth_scan": {}
- "switch_model": {"model": "model_name"}
- "run_command": {"cmd": "safe bash command"}
- "chat": {} (normal answers, explanations, assistance)

Always maintain the calm, capable persona of JARVIS. Output ONLY valid JSON.
"""

def query_llm(prompt: str) -> dict:
    model = get_active_model()
    payload = {
        "model": model,
        "prompt": f"{SYSTEM_PROMPT}\nUser: {prompt}\nJarvis JSON:",
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
            "response": f"Jarvis Core Offline or Initializing ({e}). Please ensure Ollama is active."
        }

def execute_action(action_data: dict) -> str:
    action = action_data.get("action", "chat")
    params = action_data.get("params", {})
    response = action_data.get("response", "")

    print(f"\n⚡ JARVIS: {response}")

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
        print(f"   ↳ [System Action] {result_detail}")

    return response

def main():
    if len(sys.argv) < 2:
        print("⚡ JARVIS AI Operating System Core")
        print("Usage: jarvis <instruction>")
        print("Example: jarvis 'open files and set volume to 70'")
        print("         jarvis 'turn on living room light via esp32'")
        print("         jarvis 'switch model to llama3.2'")
        sys.exit(0)

    prompt = " ".join(sys.argv[1:])
    action_data = query_llm(prompt)
    execute_action(action_data)

if __name__ == "__main__":
    main()
