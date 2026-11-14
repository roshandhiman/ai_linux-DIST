# MineOS

A Debian-based Linux desktop project with a local Ollama assistant, a terminal agent, and system-monitoring services. Development currently targets Debian 13 ARM64 on Parallels.

The desktop uses XFCE/X11, Thunar, neutral light and dark GTK themes, a slim charcoal top panel, a compact translucent Plank dock, and still or live wallpaper. The assistant opens on demand; the desktop does not display service badges, promotional text, or a custom file-manager dashboard.

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

## Startup branding

Run `sudo bash boot/install.sh` on the installed Debian guest to apply the MineOS GRUB label and Plymouth theme. The installer backs up the system label and boot settings before updating the running kernel's initramfs.

## Live ISO

On a native Debian 13 ARM64 or AMD64 build machine, run `sudo bash build-iso.sh /absolute/path/to/MineOS.iso`. The builder creates a separate temporary Debian root and uses the XFCE desktop and MineOS splash from this repository. Building an ISO can use several gigabytes of disk space and downloads packages from Debian.

Set `MINEOS_OLLAMA_DIR` to a trusted Ollama installation tree containing `bin/ollama` and `lib/ollama` to embed the local engine. Set `MINEOS_OLLAMA_MODELS` to its model store to include downloaded model weights. Without the Ollama tree the live desktop starts normally and Assistant needs a local model service.
