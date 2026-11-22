#!/usr/bin/env bash
set -euo pipefail
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if (( EUID == 0 )); then
    printf '%s\n' 'Run as your normal MineOS user; the installer uses sudo.' >&2
    exit 2
fi
if [[ ! -f /etc/debian_version ]]; then
    printf '%s\n' 'This installer targets Debian-based MineOS.' >&2
    exit 2
fi
sudo apt-get install -y --no-install-recommends python3-venv python3-gi gir1.2-gtk-3.0 xdg-utils
sudo install -d -m 755 /opt/ai/dealreview/data /opt/mineos-dealreview
if [[ ! -x /opt/mineos-dealreview/venv/bin/python ]]; then
    sudo python3 -m venv --system-site-packages /opt/mineos-dealreview/venv
fi
sudo /opt/mineos-dealreview/venv/bin/python -m pip install --disable-pip-version-check --no-cache-dir 'pypdf==6.21.4' 'Markdown==3.11.3'
sudo install -m 644 "$source_dir/ai/dealreview/"*.py /opt/ai/dealreview/
sudo install -m 644 "$source_dir/ai/dealreview/data/cuad_demo.json" /opt/ai/dealreview/data/
sudo install -m 644 "$source_dir/ai/dealreview/data/NOTICE.md" /opt/ai/dealreview/data/
sudo install -Dm 755 "$source_dir/ai/system/mino-review" /usr/local/bin/mino-review
sudo install -Dm 644 "$source_dir/ai/system/org.mineos.DealReview.desktop" /usr/local/share/applications/org.mineos.DealReview.desktop
if [[ "${1:-}" == --download-demo ]]; then mino-review --download-demo; fi
printf '%s\n' 'Mino Deal Review installed. Run mino-review or ai dealreview.'
