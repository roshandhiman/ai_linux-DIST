#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
fi
xfconf-query -c xfce4-session -p /sessions/Failsafe/Count -n -t int -s 2
