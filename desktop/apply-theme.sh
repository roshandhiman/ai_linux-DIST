#!/usr/bin/env bash
# Configure XFCE to have a modern Windows 11 + macOS Hybrid Look
set -euo pipefail

echo "Configuring Modern Windows + macOS Hybrid UI for XFCE..."

# 1. Enable Window Compositor for Shadows & Transparency
xfconf-query -c xfwm4 -p /general/use_compositing -s true || true
xfconf-query -c xfwm4 -p /general/frame_opacity -s 95 || true
xfconf-query -c xfwm4 -p /general/shadow_delta_y -s 3 || true
xfconf-query -c xfwm4 -p /general/shadow_opacity -s 70 || true

# 2. Window title buttons layout: macOS style (Close, Minimize, Maximize on left) or Windows style
# Can be toggled: default modern macOS style on left: "CHM|"
# xfconf-query -c xfwm4 -p /general/button_layout -s "CHM|O" || true

# 3. Add Jarvis shortcut: Super + Space -> jarvis-hud
xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Super>space" -n -t string -s "/usr/local/bin/jarvis-hud" || true
xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Primary>space" -n -t string -s "/usr/local/bin/jarvis-hud" || true

echo "UI Customization Applied!"
