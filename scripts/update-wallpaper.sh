#!/usr/bin/env bash
set -euo pipefail

source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/desktop"
desktop_dir=/opt/ai/desktop
plugin_dir=/usr/share/plasma/wallpapers/org.mineos.video
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/mineos"

if (( EUID == 0 )); then
    printf '%s\n' 'Run this from MineOS Terminal as your normal user.' >&2
    exit 1
fi
if ! grep -qx 'VERSION_CODENAME=trixie' /etc/os-release ||
    [[ ! -f "$desktop_dir/settings.py" || -z "${DISPLAY:-}" || ":${XDG_CURRENT_DESKTOP:-}:" != *:KDE:* ]] ||
    ! busctl --user status org.kde.plasmashell >/dev/null 2>&1; then
    printf '%s\n' 'Open Terminal in the desktop from MineOS 1.0.4 or newer, then run the updater.' >&2
    exit 1
fi
if grep -Eq '(^|[[:space:]])boot=live([[:space:]]|$)' /proc/cmdline; then
    printf '%s\n' 'This is a live session. The update lasts until reboot unless the live system has persistence.'
fi

mkdir -p "$state_dir"
exec 9>"$state_dir/update-desktop.lock"
flock -n 9 || { printf '%s\n' 'A MineOS desktop update is already running.' >&2; exit 1; }

desktop_files=(settings.py preferences.py companion.py native_wallpaper.py native-wallpaper.js)
plugin_files=(metadata.json contents/config/main.xml contents/ui/main.qml contents/ui/config.qml)

for file in "${desktop_files[@]}"; do
    test -s "$source_dir/$file"
done
for file in "${plugin_files[@]}"; do
    test -s "$source_dir/native-wallpaper/$file"
done
python3 - "$source_dir" "${desktop_files[@]}" <<'PY'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])
for filename in sys.argv[2:]:
    if filename.endswith(".py"):
        ast.parse((root / filename).read_text(), filename=filename)
PY

missing=()
for package in ffmpeg qml6-module-qtmultimedia qml6-module-qtquick-dialogs; do
    if [[ "$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null || true)" != installed ]]; then
        missing+=("$package")
    fi
done
if (( ${#missing[@]} )); then
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends "${missing[@]}"
fi

backup="$(mktemp -d "$state_dir/wallpaper-backup.XXXXXXXX")"
save_files() {
    local base=$1
    shift
    local file
    for file in "$@"; do
        if [[ -e "$base/$file" ]]; then
            mkdir -p "$backup$base/$(dirname -- "$file")"
            sudo cp -a -- "$base/$file" "$backup$base/$file"
        fi
    done
}
save_files "$desktop_dir" "${desktop_files[@]}"
save_files "$plugin_dir" "${plugin_files[@]}"

restore_files() {
    local base=$1
    shift
    local file
    for file in "$@"; do
        if [[ -e "$backup$base/$file" ]]; then
            sudo cp -a -- "$backup$base/$file" "$base/$file"
        else
            sudo rm -f -- "$base/$file"
        fi
    done
}
restore_on_error() {
    local status=$?
    if (( status )); then
        restore_files "$desktop_dir" "${desktop_files[@]}"
        restore_files "$plugin_dir" "${plugin_files[@]}"
        printf 'Previous wallpaper files restored. Backup: %s\n' "$backup" >&2
    fi
}
trap restore_on_error EXIT
for file in "${plugin_files[@]}"; do
    sudo install -D -m 644 -- "$source_dir/native-wallpaper/$file" "$plugin_dir/$file"
done
for file in "${desktop_files[@]}"; do
    sudo install -D -m 644 -- "$source_dir/$file" "$desktop_dir/$file"
done
plugins=$(kpackagetool6 --global --type Plasma/Wallpaper --list)
grep -Fxq org.mineos.video <<< "$plugins"
trap - EXIT

if ! PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$desktop_dir" python3 - <<'PY'
from pathlib import Path
import native_wallpaper
import preferences

saved = preferences.read()
if saved["live"] and saved["video"] and Path(saved["video"]).is_file() and not native_wallpaper.selection().get("live"):
    native_wallpaper.apply(saved, {**saved, "live": False})
PY
then
    printf '%s\n' 'The update is installed. Re-select your video in Settings to apply it.' >&2
fi

if read -r _ companion_pid < <(busctl --user call org.freedesktop.DBus /org/freedesktop/DBus \
    org.freedesktop.DBus GetConnectionUnixProcessID s org.mineos.Companion 2>/dev/null); then
    kill -TERM "$companion_pid" 2>/dev/null || true
fi
if ! systemd-run --user --collect --setenv="DISPLAY=$DISPLAY" \
    --setenv="XAUTHORITY=${XAUTHORITY:-$HOME/.Xauthority}" \
    --setenv="XDG_CURRENT_DESKTOP=$XDG_CURRENT_DESKTOP" \
    /usr/bin/nice -n 8 /usr/bin/python3 "$desktop_dir/companion.py"; then
    printf '%s\n' 'Sign out and back in when convenient to reload the desktop companion.' >&2
fi

printf 'Live wallpaper installed. Close and reopen Settings, then select Wallpaper. Backup: %s\n' "$backup"
