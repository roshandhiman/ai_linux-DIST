# MineOS

A standalone AI-powered Linux operating system built with the Linux kernel and drivers, featuring a macOS x Windows 11 hybrid UI, embedded offline Qwen 2.5 1.5B, kernel-level telemetry, and hardware/IoT integration.

## Build Standalone Bootable ISO

Anyone on Debian/Ubuntu can build the complete bootable ISO with a single command:

```bash
git clone https://github.com/roshandhiman/ai_linux-DIST.git
cd ai_linux-DIST
sudo ./build-iso.sh
```

## Features
- **Linux Kernel & Hardware Drivers**: Full Wi-Fi, Bluetooth, GPU, audio, and USB support out-of-the-box.
- **Custom Hybrid Desktop Shell**: macOS top translucent bar + Windows 11 centered floating glass dock.
- **Embedded Offline AI**: Pre-baked Qwen 2.5 1.5B running on a native system daemon without internet.
- **Kernel-Level Integration**: Udev hardware hotplug hooks (`/dev/ai-iot`, ESP32/Arduino) and kernel ring-buffer sentinel (`ai-sentinel.service`).
- **Terminal Copilot**: Native shell execution (`?? <query>`) and kernel error diagnostics.
