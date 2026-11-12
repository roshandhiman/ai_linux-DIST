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

SYSTEM_PROMPT = """You are an AI Operating System Assistant embedded in Linux.
You respond in pure ENGLISH only. Never use Chinese or any other language.

Action Rules:
1. When asked to open ANY website or app (e.g. "open youtube", "open whatsapp web", "open google.com", "open files", "open terminal", "open calculator"):
   action: "open_app", params: {"app": "<name or website>"}
2. When asked to search (e.g. "search youtube for X" or "search google for X"):
   action: "web_search", params: {"query": "<search query>", "platform": "youtube" or "google"}
3. When asked to create or write a file:
   action: "create_file", params: {"path": "~/Documents/filename.ext", "content": "..."}
4. When asked about system memory/RAM or disk:
   action: "system_status", params: {}
5. When asked to set volume:
   action: "set_volume", params: {"percentage": <number>}
6. For greetings, identity, explanations, or chat (e.g. "hi", "who are you"):
   action: "chat", params: {}

Output STRICT JSON only:
{
  "action": "chat" | "open_app" | "web_search" | "create_file" | "system_status" | "set_volume" | "esp32_cmd" | "run_command",
  "params": { ... },
  "response": "friendly response in English"
}
"""

def query_llm(prompt: str) -> dict:
    model = get_active_model()
    payload = {
        "model": model,
        "prompt": f"{SYSTEM_PROMPT}\nUser: {prompt}\nAI JSON:",
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1
        }
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
    if action == "open_app":
        app = params.get("app", "")
        result_detail = system_ctrl.open_app(app)
    elif action == "web_search":
        q = params.get("query", "")
        p = params.get("platform", "google")
        result_detail = system_ctrl.web_search(q, p)
    elif action == "create_file":
        path = params.get("path", "~/Documents/untitled.txt")
        content = params.get("content", "")
        result_detail = system_ctrl.create_file(path, content)
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
