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

: > "$LOG"
qemu-system-x86_64 "${accel[@]}" -m 4096 -smp 2 \
    -display none -vga std -no-reboot -monitor none \
    -kernel "$WORK/vmlinuz" -initrd "$WORK/initrd.img" \
    -append "boot=live components username=mineos hostname=mineos console=ttyS0,115200 systemd.show_status=1" \
    -drive "file=$ISO,media=cdrom,readonly=on" \
    -serial "file:$LOG" &
QEMU_PID=$!

started=$SECONDS
lightdm_at=""
while kill -0 "$QEMU_PID" 2>/dev/null; do
    if grep -Eq 'Kernel panic|Unable to find a medium|\(initramfs\)|emergency mode|Failed to start lightdm' "$LOG"; then
        break
    fi
    if [[ -z "$lightdm_at" ]] && grep -Eq 'Started lightdm\.service|Started .*Light Display Manager' "$LOG"; then
        lightdm_at=$SECONDS
    fi
    # Give the display manager 30 seconds to crash before calling it a pass.
    if [[ -n "$lightdm_at" ]] && (( SECONDS - lightdm_at >= 30 )); then
        if ! grep -Eq 'lightdm\.service: (Main process exited|Failed)' "$LOG"; then
            printf 'PASS: MineOS reached the desktop in %d seconds.\n' "$lightdm_at"
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
