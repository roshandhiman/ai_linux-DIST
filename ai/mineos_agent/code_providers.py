"""Per-user provider settings for MineOS Code."""

import fcntl
import json
import os
import re
import shlex
import stat
import tempfile
from contextlib import contextmanager
from getpass import getpass
from pathlib import Path
from urllib.parse import urlsplit

from .config import user_paths

PROVIDER_NAMES = {"zai", "groq", "local", "auto"}
_EXISTING_KEYS = {"ZAI_API_KEY", "Z_AI_API_KEY", "GROQ_API_KEY"}


def private_config(name: str) -> Path:
    return user_paths()["config"].with_name(name)


def _read_private(path: Path) -> str:
    if not path.exists():
        return ""
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError(f"Set permissions to 600 on {path} and use a regular file.")
    return path.read_text(encoding="utf-8")


def default_keys() -> dict[str, str]:
    values = {}
    for line in _read_private(private_config("code.env")).splitlines():
        try:
            words = shlex.split(line, comments=True)
        except ValueError:
            continue
        if len(words) != 2 or words[0] != "export":
            continue
        key, separator, value = words[1].partition("=")
        if separator and key in _EXISTING_KEYS:
            values[key] = value
    return {key: os.environ.get(key) or values.get(key, "") for key in _EXISTING_KEYS}


def private_write(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, mode="w", encoding="utf-8", delete=False
    ) as handle:
        pending = Path(handle.name)
        try:
            handle.write(contents)
            handle.close()
            pending.replace(path)
        finally:
            pending.unlink(missing_ok=True)


@contextmanager
def _provider_update():
    path = private_config("code-providers.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        configs = custom_providers()
        yield configs
        private_write(path, json.dumps(configs, indent=2) + "\n")


def custom_providers() -> dict:
    raw = _read_private(private_config("code-providers.json"))
    if not raw:
        return {}
    try:
        configs = json.loads(raw)
        if not isinstance(configs, dict) or any(
            not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", name) or name in PROVIDER_NAMES
            or not isinstance(value, dict) or not all(isinstance(value.get(key), str)
                for key in ("url", "model", "key")) for name, value in configs.items()
        ):
            raise ValueError
    except ValueError:
        raise ValueError("Invalid MineOS Code provider settings.") from None
    return configs


def add_provider() -> str:
    if not os.isatty(0):
        raise ValueError("Open an interactive terminal for /apiadd.")
    name = input("  Provider name > ").strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", name) or name in PROVIDER_NAMES:
        raise ValueError("Use a new name such as openrouter or my-provider.")
    configs = custom_providers()
    if name in configs:
        raise ValueError(f"{name} already exists. Use /apiremove {name} to replace it.")
    url = input("  OpenAI-compatible base URL > ").strip().rstrip("/")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or url.endswith("/chat/completions")
            or any(char.isspace() for char in url)):
        raise ValueError("Enter an HTTPS base URL such as https://openrouter.ai/api/v1.")
    model = input("  Model ID > ").strip()
    if not model or len(model) > 256 or any(char.isspace() for char in model):
        raise ValueError("Enter the provider's exact model ID.")
    key = getpass(f"  API key for {parsed.hostname} (hidden) > ").strip()
    if not key or any(char.isspace() for char in key):
        raise ValueError("An API key is required.")
    with _provider_update() as current:
        if name in current:
            raise ValueError(f"{name} already exists. Use /apiremove {name} to replace it.")
        current[name] = {"url": url, "model": model, "key": key}
    return name


def remove_provider(name: str) -> None:
    with _provider_update() as configs:
        if name not in configs:
            raise ValueError("Give the name of a custom provider from /providers.")
        del configs[name]


def command_environment() -> dict[str, str]:
    return {
        key: value for key, value in os.environ.items()
        if key not in _EXISTING_KEYS and not re.search(r"TOKEN|SECRET|PASSWORD|API[_-]?KEY", key, re.I)
    }
