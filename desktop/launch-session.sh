#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/session-processes.sh"
export DISPLAY="${DISPLAY:-:0}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP=XFCE
export XDG_SESSION_DESKTOP=xfce
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/mineos"
mkdir -p "$STATE_DIR"
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/mineos-session-$(id -u)-${DISPLAY//[^[:alnum:]]/_}.lock"
flock -n 9 || exit 0
session_stop -x xfce4-panel
if [[ -z "$(session_pids -x xfdesktop)" ]]; then
    nohup xfdesktop --sm-client-disable >>"$STATE_DIR/desktop.log" 2>&1 </dev/null 9>&- &
fi
if [[ -z "$(session_pids -ix thunar)" ]]; then
    nohup thunar --daemon >>"$STATE_DIR/files.log" 2>&1 </dev/null 9>&- &
fi
if [[ -z "$(session_pids -x tint2)" ]]; then
    nohup tint2 -c "$CONFIG/tint2/tint2rc" >>"$STATE_DIR/bar.log" 2>&1 </dev/null 9>&- &
fi
if [[ -z "$(session_pids -x picom)" ]]; then
    picom_config="$CONFIG/picom/picom.conf"
    compositor_log="$STATE_DIR/compositor.log"
    picom_args=(--config "$picom_config" --daemon)
    # Parallels returns invalid X Present timestamps. Keep GLX VSync, but skip
    # the frame scheduler that depends on those timestamps.
    if grep -qi '^Parallels' /sys/class/dmi/id/sys_vendor 2>/dev/null; then
        picom_args+=(--no-frame-pacing)
    fi
    if timeout 4s picom --config "$picom_config" --diagnostics 2>>"$compositor_log" 9>&- |
        awk '/^### Backend:/{glx = ($3 == "glx")} glx && /Accelerated: 1/{hardware = 1} END{exit !hardware}'; then
        picom "${picom_args[@]}" >>"$compositor_log" 2>&1 9>&- || true
    fi
    if [[ -z "$(session_pids -x picom)" ]] &&
        ! picom "${picom_args[@]}" --backend xrender --blur-method none >>"$compositor_log" 2>&1 9>&-; then
        printf '%s\n' 'Could not start picom. Starting the panel and dock anyway.' >>"$STATE_DIR/compositor.log"
        xfconf-query -c xfwm4 -p /general/use_compositing -n -t bool -s true
    fi
fi
if [[ -z "$(session_pids -x plank)" ]]; then
    nohup plank >>"$STATE_DIR/dock.log" 2>&1 </dev/null 9>&- &
fi
if [[ -z "$(session_pids -f '^(/usr/bin/)?python3 .*/companion.py$')" ]]; then
    nohup nice -n 8 python3 "$DIR/companion.py" >>"$STATE_DIR/companion.log" 2>&1 </dev/null 9>&- &
fi
