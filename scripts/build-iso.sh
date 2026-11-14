#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID != 0 ]]; then
    printf '%s\n' 'Run with sudo on a Debian build machine.' >&2
    exit 1
fi

SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
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

WORK=$(mktemp -d)
ROOTFS="$WORK/rootfs"
IMAGE="$WORK/image"
PARTIAL=""
cleanup() {
    for mount in "$ROOTFS/dev" "$ROOTFS/sys" "$ROOTFS/proc"; do
        if mountpoint -q "$mount"; then umount -R "$mount" || return; fi
    done
    if [[ -n "$PARTIAL" ]]; then rm -f -- "$PARTIAL"; fi
    rm -rf -- "$WORK"
}
trap cleanup EXIT
. /etc/os-release
if [[ "$ID" != debian || "$VERSION_CODENAME" != trixie ]]; then
    printf '%s\n' 'Build from a Debian 13 host or the Debian 13 Actions container.' >&2
    exit 1
fi
HOST_SOURCES="$WORK/build-debian.list"
printf 'deb http://deb.debian.org/debian trixie main\ndeb http://deb.debian.org/debian-security trixie-security main\n' > "$HOST_SOURCES"
APT_OPTIONS=(-o "Dir::Etc::sourcelist=$HOST_SOURCES" -o "Dir::Etc::sourceparts=-")
apt-get "${APT_OPTIONS[@]}" update
DEBIAN_FRONTEND=noninteractive apt-get "${APT_OPTIONS[@]}" install -y --no-install-recommends \
    debootstrap debian-archive-keyring ca-certificates wget squashfs-tools xorriso mtools grub-common "${grub_packages[@]}"

mkdir -p "$IMAGE/live" "$IMAGE/boot/grub"
debootstrap --arch="$ARCH" --variant=minbase --include=ca-certificates --components=main,non-free-firmware trixie "$ROOTFS" http://deb.debian.org/debian
printf 'deb https://deb.debian.org/debian trixie main non-free-firmware\ndeb https://deb.debian.org/debian-security trixie-security main non-free-firmware\ndeb https://deb.debian.org/debian trixie-updates main non-free-firmware\n' > "$ROOTFS/etc/apt/sources.list"
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
done < "$SOURCE/config/packages.list"
chroot "$ROOTFS" apt-get update
chroot "$ROOTFS" env DEBIAN_FRONTEND=noninteractive apt-get install -y "linux-image-$ARCH" "${packages[@]}" \
    live-boot live-config live-config-systemd network-manager-gnome pulseaudio-utils desktop-file-utils xdg-user-dirs ca-certificates

install -d "$ROOTFS/opt/ai/desktop" "$ROOTFS/usr/share/plymouth/themes/mineos" \
    "$ROOTFS/etc/xdg/autostart" "$ROOTFS/usr/share/applications" "$ROOTFS/usr/local/share/applications" \
    "$ROOTFS/etc/systemd/system" "$ROOTFS/etc/lightdm/lightdm.conf.d"
cp -a "$SOURCE/ai/agent/." "$ROOTFS/opt/ai/"
cp -a "$SOURCE/desktop/." "$ROOTFS/opt/ai/desktop/"
ln -s /opt/ai/jarvis.py "$ROOTFS/usr/local/bin/ai"
ln -s /opt/ai/jarvis_gui.py "$ROOTFS/usr/local/bin/ai-hud"
install -m 644 "$SOURCE/desktop/settings.desktop" "$ROOTFS/usr/share/applications/org.mineos.Settings.desktop"
for app in xfce-settings-manager xfce-backdrop-settings xfce-ui-settings; do
    install -m 644 "$SOURCE/desktop/hidden-settings.desktop" "$ROOTFS/usr/local/share/applications/$app.desktop"
done
install -m 644 "$SOURCE/desktop/companion.desktop" "$ROOTFS/usr/share/applications/org.mineos.Companion.desktop"
install -m 644 "$SOURCE/desktop/ai.desktop" "$ROOTFS/usr/share/applications/org.mineos.Assistant.desktop"
SESSION_XML="$ROOTFS/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-session.xml"
sed -i '0,/<property name="Count" type="int" value="5"\//s//<property name="Count" type="int" value="2"\//' "$SESSION_XML"
grep -q '<property name="Count" type="int" value="2"/>' "$SESSION_XML"
install -m 644 "$SOURCE/branding/plymouth/mineos.script" "$SOURCE/branding/plymouth/mineos.plymouth" "$ROOTFS/usr/share/plymouth/themes/mineos/"
install -m 644 "$SOURCE/rootfs/etc/lightdm/lightdm.conf.d/live.conf" "$ROOTFS/etc/lightdm/lightdm.conf.d/40-mineos.conf"
bash "$SOURCE/branding/install-login.sh" "$ROOTFS"

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
    install -m 644 "$SOURCE/ai/system/ai-core.service" "$ROOTFS/etc/systemd/system/ai-core.service"
    if [[ -n "${MINEOS_OLLAMA_MODELS:-}" ]]; then
        [[ -d "$MINEOS_OLLAMA_MODELS/blobs" && -d "$MINEOS_OLLAMA_MODELS/manifests" ]]
        install -d "$ROOTFS/usr/share/ollama/models"
        cp -a "$MINEOS_OLLAMA_MODELS/." "$ROOTFS/usr/share/ollama/models/"
    fi
    chroot "$ROOTFS" chown -R ollama:ollama /usr/share/ollama
    chroot "$ROOTFS" systemctl enable ai-core.service
fi

install -m 644 "$SOURCE/branding/render_frames.py" "$ROOTFS/opt/ai/boot-render.py"
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
mksquashfs "$ROOTFS" "$IMAGE/live/filesystem.squashfs" -noappend -comp zstd -Xcompression-level 6 -processors "$(nproc)" -e boot
PARTIAL=$(mktemp "$(dirname -- "$OUTPUT")/.mineos-XXXXXXXX.iso")
grub-mkrescue -o "$PARTIAL" "$IMAGE" -- -volid MINEOS
boot_report=$(xorriso -indev "$PARTIAL" -report_el_torito plain)
printf '%s\n' "$boot_report"
grep -Eq '^El Torito boot img[[:space:]]*:[[:space:]]+[0-9]+[[:space:]]+UEFI([[:space:]]|$)' <<< "$boot_report"
if [[ "$ARCH" == amd64 ]]; then
    grep -Eq '^El Torito boot img[[:space:]]*:[[:space:]]+[0-9]+[[:space:]]+BIOS([[:space:]]|$)' <<< "$boot_report"
fi
xorriso -indev "$PARTIAL" -ls /live/filesystem.squashfs /live/vmlinuz /live/initrd.img
chmod 644 "$PARTIAL"
mv -T --no-clobber "$PARTIAL" "$OUTPUT"
if [[ -e "$PARTIAL" ]]; then
    printf 'The output path became occupied: %s\n' "$OUTPUT" >&2
    exit 1
fi
PARTIAL=""
printf 'ISO: %s\n' "$OUTPUT"
