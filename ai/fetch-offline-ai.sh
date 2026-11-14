#!/usr/bin/env bash
set -euo pipefail

ARCH=$(dpkg --print-architecture)
VERSION=0.40.16
case "$ARCH" in
    arm64) CHECKSUM=e45b8e6dcb86cb9f3057396351655079c9a4879b4ced2678c9350d375dcbc224 ;;
    amd64) CHECKSUM=87bfafb2acbc89b2e6a1be0a9043de6aa75fb450696f86bc426e65fc448f788d ;;
    *) printf 'Unsupported architecture: %s\n' "$ARCH" >&2; exit 1 ;;
esac

DEST="$(realpath -m -- "$1")"
[[ ! -e "$DEST" ]]
TEMP="$(mktemp -d "$(dirname -- "$DEST")/.mineos-ai-XXXXXXXX")"
trap 'rm -rf -- "$TEMP"' EXIT
archive=ollama-linux-$ARCH.tar.zst
mkdir -p "$TEMP/engine" "$TEMP/models/blobs" "$TEMP/models/manifests/registry.ollama.ai/library/qwen2.5"
curl --fail --location --retry 3 --output "$TEMP/$archive" "https://github.com/ollama/ollama/releases/download/v$VERSION/$archive"
printf '%s  %s\n' "$CHECKSUM" "$TEMP/$archive" | sha256sum -c -
tar --zstd -xf "$TEMP/$archive" -C "$TEMP/engine" \
    --exclude='*/lib/ollama/cuda_*' --exclude='lib/ollama/cuda_*' \
    --exclude='*/lib/ollama/rocm' --exclude='lib/ollama/rocm'
rm -- "$TEMP/$archive"
test -x "$TEMP/engine/bin/ollama"
test -d "$TEMP/engine/lib/ollama"

REGISTRY=https://registry.ollama.ai/v2/library/qwen2.5
MANIFEST="$TEMP/models/manifests/registry.ollama.ai/library/qwen2.5/1.5b"
curl --fail --location --retry 3 -H 'Accept: application/vnd.docker.distribution.manifest.v2+json' \
    --output "$MANIFEST" "$REGISTRY/manifests/1.5b"
printf '%s  %s\n' 65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b "$MANIFEST" | sha256sum -c -
jq -er '.config.digest, .layers[].digest' "$MANIFEST" > "$TEMP/digests"
while read -r digest; do
    [[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]
    file="$TEMP/models/blobs/${digest/:/-}"
    curl --fail --location --retry 3 --output "$file" "$REGISTRY/blobs/$digest"
    printf '%s  %s\n' "${digest#sha256:}" "$file" | sha256sum -c -
done < "$TEMP/digests"
rm "$TEMP/digests"
mv -T "$TEMP" "$DEST"
