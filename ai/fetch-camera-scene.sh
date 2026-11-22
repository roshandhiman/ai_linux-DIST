#!/usr/bin/env bash
# Fetch the MIT-licensed ONNX Community conversion of Microsoft Florence-2-base-ft.
set -euo pipefail
dest="$(realpath -m -- "${1:?Usage: fetch-camera-scene.sh <new-directory>}")"
[[ ! -e "$dest" ]] || { printf '%s already exists\n' "$dest" >&2; exit 1; }
stage="$(mktemp -d "$(dirname -- "$dest")/.mineos-scene.XXXXXXXX")"
trap 'rm -rf -- "$stage"' EXIT

repo=https://huggingface.co/onnx-community/Florence-2-base-ft
revision=e88a44eaf3791a35eae0c5a47b3dbcd36e67eb6f
download() {
    local hash=$1 file=$2
    curl -fsSL --retry 2 --connect-timeout 20 --max-time 1200 \
        "$repo/resolve/$revision/$file?download=true" -o "$stage/${file##*/}"
    printf '%s  %s\n' "$hash" "$stage/${file##*/}" | sha256sum -c -
}
pids=()
while read -r hash file; do
    download "$hash" "$file" &
    pids+=("$!")
done <<'FILES'
f22f52f980c33df0efa15932c2f3db6d9d3595ce6387eca938b8cfe23dc4c641 onnx/decoder_model_merged_int8.onnx
3b79d54f23f666f731549db23cb070c35a979ce19cbd9720e90e67a78dc9768c onnx/vision_encoder_uint8.onnx
f4ad7a68f1fb875d3bcf735ea14a7021b7ba7e83baf7cf10289881b4ed6d9b85 onnx/encoder_model_int8.onnx
6b2258db1c8ee9b160576ccde3cd3814d83a2edaed0dd1c6ca9ff3c38fa62214 onnx/embed_tokens_int8.onnx
d69dcdb2323e124ac4f800cb9863ddccea0d7bb11e16125e8df3bd60f2f8aeac tokenizer.json
FILES
failed=0
for pid in "${pids[@]}"; do
    wait "$pid" || failed=1
done
(( failed == 0 ))
curl -fsSL --retry 2 --connect-timeout 20 --max-time 60 \
    'https://huggingface.co/microsoft/Florence-2-base-ft/resolve/f6c1a25888ffc1d945ee8a1a77ac833c7303d46e/LICENSE' \
    -o "$stage/LICENSE"
printf '%s  %s\n' c2cfccb812fe482101a8f04597dfc5a9991a6b2748266c47ac91b6a5aae15383 "$stage/LICENSE" | sha256sum -c -
printf '%s\n' 'Florence-2-base-ft by Microsoft, converted to ONNX by ONNX Community. MIT license.' \
    "$repo/tree/$revision" 'https://huggingface.co/microsoft/Florence-2-base-ft' > "$stage/ATTRIBUTION"
mv -T --no-clobber "$stage" "$dest"
test ! -d "$stage"
