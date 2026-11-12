#!/usr/bin/env bash
set -euo pipefail

xfconf-query -c xfwm4 -p /general/use_compositing -s true || true
xfconf-query -c xfwm4 -p /general/frame_opacity -s 95 || true
xfconf-query -c xfwm4 -p /general/shadow_delta_y -s 3 || true
xfconf-query -c xfwm4 -p /general/shadow_opacity -s 70 || true

xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>space" -n -t string -s "/usr/local/bin/ai-hud" || true
xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Primary>space" -n -t string -s "/usr/local/bin/ai-hud" || true
