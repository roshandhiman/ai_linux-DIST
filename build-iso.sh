#!/usr/bin/env bash
set -euo pipefail

ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64)
        DEB_ARCH="amd64"
        KERNEL_PKG="linux-image-amd64"
        GRUB_PKG="grub-efi-amd64-bin grub-pc-bin"
        ;;
    aarch64|arm64)
        DEB_ARCH="arm64"
        KERNEL_PKG="linux-image-arm64"
        GRUB_PKG="grub-efi-arm64-bin"
        ;;
    *)
        echo "Unsupported architecture: ${ARCH}"
        exit 1
        ;;
esac

WORK_DIR="/tmp/mineos-iso-build"
ROOTFS="${WORK_DIR}/rootfs"
ISO_DIR="${WORK_DIR}/iso"
OUTPUT_ISO="$(pwd)/MineOS-1.0-${DEB_ARCH}.iso"

echo "=== Step 1: Installing Host Build Tools ==="
sudo apt-get update -qq
sudo apt-get install -y -qq debootstrap squashfs-tools xorriso mtools dosfstools grub-common ${GRUB_PKG} curl jq

echo "=== Step 2: Bootstrapping Base Linux Filesystem (${DEB_ARCH}) ==="
sudo rm -rf "${WORK_DIR}"
mkdir -p "${ROOTFS}" "${ISO_DIR}/live" "${ISO_DIR}/boot/grub"

sudo debootstrap --arch="${DEB_ARCH}" --variant=minbase trixie "${ROOTFS}" http://deb.debian.org/debian/

echo "=== Step 3: Installing Kernel, Drivers, Display & Audio Stack ==="
sudo chroot "${ROOTFS}" /bin/bash -c "
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    ${KERNEL_PKG} \
    systemd systemd-sysv udev kmod \
    firmware-linux-free \
    network-manager network-manager-gnome wireless-tools wpasupplicant \
    bluetooth bluez \
    pipewire pipewire-pulse wireplumber alsa-utils \
    xserver-xorg xinit xterm \
    openbox tint2 plank compton feh \
    firefox-esr thunar \
    python3 python3-tk python3-pip python3-serial \
    curl wget git htop sudo jq fcntl

useradd -m -s /bin/bash -G sudo,video,audio,plugdev,dialout mineos
echo 'mineos:mineos' | chpasswd
echo 'mineos ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/mineos
"

echo "=== Step 4: Embedding Offline AI Core (Ollama + Qwen 2.5 1.5B) ==="
sudo chroot "${ROOTFS}" /bin/bash -c "
curl -fsSL https://ollama.com/install.sh | sh
mkdir -p /usr/share/ollama/.ollama/models
"

if [ -d "/usr/share/ollama/.ollama/models/blobs" ]; then
    sudo cp -rn /usr/share/ollama/.ollama/models/* "${ROOTFS}/usr/share/ollama/.ollama/models/" || true
elif [ -d "${HOME}/.ollama/models/blobs" ]; then
    sudo cp -rn ${HOME}/.ollama/models/* "${ROOTFS}/usr/share/ollama/.ollama/models/" || true
fi

sudo chroot "${ROOTFS}" /bin/bash -c "
chown -R ollama:ollama /usr/share/ollama/.ollama || true
systemctl enable ollama
"

echo "=== Step 5: Injecting Custom macOS + Windows 11 Shell & AI Core ==="
sudo mkdir -p "${ROOTFS}/opt/ai"
sudo cp -r ai-agent/* "${ROOTFS}/opt/ai/"
sudo ln -sf /opt/ai/jarvis.py "${ROOTFS}/usr/local/bin/ai"
sudo ln -sf /opt/ai/jarvis_gui.py "${ROOTFS}/usr/local/bin/ai-hud"
sudo chmod +x "${ROOTFS}/usr/local/bin/ai" "${ROOTFS}/usr/local/bin/ai-hud" "${ROOTFS}"/opt/ai/*.py

sudo cp -r rootfs/* "${ROOTFS}/" || true

sudo mkdir -p "${ROOTFS}/home/mineos/.config/openbox"
sudo mkdir -p "${ROOTFS}/home/mineos/.config/tint2"
sudo mkdir -p "${ROOTFS}/home/mineos/.config/plank/dock1/launchers"

cat << 'EOF' | sudo tee "${ROOTFS}/home/mineos/.config/openbox/autostart"
feh --bg-fill /usr/share/backgrounds/mineos-dark.png || true
compton -b --shadow-radius 12 --shadow-opacity 0.7 --active-opacity 0.98 --inactive-opacity 0.95 || true
tint2 &
plank &
python3 /opt/ai/jarvis_gui.py &
EOF
sudo chmod +x "${ROOTFS}/home/mineos/.config/openbox/autostart"

cat << 'EOF' | sudo tee "${ROOTFS}/home/mineos/.config/openbox/rc.xml"
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <keyboard>
    <keybind key="W-space">
      <action name="Execute">
        <command>/usr/local/bin/ai-hud</command>
      </action>
    </keybind>
    <keybind key="C-space">
      <action name="Execute">
        <command>/usr/local/bin/ai-hud</command>
      </action>
    </keybind>
  </keyboard>
</openbox_config>
EOF

cat << 'EOF' | sudo tee "${ROOTFS}/home/mineos/.xinitrc"
exec openbox-session
EOF

sudo mkdir -p "${ROOTFS}/etc/systemd/system/getty@tty1.service.d"
cat << 'EOF' | sudo tee "${ROOTFS}/etc/systemd/system/getty@tty1.service.d/autologin.conf"
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin mineos --noclear %I $TERM
EOF

cat << 'EOF' | sudo tee -a "${ROOTFS}/home/mineos/.bash_profile"
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    startx
fi
EOF

sudo chown -R 1000:1000 "${ROOTFS}/home/mineos"

echo "=== Step 6: Compressing SquashFS Image ==="
sudo mksquashfs "${ROOTFS}" "${ISO_DIR}/live/filesystem.squashfs" -comp xz -e boot

VMLINUZ="$(ls -1 ${ROOTFS}/boot/vmlinuz-* | head -n 1)"
INITRD="$(ls -1 ${ROOTFS}/boot/initrd.img-* | head -n 1)"
sudo cp "${VMLINUZ}" "${ISO_DIR}/live/vmlinuz"
sudo cp "${INITRD}" "${ISO_DIR}/live/initrd.img"

cat << 'EOF' | sudo tee "${ISO_DIR}/boot/grub/grub.cfg"
set default="0"
set timeout=3

menuentry "Boot MineOS 1.0 (AI Edition - macOS x Win 11 Hybrid)" {
    linux /live/vmlinuz boot=live quiet splash
    initrd /live/initrd.img
}

menuentry "MineOS (Failsafe Mode)" {
    linux /live/vmlinuz boot=live nomodeset
    initrd /live/initrd.img
}
EOF

echo "=== Step 7: Compiling Hybrid Bootable ISO ==="
grub-mkrescue -o "${OUTPUT_ISO}" "${ISO_DIR}"

echo "========================================================"
echo "🎉 SUCCESS: ISO BUILT AT:"
echo "${OUTPUT_ISO}"
echo "========================================================"
