#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID != 0 ]]; then
    printf '%s\n' 'Run the sign-in and lock screen theme installer as root.' >&2
    exit 1
fi

SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${1:-/}"
[[ "$ROOT" = /* && -d "$ROOT/etc/lightdm" ]]
ROOT="${ROOT%/}"

ASSETS="$ROOT/usr/share/backgrounds/mineos"
THEME="$ROOT/usr/share/themes/MineOS-Greeter/gtk-3.0"
CONFIG="$ROOT/etc/lightdm/lightdm-gtk-greeter.conf"
LOCK_CONFIG="$ROOT/etc/xdg/kscreenlockerrc"
FACE="$ROOT/etc/skel/.face"

if [[ -z "$ROOT" ]]; then
    BACKUP="$(mktemp -d /var/backups/mineos-signin-XXXXXXXX)"
    for file in "$CONFIG" "$LOCK_CONFIG" "$FACE"; do
        if [[ -e "$file" || -L "$file" ]]; then
            cp -a "$file" "$BACKUP/"
        fi
    done
    printf 'Sign-in backup: %s\n' "$BACKUP"
fi

install -d -m 755 "$ASSETS" "$THEME" "$ROOT/etc/xdg" "$ROOT/etc/skel"
install -m 644 "$SOURCE/login/"*.svg "$ASSETS/"
install -m 644 "$SOURCE/login/debian-face.sha256" "$ASSETS/"
install -m 644 "$SOURCE/../desktop/assets/graphite.svg" "$ASSETS/graphite.svg"
install -m 644 "$SOURCE/login/gtk.css" "$THEME/gtk.css"

if [[ -f "$LOCK_CONFIG" ]]; then
    if [[ -n "$ROOT" ]]; then
        write_config=(chroot "$ROOT" /usr/bin/kwriteconfig6)
    else
        write_config=(kwriteconfig6)
    fi
    "${write_config[@]}" --file /etc/xdg/kscreenlockerrc --group Greeter --key WallpaperPlugin org.kde.image
    "${write_config[@]}" --file /etc/xdg/kscreenlockerrc --group Greeter --group Wallpaper \
        --group org.kde.image --group General --key Image file:///usr/share/backgrounds/mineos/graphite.svg
else
    install -m 644 "$SOURCE/login/kscreenlockerrc" "$LOCK_CONFIG"
fi

read -r STOCK_FACE < "$SOURCE/login/debian-face.sha256"
if [[ ! -L "$FACE" ]] && { [[ ! -e "$FACE" ]] || [[ "$(sha256sum < "$FACE" | cut -d ' ' -f 1)" == "$STOCK_FACE" ]]; }; then
    install -m 644 "$ASSETS/account.svg" "$FACE"
fi
TEMP="$(mktemp "$ROOT/etc/lightdm/.mineos-greeter-XXXXXXXX")"
trap 'rm -f -- "$TEMP"' EXIT
install -m 644 "$SOURCE/login/greeter.conf" "$TEMP"
mv -Tf "$TEMP" "$CONFIG"
