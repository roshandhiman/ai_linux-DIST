#!/usr/bin/env bash
# Smoke test: boots a MineOS amd64 ISO in headless QEMU and waits until the
# graphical desktop starts. Usage: bash scripts/boot-test.sh MineOS.iso [serial.log]
# Needs qemu-system-x86 and xorriso. Uses KVM when /dev/kvm is writable.
set -euo pipefail

if [[ $# -lt 1 || ! -f "$1" ]]; then
    printf '%s\n' 'Usage: boot-test.sh path/to/MineOS-amd64.iso [serial.log]' >&2
    exit 2
fi
ISO=$(realpath -- "$1")
LOG=$(realpath -m -- "${2:-boot-test.log}")
TIMEOUT=${MINEOS_BOOT_TIMEOUT:-900}

WORK=$(mktemp -d)
QEMU_PID=""
cleanup() {
    if [[ -n "$QEMU_PID" ]] && kill -0 "$QEMU_PID" 2>/dev/null; then
        kill "$QEMU_PID" 2>/dev/null || true
        wait "$QEMU_PID" 2>/dev/null || true
    fi
    rm -rf -- "$WORK"
}
trap cleanup EXIT

# Boot the ISO's own kernel and initrd directly so the boot messages go to the
# serial port. live-boot still has to find and mount the squashfs on the CD.
xorriso -osirrox on -indev "$ISO" \
    -extract /live/vmlinuz "$WORK/vmlinuz" \
    -extract /live/initrd.img "$WORK/initrd.img" >/dev/null 2>&1

if [[ -w /dev/kvm ]]; then
    accel=(-accel kvm -cpu host)
else
    printf '%s\n' 'KVM is not available; using software emulation (much slower).'
    accel=(-accel tcg -cpu max)
fi

# systemd stops echoing status lines once the login prompt owns the serial
# console, so journald also copies the system log there. That log records the
# autologin session opening, which is the proof that the desktop started.
: > "$LOG"
qemu-system-x86_64 "${accel[@]}" -m 4096 -smp 2 \
    -display none -vga std -no-reboot -monitor none \
    -kernel "$WORK/vmlinuz" -initrd "$WORK/initrd.img" \
    -append "boot=live components username=mineos hostname=mineos console=ttyS0,115200 systemd.show_status=1 systemd.journald.forward_to_console=1" \
    -drive "file=$ISO,media=cdrom,readonly=on" \
    -serial "file:$LOG" &
QEMU_PID=$!

started=$SECONDS
desktop_at=""
while kill -0 "$QEMU_PID" 2>/dev/null; do
    if grep -Eq 'Kernel panic|Unable to find a medium|\(initramfs\)|emergency mode|Failed to start lightdm' "$LOG"; then
        break
    fi
    # LightDM logs this through PAM when it signs the live user in automatically.
    if [[ -z "$desktop_at" ]] && grep -Eq 'lightdm-autologin:session\): session opened for user mineos' "$LOG"; then
        desktop_at=$SECONDS
    fi
    # Give the session 30 seconds to crash before calling it a pass.
    if [[ -n "$desktop_at" ]] && (( SECONDS - desktop_at >= 30 )); then
        if ! grep -Eq 'lightdm\.service: (Main process exited|Failed)|lightdm-autologin:session\): session closed' "$LOG"; then
            printf 'PASS: MineOS reached the desktop in %d seconds.\n' "$desktop_at"
            exit 0
        fi
        break
    fi
    if (( SECONDS - started > TIMEOUT )); then
        printf 'Timed out after %d seconds.\n' "$TIMEOUT"
        break
    fi
    sleep 5
done

printf '%s\n' 'FAIL: MineOS did not reach the desktop. Last serial output:' >&2
tail -n 60 "$LOG" >&2
exit 1
