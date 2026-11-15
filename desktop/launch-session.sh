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
parallels=false
if [[ "$(systemd-detect-virt --vm 2>/dev/null || true)" == parallels ]]; then
    parallels=true
fi
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
glass_display=${DISPLAY%.0}
glass_marker="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/mineos-glass-${glass_display//[^[:alnum:]]/_}"
if [[ -z "$(session_pids -x picom)" ]]; then
    rm -f -- "$glass_marker"
    picom_config="$CONFIG/picom/picom.conf"
    compositor_log="$STATE_DIR/compositor.log"
    picom_args=(--config "$picom_config" --daemon)
    if $parallels; then
        picom_config="$CONFIG/picom/mineos-parallels.conf"
        PYTHONPATH="$DIR" python3 -c 'import preferences; preferences.compositor(preferences.read())'
        xfconf-query -c xfwm4 -p /general/use_compositing -n -t bool -s false
        nohup picom --config "$picom_config" --no-frame-pacing --blur-method none \
            >>"$compositor_log" 2>&1 </dev/null 9>&- &
        sleep 0.3
        if ! kill -0 "$!" 2>/dev/null; then
            picom --config "$picom_config" --backend xrender --blur-method none --daemon \
                >>"$compositor_log" 2>&1 9>&- || true
        fi
    else
        if timeout 4s picom --config "$picom_config" --diagnostics 2>>"$compositor_log" 9>&- |
            awk '/^### Backend:/{glx = ($3 == "glx")} glx && /Accelerated: 1/{hardware = 1} END{exit !hardware}'; then
            if picom "${picom_args[@]}" >>"$compositor_log" 2>&1 9>&-; then
                picom_pid=$(session_pids -x picom)
                if [[ -n "$picom_pid" ]]; then
                    printf '%s\n' "${picom_pid%%$'\n'*}" > "$glass_marker"
                fi
            fi
        fi
        if [[ -z "$(session_pids -x picom)" ]]; then
            picom "${picom_args[@]}" --backend xrender --blur-method none >>"$compositor_log" 2>&1 9>&- || true
        fi
    fi
    if [[ -z "$(session_pids -x picom)" ]]; then
        printf '%s\n' 'Could not start picom. Starting the panel and dock anyway.' >>"$compositor_log"
        xfconf-query -c xfwm4 -p /general/use_compositing -n -t bool -s true
    fi
fi
dock_spacing_process='^(/usr/bin/)?python3 .*/dock_spacing.py '
if [[ "${1:-}" == --restart-dock ]]; then
    session_stop -x plank
    for attempt in {1..20}; do
        [[ -z "$(session_pids -x plank)" ]] && break
        sleep 0.05
    done
    while read -r pid; do
        [[ -n "$pid" ]] && kill -KILL "$pid" 2>/dev/null || true
    done < <(session_pids -x plank)
fi
if [[ -z "$(session_pids -x plank)" ]]; then
    PYTHONPATH="$DIR" python3 -c 'import preferences; preferences.dock(preferences.read())' 9>&- >>"$STATE_DIR/dock.log" 2>&1 || true
    session_stop -f "$dock_spacing_process"
    dock_ready="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/mineos-dock-${glass_display//[^[:alnum:]]/_}"
    rm -f -- "$dock_ready"
    nohup env GDK_SCALE=1 python3 "$DIR/dock_spacing.py" "$dock_ready" >>"$STATE_DIR/dock.log" 2>&1 </dev/null 9>&- &
    for attempt in {1..10}; do
        [[ -e "$dock_ready" ]] && break
        sleep 0.05
    done
    plank_command=(plank)
    if $parallels; then
        plank_command=(env GDK_SCALE=1 plank)
    fi
    nohup "${plank_command[@]}" >>"$STATE_DIR/dock.log" 2>&1 </dev/null 9>&- &
fi
if [[ -z "$(session_pids -f '^(/usr/bin/)?python3 .*/companion.py$')" ]]; then
    nohup nice -n 8 python3 "$DIR/companion.py" >>"$STATE_DIR/companion.log" 2>&1 </dev/null 9>&- &
fi
