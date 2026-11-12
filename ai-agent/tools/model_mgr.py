"""
Jarvis Model Manager Tool
Supports hot-swapping models, downloading new ones, and inspecting loaded model.
"""
import subprocess
import json
import urllib.request

OLLAMA_API = "http://127.0.0.1:11434/api"

def list_installed_models() -> list:
    """Lists all models installed on the system."""
    try:
        req = urllib.request.Request(f"{OLLAMA_API}/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return [m.get("name") for m in data.get("models", [])]
    except Exception:
        # Fallback to CLI
        res = subprocess.run("ollama list", shell=True, capture_output=True, text=True)
        return res.stdout.strip().split("\n")

def pull_model(model_name: str) -> str:
    """Download a new model into the system."""
    try:
        proc = subprocess.Popen(f"ollama pull {model_name}", shell=True)
        return f"Download initiated for {model_name}. Check progress with: ollama list"
    except Exception as e:
        return f"Failed to pull model: {e}"

def set_active_model(model_name: str, config_path: str = "/etc/jarvis/config.json") -> str:
    """Set the system default active model."""
    import os
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        config = {"active_model": model_name}
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return f"Default AI model switched to: {model_name}"
    except Exception as e:
        return f"Could not set active model: {e}"
