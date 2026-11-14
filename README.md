# MineOS

A Debian-based Linux desktop project with a local Ollama assistant, a terminal agent, and system-monitoring services. Development currently targets Debian 13 ARM64 on Parallels.

The desktop uses XFCE/X11, Thunar, neutral light and dark GTK themes, a slim charcoal top panel, a compact translucent Plank dock, and still or live wallpaper. The assistant opens on demand; the desktop does not display service badges, promotional text, or a custom file-manager dashboard.

## Download MineOS 1.0 Live ISO

Open the [MineOS 1.0 GitHub release](https://github.com/roshandhiman/ai_linux-DIST/releases/tag/v1.0.0) and choose the files for your system under **Assets**.

- **ARM64** for Apple Silicon Macs running Parallels and other ARM64 UEFI VMs.
- **AMD64 (x86-64)** for Intel and AMD PCs with UEFI or legacy BIOS.

Download both ISO parts and the SHA-256 checksum for your architecture. Follow the release notes to join the parts and verify the ISO. For development builds, see [GitHub Actions](https://github.com/roshandhiman/ai_linux-DIST/actions/workflows/build-iso.yml).

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

Apply the MineOS sign-in theme with `sudo bash boot/install-login.sh`. LightDM picks it up the next time the sign-in screen opens.

## Build a live ISO

On a native Debian 13 ARM64 or AMD64 build machine, run `sudo bash build-iso.sh /absolute/path/to/MineOS.iso`. The builder creates a separate temporary Debian root and uses the XFCE desktop and MineOS splash from this repository. Building an ISO can use several gigabytes of disk space and downloads packages from Debian.

Set `MINEOS_OLLAMA_DIR` to a trusted Ollama installation tree containing `bin/ollama` and `lib/ollama` to embed the local engine. Set `MINEOS_OLLAMA_MODELS` to its model store to include downloaded model weights. Without the Ollama tree the live desktop starts normally and Assistant needs a local model service.

- **ARM64** boots in an ARM64 UEFI VM, such as Parallels on Apple Silicon.
- **AMD64** boots on 64-bit Intel or AMD PCs, including machines that normally run Windows, and in compatible x86-64 VMs. The image supports UEFI and legacy BIOS. UEFI requires firmware configuration that permits the unsigned live bootloader.

These are live Linux ISOs. The included Ollama engine uses the CPU and comes with Qwen2.5 1.5B for offline chat.
