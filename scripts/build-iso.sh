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
VERSION=$(tr -d '[:space:]' < "$SOURCE/VERSION")
if [[ ! "$VERSION" =~ ^[0-9]+(\.[0-9]+)*$ ]]; then
    printf 'VERSION must look like 1.0 or 1.2.3, got: %s\n' "$VERSION" >&2
    exit 1
fi
BUILD_ID=${MINEOS_BUILD_ID:-$(date -u +%Y%m%d)}
OUTPUT=$(realpath -m -- "${1:-$PWD/MineOS-$VERSION-$ARCH.iso}")
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

# packages.list is architecture-neutral; the kernel for $ARCH is added below.
packages=()
while read -r package _; do
    case "$package" in
        ""|"#"*) ;;
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
cp -a "$SOURCE/ai/mineos_agent" "$ROOTFS/opt/ai/"
find "$ROOTFS/opt/ai" -name __pycache__ -prune -exec rm -rf {} +
cp -a "$SOURCE/desktop/." "$ROOTFS/opt/ai/desktop/"
install -m 755 "$SOURCE/ai/system/ai" "$ROOTFS/usr/local/bin/ai"
ln -s /opt/ai/jarvis_gui.py "$ROOTFS/usr/local/bin/ai-hud"
install -d "$ROOTFS/etc/mineos"
install -m 644 "$SOURCE/ai/system/agent.json" "$ROOTFS/etc/mineos/agent.json"
install -m 644 "$SOURCE/ai/system/ai-shell.sh" "$ROOTFS/etc/profile.d/mineos-ai.sh"
# The assistant must at least start and describe itself inside the image.
chroot "$ROOTFS" /usr/local/bin/ai --version
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

install -m 755 "$SOURCE/rootfs/usr/local/bin/mineos-vm-display" "$ROOTFS/usr/local/bin/mineos-vm-display"

# /etc/os-release tells every tool which OS this is. ID_LIKE=debian keeps
# Debian-aware software working; VERSION_CODENAME stays the Debian codename.
cat > "$ROOTFS/etc/mineos-os-release" <<OSRELEASE
PRETTY_NAME="MineOS $VERSION (based on Debian 13)"
NAME="MineOS"
VERSION_ID="$VERSION"
VERSION="$VERSION"
VERSION_CODENAME=trixie
ID=mineos
ID_LIKE=debian
BUILD_ID=$BUILD_ID
HOME_URL="https://github.com/roshandhiman/ai_linux-DIST"
SUPPORT_URL="https://github.com/roshandhiman/ai_linux-DIST/issues"
BUG_REPORT_URL="https://github.com/roshandhiman/ai_linux-DIST/issues"
OSRELEASE
mv -Tf "$ROOTFS/etc/mineos-os-release" "$ROOTFS/etc/os-release"
# \n and \l are agetty placeholders for the hostname and terminal, so pass them as data.
printf 'MineOS %s %s\n\n' "$VERSION" '\n \l' > "$ROOTFS/etc/issue"
printf 'MineOS %s\n' "$VERSION" > "$ROOTFS/etc/issue.net"
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
cat > "$ROOTFS/etc/xdg/autostart/mineos-vm-display.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=MineOS VM display size
Exec=/usr/local/bin/mineos-vm-display
OnlyShowIn=XFCE;
Terminal=false
NoDisplay=true
ENTRY
cat > "$ROOTFS/etc/xdg/autostart/picom.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Picom
Hidden=true
ENTRY

# The offline models: llama.cpp's server plus one GGUF file (tier two), and
# the Laya router (tier one), all fetched and checksummed by
# ai/fetch-offline-ai.sh. Without MINEOS_AI_DIR the ISO still boots and `ai`
# still does the simple things with its rules (open apps, volume, memory);
# requests that need the language model say the server is not running.
if [[ -n "${MINEOS_AI_DIR:-}" ]]; then
    AI_DIR="$MINEOS_AI_DIR"
    MODEL=qwen2.5-1.5b-instruct-q4_k_m.gguf
    [[ -x "$AI_DIR/llama.cpp/llama-server" && -f "$AI_DIR/models/$MODEL" ]]
    install -d "$ROOTFS/opt/llama.cpp" "$ROOTFS/usr/share/mineos/models"
    cp -a "$AI_DIR/llama.cpp/." "$ROOTFS/opt/llama.cpp/"
    install -m 644 "$AI_DIR/models/$MODEL" "$ROOTFS/usr/share/mineos/models/$MODEL"
    # Fails the build if a shared library llama-server needs is missing.
    chroot "$ROOTFS" /opt/llama.cpp/llama-server --version
    install -m 644 "$SOURCE/ai/system/mineos-llm.service" "$ROOTFS/etc/systemd/system/mineos-llm.service"
    chroot "$ROOTFS" systemctl enable mineos-llm.service

    # Tier one: the Laya router. Its Python packages are installed from the
    # wheels the fetch script pinned, with no index, so the build cannot pick
    # up anything else; its weights are a plain folder read offline.
    if [[ -d "$AI_DIR/laya-wheels" && -f "$AI_DIR/models/laya-multilingual/model.safetensors" ]]; then
        install -d "$ROOTFS/tmp/laya-wheels"
        cp -a "$AI_DIR/laya-wheels/." "$ROOTFS/tmp/laya-wheels/"
        install -m 644 "$SOURCE/ai/laya-requirements.txt" "$ROOTFS/tmp/laya-wheels/requirements.txt"
        chroot "$ROOTFS" python3 -m venv /opt/laya
        chroot "$ROOTFS" /opt/laya/bin/pip install --no-index --no-cache-dir \
            --find-links /tmp/laya-wheels -r /tmp/laya-wheels/requirements.txt
        rm -rf "$ROOTFS/tmp/laya-wheels"
        find "$ROOTFS/opt/laya" -name __pycache__ -prune -exec rm -rf {} +
        cp -a "$AI_DIR/models/laya-multilingual" "$ROOTFS/usr/share/mineos/models/"
        chmod -R a+rX "$ROOTFS/usr/share/mineos/models/laya-multilingual"
        # Fails the build if torch, transformers or laya cannot import here.
        chroot "$ROOTFS" env USE_TF=0 /opt/laya/bin/python -c 'import laya.serve, torch, transformers'
        install -m 644 "$SOURCE/ai/system/mineos-router.service" "$ROOTFS/etc/systemd/system/mineos-router.service"
        chroot "$ROOTFS" systemctl enable mineos-router.service
    fi
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
