#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID != 0 ]]; then
    printf '%s\n' 'Run with sudo on a Debian build machine.' >&2
    exit 1
fi

SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ARCH=$(dpkg --print-architecture)
case "$ARCH" in
    arm64) grub_packages=(grub-efi-arm64-bin) ;;
    amd64) grub_packages=(grub-efi-amd64-bin grub-pc-bin) ;;
    *) printf 'Unsupported architecture: %s\n' "$ARCH" >&2; exit 1 ;;
esac
OUTPUT=$(realpath -m -- "${1:-$PWD/MineOS-1.0-$ARCH.iso}")
if [[ -e "$OUTPUT" || ! -d "$(dirname -- "$OUTPUT")" ]]; then
    printf '%s\n' 'Choose a new ISO filename in an existing directory.' >&2
    exit 1
fi

apt-get update
apt-get install -y debootstrap squashfs-tools xorriso mtools grub-common "${grub_packages[@]}"
WORK=$(mktemp -d)
ROOTFS="$WORK/rootfs"
IMAGE="$WORK/image"
PARTIAL=""
cleanup() {
    for mount in "$ROOTFS/proc" "$ROOTFS/sys" "$ROOTFS/dev"; do
        if mountpoint -q "$mount"; then umount -R "$mount" || return; fi
    done
    if [[ -n "$PARTIAL" ]]; then rm -f -- "$PARTIAL"; fi
    rm -rf -- "$WORK"
}
trap cleanup EXIT
mkdir -p "$IMAGE/live" "$IMAGE/boot/grub"
debootstrap --arch="$ARCH" --variant=minbase trixie "$ROOTFS" http://deb.debian.org/debian
mount -t proc proc "$ROOTFS/proc"
mount --rbind /sys "$ROOTFS/sys"
mount --make-rslave "$ROOTFS/sys"
mount --rbind /dev "$ROOTFS/dev"
mount --make-rslave "$ROOTFS/dev"
printf '#!/bin/sh\nexit 101\n' > "$ROOTFS/usr/sbin/policy-rc.d"
chmod 755 "$ROOTFS/usr/sbin/policy-rc.d"

packages=()
while read -r package; do
    case "$package" in
        ""|grub-efi-arm64|grub-common|linux-image-arm64|linux-headers-arm64) ;;
        *) packages+=("$package") ;;
    esac
done < "$SOURCE/packages.list"
chroot "$ROOTFS" apt-get update
chroot "$ROOTFS" env DEBIAN_FRONTEND=noninteractive apt-get install -y "linux-image-$ARCH" "${packages[@]}" \
    live-boot live-config live-config-systemd network-manager-gnome pulseaudio-utils desktop-file-utils xdg-user-dirs

install -d "$ROOTFS/opt/ai/desktop" "$ROOTFS/usr/share/plymouth/themes/mineos" \
    "$ROOTFS/etc/xdg/autostart" "$ROOTFS/usr/share/applications" \
    "$ROOTFS/etc/systemd/system" "$ROOTFS/etc/lightdm/lightdm.conf.d"
cp -a "$SOURCE/ai-agent/." "$ROOTFS/opt/ai/"
cp -a "$SOURCE/desktop/." "$ROOTFS/opt/ai/desktop/"
ln -s /opt/ai/jarvis.py "$ROOTFS/usr/local/bin/ai"
ln -s /opt/ai/jarvis_gui.py "$ROOTFS/usr/local/bin/ai-hud"
install -m 644 "$SOURCE/desktop/settings.desktop" "$ROOTFS/usr/share/applications/org.mineos.Settings.desktop"
install -m 644 "$SOURCE/desktop/companion.desktop" "$ROOTFS/usr/share/applications/org.mineos.Companion.desktop"
install -m 644 "$SOURCE/desktop/ai.desktop" "$ROOTFS/usr/share/applications/org.mineos.Assistant.desktop"
install -m 644 "$SOURCE/boot/mineos/mineos.script" "$SOURCE/boot/mineos/mineos.plymouth" "$ROOTFS/usr/share/plymouth/themes/mineos/"
install -m 644 "$SOURCE/rootfs/etc/lightdm/lightdm.conf.d/live.conf" "$ROOTFS/etc/lightdm/lightdm.conf.d/40-mineos.conf"
bash "$SOURCE/boot/install-login.sh" "$ROOTFS"

awk '
    /^NAME=/ { print "NAME=\"MineOS\""; next }
    /^PRETTY_NAME=/ { print "PRETTY_NAME=\"MineOS\""; next }
    { print }
' "$ROOTFS/usr/lib/os-release" > "$ROOTFS/etc/mineos-os-release"
mv -Tf "$ROOTFS/etc/mineos-os-release" "$ROOTFS/etc/os-release"
printf '%s\n' mineos > "$ROOTFS/etc/hostname"
printf '127.0.0.1 localhost\n127.0.1.1 mineos\n' > "$ROOTFS/etc/hosts"

cat > "$ROOTFS/etc/xdg/autostart/mineos-desktop.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=MineOS Desktop
Exec=/opt/ai/desktop/first-login.sh
OnlyShowIn=XFCE;
Terminal=false
ENTRY
cat > "$ROOTFS/etc/xdg/autostart/picom.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Picom
Hidden=true
ENTRY

if [[ -n "${MINEOS_OLLAMA_DIR:-}" ]]; then
    OLLAMA="$MINEOS_OLLAMA_DIR"
    [[ -x "$OLLAMA/bin/ollama" && -d "$OLLAMA/lib/ollama" ]]
    install -d "$ROOTFS/usr/local/bin" "$ROOTFS/usr/local/lib"
    install -m 755 "$OLLAMA/bin/ollama" "$ROOTFS/usr/local/bin/ollama"
    cp -a "$OLLAMA/lib/ollama" "$ROOTFS/usr/local/lib/"
    chroot "$ROOTFS" /usr/local/bin/ollama --version
    chroot "$ROOTFS" useradd --system --home /usr/share/ollama --create-home --shell /usr/sbin/nologin ollama
    install -m 644 "$SOURCE/rootfs/etc/systemd/system/ai-core.service" "$ROOTFS/etc/systemd/system/ai-core.service"
    if [[ -n "${MINEOS_OLLAMA_MODELS:-}" ]]; then
        [[ -d "$MINEOS_OLLAMA_MODELS/blobs" && -d "$MINEOS_OLLAMA_MODELS/manifests" ]]
        install -d "$ROOTFS/usr/share/ollama/models"
        cp -a "$MINEOS_OLLAMA_MODELS/." "$ROOTFS/usr/share/ollama/models/"
    fi
    chroot "$ROOTFS" chown -R ollama:ollama /usr/share/ollama
    chroot "$ROOTFS" systemctl enable ai-core.service
fi

install -m 644 "$SOURCE/boot/render_frames.py" "$ROOTFS/opt/ai/boot-render.py"
chroot "$ROOTFS" python3 /opt/ai/boot-render.py /usr/share/plymouth/themes/mineos
rm "$ROOTFS/opt/ai/boot-render.py"
chroot "$ROOTFS" plymouth-set-default-theme mineos
chroot "$ROOTFS" update-initramfs -u -k all
chroot "$ROOTFS" apt-get clean
rm "$ROOTFS/usr/sbin/policy-rc.d"
umount -R "$ROOTFS/dev"
umount -R "$ROOTFS/sys"
umount "$ROOTFS/proc"

kernel=$(find "$ROOTFS/boot" -maxdepth 1 -name 'vmlinuz-*' -printf '%f\n' | sort -V | tail -n 1)
test -n "$kernel"
cp "$ROOTFS/boot/$kernel" "$IMAGE/live/vmlinuz"
cp "$ROOTFS/boot/initrd.img-${kernel#vmlinuz-}" "$IMAGE/live/initrd.img"
install -m 644 "$SOURCE/rootfs/boot/grub/grub.cfg" "$IMAGE/boot/grub/grub.cfg"
grub-script-check "$IMAGE/boot/grub/grub.cfg"
mksquashfs "$ROOTFS" "$IMAGE/live/filesystem.squashfs" -noappend -comp xz -e boot
PARTIAL=$(mktemp "$(dirname -- "$OUTPUT")/.mineos-XXXXXXXX.iso")
grub-mkrescue -o "$PARTIAL" "$IMAGE"
xorriso -indev "$PARTIAL" -report_el_torito plain
chmod 644 "$PARTIAL"
mv -T --no-clobber "$PARTIAL" "$OUTPUT"
if [[ -e "$PARTIAL" ]]; then
    printf 'The output path became occupied: %s\n' "$OUTPUT" >&2
    exit 1
fi
PARTIAL=""
printf 'ISO: %s\n' "$OUTPUT"
