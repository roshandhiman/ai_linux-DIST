# MineOS

A Debian-based Linux desktop project with an offline AI assistant (llama.cpp serving Qwen2.5 1.5B), a terminal agent that can act on the desktop safely, and system-monitoring services. Development currently targets Debian 13 ARM64 on Parallels.

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

## The terminal assistant: `ai`

Open Terminal and type `ai` for a session, or `ai "open the browser"` for one request.

```text
mine> volume 40
Volume set to 40%.
mine> find my pdf files in downloads and tell me the biggest
  > code
    | files = mine.find_files("*.pdf", "downloads")
    | ...
The biggest is ~/Downloads/report.pdf (2.4 MB).
mine> remember that my sister is Priya
Got it, I'll remember: user -sister-> priya
```

How a request is handled:

1. **Router (tier 1).** Rules spot exact requests first: open an app or site, search, volume, time, system status, remember and recall. These run straight away. When the rules are unsure, [Laya](https://huggingface.co/convaiinnovations/laya) decides. Laya is a multilingual decision encoder served locally by `laya-serve` on `127.0.0.1:8090`. It answers one multiple-choice question (chat, system status, time, memory, or an action) with a probability for each option, so it works for requests typed in Hindi too. A Laya verdict of at least 0.85 picks the route; a doubtful one sends the request to tier 2. A request that names a file, folder, app or device always goes to tier 2 without asking Laya. Laya only chooses a route, so it can never trigger an action that needs your OK. If its service is down, the rules carry on alone.

   Measured on 41 English, Hindi and Hinglish requests (about 0.25 s per Laya answer on a laptop CPU): the rules alone answered 15 on the fast path; rules plus Laya answered 26, sent 14 to tier 2 (slower but still correct), and gave 1 wrong fast route ("the difference between RAM and ROM" read as a memory question). Laya is used without fine-tuning, so expect some mistakes on phrasings it has not seen.
2. **Language model (tier 2).** Anything else goes to Qwen2.5 1.5B, served by `llama-server` on `127.0.0.1:8080`. The model has one tool: it writes short Python. That Python runs in a sandbox (a separate process under `bubblewrap`: no network, read-only system, no `open`/`os`/`subprocess`). It reaches the computer only through the `mine` API, for example `mine.open_app`, `mine.list_dir`, `mine.system_status` and `mine.remember`.
3. **Two loops.** The outer loop counts steps that ran. Inside each step, the inner loop lets the model fix a broken block (syntax error, refused import, crash) and sees only its latest mistake.
4. **Your OK for anything that changes things.** Writing or trashing files, running a command, or talking to a USB device stops and shows the exact action, then waits for `y`. File access is limited to your home folder, with `.ssh`, browser profiles and the assistant's own settings excluded.
5. **Graph memory.** Facts you tell it are stored as `subject -relation-> object` in `~/.local/share/mineos/memory.db`. Recall follows one link, so "my sister is Priya" and "Priya lives in Pune" together answer "where does my sister live".

| Command | What it does |
| --- | --- |
| `ai --status` | Is the model server up, which router, which sandbox, how much memory |
| `ai --memory` / `ai --forget priya` | Show or delete what it remembers |
| `ai -q ...` | Hide the step-by-step trace |
| `?? show the 5 biggest files here` | Suggests one shell command for you to edit or run |
| `sudo systemctl status mineos-llm` | The local model server |
| `sudo systemctl status mineos-router` | The Laya router service |

Settings live in `/etc/mineos/agent.json`; your own changes go in `~/.config/mineos/agent.json`, which takes priority. To use a hosted model instead of the local one, set `llm.base_url`, `llm.model` and `llm.api_key` there (any OpenAI-compatible API) and run `chmod 600` on the file. To use the rules without Laya, set `"router": {"url": null}`. Without a key, nothing leaves the machine. Every request is logged to `~/.local/state/mineos/runs/` for debugging.

Run the assistant's tests from the repository root with `python3 -m unittest discover -s ai/tests -t ai`. They use a scripted fake model, so they need no server.

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
  mineos_agent/        The `ai` terminal assistant: router, sandboxed Python tool, mine API, graph memory
  tests/               Unit tests for mineos_agent (fake model, no server needed)
  agent/               jarvis_gui.py (graphical Assistant), sentinel.py, research.py, older jarvis.py and tools/
  system/              llama.cpp and sentinel systemd units, `ai` launcher, agent.json, shell hook, ESP32 udev rule
  fetch-offline-ai.sh  Downloads the pinned llama.cpp server, Qwen2.5 1.5B GGUF and Laya router, and verifies their checksums
  laya-requirements.txt  Exact Python package versions for the Laya router (installed into /opt/laya)
  download-model.sh    Downloads a GGUF model manually (not used by the build)
docs/                desktop.md: desktop setup, dependencies and components
Makefile             Shortcuts for ISO builds and pushing changes to a test VM
```

The source layout differs from the installed layout:

| Source | Installed path |
| --- | --- |
| `ai/agent/*` | `/opt/ai/` |
| `ai/mineos_agent/` | `/opt/ai/mineos_agent/` |
| `ai/system/ai` | `/usr/local/bin/ai` |
| `ai/system/agent.json` | `/etc/mineos/agent.json` |
| `ai/system/ai-shell.sh` | `/etc/profile.d/mineos-ai.sh` |
| `desktop/` | `/opt/ai/desktop/` |
| llama.cpp release (fetched) | `/opt/llama.cpp/` |
| Qwen2.5 1.5B GGUF (fetched) | `/usr/share/mineos/models/` |
| `ai/system/mineos-llm.service` | `/etc/systemd/system/` (only when the ISO embeds the model) |
| Laya multilingual checkpoint (fetched) | `/usr/share/mineos/models/laya-multilingual/` |
| Laya and its Python packages (fetched wheels) | `/opt/laya/` (a separate Python environment) |
| `ai/system/mineos-router.service` | `/etc/systemd/system/` (only when the ISO embeds the models) |
| `rootfs/etc/lightdm/lightdm.conf.d/live.conf` | `/etc/lightdm/lightdm.conf.d/40-mineos.conf` |
| `rootfs/boot/grub/grub.cfg` | The ISO boot menu (`/boot/grub/grub.cfg` on the image) |

The sentinel service, udev rule and sysctl tuning are not part of the ISO build. `make live-sync` installs them on a test VM.

## Make targets

| Target | What it does |
| --- | --- |
| `make iso ISO=/absolute/path/MineOS.iso` | Builds a live ISO on a Debian 13 host |
| `make boot-test ISO=MineOS-1.0-amd64.iso` | Boots an amd64 ISO in headless QEMU and waits for the desktop |
| `make live-sync` | Copies the agent, shell hook, sysctl, udev and sentinel files to the test VM |
| `make live-desktop` | Copies the desktop and Assistant to the test VM and reapplies the theme |
| `make live-hud` | Starts the Assistant on the test VM display |
| `make test-ai` | Checks the assistant on the test VM (`ai --status` and one request) |
| `make test-agent` | Runs the assistant unit tests locally |

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

To embed the offline model, run `bash ai/fetch-offline-ai.sh /absolute/path/mineos-ai` first. It downloads llama.cpp release b11571, the Qwen2.5 1.5B Instruct Q4_K_M GGUF (about 1.1 GB) and the Laya multilingual checkpoint (about 0.7 GB), and checks every file against pinned SHA-256 sums. It also downloads the router's Python packages (CPU-only PyTorch, transformers, laya) at the exact versions in `ai/laya-requirements.txt`. Together they add roughly 2 GB to the ISO, and the VM needs about 6 GB of RAM to run both models. Then build with `MINEOS_AI_DIR=/absolute/path/mineos-ai`. Without it, the live desktop starts normally and `ai` still handles simple requests, but anything that needs the language model reports that the server is not running.

- **ARM64** boots in an ARM64 UEFI VM, such as Parallels on Apple Silicon.
- **AMD64** boots on 64-bit Intel or AMD PCs, including machines that normally run Windows, and in compatible x86-64 VMs. The image supports UEFI and legacy BIOS. UEFI requires firmware configuration that permits the unsigned live bootloader.

These are live Linux ISOs. The included llama.cpp server runs Qwen2.5 1.5B on the CPU, fully offline.

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
