#!/usr/bin/env bash
set -euo pipefail

root=${1:-}
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
local_entries="$root/usr/local/share/applications"
install -d "$local_entries"

for entry in "$root"/usr/share/applications/*.desktop; do
    if grep -Eq '^(Name|GenericName|Comment)(\[[^]]+\])?=.*\b(KDE|Plasma)\b' "$entry"; then
        sed -E '/^(Name|GenericName|Comment)(\[[^]]+\])?=/ {
            s/\bKDE Plasma\b/MineOS/g
            s/\b(KDE|Plasma)\b/MineOS/g
        }' "$entry" > "$local_entries/${entry##*/}"
    fi
done

if [[ -f "$root/usr/share/applications/kdesystemsettings.desktop" ]]; then
    install -m 644 "$source_dir/desktop/hidden-settings.desktop" "$local_entries/kdesystemsettings.desktop"
fi
