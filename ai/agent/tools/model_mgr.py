import subprocess
import json
import urllib.request
import os

OLLAMA_API = "http://127.0.0.1:11434/api"

def list_installed_models() -> list:
    try:
        req = urllib.request.Request(f"{OLLAMA_API}/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return [m.get("name") for m in data.get("models", [])]
    except Exception:
        res = subprocess.run("ollama list", shell=True, capture_output=True, text=True)
        return res.stdout.strip().split("\n")

def pull_model(model_name: str) -> str:
    try:
        subprocess.Popen(f"ollama pull {model_name}", shell=True)
        return f"Download initiated for {model_name}"
    except Exception as e:
        return f"Failed to pull model: {e}"

def set_active_model(model_name: str, config_path: str = "/etc/jarvis/config.json") -> str:
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        config = {"active_model": model_name}
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return f"Default AI model switched to: {model_name}"
    except Exception as e:
        return f"Could not set active model: {e}"
