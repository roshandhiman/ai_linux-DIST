#!/usr/bin/env bash
# Download the optional offline vision model and verify both pinned files.
set -euo pipefail
dest="$(realpath -m -- "${1:?Usage: fetch-screen-vision.sh <new-directory>}")"
if [[ -e "$dest" ]]; then
    printf '%s already exists\n' "$dest" >&2
    exit 1
fi
stage="$(mktemp -d "$(dirname -- "$dest")/.mineos-vision.XXXXXXXX")"
trap 'rm -rf -- "$stage"' EXIT
repo=https://huggingface.co/ggml-org/SmolVLM2-256M-Video-Instruct-GGUF
revision=a48f519adb9e5a5f262e3a5004fb9a88fcfca54e
download() {
    local digest=$1 upstream=$2 output=$3
    curl --fail --location --retry 2 --connect-timeout 15 --max-time 1200 --silent --show-error \
        --output "$stage/$output" "$repo/resolve/$revision/$upstream"
    printf '%s  %s\n' "$digest" "$stage/$output" | sha256sum -c -
}
download 159de7db92a9f5817c05ed2527fc7ca223939e7cca06589051fc34d5dca1cffa \
    SmolVLM2-256M-Video-Instruct-Q4_K_M.gguf model.gguf &
model_pid=$!
download 05d5751132244a6ebd64cba9b34898c0d874b2cb78159d758e1d4da3aad91581 \
    mmproj-SmolVLM2-256M-Video-Instruct-Q8_0.gguf projector.gguf &
projector_pid=$!
status=0
wait "$model_pid" || status=1
wait "$projector_pid" || status=1
(( status == 0 ))
mv -T --no-clobber "$stage" "$dest"
test ! -d "$stage"
