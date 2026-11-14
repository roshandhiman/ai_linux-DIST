import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "mineos" / "wallpapers"


def playback_copy(source):
    path = Path(source).resolve(strict=True)
    info = path.stat()
    key = hashlib.sha256(f"640x360-15-v1:{path}:{info.st_size}:{info.st_mtime_ns}".encode()).hexdigest()
    CACHE.mkdir(parents=True, exist_ok=True)
    result = CACHE / f"{key}.mp4"
    if result.is_file():
        return result
    with tempfile.TemporaryDirectory(dir=CACHE) as directory:
        temp = Path(directory) / "preview.mp4"
        subprocess.run(
            ["nice", "-n", "15", "ffmpeg", "-nostdin", "-loglevel", "error",
             "-threads", "2", "-filter_threads", "1", "-i", str(path),
             "-map", "0:v:0", "-an", "-sn", "-dn",
             "-vf", "fps=15,scale=w='min(640,iw)':h='min(360,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
             "-c:v", "libx264", "-threads", "2", "-preset", "ultrafast", "-crf", "23",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temp)],
            check=True, capture_output=True, text=True, timeout=600,
        )
        os.replace(temp, result)
    entries = sorted(CACHE.glob("*.mp4"), key=lambda item: item.stat().st_mtime, reverse=True)
    for old in entries[4:]:
        old.unlink(missing_ok=True)
    return result
