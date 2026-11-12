#!/usr/bin/env bash
set -euo pipefail

DISTRO_NAME="mineos"
ARCH="arm64"
WORK_DIR="/tmp/mineos-build"
ROOTFS="${WORK_DIR}/rootfs"
IMAGE_DIR="${WORK_DIR}/image"
OUTPUT_ISO="$(pwd)/mineos-1.0-${ARCH}.iso"

sudo apt-get update -qq
sudo apt-get install -y -qq debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-arm64-bin mtools dosfstools

sudo rm -rf "${WORK_DIR}"
mkdir -p "${ROOTFS}" "${IMAGE_DIR}/live" "${IMAGE_DIR}/boot/grub"

sudo debootstrap --arch="${ARCH}" --variant=minbase trixie "${ROOTFS}" http://deb.debian.org/debian/

sudo cp rootfs/etc/os-release "${ROOTFS}/etc/os-release"
sudo cp rootfs/etc/hostname "${ROOTFS}/etc/hostname"
sudo cp rootfs/etc/hosts "${ROOTFS}/etc/hosts"
sudo cp rootfs/boot/grub/grub.cfg "${IMAGE_DIR}/boot/grub/grub.cfg"

sudo mkdir -p "${ROOTFS}/etc/systemd/system"
sudo cp rootfs/etc/systemd/system/ai-core.service "${ROOTFS}/etc/systemd/system/"

sudo mkdir -p "${ROOTFS}/opt/ai"
sudo cp -r ai-agent/* "${ROOTFS}/opt/ai/"
sudo ln -sf /opt/ai/jarvis.py "${ROOTFS}/usr/local/bin/ai"
sudo ln -sf /opt/ai/jarvis_gui.py "${ROOTFS}/usr/local/bin/ai-hud"

PKGS=$(tr '\n' ',' < packages.list | sed 's/,$//')

sudo chroot "${ROOTFS}" /bin/bash -c "
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ${PKGS//,/ }
useradd -m -s /bin/bash -G sudo,video,audio,plugdev mineos
echo 'mineos:mineos' | chpasswd
echo 'mineos ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/mineos
systemctl enable ai-core
systemctl enable lightdm
apt-get clean
"

sudo cp -L "${ROOTFS}/vmlinuz" "${IMAGE_DIR}/live/vmlinuz" || sudo cp "${ROOTFS}"/boot/vmlinuz-* "${IMAGE_DIR}/live/vmlinuz"
sudo cp -L "${ROOTFS}/initrd.img" "${IMAGE_DIR}/live/initrd.img" || sudo cp "${ROOTFS}"/boot/initrd.img-* "${IMAGE_DIR}/live/initrd.img"

sudo mksquashfs "${ROOTFS}" "${IMAGE_DIR}/live/filesystem.squashfs" -comp xz

grub-mkrescue -o "${OUTPUT_ISO}" "${IMAGE_DIR}"

echo "ISO Generated: ${OUTPUT_ISO}"

