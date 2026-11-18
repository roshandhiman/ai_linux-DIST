#!/usr/bin/env bash
set -euo pipefail

source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
revision=91029df68d3cc3b4013091374495a25ee0c6d650
target="${1:-}"
case "$target" in
    amd64) target=bun-linux-x64-baseline ;;
    arm64) target=bun-linux-arm64 ;;
    *) printf 'Usage: %s arm64|amd64\n' "$0" >&2; exit 2 ;;
esac
if ! command -v bun >/dev/null || [[ "$(bun --version)" != 1.3.14 ]]; then
    printf 'Install Bun 1.3.14 to build the MineOS Code engine.\n' >&2
    exit 1
fi

output="$source_dir/build/code/${1}/mineos-code-engine"
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
git -C "$work" init -q
git -C "$work" fetch --quiet --depth=1 https://github.com/CodebuffAI/freebuff.git "$revision"
git -C "$work" checkout --quiet --detach FETCH_HEAD
cp -- "$source_dir/ai/code/engine.ts" "$work/cli/mineos-engine.ts"
mkdir -p -- "$(dirname -- "$output")"
(cd -- "$work" &&
    bun install --frozen-lockfile --ignore-scripts &&
    bun build --compile --no-compile-autoload-dotenv --no-compile-autoload-bunfig \
        --target="$target" --outfile="$output" cli/mineos-engine.ts)
printf 'Built %s\n' "$output"
