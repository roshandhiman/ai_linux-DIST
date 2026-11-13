# MineOS

A Debian-based Linux desktop project with a local Ollama assistant, a terminal agent, and system-monitoring services. Development currently targets Debian 13 ARM64 on Parallels.

The desktop uses XFCE/X11, Thunar, a neutral light GTK theme, a slim charcoal top panel, a compact translucent Plank dock, and a photographic wallpaper. The assistant opens on demand; the desktop does not display service badges, promotional text, or a custom file-manager dashboard.

## Update the live desktop

From the existing checkout, with SSH access to the Debian desktop user:

```bash
make live-desktop
```

Override `VM_HOST` when needed. This target copies only the desktop and graphical assistant and applies the user-session appearance. It does not build an ISO.

Desktop setup and dependencies are documented in [desktop/README.md](desktop/README.md). Desktop runtime packages are listed in `packages.list`.

## Other components

- `ai-agent/jarvis.py`: terminal agent.
- `ai-agent/jarvis_gui.py`: native GTK3 assistant with local model requests and explicit app actions.
- `ai-agent/sentinel.py`: kernel-message monitoring service.
- `rootfs/`: system service and shell integration overlays.

`build-iso.sh` is the earlier image-build prototype. It has not been updated or executed as part of the desktop redesign, and its Openbox setup does not yet reproduce the current XFCE desktop. Use the live Debian VM to review this desktop.
