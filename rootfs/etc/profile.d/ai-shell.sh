command_not_found_handle() {
    local cmd="$1"
    echo -e "\033[1;36m⚡ AI OS Kernel Diagnostic:\033[0m Command '\033[1;31m$cmd\033[0m' not found."
    python3 -c "
import urllib.request, json
prompt = 'In Linux bash, the user typed command \"$cmd\" which failed. In 1 short line, explain what package to install or what the correct command is.'
try:
    req = urllib.request.Request('http://127.0.0.1:11434/api/generate', data=json.dumps({'model': 'qwen2.5:1.5b', 'prompt': prompt, 'stream': False}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=4) as resp:
        res = json.loads(resp.read().decode())['response']
        print('\033[0;32m↳ Suggestion: ' + res.strip() + '\033[0m')
except Exception:
    pass
"
    return 127
}

??() {
    local query="$*"
    if [[ -z "$query" ]]; then
        echo "Usage: ?? <natural language instruction>"
        return 1
    fi

    echo -e "\033[1;36m⚡ Synthesizing command for:\033[0m $query"
    python3 -c "
import urllib.request, json, os
prompt = 'Translate this natural language query into a SINGLE exact Linux bash command. Output ONLY the bash command with no quotes, no markdown, no explanation: $query'
try:
    req = urllib.request.Request('http://127.0.0.1:11434/api/generate', data=json.dumps({'model': 'qwen2.5:1.5b', 'prompt': prompt, 'stream': False}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=5) as resp:
        cmd = json.loads(resp.read().decode())['response'].strip()
        print('\033[1;33m$ ' + cmd + '\033[0m')
        ans = input('Execute this command? [Y/n]: ')
        if ans.lower() in ['', 'y', 'yes']:
            os.system(cmd)
except Exception as e:
    print('AI unreachable: ' + str(e))
"
}

