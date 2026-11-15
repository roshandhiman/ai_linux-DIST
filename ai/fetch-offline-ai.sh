#!/usr/bin/env bash
# Download the offline AI that ships inside the ISO, and verify every byte.
#
#   bash ai/fetch-offline-ai.sh <new-directory>
#
# Produces:
#   <dir>/llama.cpp/   llama-server and its libraries (llama.cpp release b11571)
#   <dir>/models/qwen2.5-1.5b-instruct-q4_k_m.gguf
#   <dir>/models/laya-multilingual/   the router's encoder checkpoint
#   <dir>/laya-wheels/                its Python packages (torch CPU, laya, ...)
#
# All pinned: a fixed llama.cpp release and fixed Hugging Face commits, each
# file checked against a sha256 written here, and exact package versions in
# laya-requirements.txt. A changed upstream file fails the build instead of
# silently shipping something nobody tested.
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

LAYA_REPO=convaiinnovations/laya
LAYA_REVISION=85cc74ddae6109077ebe2853a9b3077fb6606a78

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

# Tier one: the Laya router's multilingual checkpoint (Apache-2.0), one
# folder of the convaiinnovations/laya repo at a fixed commit.
LAYA_DIR="$TEMP/models/laya-multilingual"
mkdir -p "$LAYA_DIR/encoder" "$LAYA_DIR/tokenizer"
while read -r sha file; do
    curl --fail --location --retry 3 --output "$LAYA_DIR/$file" \
        "https://huggingface.co/$LAYA_REPO/resolve/$LAYA_REVISION/multilingual/$file"
    printf '%s  %s\n' "$sha" "$LAYA_DIR/$file" | sha256sum -c -
done <<LAYA_FILES
25061739243b617ad88d1219ba6f8a9c86c5881ca28df024fa2d9b3b2fcc30c6 rl_agent_config.json
83f6916d13ef0f556ac461f28308dc2bffa7ebeadee8ec9e2db5812020ea5bb4 encoder/config.json
609d8f4c067cd3950f88594c5a802616cea245823836ef5848ee4fc40aab5b6f tokenizer/tokenizer.json
6c6b2d8e3c84ce0e671c129cd6b374b235d6f9863042a5836358d00a89bbb5a1 tokenizer/tokenizer_config.json
9d628fd971b700382ac6f65920a86f149777b2e748e0c955fb3b19695aa8f204 model.safetensors
LAYA_FILES

# Its Python packages, as wheels for the image's Python (Debian 13: 3.13),
# exact versions from ai/laya-requirements.txt. torch comes from PyTorch's
# CPU-only index: the CUDA build would add gigabytes a VM cannot use.
case "$ARCH" in
    amd64) MACHINE=x86_64 ;;
    arm64) MACHINE=aarch64 ;;
esac
# Every manylinux level up to Debian 13's glibc (2.41) runs there.
PLATFORMS=(--platform any --platform "manylinux2014_$MACHINE")
for glibc in 17 24 26 27 28 31 34 35 38 39; do
    PLATFORMS+=(--platform "manylinux_2_${glibc}_$MACHINE")
done
python3 -m pip download --quiet --dest "$TEMP/laya-wheels" \
    --only-binary=:all: --python-version 3.13 --implementation cp \
    --abi cp313 --abi abi3 --abi none "${PLATFORMS[@]}" \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r "$(dirname -- "$(realpath -- "$0")")/laya-requirements.txt"

mv -T "$TEMP" "$DEST"
trap - EXIT
printf 'Offline AI ready in %s\n' "$DEST"
