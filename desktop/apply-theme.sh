#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
export HOME=/home/roshanpreet
USER_HOME=/home/roshanpreet

echo "[MineOS] Applying flat dark UI..."

mkdir -p "$USER_HOME/.config/tint2"
mkdir -p "$USER_HOME/.config/picom"
mkdir -p "$USER_HOME/.config/plank/dock1/launchers"
mkdir -p "$USER_HOME/.config/autostart"

cp /opt/ai/desktop/tint2rc "$USER_HOME/.config/tint2/tint2rc"
cp /opt/ai/desktop/picom.conf "$USER_HOME/.config/picom/picom.conf"

cat > "$USER_HOME/.config/plank/dock1/launchers/xfce4-terminal.dockitem" << 'EOF'
[PlankDockItemPreferences]
Launcher=file:///usr/share/applications/xfce4-terminal.desktop
EOF

cat > "$USER_HOME/.config/plank/dock1/launchers/thunar.dockitem" << 'EOF'
[PlankDockItemPreferences]
Launcher=file:///usr/share/applications/Thunar.desktop
EOF

cat > "$USER_HOME/.config/plank/dock1/launchers/firefox-esr.dockitem" << 'EOF'
[PlankDockItemPreferences]
Launcher=file:///usr/share/applications/firefox-esr.desktop
EOF

cp /opt/ai/desktop/plank.conf "$USER_HOME/.config/plank/dock1/settings"

ICON_THEME="Papirus-Dark"
GTK_THEME="Adwaita-dark"
xfconf-query -c xsettings -p /Net/IconThemeName -s "$ICON_THEME" 2>/dev/null || true
xfconf-query -c xsettings -p /Net/ThemeName -s "$GTK_THEME" 2>/dev/null || true
xfconf-query -c xsettings -p /Gtk/FontName -s "Inter 10" 2>/dev/null || true
xfconf-query -c xsettings -p /Gtk/CursorThemeName -s "Adwaita" 2>/dev/null || true

xfconf-query -c xfwm4 -p /general/theme -s "Numix" 2>/dev/null || true
xfconf-query -c xfwm4 -p /general/title_font -s "Inter Bold 10" 2>/dev/null || true
xfconf-query -c xfwm4 -p /general/title_alignment -s "center" 2>/dev/null || true
xfconf-query -c xfwm4 -p /general/button_layout -s "O|HMC" 2>/dev/null || true
xfconf-query -c xfwm4 -p /general/use_compositing -s false 2>/dev/null || true

xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitorVirtual-1/workspace0/color-style -s 0 2>/dev/null || true
xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitorVirtual-1/workspace0/rgba1 \
  --create -t double -t double -t double -t double -s 0.039 -s 0.039 -s 0.059 -s 1.0 2>/dev/null || true
xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitorVirtual-1/workspace0/image-style -s 0 2>/dev/null || true

pkill -x picom 2>/dev/null || true
sleep 0.3
picom --config "$USER_HOME/.config/picom/picom.conf" --daemon

pkill -x tint2 2>/dev/null || true
sleep 0.3
tint2 -c "$USER_HOME/.config/tint2/tint2rc" &

pkill -x plank 2>/dev/null || true
sleep 0.3
plank --preferences=/home/roshanpreet/.config/plank/dock1/settings &

pkill -f "jarvis_gui.py" 2>/dev/null || true
sleep 0.5
python3 /opt/ai/jarvis_gui.py &

cat > "$USER_HOME/.config/autostart/mineos-ui.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=MineOS UI
Exec=/opt/ai/desktop/apply-theme.sh
X-GNOME-Autostart-enabled=true
NoDisplay=false
Hidden=false
EOF

echo "[MineOS] Flat UI applied. Desktop transformed."
