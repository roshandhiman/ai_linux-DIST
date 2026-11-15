#!/usr/bin/env bash
set -euo pipefail

source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if (( EUID == 0 )); then
    printf '%s\n' 'Run this from the MineOS desktop as your normal user. The updater uses sudo when needed.' >&2
    exit 1
fi
if ! grep -qx 'VERSION_CODENAME=trixie' /etc/os-release || [[ ! -f /opt/ai/desktop/apply-theme.sh ]]; then
    printf '%s\n' 'This updater requires an existing Debian 13 based MineOS desktop.' >&2
    exit 1
fi
if [[ -z "${DISPLAY:-}" || "${XDG_SESSION_TYPE:-x11}" != x11 ]] || ! xrandr --query >/dev/null 2>&1; then
    printf '%s\n' 'Open Terminal inside your MineOS XFCE desktop and run the updater there.' >&2
    exit 1
fi

if grep -Eq '(^|[[:space:]])boot=live([[:space:]]|$)' /proc/cmdline; then
    printf '%s\n' 'This is a live session. Updates last until reboot unless the system has persistent storage.'
fi

state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/mineos"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}"
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
mkdir -p "$state_dir"
exec 9>"$state_dir/update-desktop.lock"
if ! flock -n 9; then
    printf '%s\n' 'A MineOS desktop update is already running.' >&2
    exit 1
fi

packages=(
    gir1.2-nm-1.0 packagekit-tools bluez xfce4-notifyd xfce4-power-manager
    ffmpeg gir1.2-gtk-3.0 gir1.2-gstreamer-1.0 gstreamer1.0-gtk3
    gstreamer1.0-libav python3-cairo python3-gi-cairo python3-requests
    desktop-file-utils x11-xserver-utils dconf-cli fonts-inter arc-theme papirus-icon-theme
)
missing=()
for package in "${packages[@]}"; do
    status="$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null || true)"
    if [[ "$status" != installed ]]; then
        missing+=("$package")
    fi
done
if (( ${#missing[@]} > 0 )); then
    sudo apt-get update
    sudo apt-get install -y "${missing[@]}"
fi

python3 - "$source_dir" <<'PYTHON'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])
for directory in ("desktop", "ai/agent", "branding"):
    for source in (root / directory).glob("*.py"):
        ast.parse(source.read_text(), filename=str(source))
PYTHON
for script in "$source_dir/desktop/"*.sh "$source_dir/branding/install-login.sh"; do
    bash -n "$script"
done

backup="$(mktemp -d "$state_dir/desktop-backup.XXXXXXXX")"
sudo cp -a /opt/ai/desktop "$backup/desktop"
mkdir -p "$backup/assistant" "$backup/config"
for file in jarvis_gui.py artifacts.py research.py; do
    if [[ -f "/opt/ai/$file" ]]; then
        cp -a "/opt/ai/$file" "$backup/assistant/"
    fi
done
for item in mineos plank tint2 picom gtk-3.0 xfce4 autostart; do
    if [[ -e "$config_dir/$item" ]]; then
        cp -a "$config_dir/$item" "$backup/config/"
    fi
done
if [[ -d "$data_dir/applications" ]]; then
    cp -a "$data_dir/applications" "$backup/applications"
fi
dconf dump /net/launchpad/plank/ > "$backup/plank.dconf"
printf 'Desktop backup: %s\n' "$backup"

stage="$(sudo mktemp -d /opt/ai/.desktop-update.XXXXXXXX)"
cleanup() {
    sudo rm -rf -- "$stage"
}
trap cleanup EXIT
tar --exclude='__pycache__' --exclude='*.pyc' -C "$source_dir/desktop" -cf - . |
    sudo tar --no-same-owner -C "$stage" -xf -
sudo find "$stage" -type d -exec chmod 755 {} +
sudo chmod 755 "$stage/"*.sh
sudo install -m 644 "$source_dir/ai/agent/"{artifacts,research}.py /opt/ai/
sudo install -m 755 "$source_dir/ai/agent/jarvis_gui.py" /opt/ai/jarvis_gui.py
sudo mv -- /opt/ai/desktop "$stage.old"
if ! sudo mv -- "$stage" /opt/ai/desktop; then
    sudo mv -- "$stage.old" /opt/ai/desktop
    exit 1
fi
if ! bash /opt/ai/desktop/apply-theme.sh; then
    sudo mv -- /opt/ai/desktop "$stage"
    sudo mv -- "$stage.old" /opt/ai/desktop
    for file in "$backup/assistant/"*; do
        [[ -f "$file" ]] && sudo cp -a "$file" /opt/ai/
    done
    cp -a "$backup/config/." "$config_dir/"
    if [[ -d "$backup/applications" ]]; then
        cp -a "$backup/applications/." "$data_dir/applications/"
    fi
    dconf load /net/launchpad/plank/ < "$backup/plank.dconf"
    bash /opt/ai/desktop/apply-theme.sh || true
    printf 'Desktop setup failed. The previous desktop code was restored. Configuration backup: %s\n' "$backup" >&2
    exit 1
fi
sudo rm -rf -- "$stage.old"
trap - EXIT
if [[ "$(cat /etc/X11/default-display-manager 2>/dev/null || true)" == /usr/sbin/lightdm ]]; then
    sudo bash "$source_dir/branding/install-login.sh"
fi

printf '%s\n' 'MineOS desktop update installed. Reopen Settings and Assistant to load the new version.'
