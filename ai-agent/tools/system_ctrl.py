import subprocess
import shutil
import os
import urllib.parse

COMMON_SITES = {
    "youtube": "https://www.youtube.com",
    "youtbe": "https://www.youtube.com",
    "yt": "https://www.youtube.com",
    "whatsapp": "https://web.whatsapp.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://www.github.com",
    "chatgpt": "https://chatgpt.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "instagram": "https://www.instagram.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "linkedin": "https://www.linkedin.com"
}

APP_MAP = {
    "browser": "firefox",
    "firefox": "firefox",
    "chrome": "google-chrome",
    "terminal": "xfce4-terminal",
    "console": "xfce4-terminal",
    "files": "thunar",
    "file manager": "thunar",
    "folder": "thunar",
    "documents": "thunar ~/Documents",
    "downloads": "thunar ~/Downloads",
    "desktop": "thunar ~/Desktop",
    "settings": "xfce4-settings-manager",
    "calculator": "gnome-calculator",
    "editor": "mousepad",
    "text editor": "mousepad",
    "code": "code",
    "vscode": "code",
    "task manager": "xfce4-taskmanager"
}

def get_desktop_env():
    env = dict(os.environ)
    env["DISPLAY"] = ":0"
    if "DBUS_SESSION_BUS_ADDRESS" not in env:
        env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1000/bus"
    return env

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return res.stdout.strip() or res.stderr.strip() or "Success"
    except Exception as e:
        return f"Error: {e}"

def open_url(url: str) -> str:
    url_clean = url.strip()
    if not url_clean.startswith("http://") and not url_clean.startswith("https://"):
        url_clean = "https://" + url_clean
    subprocess.Popen(f"xdg-open '{url_clean}'", shell=True, env=get_desktop_env())
    return f"Opened {url_clean}"

def web_search(query: str, platform: str = "google") -> str:
    encoded = urllib.parse.quote_plus(query.strip())
    if "youtube" in platform.lower():
        target = f"https://www.youtube.com/results?search_query={encoded}"
    else:
        target = f"https://www.google.com/search?q={encoded}"
    return open_url(target)

def open_app(app_name: str) -> str:
    app_lower = app_name.lower().strip()

    for site_key, site_url in COMMON_SITES.items():
        if site_key in app_lower:
            return open_url(site_url)

    for tld in [".com", ".org", ".net", ".io", ".in", ".co", ".app", ".ai"]:
        if tld in app_lower:
            return open_url(app_lower)

    for app_key, cmd in APP_MAP.items():
        if app_key in app_lower:
            subprocess.Popen(cmd, shell=True, env=get_desktop_env())
            return f"Opened {app_key}"

    try:
        subprocess.Popen(app_lower, shell=True, env=get_desktop_env())
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
