#!/usr/bin/env bash
set -euo pipefail

source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
version=1.143.17232
case "$(uname -m)" in
    aarch64|arm64) arch=arm64; checksum=9f270ae242561812acd02be9cf5c13c848da359b356327adfe44b815a9532309 ;;
    x86_64|amd64) arch=x64; checksum=ca1895aa040bd91a09c709d79eac7862d8c1aa0237fdc25b503deeb8bcd87efd ;;
    *) printf 'MineOS IDE supports Linux ARM64 and x86-64.\n' >&2; exit 1 ;;
esac
if [[ "$(uname -s)" != Linux || $EUID == 0 ]]; then
    printf 'Run this installer as your normal MineOS Linux user.\n' >&2
    exit 1
fi

archive="VSCodium-linux-$arch-$version.tar.gz"
cache="${XDG_CACHE_HOME:-$HOME/.cache}/mineos-ide"
bin="$HOME/.local/bin"
data="${XDG_DATA_HOME:-$HOME/.local/share}"
install_root="$data/mineos-ide"
destination="$install_root/$version"
mkdir -p "$cache" "$bin" "$install_root" "$data/applications"
exec 9>"$install_root/install.lock"
flock 9

stage="$(mktemp -d "$install_root/.build.XXXXXXXX")"
partial=""
cleanup() {
    rm -rf -- "$stage"
    [[ -z "$partial" ]] || rm -f -- "$partial"
}
trap cleanup EXIT

verify() {
    printf '%s  %s\n' "$checksum" "$1" | sha256sum --strict -c -
}
if [[ -f "$cache/$archive" ]]; then
    verify "$cache/$archive"
else
    partial="$(mktemp "$cache/.download.XXXXXXXX")"
    curl -fL --retry 3 -o "$partial" "https://github.com/VSCodium/vscodium/releases/download/$version/$archive"
    verify "$partial"
    mv -T -- "$partial" "$cache/$archive"
    partial=""
fi

if [[ -x "$destination/bin/codium" ]]; then
    app="$destination/resources/app"
else
    mkdir "$stage/runtime"
    tar -xzf "$cache/$archive" --no-same-owner -C "$stage/runtime"
    app="$stage/runtime/resources/app"
fi

tar -xOzf "$cache/$archive" ./resources/app/product.json > "$stage/product.json"
python3 - "$app/product.json" "$stage/product.json" <<'PYTHON'
import json
from pathlib import Path
import sys

target = Path(sys.argv[1])
product = json.loads(Path(sys.argv[2]).read_text())
product.update({
    "nameShort": "MineOS IDE",
    "nameLong": "MineOS IDE",
    "applicationName": "mineos-ide",
    "dataFolderName": ".mineos-ide",
    "sharedDataFolderName": ".mineos-ide-shared",
    "linuxIconName": "mineos-ide",
    "urlProtocol": "mineos-ide",
})
product["reportIssueUrl"] = "https://github.com/roshandhiman/ai_linux-DIST/issues"
product["extensionsGallery"] = {
    "serviceUrl": "https://open-vsx.org/vscode/gallery",
    "itemUrl": "https://open-vsx.org/vscode/item",
    "publisherUrl": "https://open-vsx.org",
    "resourceUrlTemplate": "https://open-vsx.org/vscode/unpkg/{publisher}/{name}/{version}/{path}",
}
for flag in ("updateUrl", "downloadUrl", "webUrl", "serverDownloadUrlTemplate", "documentationUrl",
             "requestFeatureUrl", "newsletterSignupUrl", "showTelemetryOptOut"):
    product.pop(flag, None)
temporary = target.with_suffix(".mineos.tmp")
temporary.write_text(json.dumps(product, indent=2) + "\n")
temporary.replace(target)
PYTHON

install -m 644 "$source_dir/extension/media/mineos-ide.png" "$app/resources/linux/code.png"
for icon in "$app/out/media/code-icon.svg" "$app/out/vs/workbench/browser/media/code-icon.svg"; do
    if [[ -f "$icon" ]]; then
        install -m 644 "$source_dir/extension/media/mineos-ide.svg" "$icon"
    fi
done

mkdir "$stage/mineos-assistant"
cp -a "$source_dir/extension/." "$stage/mineos-assistant/"
if [[ -d "$app/extensions/mineos-assistant" ]]; then
    rm -rf -- "$app/extensions/mineos-assistant"
fi
mv -T -- "$stage/mineos-assistant" "$app/extensions/mineos-assistant"
if [[ -d "$stage/runtime" ]]; then
    mv -T -- "$stage/runtime" "$destination"
fi

ln -s -- "$destination" "$stage/current"
mv -Tf -- "$stage/current" "$install_root/current"
install -m 755 "$source_dir/mineos-ide" "$bin/mineos-ide"
install -m 644 "$source_dir/extension/media/mineos-ide.svg" "$install_root/mineos-ide.svg"
cat > "$stage/org.mineos.IDE.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=MineOS IDE
Comment=Edit code and work with MineOS Assistant
Exec="$bin/mineos-ide" %F
Icon=$install_root/mineos-ide.svg
Categories=Development;IDE;
Terminal=false
StartupWMClass=codium
ENTRY
install -m 644 "$stage/org.mineos.IDE.desktop" "$data/applications/org.mineos.IDE.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$data/applications" || true
printf 'MineOS IDE installed at %s\n' "$bin/mineos-ide"
