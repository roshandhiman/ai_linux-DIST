"""Voice settings shared by the desktop service and setup commands."""

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

VOICES = ("en_US-amy-low", "en_US-lessac-medium", "hi_IN-rohan-medium", "hi_IN-pratham-medium")
SIZES = ("auto", "tiny", "base", "small")
LANGUAGES = ("auto", "en", "hi")
SYSTEM_MODELS = Path("/usr/share/mineos/models/voice")


def config_path():
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "mineos/mino.json"


def model_dir():
    override = os.environ.get("MINO_MODEL_DIR")
    return Path(override) if override else Path(os.environ.get(
        "XDG_DATA_HOME", Path.home() / ".local/share")) / "mineos/mino/models"


def model_asset(name):
    """Prefer personal models, then the read-only models shipped on the ISO."""
    personal = model_dir() / name
    if personal.exists() or os.environ.get("MINO_MODEL_DIR"):
        return personal
    bundled = SYSTEM_MODELS / name
    return bundled if bundled.exists() else personal


def memory_mib():
    try:
        return int(Path("/proc/meminfo").read_text().splitlines()[0].split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return 4096


@dataclass(frozen=True)
class Settings:
    wake_word: bool = True
    model_size: str = "auto"
    language: str = "auto"
    en_voice: str = "en_US-amy-low"
    hi_voice: str = "hi_IN-rohan-medium"
    speed: float = 1.0
    voice_engine: str = "piper"
    wake_model: str = ""
    local_vision: bool = False
    use_hosted_planner: bool = False

    def __post_init__(self):
        if self.model_size not in SIZES or self.language not in LANGUAGES:
            raise ValueError("Select a valid speech language and model size.")
        if self.en_voice not in VOICES[:2] or self.hi_voice not in VOICES[2:]:
            raise ValueError("Select a supported English and Hindi voice.")
        if self.voice_engine not in ("piper", "kokoro"):
            raise ValueError("Choose piper or kokoro.")
        if type(self.speed) not in (int, float) or not .65 <= self.speed <= 1.5:
            raise ValueError("Voice speed must be between 0.65 and 1.5.")
        if not isinstance(self.wake_model, str):
            raise ValueError("The optional wake model must be a path.")
        if any(type(flag) != bool for flag in (self.wake_word, self.local_vision, self.use_hosted_planner)):
            raise ValueError("Wake, vision, and hosted options must be true or false.")

    @property
    def stt_size(self):
        if self.model_size != "auto":
            return self.model_size
        ram = memory_mib()
        return "tiny" if ram <= 5200 else "base" if ram <= 10000 else "small"

    @property
    def threads(self):
        return max(1, min(os.cpu_count() or 2, 2 if memory_mib() <= 5200 else 4))


def load():
    file = config_path()
    try:
        return Settings(**json.loads(file.read_text(encoding="utf-8"))), ""
    except FileNotFoundError:
        return Settings(), ""
    except (OSError, ValueError, TypeError):
        return Settings(wake_word=False), f"Could not read {file}. Open Mino Settings to fix it."


def save(settings):
    file = config_path()
    file.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=file.parent, delete=False) as out:
        pending = Path(out.name)
        try:
            json.dump(asdict(settings), out, indent=2)
            out.write("\n")
            out.close()
            pending.replace(file)
        finally:
            pending.unlink(missing_ok=True)
