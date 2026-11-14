#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
if [[ -f "$CONFIG/autostart/mineos-ui.desktop" ]]; then
    exit 0
fi
exec "$DIR/apply-theme.sh"
