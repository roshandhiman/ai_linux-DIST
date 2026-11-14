#!/usr/bin/env bash
set -euo pipefail
desktop="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$desktop/launcher.py" "$@"
