#!/usr/bin/env bash
set -euo pipefail

assets=/usr/share/backgrounds/mineos
face="$HOME/.face"
config="${XDG_CONFIG_HOME:-$HOME/.config}/kscreenlockerrc"
[[ -r "$assets/account.svg" && -r "$assets/debian-face.sha256" ]] || exit 0

# Existing accounts inherit Debian's logo from /etc/skel. Match the original
# file exactly so this migration never replaces a personal profile image.
read -r stock_face < "$assets/debian-face.sha256"
if [[ -f "$face" && ! -L "$face" && "$(sha256sum < "$face" | cut -d ' ' -f 1)" == "$stock_face" ]]; then
    temp=$(mktemp "$HOME/.mineos-face-XXXXXXXX")
    trap 'rm -f -- "$temp"' EXIT
    install -m 644 "$assets/account.svg" "$temp"
    mv -Tf "$temp" "$face"
fi

# The system default covers accounts with no override. Migrate user-level
# references to Debian's packaged wallpaper and keep user-chosen images.
if [[ -f "$config" ]] && command -v kreadconfig6 >/dev/null; then
    args=(--file "$config" --group Greeter --group Wallpaper --group org.kde.image --group General --key Image)
    image=$(kreadconfig6 "${args[@]}")
    case "${image#file://}" in
        /usr/share/desktop-base/*|/usr/share/wallpapers/DebianTheme/*|/usr/share/wallpapers/DebianTheme|DebianTheme|/etc/alternatives/desktop-background|/etc/alternatives/desktop-plasma5-wallpaper/*|/etc/alternatives/desktop-plasma5-wallpaper)
            kwriteconfig6 "${args[@]}" "file://$assets/graphite.svg"
            ;;
    esac
fi
