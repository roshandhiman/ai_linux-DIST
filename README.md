# MineOS

MineOS is a Debian 13–based Linux desktop with built-in AI tools for everyday work. The terminal assistant and AI Camera can run locally on the CPU. MineOS also includes a coding IDE, desktop search, system settings, and live wallpapers.

## Get MineOS

- **Try the live system.** Download the matching architecture from [GitHub Releases](https://github.com/roshandhiman/ai_linux-DIST/releases/latest). Choose ARM64 for Apple Silicon VMs such as Parallels, or AMD64 for Intel and AMD systems. When a release splits the ISO into parts, follow its instructions to join the files and verify the SHA-256 checksum.
- **Update a running installation.** Use the desktop updater below to get the Camera apps and other desktop changes from `main`.

### Update the desktop

Run these commands in MineOS Terminal as a normal user with sudo access. For an existing checkout, use its directory and run the last two commands.

```bash
git clone --branch main https://github.com/roshandhiman/ai_linux-DIST.git ~/mineos-source
cd ~/mineos-source
git pull --ff-only
bash scripts/update-desktop.sh
```

The updater installs missing dependencies, prints a backup path, and downloads the offline camera models if needed. Reopen Camera, Settings, or Assistant after updating. Live sessions without persistent storage lose the update at reboot.

To update live wallpapers separately, run `bash scripts/update-wallpaper.sh` from the checkout and open **Settings → Wallpaper**.

## Camera and AI Camera

Open **Camera** or **AI Camera** from Applications. The two modes share one window.

| Mode | What you can do |
| --- | --- |
| **Camera** | Pick a webcam, take JPG photos, record silent AVI video, or open a local image or video. Captures go to the **MineOS Camera** folder in Pictures. |
| **AI Camera** | See labeled boxes for recognized objects such as people, bottles, and phones. See a skeleton overlay for visible body joints. Use **Ask** for questions about objects, clothing colors, or counts in the current frame. |

Live webcam frames are mirrored left to right. MineOS corrects reversed red and blue channels for the built-in MacBook camera forwarded by Parallels. The preview, captures, and AI all receive the corrected live frames.

OpenCV runs NanoDet for common objects and MediaPipe for hands and body joints. YOLOX-Nano checks closer crops around hands to help recognize small held objects. Live detection runs on a background worker so preview rendering can continue. For general visual questions, the camera can use the local SmolVLM2 model when installed.

The detectors recognize a fixed set of common objects. Labels and pose estimates can be missed when something is cropped, obscured, or hard to see. A whole-video count reports the highest count in up to 12 sampled frames.

## Terminal assistant and IDE

Run `ai` in Terminal for a conversation, or `ai "open the browser"` for a single request. Built-in rules and the local Laya router handle simple requests. More complex requests can go to Qwen2.5 1.5B through llama.cpp. The agent runs generated Python through Bubblewrap, exposes desktop tools through the `mine` API, and asks before actions such as writing files or running commands.

| Command | What it does |
| --- | --- |
| `ai --status` | Checks the model, router, sandbox, and memory |
| `ai --memory` | Lists stored facts |
| `ai --forget <name>` | Removes matching facts |
| `?? show the 5 biggest files here` | Suggests a shell command you can review |

System defaults are in `/etc/mineos/agent.json`. User settings in `~/.config/mineos/agent.json` take precedence. For an optional hosted provider, configure the provider and model in that file and supply its API key through the environment. The terminal assistant stores memory in `~/.local/share/mineos/memory.db` and run logs in `~/.local/state/mineos/runs/`.

The **MineOS IDE** is based on Code - OSS and supports local and hosted models for coding assistance and diff review. [IDE setup](ide/README.md) · [Desktop components](docs/desktop.md)

## Development

| Path | Purpose |
| --- | --- |
| `ai/agent/` | Graphical Assistant, Camera, AI Camera, and desktop context tools |
| `ai/mineos_agent/` | Terminal agent, provider adapters, sandbox tools, and graph memory |
| `ai/fetch-camera-model.sh` | Fetches pinned camera and pose models and checks their SHA-256 hashes |
| `ai/fetch-offline-ai.sh` | Fetches pinned llama.cpp, language, routing, and screen vision models |
| `desktop/` | App launchers, Settings, wallpaper, companion, and session setup |
| `branding/` and `rootfs/` | Startup and sign-in branding, system configuration, and live desktop session |
| `scripts/update-desktop.sh` | In-place desktop updater |
| `scripts/build-iso.sh` | Live-image build script for Debian 13 |

Run the terminal assistant tests from the repository root:

```bash
python3 -m unittest discover -s ai/tests -t ai
```

The tests use a scripted model and can run without a model server. For a test VM, use `make live-desktop VM_HOST=user@guest-address` to sync the desktop and Assistant.

### Build and test a live image

Run the following on a native Debian 13 AMD64 or ARM64 build host. The image build installs the desktop, camera launchers, and camera detection models.

```bash
sudo bash scripts/build-iso.sh /absolute/path/to/MineOS.iso
```

To bundle the offline language, routing, and general vision models, first run `bash ai/fetch-offline-ai.sh /absolute/path/mineos-ai`. Then pass that directory as `MINEOS_AI_DIR` to the builder.

ARM64 images use UEFI. AMD64 images support UEFI and legacy BIOS. The live bootloader is unsigned, so configure Secure Boot accordingly. GitHub Actions builds both architectures and runs an AMD64 boot test. [ISO build workflow](https://github.com/roshandhiman/ai_linux-DIST/actions/workflows/build-iso.yml)
