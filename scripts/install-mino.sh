#!/usr/bin/env bash
set -euo pipefail
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
root=/opt/mino
if (( EUID == 0 )); then
    printf '%s\n' 'Run this from your normal MineOS desktop user. The installer will use sudo.' >&2
    exit 2
fi
if [[ ! -f /etc/debian_version ]]; then
    printf '%s\n' 'This installer targets Debian-based MineOS.' >&2
    exit 2
fi

packages=(bubblewrap python3-venv python3-gi python3-xlib python3-pil python3-numpy
          gir1.2-gtk-3.0 gir1.2-atspi-2.0 libglib2.0-bin libspeexdsp1 libportaudio2
          pulseaudio-utils ripgrep fd-find tesseract-ocr tesseract-ocr-eng xdg-utils
          wmctrl xdotool maim grim slurp espeak-ng curl util-linux)
sudo apt-get install -y --no-install-recommends "${packages[@]}"
sudo install -d -m 755 "$root"
build="$(sudo mktemp -d "$root/releases.XXXXXXXX")"
keep=0
cleanup() {
    if (( ! keep )); then sudo rm -r -- "$build"; fi
}
trap cleanup EXIT
sudo chmod 755 "$build"
sudo install -d -m 755 "$build/lib/mino" "$build/lib/mineos_agent"
sudo install -m 644 "$source_dir/ai/mino/"*.py "$build/lib/mino/"
sudo install -m 644 "$source_dir/ai/mineos_agent/"*.py "$build/lib/mineos_agent/"
sudo python3 -m venv --system-site-packages "$build/venv"
pip=("$build/venv/bin/python" -m pip install --no-cache-dir --disable-pip-version-check --timeout 20 --retries 5)
sudo "${pip[@]}" 'pip>=25.2'
sudo "${pip[@]}" --resume-retries 8 -r "$source_dir/ai/mino/requirements.txt"
if [[ "${MINO_KOKORO:-0}" == 1 ]]; then
    sudo "${pip[@]}" --resume-retries 8 'kokoro-onnx>=0.4,<0.6'
fi
if [[ "${MINO_OPENWAKEWORD:-0}" == 1 ]]; then
    sudo "${pip[@]}" --resume-retries 8 'openwakeword>=0.6,<0.7'
fi
# Verify the venv and source before publishing the symlink.
PYTHONPATH="$build/lib" "$build/venv/bin/python" -B -c 'import faster_whisper, piper, webrtcvad, pocketsphinx; from mino.agent import Mino'
sudo install -Dm 755 "$source_dir/ai/system/mino" /usr/local/bin/mino
sudo install -Dm 644 "$source_dir/ai/system/mino.service" /usr/lib/systemd/user/mino.service
sudo install -Dm 644 "$source_dir/ai/system/mino-session.desktop" /etc/xdg/autostart/mino-session.desktop
sudo install -Dm 644 "$source_dir/ai/system/org.mineos.Mino.desktop" /usr/local/share/applications/org.mineos.Mino.desktop
sudo ln -s "$build" "$build.link"
sudo mv -Tf "$build.link" "$root/current"
keep=1
if [[ "${MINO_SKIP_MODELS:-0}" != 1 ]]; then
    if [[ "${MINO_KOKORO:-0}" == 1 ]]; then mino models kokoro; else mino models; fi
fi
systemctl --user daemon-reload
systemctl --user enable mino.service
if systemctl --user is-active --quiet mino.service; then
    systemctl --user restart mino.service
elif [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    mino session-start
fi
printf '%s\n' 'Mino installed. Say Mino or hold Ctrl+Alt+Space in the X11 desktop.'
