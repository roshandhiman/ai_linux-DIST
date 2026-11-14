#!/usr/bin/env bash
set -euo pipefail
export DISPLAY="${DISPLAY:-:0}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP=XFCE
export XDG_SESSION_DESKTOP=xfce
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/mineos"
mkdir -p "$STATE_DIR"
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/mineos-session-$(id -u).lock"
flock -n 9 || exit 0
pkill -u "$(id -u)" -x xfce4-panel 2>/dev/null || true
if ! pgrep -u "$(id -u)" -x picom >/dev/null; then
    if ! picom --config "$HOME/.config/picom/picom.conf" --daemon >>"$STATE_DIR/compositor.log" 2>&1 9>&- &&
        ! picom --backend xrender --blur-method none --config "$HOME/.config/picom/picom.conf" --daemon >>"$STATE_DIR/compositor.log" 2>&1 9>&-; then
        printf '%s\n' 'Could not start picom. Starting the panel and dock anyway.' >>"$STATE_DIR/compositor.log"
    fi
fi
if ! pgrep -u "$(id -u)" -x tint2 >/dev/null; then
    nohup tint2 -c "$HOME/.config/tint2/tint2rc" >>"$STATE_DIR/bar.log" 2>&1 </dev/null 9>&- &
fi
if ! pgrep -u "$(id -u)" -x plank >/dev/null; then
    nohup plank >>"$STATE_DIR/dock.log" 2>&1 </dev/null 9>&- &
fi
if ! pgrep -u "$(id -u)" -f '^(/usr/bin/)?python3 /opt/ai/desktop/companion.py$' >/dev/null; then
    nohup python3 /opt/ai/desktop/companion.py >>"$STATE_DIR/companion.log" 2>&1 </dev/null 9>&- &
fi
