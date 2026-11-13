# Desktop

A native XFCE/X11 desktop for Debian 13, combining light neutral application windows with a slim charcoal top panel and a compact translucent dock. Thunar is the file manager. There is no custom file-manager dashboard, AI service badge, promotional copy, wallpaper typography, or assistant window at login.

## Apply to an existing desktop

Install this directory at `/opt/ai/desktop` and the assistant at `/opt/ai/jarvis_gui.py`, then run as the desktop user:

```bash
bash /opt/ai/desktop/apply-theme.sh
```

The existing user session must be unlocked to view the result. The script does not unlock a session, build an ISO, or change the kernel.

Required packages include XFCE, Thunar, picom, tint2, Plank, rofi, Arc, Papirus, Inter, dconf, Python 3, requests, and GTK3 introspection. The desktop uses native settings and volume tools. The assistant remains available through application search and Super+A, and uses the existing local Ollama model.

Super+Space opens application search, Super+E opens Files, and Super+I opens Settings. These shortcuts are not displayed as desktop decorations.

The session autostart entry starts the compositor, top panel, and dock once. Old generated dashboard entries and dock launchers are moved into a timestamped folder under `~/.local/state/mineos/` when applying the theme. User files are preserved.

The photograph in `assets/dunes.png` is generated with the built-in imagegen tool. Its prompt is recorded in `assets/wallpaper-prompt.txt`.
