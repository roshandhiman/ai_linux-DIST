#!/usr/bin/env bash
set -euo pipefail
export DISPLAY="${DISPLAY:-:0}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"
DESKTOP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$DESKTOP_DIR/session-processes.sh"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/mineos"
RETIRED_DIR="$STATE_DIR/retired-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RETIRED_DIR" "$CONFIG/tint2" "$CONFIG/picom" "$CONFIG/plank/dock1/launchers" "$CONFIG/autostart" "$CONFIG/gtk-3.0" "$CONFIG/xfce4/terminal" "$DATA/plank/themes/MineOS" "$DATA/applications"
session_stop -f '^(/usr/bin/)?python3 /opt/ai/desktop/mineos_home.py( |$)'
for name in mineos-home mineos-ai mineos-settings mineos-launcher mineos-files org.mineos.Workspace; do
    entry="$DATA/applications/$name.desktop"
    if [[ -f "$entry" ]]; then mv "$entry" "$RETIRED_DIR/"; fi
done
cat > "$DATA/applications/ai.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Assistant
Hidden=true
ENTRY
cp "$DESKTOP_DIR/tint2rc" "$CONFIG/tint2/tint2rc"
cp "$DESKTOP_DIR/picom.conf" "$CONFIG/picom/picom.conf"
cp "$DESKTOP_DIR/ai.desktop" "$DATA/applications/org.mineos.Assistant.desktop"
cat > "$DATA/applications/org.mineos.Trash.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Trash
Exec=thunar trash:///
Icon=/opt/ai/desktop/assets/icons/trash.svg
Terminal=false
Categories=Utility;
NoDisplay=true
ENTRY
cp "$DESKTOP_DIR/launcher.desktop" "$DATA/applications/org.mineos.Apps.desktop"
cp "$DESKTOP_DIR/settings.desktop" "$DATA/applications/org.mineos.Settings.desktop"
cp "$DESKTOP_DIR/companion.desktop" "$DATA/applications/org.mineos.Companion.desktop"
printf '[PlankDockItemPreferences]\nLauncher=file://%s\n' "$DATA/applications/org.mineos.Settings.desktop" > "$CONFIG/plank/dock1/launchers/mineos-settings.dockitem"
printf '[PlankDockItemPreferences]\nLauncher=file://%s\n' "$DATA/applications/org.mineos.Assistant.desktop" > "$CONFIG/plank/dock1/launchers/mineos-assistant.dockitem"
for app in thunar firefox-esr xfce4-terminal org.xfce.mousepad; do
    app_file="/usr/share/applications/$app.desktop"
    if [[ -f "$app_file" ]]; then
        printf '[PlankDockItemPreferences]\nLauncher=file://%s\n' "$app_file" > "$CONFIG/plank/dock1/launchers/$app.dockitem"
    fi
done
printf '[PlankDockItemPreferences]\nLauncher=file://%s\n' "$DATA/applications/org.mineos.Trash.desktop" > "$CONFIG/plank/dock1/launchers/trash.dockitem"
if [[ ! -e "$CONFIG/mineos/appearance.json" ]]; then
    dconf load / < "$DESKTOP_DIR/plank.conf"
    python3 "$DESKTOP_DIR/app_catalog.py" --defaults
else
    python3 "$DESKTOP_DIR/app_catalog.py"
fi
for entry in xfce-settings-manager xfce-backdrop-settings xfce-ui-settings gnome-control-center org.gnome.Settings; do
    install -m 644 "$DESKTOP_DIR/hidden-settings.desktop" "$DATA/applications/$entry.desktop"
done
set_string() { xfconf-query -c "$1" -p "$2" --create -t string -s "$3"; }
set_bool() { xfconf-query -c "$1" -p "$2" --create -t bool -s "$3"; }
set_int() { xfconf-query -c "$1" -p "$2" --create -t int -s "$3"; }
set_string xsettings /Gtk/FontName 'Inter 9'
set_string xsettings /Gtk/MonospaceFontName 'DejaVu Sans Mono 10'
set_string xsettings /Gtk/CursorThemeName Adwaita
set_string xsettings /Gtk/DecorationLayout 'menu:minimize,maximize,close'
set_bool xsettings /Gtk/DialogsUseHeader true
set_string xfwm4 /general/title_font 'Inter Medium 10'
set_string xfwm4 /general/title_alignment center
set_string xfwm4 /general/button_layout '|HMC'
set_bool xfwm4 /general/use_compositing false
set_bool xfce4-session /general/SaveOnExit false
"$DESKTOP_DIR/configure-session.sh"
set_int xfce4-desktop /desktop-icons/style 0
set_bool xfce4-desktop /desktop-menu/show false
set_string xfce4-keyboard-shortcuts '/commands/custom/<Super>space' /opt/ai/desktop/launcher.sh
set_string xfce4-keyboard-shortcuts '/commands/custom/<Super>e' thunar
set_string xfce4-keyboard-shortcuts '/commands/custom/<Super>a' 'python3 /opt/ai/jarvis_gui.py'
set_string xfce4-keyboard-shortcuts '/commands/custom/<Super>i' 'python3 /opt/ai/desktop/settings.py'
set_string thunar /last-view ThunarIconView
set_int thunar /last-window-width 790
set_int thunar /last-window-height 500
set_int thunar /last-separator-position 170
set_bool thunar /last-show-menubar false
set_bool thunar /last-show-statusbar true
set_string thunar /last-location-bar ThunarLocationButtons
set_string thunar /last-side-pane ThunarShortcutsPane
set_string thunar /last-icon-view-zoom-level THUNAR_ZOOM_LEVEL_100_PERCENT
BOOKMARKS="$CONFIG/gtk-3.0/bookmarks"
touch "$BOOKMARKS"
if ! grep -q '^computer:///' "$BOOKMARKS"; then
    printf 'computer:/// This PC\n' >> "$BOOKMARKS"
fi
cat > "$CONFIG/xfce4/terminal/terminalrc" <<'TERMINAL'
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
cat > "$CONFIG/autostart/picom.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Picom
Hidden=true
ENTRY
python3 "$DESKTOP_DIR/preferences.py"
cat > "$CONFIG/autostart/mineos-ui.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Desktop
Exec=$DESKTOP_DIR/launch-session.sh
OnlyShowIn=XFCE;
Terminal=false
ENTRY
update-desktop-database "$DATA/applications" 2>/dev/null || true
session_stop -x xfce4-panel
session_stop -f '^(/usr/bin/)?python3 .*/companion.py$'
session_stop -x tint2
session_stop -x picom
session_stop -x plank
sleep 0.3
"$DESKTOP_DIR/launch-session.sh"
printf 'Desktop settings applied.\n'
