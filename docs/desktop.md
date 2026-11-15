# Desktop

A native XFCE/X11 desktop for Debian 13, combining light neutral application windows with a slim charcoal top panel and a compact translucent dock. Thunar is the file manager. There is no custom file-manager dashboard, AI service badge, promotional copy, wallpaper typography, or assistant window at login.

## Apply to an existing desktop

Install the repository's `desktop/` directory at `/opt/ai/desktop` and `ai/agent/jarvis_gui.py` at `/opt/ai/jarvis_gui.py`, then run as the desktop user:

```bash
bash /opt/ai/desktop/apply-theme.sh
```

The existing user session must be unlocked to view the result. The script does not unlock a session, build an ISO, or change the kernel.

Required packages include XFCE, Thunar, picom, tint2, Plank, Arc, Papirus, Inter, dconf, Python 3, requests, and GTK3 introspection. The desktop uses native settings and volume tools. The assistant remains available through application search and Super+A, and uses the existing local Ollama model.

Open the Applications grid from Apps in the dock or menu bar. It groups installed apps by category and shows your dock pins. Super+Space opens app search, Super+E opens Files, and Super+I opens Settings. These shortcuts are not displayed as desktop decorations.

The session autostart entry starts the compositor, top panel, and dock once. Old generated dashboard entries and dock launchers are moved into a timestamped folder under `~/.local/state/mineos/` when applying the theme. User files are preserved.

New sessions use a solid background. Open Wallpaper in MineOS Settings to choose a color, picture, or looping video.

Open Settings from the dock or with Super+I. Its sidebar search, back and forward buttons, and General subpages stay in the same window. Display, input, accessibility, notifications, and default app panels are embedded on X11. Network, audio, storage, and updates use NetworkManager, PulseAudio-compatible PipeWire, filesystem statistics, and PackageKit. Appearance controls light and dark GTK themes, blur, and top-bar opacity. Desktop & Dock controls size, placement, opacity, corners, magnification, and auto-hide. Right-click a dock item to pin or unpin it. Wallpaper accepts a picture or a muted looping local video. Desktop Companion controls visibility, size, and motion. Click the companion to open Assistant, or drag it to another part of the screen.

Assistant uses the local Ollama model in Chat and Team modes. Team runs planner, writer, and reviewer passes. Web sends the current query to Wikimedia or Google News, with Brave available for broader searches when the session has a `BRAVE_SEARCH_API_KEY`. The selected model receives the returned excerpts over localhost, and the app shows the source links. File requests can produce HTML, text, Markdown, CSV, or JSON drafts for preview and saving.

About → Startup Animation previews the same frames used by the MineOS Plymouth theme.

The panel and dock start independently of the live wallpaper. MineOS keeps the original video and creates a smaller playback copy in the user cache, then pauses playback when the desktop is covered by a full-size window.
