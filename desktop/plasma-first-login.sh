#!/usr/bin/env bash
set -euo pipefail

config="${XDG_CONFIG_HOME:-$HOME/.config}"
marker="$config/mineos/plasma-branding-v2"
[[ ! -e "$marker" ]] || exit 0

desktop="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
gdbus wait --session --timeout 30 org.kde.plasmashell
PYTHONPATH="$desktop" python3 -c "import preferences; preferences.terminal_defaults()"
if [[ ! -e "$config/mineos/plasma-initialized" && ! -e "$config/mineos/plasma-branding-v1" ]]; then
    plasma-apply-wallpaperimage "$desktop/assets/plasma/scarlet-tree.png"
fi
panel_ids=$(busctl --user --json=short call org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell evaluateScript s "$(<"$desktop/plasma-panel.js")" |
    python3 -c 'import json, sys; print(json.load(sys.stdin)["data"][0])')
[[ -n "$panel_ids" ]]
systemctl --user stop plasma-plasmashell.service
trap 'systemctl --user start plasma-plasmashell.service' EXIT
while read -r panel launcher; do
    [[ "$panel" =~ ^[0-9]+$ && "$launcher" =~ ^[0-9]+$ ]] || exit 1
    order_args=(--file "$config/plasma-org.kde.plasma.desktop-appletsrc" --group Containments --group "$panel" --group General --key AppletOrder)
    IFS=';' read -r -a applets <<< "$(kreadconfig6 "${order_args[@]}")"
    order="$launcher"
    for applet in "${applets[@]}"; do
        if [[ -n "$applet" && "$applet" != "$launcher" ]]; then
            order+=";$applet"
        fi
    done
    kwriteconfig6 "${order_args[@]}" "$order"
done <<< "$panel_ids"
systemctl --user start plasma-plasmashell.service
trap - EXIT
install -d "$config/mineos"
touch "$marker"
printf '%s\n' 'MineOS desktop ready' | systemd-cat --identifier=mineos-desktop
