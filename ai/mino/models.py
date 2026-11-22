"""Explicit, resumable downloads for the on-device voice models."""

import subprocess
from pathlib import Path

from .config import SIZES, Settings, model_dir

PIPER_REV = "6428fc718959cf446b00df24966c0185b7f7fcbe"
WHISPER_FILES = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")
KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"


def fetch(url, target):
    if target.is_file() and target.stat().st_size:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    argv = ["curl", "--fail", "--silent", "--show-error", "--location", "--connect-timeout", "10",
            "--retry", "4", "--retry-delay", "1", "--continue-at", "-", "--output", str(partial), url]
    print(f"Downloading {target.name}", flush=True)
    try:
        subprocess.run(argv, check=True, timeout=480)
    except subprocess.CalledProcessError as error:
        if error.returncode not in (33, 36) or not partial.exists():
            raise
        partial.unlink()
        subprocess.run(argv, check=True, timeout=480)
    if not partial.stat().st_size:
        raise ValueError(f"Empty download for {target.name}.")
    partial.replace(target)


def download(settings: Settings, size=None, *, kokoro=False):
    size = size or settings.stt_size
    if size not in SIZES[1:]:
        raise ValueError("Choose tiny, base, or small.")
    root = model_dir()
    for filename in WHISPER_FILES:
        fetch(f"https://huggingface.co/Systran/faster-whisper-{size}/resolve/main/{filename}",
              root / f"whisper-{size}" / filename)
    for voice in (settings.en_voice, settings.hi_voice):
        language, speaker, quality = voice.split("-")
        base = (f"https://huggingface.co/rhasspy/piper-voices/resolve/{PIPER_REV}/"
                f"{language[:2]}/{language}/{speaker}/{quality}")
        for suffix in (".onnx", ".onnx.json"):
            fetch(f"{base}/{voice}{suffix}", root / f"{voice}{suffix}")
        fetch(f"{base}/MODEL_CARD", root / f"{voice}.LICENSE.txt")
    if kokoro:
        for file in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
            fetch(f"{KOKORO_URL}/{file}", root / file)
    print(f"Mino models are ready in {root}")
