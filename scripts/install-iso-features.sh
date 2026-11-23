#!/usr/bin/env bash
# Install the current optional desktop features into a fresh ISO rootfs.
set -euo pipefail
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
root=${1:?Usage: install-iso-features.sh rootfs arm64|amd64}
arch=${2:?Specify the target architecture}
[[ $EUID == 0 && "$root" = /* && -d "$root/etc" ]]
[[ "$arch" == arm64 || "$arch" == amd64 ]]
version=$(tr -d '[:space:]' < "$source_dir/VERSION")
source_sha=$(git -c safe.directory="$source_dir" -C "$source_dir" rev-parse HEAD)
[[ "$source_sha" =~ ^[0-9a-f]{40}$ ]]

# Native Freebuff client and the separate direct-provider SDK bridge.
client="$source_dir/build/mino-code/$arch"
engine="$source_dir/build/code/$arch/mineos-code-engine"
test -x "$client/mino-code"
test -x "$engine"
install -d "$root/opt/mino-code/$version" "$root/opt/ai/code"
install -m 755 "$client/mino-code" "$root/opt/mino-code/$version/"
install -m 644 "$client/"{tree-sitter.wasm,LICENSE,NOTICE,UPSTREAM_REVISION} "$root/opt/mino-code/$version/"
ln -s "$version" "$root/opt/mino-code/current"
install -m 755 "$source_dir/ai/mino-code/mino-code" "$root/usr/local/bin/mino-code"
install -m 755 "$engine" "$root/opt/ai/code/mineos-code-engine"
install -m 644 "$source_dir/ai/code/"{LICENSE,NOTICE} "$root/opt/ai/code/"
cat > "$root/usr/share/applications/org.mineos.Code.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Mino Code
Comment=Open the Mino coding terminal
Exec=xfce4-terminal --command=mino-code
Icon=utilities-terminal
Terminal=false
Categories=Development;
ENTRY

# Keep shared voice weights in the image rather than copying them into RAM
# for every new live user. Personal downloads still use the user's data dir.
release="/opt/mino/releases/$version"
install -d "$root$release/lib/mino" "$root$release/lib/mineos_agent" "$root/opt/mino"
install -m 644 "$source_dir/ai/mino/"*.py "$root$release/lib/mino/"
install -m 644 "$source_dir/ai/mineos_agent/"*.py "$root$release/lib/mineos_agent/"
chroot "$root" python3 -m venv --system-site-packages "$release/venv"
install -m 644 "$source_dir/ai/mino/requirements.txt" "$root/tmp/mino-requirements.txt"
chroot "$root" "$release/venv/bin/python" -m pip install --no-cache-dir --disable-pip-version-check \
    --timeout 30 --retries 5 -r /tmp/mino-requirements.txt
rm "$root/tmp/mino-requirements.txt"
ln -s "releases/$version" "$root/opt/mino/current"
install -m 755 "$source_dir/ai/system/mino" "$root/usr/local/bin/mino"
install -Dm 644 "$source_dir/ai/system/mino.service" "$root/usr/lib/systemd/user/mino.service"
install -m 644 "$source_dir/ai/system/mino-session.desktop" "$root/etc/xdg/autostart/mino-session.desktop"
install -m 644 "$source_dir/ai/system/org.mineos.Mino.desktop" "$root/usr/share/applications/org.mineos.Mino.desktop"
chroot "$root" systemctl --global enable mino.service
for size in tiny base small; do
    chroot "$root" env MINO_MODEL_DIR=/usr/share/mineos/models/voice mino models "$size"
done
chroot "$root" env MINO_MODEL_DIR=/usr/share/mineos/models/voice \
    PYTHONPATH=/opt/mino/current/lib "$release/venv/bin/python" -c \
    'from mino.config import Settings; from mino.models import download; download(Settings(en_voice="en_US-lessac-medium", hi_voice="hi_IN-pratham-medium"), "tiny")'
chroot "$root" env PYTHONPATH=/opt/mino/current/lib "$release/venv/bin/python" -c \
    'import faster_whisper, piper, webrtcvad, pocketsphinx; from mino.voice import Recognizer; from mino.config import Settings; Recognizer(Settings(model_size="tiny")).load()'

# Public, labelled review demo. Users receive writable copies of the 20 PDFs;
# no reports, credentials, conversation history or personal files are copied.
install -d "$root/opt/ai/dealreview/data" "$root/opt/mineos-dealreview"
install -m 644 "$source_dir/ai/dealreview/"*.py "$root/opt/ai/dealreview/"
install -m 644 "$source_dir/ai/dealreview/data/"{cuad_demo.json,NOTICE.md} "$root/opt/ai/dealreview/data/"
chroot "$root" python3 -m venv --system-site-packages /opt/mineos-dealreview/venv
chroot "$root" /opt/mineos-dealreview/venv/bin/python -m pip install --no-cache-dir \
    --disable-pip-version-check 'pypdf==6.21.4' 'Markdown==3.11.3'
install -m 755 "$source_dir/ai/system/mino-review" "$root/usr/local/bin/mino-review"
install -m 644 "$source_dir/ai/system/org.mineos.DealReview.desktop" "$root/usr/share/applications/org.mineos.DealReview.desktop"
chroot "$root" mino-review --download-demo --dealroom /etc/skel/DealRoom
install -m 644 "$source_dir/ai/dealreview/data/NOTICE.md" "$root/etc/skel/DealRoom/NOTICE.md"
install -d "$root/etc/skel/Desktop"
ln -s ../DealRoom "$root/etc/skel/Desktop/CUAD Demo"
chroot "$root" mino-review --check --json --dealroom /etc/skel/DealRoom

# Fail the build if a command or a required feature is missing.
chroot "$root" mino --help
chroot "$root" timeout 30 mino-code --help
chroot "$root" env PYTHONPATH=/opt/ai python3 -c 'import camera_scene, camera_overlay, camera_vision'
test -s "$root/opt/ai/desktop/assets/plasma/scarlet-tree.png"
test -s "$root/usr/share/plasma/wallpapers/org.mineos.video/contents/ui/main.qml"
test -s "$root/usr/share/backgrounds/mineos/graphite.svg"
find "$root/opt/ai" "$root$release/lib" -type d -name __pycache__ -prune -exec rm -rf {} +
install -d "$root/usr/share/mineos"
python3 - "$root/usr/share/mineos/build-manifest.json" "$version" "$source_sha" "$arch" <<'PY'
import json, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({
    'version': sys.argv[2], 'source_commit': sys.argv[3], 'architecture': sys.argv[4],
    'features': ['KDE desktop', 'wallpaper and video wallpaper support', 'Mino voice',
                 'Mino Code native client', 'direct-provider code engine', 'AI camera',
                 'offline Qwen and Laya', 'MineOS IDE', 'reviewed 20-contract CUAD demo'],
    'voice_models': ['tiny', 'base', 'small'],
    'note': 'Cloud coding requires upstream sign-in or user-supplied provider credentials. No personal credentials are bundled.'
}, indent=2) + '\n')
PY
printf '%s\n' 'PASS: full MineOS feature payload validated.'
