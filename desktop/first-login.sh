#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
if [[ -f "$CONFIG/autostart/mineos-ui.desktop" ]]; then
    exit 0
fi
bash "$DIR/launch-session.sh" --shell-only
exec "$DIR/apply-theme.sh"
