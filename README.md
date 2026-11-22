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
| **AI Camera** | See labeled boxes for recognized objects such as people, bottles, and phones. See a skeleton overlay for visible body joints. Recognized items are labeled automatically. |

Live webcam frames are mirrored left to right. MineOS corrects reversed red and blue channels for the built-in MacBook camera forwarded by Parallels. The preview, captures, and AI all receive the corrected live frames.

OpenCV supplies fast boxes and MediaPipe body joints. The offline Florence-2 detector adds more specific labels and can name items outside the fast detector’s fixed class list. Analysis runs in the background while the preview keeps playing.

Accuracy depends on lighting, focus, and whether the object is clearly visible. Moving or heavily obscured objects may receive a more general label or be missed.

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

### MineOS Code

Run `ai code` from a project folder. The CLI uses the pinned
[Freebuff direct-provider agent runtime](https://github.com/CodebuffAI/freebuff/tree/91029df68d3cc3b4013091374495a25ee0c6d650/sdk)
with MineOS project tools and provider settings. It can find and read files,
create files, preview edits as diffs, move files to Trash, create a Python
virtual environment or a new `.env`, and run project commands. Writes and
commands ask for terminal approval.

| Command | What it does |
| --- | --- |
| `/providers` | List providers and key status |
| `/model auto` | Use Z.ai, then Groq, custom providers, and the local model |
| `/model local` | Use the on-device model only |
| `/model groq` | Use a specific hosted provider |
| `/apiadd` | Add an HTTPS OpenAI-compatible provider with hidden key entry |
| `/apiremove NAME` | Remove a custom provider |
| `/resume` | Continue the session in this project and model mode |
| `/new` | Clear the current session |

Existing Z.ai and Groq keys load from the environment or MineOS Code’s private
`code.env`. Keys added in the CLI live in the user's private
`code-providers.json` under `~/.config/mineos/`. Provider requests include the
prompt and tool results relevant to the task. The on-device mode keeps these
requests on the machine. Automatic failover retries the pending model request
and preserves completed tool calls.

To build the runtime, install Bun 1.3.14 and run
`scripts/build-code-engine.sh arm64` or `scripts/build-code-engine.sh amd64`.
The desktop updater and image builder install the matching binary from
`build/code/` when it is present. A checkout without the binary still has the Python coding agent.

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

## Mino Deal Review — public CUAD demo

Run `ai dealreview` or `mino dealreview` to open the native review window.
Paste a request and choose **Generate review**. The window reads the original
20 public PDFs, verifies their hashes and quoted pages, calculates notice dates,
and previews the full Markdown draft. **Save report** approves local Markdown
and HTML output in `~/DealRoom`; **View saved report** opens the readable report.
The app never sends a report or document to a model or search provider.

This is a reviewed CUAD demonstration for a **31 March 2027** closing. It uses
reviewed clause annotations and a dated external-research snapshot, rather than
claiming new legal inference or fresh online verification. Changed PDFs or
mismatched quotations stop generation. Other contracts/closing dates require a
new review. Unverified facts and `NOT FOUND - human review` items remain marked.

Install on the existing Debian MineOS desktop:

```bash
bash scripts/install-dealreview.sh --download-demo
ai dealreview
```

The explicit download prepares only the 20 reviewed public PDFs and checks their
SHA-256 hashes. An already prepared `~/DealRoom/Contracts` needs no download.
No ISO build or model download is involved.

Prompt for the graphical Mino assistant or `ai "..."`:

```text
Prepare the CUAD red-flag due diligence demo in ~/DealRoom for the buyer,
closing on 31 March 2027. Review all 20 contracts with exact quotations,
page references, risks and calculated deadlines. Mark missing clauses
NOT FOUND - human review. Preview before saving.
```

For a terminal recording or a read-only verification:

```bash
ai dealreview --cli
ai dealreview --check --json
```

The terminal asks before saving; `--check` generates and validates in memory
without writing a report. Research queries in the output are the historical
preparation log, not searches issued by this offline run.
