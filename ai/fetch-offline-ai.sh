#!/usr/bin/env bash
# Download the offline AI that ships inside the ISO, and verify every byte.
#
#   bash ai/fetch-offline-ai.sh <new-directory>
#
# Produces:
#   <dir>/llama.cpp/   llama-server and its libraries (llama.cpp release b11571)
#   <dir>/models/qwen2.5-1.5b-instruct-q4_k_m.gguf
#
# Both are pinned: a fixed llama.cpp release and a fixed Hugging Face commit,
# each checked against a sha256 written here. A changed upstream file fails
# the build instead of silently shipping something nobody tested.
set -euo pipefail

ARCH=$(dpkg --print-architecture)
LLAMA_VERSION=b11571
case "$ARCH" in
    amd64) LLAMA_ASSET=llama-$LLAMA_VERSION-bin-ubuntu-x64.tar.gz
           LLAMA_SHA256=f955f2eb69357c2b0a2ed3f796652a24763d7e068be3ab30fcc4e12c92d0f4be ;;
    arm64) LLAMA_ASSET=llama-$LLAMA_VERSION-bin-ubuntu-arm64.tar.gz
           LLAMA_SHA256=7c7c7e6f84a1f951ac8cb9e58fbdbd1355ff6aac2cf0746ed935284056a18b3a ;;
    *) printf 'Unsupported architecture: %s\n' "$ARCH" >&2; exit 1 ;;
esac

MODEL_REPO=Qwen/Qwen2.5-1.5B-Instruct-GGUF
MODEL_REVISION=91cad51170dc346986eccefdc2dd33a9da36ead9
MODEL_FILE=qwen2.5-1.5b-instruct-q4_k_m.gguf
MODEL_SHA256=6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e

DEST="$(realpath -m -- "$1")"
[[ ! -e "$DEST" ]] || { printf '%s already exists\n' "$DEST" >&2; exit 1; }
TEMP="$(mktemp -d "$(dirname -- "$DEST")/.mineos-ai-XXXXXXXX")"
trap 'rm -rf -- "$TEMP"' EXIT
mkdir -p "$TEMP/llama.cpp" "$TEMP/models"

curl --fail --location --retry 3 --output "$TEMP/$LLAMA_ASSET" \
    "https://github.com/ggml-org/llama.cpp/releases/download/$LLAMA_VERSION/$LLAMA_ASSET"
printf '%s  %s\n' "$LLAMA_SHA256" "$TEMP/$LLAMA_ASSET" | sha256sum -c -
tar -xzf "$TEMP/$LLAMA_ASSET" -C "$TEMP/llama.cpp" --strip-components=1
rm -- "$TEMP/$LLAMA_ASSET"
test -x "$TEMP/llama.cpp/llama-server"

curl --fail --location --retry 3 --output "$TEMP/models/$MODEL_FILE" \
    "https://huggingface.co/$MODEL_REPO/resolve/$MODEL_REVISION/$MODEL_FILE"
printf '%s  %s\n' "$MODEL_SHA256" "$TEMP/models/$MODEL_FILE" | sha256sum -c -

mv -T "$TEMP" "$DEST"
trap - EXIT
printf 'Offline AI ready in %s\n' "$DEST"
