# MineOS

A Debian-based Linux desktop project with a local Ollama assistant, a terminal agent, and system-monitoring services. Development currently targets Debian 13 ARM64 on Parallels.

The desktop uses XFCE/X11, Thunar, neutral light and dark GTK themes, a slim charcoal top panel, a compact translucent Plank dock, and still or live wallpaper. The assistant opens on demand; the desktop does not display service badges, promotional text, or a custom file-manager dashboard.

## Download MineOS 1.0 Live ISO

Open the [MineOS 1.0 GitHub release](https://github.com/roshandhiman/ai_linux-DIST/releases/tag/v1.0.0) and choose the files for your system under **Assets**.

- **ARM64** for Apple Silicon Macs running Parallels and other ARM64 UEFI VMs.
- **AMD64 (x86-64)** for Intel and AMD PCs with UEFI or legacy BIOS.

Download both ISO parts and the SHA-256 checksum for your architecture. Follow the release notes to join the parts and verify the ISO. For development builds, see [GitHub Actions](https://github.com/roshandhiman/ai_linux-DIST/actions/workflows/build-iso.yml).

## Update an existing MineOS desktop

Open Terminal inside the running MineOS desktop (in your VM or on your PC). Use your normal account with sudo access.

First time downloading the source:

```bash
git clone --branch main https://github.com/roshandhiman/ai_linux-DIST.git ~/mineos-source
cd ~/mineos-source
bash scripts/update-desktop.sh
```

For later updates from the same checkout:

```bash
cd ~/mineos-source
git pull --ff-only
bash scripts/update-desktop.sh
```

The script installs any missing desktop dependencies, saves a backup, and applies the latest launcher, dock, Settings, companion and graphical Assistant. The update keeps home files, installed models, and your saved wallpaper and dock preferences. Reopen Settings or Assistant if either was already open. The script prints the backup path.

On a system installed to disk, the update survives reboot. If you booted the old live ISO, the update only lasts for the current session unless you configured persistence for the system. To keep the new desktop with a live ISO, get the latest successful [Build MineOS ISOs run](https://github.com/roshandhiman/ai_linux-DIST/actions/workflows/build-iso.yml?query=branch%3Amain+is%3Asuccess), unzip the ARM64 or x86-64 artifact, and attach the new ISO to your VM.

For development over SSH, `make live-desktop` uses `VM_HOST` to select a test VM. Desktop setup and dependencies are documented in [docs/desktop.md](docs/desktop.md).

## Repository layout

```
VERSION              The MineOS version. Used for ISO names, artifacts and /etc/os-release
.github/workflows/   build-iso.yml (CI ISO builds for amd64 and arm64, amd64 boot test), publish-iso.yml (release upload)
scripts/             build-iso.sh (live ISO builder), boot-test.sh (headless QEMU boot test), update-desktop.sh (in-place desktop updater)
config/              packages.list: architecture-neutral Debian packages installed into the image
desktop/             XFCE desktop: launcher, dock, Settings, companion, themes. Installed as-is to /opt/ai/desktop
branding/            Startup and sign-in branding
  install-startup.sh   Applies the GRUB label and Plymouth theme
  install-login.sh     Applies the LightDM sign-in theme
  plymouth/            Plymouth boot animation theme
  login/               LightDM greeter config, CSS and artwork
  render_frames.py     Renders the boot animation frames
rootfs/              Files copied into the image (GRUB menu, LightDM live session, sysctl tuning)
ai/                  Everything AI-related, kept separate from the OS
  agent/               jarvis.py (terminal agent), jarvis_gui.py (Assistant), sentinel.py, tools/
  system/              Ollama and sentinel systemd units, shell hook, ESP32 udev rule and handler
  fetch-offline-ai.sh  Downloads the verified Ollama engine and Qwen2.5 model for CI builds
  download-model.sh    Downloads a GGUF model manually (not used by the build)
docs/                desktop.md: desktop setup, dependencies and components
Makefile             Shortcuts for ISO builds and pushing changes to a test VM
```

The source layout differs from the installed layout:

| Source | Installed path |
| --- | --- |
| `ai/agent/*` | `/opt/ai/` |
| `desktop/` | `/opt/ai/desktop/` |
| `ai/system/ai-core.service` | `/etc/systemd/system/` (only when the ISO embeds Ollama) |
| `rootfs/etc/lightdm/lightdm.conf.d/live.conf` | `/etc/lightdm/lightdm.conf.d/40-mineos.conf` |
| `rootfs/boot/grub/grub.cfg` | The ISO boot menu (`/boot/grub/grub.cfg` on the image) |

The sentinel service, shell hook, udev rule and sysctl tuning are not part of the ISO build. `make live-sync` installs them on a test VM.

## Make targets

| Target | What it does |
| --- | --- |
| `make iso ISO=/absolute/path/MineOS.iso` | Builds a live ISO on a Debian 13 host |
| `make boot-test ISO=MineOS-1.0-amd64.iso` | Boots an amd64 ISO in headless QEMU and waits for the desktop |
| `make live-sync` | Copies the agent, shell hook, sysctl, udev and sentinel files to the test VM |
| `make live-desktop` | Copies the desktop and Assistant to the test VM and reapplies the theme |
| `make live-hud` | Starts the Assistant on the test VM display |
| `make test-ai` | Runs a sample prompt through the terminal agent on the test VM |

The VM targets use `VM_HOST` and `REMOTE_DIR`. Override them per run, for example `make live-desktop VM_HOST=user@10.0.0.5`.

## Working on Windows

Everything in this repository runs on Linux. `.gitattributes` keeps LF line endings so shell scripts do not fail with `$'\r': command not found`. If you cloned before `.gitattributes` existed, run this once:

```bash
git add --renormalize .
```

## Startup branding

Run `sudo bash branding/install-startup.sh` on the installed Debian guest to apply the MineOS GRUB label and Plymouth theme. The installer backs up the system label and boot settings before updating the running kernel's initramfs.

Apply the MineOS sign-in theme with `sudo bash branding/install-login.sh`. LightDM picks it up the next time the sign-in screen opens.

## Build a live ISO

On a native Debian 13 ARM64 or AMD64 build machine, run `sudo bash scripts/build-iso.sh /absolute/path/to/MineOS.iso` (or `make iso ISO=/absolute/path/to/MineOS.iso`). The builder creates a separate temporary Debian root and uses the XFCE desktop and MineOS splash from this repository. Building an ISO can use several gigabytes of disk space and downloads packages from Debian.

Set `MINEOS_OLLAMA_DIR` to a trusted Ollama installation tree containing `bin/ollama` and `lib/ollama` to embed the local engine. Set `MINEOS_OLLAMA_MODELS` to its model store to include downloaded model weights. Without the Ollama tree the live desktop starts normally and Assistant needs a local model service.

- **ARM64** boots in an ARM64 UEFI VM, such as Parallels on Apple Silicon.
- **AMD64** boots on 64-bit Intel or AMD PCs, including machines that normally run Windows, and in compatible x86-64 VMs. The image supports UEFI and legacy BIOS. UEFI requires firmware configuration that permits the unsigned live bootloader.

These are live Linux ISOs. The included Ollama engine uses the CPU and comes with Qwen2.5 1.5B for offline chat.

To release a new version, change the number in `VERSION`. The ISO name, the CI artifact and `/etc/os-release` all follow it. Every CI build boots the amd64 ISO in QEMU and fails if the desktop does not start. The serial log is uploaded as the `boot-test-log-amd64` artifact.

## Run MineOS in a virtual machine

The image includes guest tools for VMware (`open-vm-tools-desktop`) and QEMU/UTM (`spice-vdagent`), which resize the screen with the window and share the clipboard. Debian does not ship VirtualBox Guest Additions, so in VirtualBox MineOS switches to the largest screen mode up to 1920x1080 on login.

| Setting | VirtualBox | VMware Workstation |
| --- | --- | --- |
| Type | Linux, Debian (64-bit) | Debian 12.x 64-bit or later |
| Memory and CPUs | 4096 MB, 2 CPUs | 4 GB, 2 CPUs |
| Display | VMSVGA, 128 MB video memory, 3D acceleration off | Defaults |
| Firmware | BIOS (default) or EFI. Secure Boot off | BIOS or UEFI. Secure Boot off |

Attach the ISO as the optical drive and start the VM. Use full-screen mode (VirtualBox: Host+F) when presenting.
