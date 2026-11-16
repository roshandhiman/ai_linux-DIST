#!/usr/bin/env bash
set -euo pipefail

repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
destination="$(realpath -m -- "${1:-dist}")"
source_version=1.1.4-1
package_version="$source_version+mineos1"
stage="$(mktemp -d)"
trap 'rm -rf -- "$stage"' EXIT

cd "$stage"
apt-get source "xfce4-terminal=$source_version"
cd xfce4-terminal-1.1.4
patch --batch --forward -p1 < "$repo/desktop/patches/terminal-titlebar.patch"
sed -i "1s/($source_version)/($package_version)/" debian/changelog
test "$(dpkg-parsechangelog -S Version)" = "$package_version"
dpkg-buildpackage -b -us -uc -j"$(nproc)"

package="xfce4-terminal_${package_version}_$(dpkg --print-architecture).deb"
install -D -m 644 "$stage/$package" "$destination/$package"
printf 'Terminal package: %s\n' "$destination/$package"
