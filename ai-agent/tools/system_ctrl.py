import subprocess
import shutil
import os
import urllib.parse

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return res.stdout.strip() or res.stderr.strip() or "Success"
    except Exception as e:
        return f"Error: {e}"

def open_url(url: str) -> str:
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    subprocess.Popen(f"x-www-browser '{url}'", shell=True, env=dict(os.environ, DISPLAY=":0"))
    return f"Opened {url}"

def web_search(query: str, platform: str = "google") -> str:
    encoded = urllib.parse.quote_plus(query)
    if "youtube" in platform.lower():
        target = f"https://www.youtube.com/results?search_query={encoded}"
    else:
        target = f"https://www.google.com/search?q={encoded}"
    subprocess.Popen(f"x-www-browser '{target}'", shell=True, env=dict(os.environ, DISPLAY=":0"))
    return f"Searching {platform} for '{query}'"

def open_app(app_name: str) -> str:
    app_lower = app_name.lower().strip()
    
    if "youtube" in app_lower:
        return open_url("https://www.youtube.com")
    if "google" in app_lower:
        return open_url("https://www.google.com")
    if "github" in app_lower:
        return open_url("https://www.github.com")

    mapping = {
        "browser": "x-www-browser",
        "firefox": "firefox",
        "terminal": "xfce4-terminal",
        "files": "thunar",
        "file manager": "thunar",
        "settings": "xfce4-settings-manager",
        "calculator": "gnome-calculator",
        "editor": "mousepad",
        "text editor": "mousepad",
        "code": "code",
        "task manager": "xfce4-taskmanager",
        "music": "pragha"
    }
    cmd = mapping.get(app_lower, app_lower)
    try:
        subprocess.Popen(cmd, shell=True, env=dict(os.environ, DISPLAY=":0"))
        return f"Opened {app_name}"
    except Exception as e:
        return f"Failed to open {app_name}: {e}"

def create_file(path: str, content: str = "") -> str:
    expanded_path = os.path.expanduser(path.strip())
    os.makedirs(os.path.dirname(expanded_path), exist_ok=True)
    try:
        with open(expanded_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Created {expanded_path}"
    except Exception as e:
        return f"Failed to create file: {e}"

def read_file(path: str) -> str:
    expanded_path = os.path.expanduser(path.strip())
    try:
        with open(expanded_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def list_files(path: str = ".") -> str:
    expanded_path = os.path.expanduser(path.strip())
    try:
        files = os.listdir(expanded_path)
        return ", ".join(files) if files else "Directory is empty"
    except Exception as e:
        return f"Error listing directory: {e}"

def set_volume(percentage: int) -> str:
    if shutil.which("pactl"):
        return run_cmd(f"pactl set-sink-volume @DEFAULT_SINK@ {percentage}%")
    elif shutil.which("amixer"):
        return run_cmd(f"amixer set Master {percentage}%")
    return "Volume utility not found"

def get_system_status() -> dict:
    mem = run_cmd("free -h | awk '/^Mem:/ {print $3 \" / \" $2}'")
    disk = run_cmd("df -h / | awk 'NR==2 {print $3 \" / \" $2 \" (\" $5 \")\"}'")
    return {
        "memory_used": mem,
        "disk_used": disk
    }
