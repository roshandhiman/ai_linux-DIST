# MineOS shell helpers, sourced from /etc/profile.d for interactive bash.
#
#   ?? <what you want>     suggest one shell command; you edit or press Enter to run it
#   (typo'd command)       a one-line hint about what you probably meant
#   ai                     the full assistant (see `ai --help`)
#
# What you type is passed to Python as an *argument*, never pasted into its
# source code, so quotes and $(...) in a request cannot run anything.

[[ $- == *i* ]] || return 0

_mineos_ask() {
    # $1 = system prompt, $2 = user text, $3 = timeout seconds
    python3 -I - "$1" "$2" "$3" <<'PY' 2>/dev/null
import sys
sys.path.insert(0, "/opt/ai")
from mineos_agent.config import load_config
from mineos_agent.llm import LLMError, OpenAIChat
from mineos_agent.text import one_line

system, user, timeout = sys.argv[1], sys.argv[2], float(sys.argv[3])
config = load_config()
config.llm.timeout = timeout
config.llm.max_tokens = 96
try:
    print(one_line(OpenAIChat(config.llm).complete(system=system, user=user), 300))
except LLMError:
    sys.exit(1)
PY
}

command_not_found_handle() {
    local cmd="$1"
    printf 'bash: %s: command not found\n' "$cmd" >&2
    local hint
    hint=$(_mineos_ask \
        "You help with Linux shell typos on Debian. In one short line, say the likely intended command or the apt package to install. No markdown." \
        "The user typed: $*" 6) || return 127
    [[ -n "$hint" ]] && printf '\033[0;32m  hint: %s\033[0m\n' "$hint" >&2
    return 127
}

??() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: ?? <what you want to do>    e.g.  ?? show the 5 biggest files here"
        return 1
    fi
    local suggestion
    suggestion=$(_mineos_ask \
        "Turn the request into ONE bash command for Debian Linux. Reply with only the command: no quotes, no markdown, no explanation." \
        "$*" 30) || { echo "The local model is not answering (try: ai --status)." >&2; return 1; }
    suggestion="${suggestion#\`}"; suggestion="${suggestion%\`}"
    [[ -z "$suggestion" ]] && { echo "No suggestion." >&2; return 1; }
    echo "Edit the command if needed, then Enter to run it, or Ctrl+C to cancel:"
    local line
    read -r -e -p '$ ' -i "$suggestion" line || { echo; return 130; }
    [[ -z "$line" ]] && return 0
    history -s -- "$line"
    eval -- "$line"
}
