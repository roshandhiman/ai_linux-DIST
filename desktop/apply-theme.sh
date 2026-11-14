#!/usr/bin/env bash
set -euo pipefail
export DISPLAY="${DISPLAY:-:0}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"
DESKTOP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/mineos"
RETIRED_DIR="$STATE_DIR/retired-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RETIRED_DIR" "$HOME/.config/tint2" "$HOME/.config/picom" "$HOME/.config/plank/dock1/launchers" "$HOME/.config/autostart" "$HOME/.config/gtk-3.0" "$HOME/.config/xfce4/terminal" "$HOME/.local/share/plank/themes/MineOS" "$HOME/.local/share/applications" "$HOME/.themes/MineOS/xfwm4"
pkill -u "$(id -u)" -f '^(/usr/bin/)?python3 /opt/ai/desktop/mineos_home.py( |$)' 2>/dev/null || true
pkill -u "$(id -u)" -f '^(/usr/bin/)?python3 /opt/ai/jarvis_gui.py( |$)' 2>/dev/null || true
pkill -u "$(id -u)" -x plank 2>/dev/null || true
cp -a "$HOME/.config/plank/dock1/launchers" "$RETIRED_DIR/dock-launchers"
for name in mineos-home mineos-ai mineos-settings mineos-launcher mineos-files org.mineos.Workspace; do
    entry="$HOME/.local/share/applications/$name.desktop"
    if [[ -f "$entry" ]]; then mv "$entry" "$RETIRED_DIR/"; fi
done
for launcher in "$HOME/.config/plank/dock1/launchers/"*.dockitem; do
    [[ -f "$launcher" ]] && mv "$launcher" "$RETIRED_DIR/" || true
done
for name in mineos_home.py ui_base.py status.py; do
    if [[ -f "$DESKTOP_DIR/$name" ]]; then mv "$DESKTOP_DIR/$name" "$RETIRED_DIR/"; fi
done
for name in mineos.svg mine-ai.svg wallpaper.svg; do
    if [[ -f "$DESKTOP_DIR/assets/$name" ]]; then mv "$DESKTOP_DIR/assets/$name" "$RETIRED_DIR/"; fi
done
cat > "$HOME/.local/share/applications/ai.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Assistant
Hidden=true
ENTRY
cp "$DESKTOP_DIR/tint2rc" "$HOME/.config/tint2/tint2rc"
cp "$DESKTOP_DIR/picom.conf" "$HOME/.config/picom/picom.conf"
cp "$DESKTOP_DIR/gtk.css" "$HOME/.config/gtk-3.0/gtk.css"
cp "$DESKTOP_DIR/dock.theme" "$HOME/.local/share/plank/themes/MineOS/dock.theme"
cp -a /usr/share/themes/Arc/xfwm4/. "$HOME/.themes/MineOS/xfwm4/"
printf '\nactive_text_color=#303030\ninactive_text_color=#8b8b8b\n' >> "$HOME/.themes/MineOS/xfwm4/themerc"
cat > "$HOME/.local/share/applications/org.mineos.Assistant.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Assistant
Exec=python3 /opt/ai/jarvis_gui.py
Icon=system-search
Terminal=false
Categories=Utility;
StartupWMClass=MineAI
ENTRY
cat > "$HOME/.local/share/applications/org.mineos.Trash.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Trash
Exec=thunar trash:///
Icon=user-trash
Terminal=false
Categories=Utility;
ENTRY
for app in thunar firefox-esr xfce4-terminal org.xfce.mousepad xfce-settings-manager; do
    app_file="/usr/share/applications/$app.desktop"
    if [[ -f "$app_file" ]]; then
        printf '[PlankDockItemPreferences]\nLauncher=file://%s\n' "$app_file" > "$HOME/.config/plank/dock1/launchers/$app.dockitem"
    fi
done
printf '[PlankDockItemPreferences]\nLauncher=file://%s\n' "$HOME/.local/share/applications/org.mineos.Trash.desktop" > "$HOME/.config/plank/dock1/launchers/trash.dockitem"
dconf load / < "$DESKTOP_DIR/plank.conf"
gsettings set net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/ dock-items "['thunar.dockitem', 'firefox-esr.dockitem', 'xfce4-terminal.dockitem', 'org.xfce.mousepad.dockitem', 'xfce-settings-manager.dockitem', 'trash.dockitem']"
set_string() { xfconf-query -c "$1" -p "$2" --create -t string -s "$3"; }
set_bool() { xfconf-query -c "$1" -p "$2" --create -t bool -s "$3"; }
set_int() { xfconf-query -c "$1" -p "$2" --create -t int -s "$3"; }
set_string xsettings /Net/ThemeName Arc
set_string xsettings /Net/IconThemeName Papirus
set_string xsettings /Gtk/FontName 'Inter 9'
set_string xsettings /Gtk/MonospaceFontName 'DejaVu Sans Mono 10'
set_string xsettings /Gtk/CursorThemeName Adwaita
set_string xsettings /Gtk/DecorationLayout 'menu:minimize,maximize,close'
set_bool xsettings /Gtk/DialogsUseHeader true
set_string xfwm4 /general/theme MineOS
set_string xfwm4 /general/title_font 'Inter Medium 10'
set_string xfwm4 /general/title_alignment center
set_string xfwm4 /general/button_layout '|HMC'
set_bool xfwm4 /general/use_compositing false
set_int xfwm4 /general/workspace_count 1
set_bool xfce4-session /general/SaveOnExit false
xfconf-query -c xfce4-session -p /sessions/Failsafe/Client2_Command --force-array -t string -s /usr/bin/true
set_int xfce4-desktop /desktop-icons/style 0
while IFS= read -r property; do
    case "$property" in
        */last-image) set_string xfce4-desktop "$property" "$DESKTOP_DIR/assets/dunes.png" ;;
        */image-style) set_int xfce4-desktop "$property" 5 ;;
    esac
done < <(xfconf-query -c xfce4-desktop -l)
set_string xfce4-keyboard-shortcuts '/commands/custom/<Super>space' /opt/ai/desktop/launcher.sh
set_string xfce4-keyboard-shortcuts '/commands/custom/<Super>e' thunar
set_string xfce4-keyboard-shortcuts '/commands/custom/<Super>a' 'python3 /opt/ai/jarvis_gui.py'
set_string xfce4-keyboard-shortcuts '/commands/custom/<Super>i' xfce4-settings-manager
set_string thunar /last-view ThunarIconView
set_int thunar /last-window-width 790
set_int thunar /last-window-height 500
set_int thunar /last-separator-position 170
set_bool thunar /last-show-menubar false
set_bool thunar /last-show-statusbar true
set_string thunar /last-location-bar ThunarLocationButtons
set_string thunar /last-side-pane ThunarShortcutsPane
set_string thunar /last-icon-view-zoom-level THUNAR_ZOOM_LEVEL_100_PERCENT
BOOKMARKS="$HOME/.config/gtk-3.0/bookmarks"
touch "$BOOKMARKS"
if ! grep -q '^computer:///' "$BOOKMARKS"; then
    printf 'computer:/// This PC\n' >> "$BOOKMARKS"
fi
cat > "$HOME/.config/xfce4/terminal/terminalrc" <<'TERMINAL'
[Configuration]
FontName=DejaVu Sans Mono 10
MiscMenubarDefault=FALSE
MiscToolbarDefault=FALSE
MiscBordersDefault=TRUE
ColorForeground=#e9e9e9
ColorBackground=#252525
ColorCursor=#ffffff
BackgroundMode=TERMINAL_BACKGROUND_SOLID
TERMINAL
cat > "$HOME/.config/autostart/picom.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Picom
Hidden=true
ENTRY
cat > "$HOME/.config/autostart/mineos-ui.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Desktop
Exec=/opt/ai/desktop/launch-session.sh
OnlyShowIn=XFCE;
Terminal=false
ENTRY
chmod +x "$DESKTOP_DIR/apply-theme.sh" "$DESKTOP_DIR/launch-session.sh" "$DESKTOP_DIR/launcher.sh"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
pkill -u "$(id -u)" -x xfce4-panel 2>/dev/null || true
pkill -u "$(id -u)" -x tint2 2>/dev/null || true
pkill -u "$(id -u)" -x picom 2>/dev/null || true
sleep 0.3
"$DESKTOP_DIR/launch-session.sh"
printf 'Desktop settings applied.\n'
