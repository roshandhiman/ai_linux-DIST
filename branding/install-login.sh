#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID != 0 ]]; then
    printf '%s\n' 'Run the sign-in theme installer as root.' >&2
    exit 1
fi

SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${1:-/}"
[[ "$ROOT" = /* && -d "$ROOT/etc/lightdm" ]]
ROOT="${ROOT%/}"

ASSETS="$ROOT/usr/share/backgrounds/mineos"
THEME="$ROOT/usr/share/themes/MineOS-Greeter/gtk-3.0"
CONFIG="$ROOT/etc/lightdm/lightdm-gtk-greeter.conf"

install -d -m 755 "$ASSETS" "$THEME"
install -m 644 "$SOURCE/login/"*.svg "$ASSETS/"
install -m 644 "$SOURCE/../desktop/assets/plasma/scarlet-tree.png" "$ASSETS/scarlet-tree.png"
install -m 644 "$SOURCE/login/gtk.css" "$THEME/gtk.css"

if [[ -z "$ROOT" && -e "$CONFIG" ]]; then
    BACKUP="$(mktemp -d /var/backups/mineos-signin-XXXXXXXX)"
    cp -a "$CONFIG" "$BACKUP/"
    printf 'Sign-in backup: %s\n' "$BACKUP"
fi
TEMP="$(mktemp "$ROOT/etc/lightdm/.mineos-greeter-XXXXXXXX")"
trap 'rm -f -- "$TEMP"' EXIT
install -m 644 "$SOURCE/login/greeter.conf" "$TEMP"
mv -Tf "$TEMP" "$CONFIG"
