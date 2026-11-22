#!/usr/bin/env bash
set -euo pipefail
project="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
case "$(uname -m)" in
    aarch64|arm64) architecture=arm64 ;;
    x86_64|amd64) architecture=amd64 ;;
    *) printf 'Mino Code supports arm64 and amd64.\n' >&2; exit 2 ;;
esac
if [[ "$(uname -s)" != Linux ]]; then
    printf 'Run this installer inside MineOS.\n' >&2
    exit 2
fi
output="$project/build/mino-code/$architecture"
if [[ ! -x "$output/mino-code" ]]; then
    bash "$project/scripts/build-mino-code.sh" "$architecture"
fi
root=/opt/mino-code
sudo install -d -m 755 "$root"
release="$(sudo mktemp -d "$root/release.XXXXXXXX")"
sudo chmod 755 "$release"
sudo install -m 755 "$output/mino-code" "$release/"
sudo install -m 644 "$output/tree-sitter.wasm" "$output/LICENSE" "$output/NOTICE" \
    "$output/UPSTREAM_REVISION" "$release/"
sudo ln -s "$release" "$release.link"
sudo mv -Tf "$release.link" "$root/current"
sudo install -m 755 "$project/ai/mino-code/mino-code" /usr/local/bin/mino-code
if [[ -d /opt/mino/current/lib/mino ]]; then
    sudo install -m 644 "$project/ai/mino/__main__.py" /opt/mino/current/lib/mino/
fi
printf 'Mino Code is installed. Run mino-code or mino code from your project folder.\n'
