session_pids() {
    local pid display
    while read -r pid; do
        if [[ -r "/proc/$pid/environ" ]]; then
            display=$(tr '\0' '\n' 2>/dev/null < "/proc/$pid/environ" | sed -n 's/^DISPLAY=//p')
            if [[ "${display%.0}" == "${DISPLAY%.0}" ]]; then
                printf '%s\n' "$pid"
            fi
        fi
    done < <(pgrep -u "$(id -u)" "$@" || true)
}

session_stop() {
    local pid
    while read -r pid; do
        kill "$pid" 2>/dev/null || true
    done < <(session_pids "$@")
}
