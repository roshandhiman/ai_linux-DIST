# JarvisOS (AI-Powered Linux Distro)

> **Next-Gen AI Operating System** based on Debian with embedded offline AI (Qwen 2.5 1.5B), macOS + Windows hybrid UI, IoT/ESP32 & Bluetooth controls, and hot-swappable local models.

---

## 🌟 Key Features

1. **Embedded Offline Intelligence (Jarvis Core)**
   - Powered by **Qwen 2.5 1.5B Instruct** (Q4_K_M GGUF) via native C++ inference.
   - 100% offline — boots ready to think without internet.
   - Hot-swappable models: Switch between models (e.g. Qwen 2.5, Llama 3.2, DeepSeek-R1-Distill) via `jarvis model switch <name>`.

2. **OS Agent & Action Executor**
   - Natural language OS control: `jarvis "open firefox and search debian wiki"`
   - System controls: volume, brightness, battery info, network management.
   - Hardware & IoT: ESP32 / Arduino serial & HTTP integration (lights, fans, sensors) + Bluetooth device pairing.

3. **Hybrid Windows 11 + macOS UI**
   - Centered floating dock / taskbar with rounded corners and frosted glass aesthetic.
   - Global AI Spotlight HUD (summon with `Super + Space`).
   - Clean dark-mode theme with modern icon sets.

4. **1-Click Bootable ISO Generator**
   - Live development mode (test directly in VM).
   - Packaging pipeline: bundles kernel, packages, desktop overlay, model weights, and systemd daemons into a bootable `.iso`.

---

## 🚀 Repository Structure

```
mine-os/
├── ai-agent/                # Jarvis AI Agent runtime & tools
│   ├── jarvis.py            # Main Agent CLI & Tool Orchestrator
│   ├── tools/               # System, App, Bluetooth & ESP32 control plugins
│   ├── models/              # Model download & manager scripts
│   └── service/             # Systemd service units
├── desktop/                 # macOS + Windows hybrid UI configuration
│   ├── theme/               # GTK themes & icon themes
│   ├── panel/               # Centered floating dock & top bar configs
│   └── wallpapers/          # Distro wallpapers & assets
├── builder/                 # ISO builder scripts
│   ├── build-iso.sh         # Live-build / Debootstrap compiler
│   └── packages.list        # Base system package list
└── Makefile                 # Quick workflow shortcuts
```

---

## 🛠️ Quick Commands

- **Live Test on VM:** `make live-sync`
- **Summon Jarvis:** `jarvis "tell me battery and free memory"`
- **Switch Model:** `jarvis model switch qwen-2.5-3b`
- **Build ISO:** `make build-iso`
