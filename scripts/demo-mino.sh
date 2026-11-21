#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == --check ]]; then
    project="$(cd -- "$(dirname -- "$0")/.." && pwd)"
    PYTHONPATH="$project/ai" python3 -B -m unittest discover -s "$project/ai/tests" -p test_mino.py -v
    exit
fi

mino status
mino --speak 'Mino, open VS Code'
mkdir -p "$HOME/Documents"
demo_dir="$(mktemp -d "$HOME/Documents/mino-demo.XXXXXXXX")"
mino --speak "create a file \"$demo_dir/notes.txt\" and write hello"
printf 'Demo file saved in %s\n' "$demo_dir"

printf 'Focus a window showing an error within 5 seconds. '
read -r -p 'Press Enter to start the countdown. '
sleep 5
mino --speak 'read my screen and explain this error'
mino --speak 'play Sourav Joshi latest vlog'
