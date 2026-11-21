#!/usr/bin/env bash
set -euo pipefail
project="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
revision=35ed93aeb6bfcb739effda228ba34f1d03986d98
architecture="${1:-$(uname -m)}"
case "$architecture" in
    aarch64|arm64) architecture=arm64; target=bun-linux-arm64; target_arch=arm64 ;;
    x86_64|amd64) architecture=amd64; target=bun-linux-x64-baseline; target_arch=x64 ;;
    *) printf 'Supported targets are arm64 and amd64.\n' >&2; exit 2 ;;
esac
case "$(uname -m)" in
    aarch64|arm64) bun_arch=aarch64 ;;
    x86_64|amd64) bun_arch=x64 ;;
    *) printf 'Unsupported build machine.\n' >&2; exit 2 ;;
esac
case "$(uname -s)" in
    Linux) bun_os=linux ;;
    Darwin) bun_os=darwin ;;
    *) printf 'Build on Linux or macOS.\n' >&2; exit 2 ;;
esac
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
curl --disable --fail --location --silent --show-error --retry 3 \
    "https://codeload.github.com/CodebuffAI/freebuff/tar.gz/$revision" -o "$work/source.tar.gz"
mkdir "$work/source"
tar -xzf "$work/source.tar.gz" --strip-components=1 -C "$work/source"
curl --disable --fail --location --silent --show-error --retry 3 \
    "https://github.com/oven-sh/bun/releases/download/bun-v1.3.14/bun-$bun_os-$bun_arch.zip" -o "$work/bun.zip"
python3 - "$work/bun.zip" "$work" <<'PY'
import sys
import zipfile
with zipfile.ZipFile(sys.argv[1]) as bundle:
    bundle.extractall(sys.argv[2])
PY
bun_path="$work/bun-$bun_os-$bun_arch"
chmod +x "$bun_path/bun"
export PATH="$bun_path:$PATH"
cd "$work/source"
git apply --unidiff-zero --check "$project/ai/mino-code/interface.patch"
git apply --unidiff-zero "$project/ai/mino-code/interface.patch"
bun install --frozen-lockfile --ignore-scripts
# Public production endpoints follow upstream freebuff/e2e/README.md.
# The free CLI does not embed web billing or analytics credentials.
export NEXT_PUBLIC_CB_ENVIRONMENT=prod
export NEXT_PUBLIC_CODEBUFF_APP_URL=https://www.codebuff.com
export NEXT_PUBLIC_FREEBUFF_APP_URL=https://freebuff.com
export NEXT_PUBLIC_SUPPORT_EMAIL=support@freebuff.com
export NEXT_PUBLIC_POSTHOG_API_KEY=test
export NEXT_PUBLIC_POSTHOG_HOST_URL=http://127.0.0.1:9
export NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=test
export NEXT_PUBLIC_STRIPE_CUSTOMER_PORTAL=http://127.0.0.1:9
export NEXT_PUBLIC_WEB_PORT=3000
NODE_ENV=production FREEBUFF_MODE=true OVERRIDE_TARGET="$target" OVERRIDE_PLATFORM=linux \
    OVERRIDE_ARCH="$target_arch" bun cli/scripts/build-binary.ts mino-code 0.1.0-mino
output="$project/build/mino-code/$architecture"
mkdir -p "$output"
install -m 755 cli/bin/mino-code "$output/mino-code"
install -m 644 cli/bin/tree-sitter.wasm LICENSE NOTICE "$output/"
printf '%s\n' "$revision" > "$output/UPSTREAM_REVISION"
printf 'Built %s\n' "$output/mino-code"
