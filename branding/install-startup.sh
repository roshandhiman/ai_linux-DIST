#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID != 0 ]]; then
    printf '%s\n' 'Run the startup installer as root.' >&2
    exit 1
fi

SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for command in update-grub update-initramfs plymouth-set-default-theme; do
    command -v "$command" >/dev/null
done
BACKUP="$(mktemp -d /var/backups/mineos-startup-XXXXXXXX)"
install -d -m 755 /etc/default/grub.d /usr/share/plymouth/themes/mineos /usr/share/backgrounds/mineos
cp -a /etc/os-release "$BACKUP/os-release"
cp -L /etc/os-release "$BACKUP/os-release-effective"
cp -a /boot/grub/grub.cfg "$BACKUP/grub.cfg"
plymouth-set-default-theme > "$BACKUP/plymouth-theme"
if [[ -e /etc/default/grub.d/95-mineos.cfg ]]; then
    cp -a /etc/default/grub.d/95-mineos.cfg "$BACKUP/"
fi

THEME=/usr/share/plymouth/themes/mineos
install -m 644 "$SOURCE/plymouth/mineos.plymouth" "$SOURCE/plymouth/mineos.script" "$THEME/"
python3 "$SOURCE/render_frames.py" "$THEME"
awk '
    /^NAME=/ { print "NAME=\"MineOS\""; next }
    /^PRETTY_NAME=/ { print "PRETTY_NAME=\"MineOS\""; next }
    { print }
' "$BACKUP/os-release-effective" > "$BACKUP/mineos-os-release"
install -m 644 "$BACKUP/mineos-os-release" /etc/.mineos-os-release
mv -Tf /etc/.mineos-os-release /etc/os-release
cat > /etc/default/grub.d/95-mineos.cfg <<'GRUB'
GRUB_DISTRIBUTOR="MineOS"
GRUB_BACKGROUND=""
case " ${GRUB_CMDLINE_LINUX_DEFAULT:-} " in
    *" splash "*) ;;
    *) GRUB_CMDLINE_LINUX_DEFAULT="${GRUB_CMDLINE_LINUX_DEFAULT:-quiet} splash" ;;
esac
GRUB
plymouth-set-default-theme mineos
update-initramfs -u -k "$(uname -r)"
update-grub
grub-script-check /boot/grub/grub.cfg
printf 'Startup backup: %s\n' "$BACKUP"
