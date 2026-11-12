#!/usr/bin/env python3
import subprocess
import select
import json
import urllib.request
import os
import sys

LOG_FILE = "/var/log/ai-sentinel.log"

def analyze_kernel_event(line):
    prompt = f"A Linux kernel event occurred: '{line}'. In 1 sentence, explain what happened and if action is required."
    try:
        payload = {"model": "qwen2.5:1.5b", "prompt": prompt, "stream": False}
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "").strip()
    except Exception:
        return None

def main():
    try:
        proc = subprocess.Popen(["dmesg", "-w", "--level=emerg,alert,crit,err,warn"], stdout=subprocess.PIPE, text=True, bufsize=1)
    except Exception:
        sys.exit(0)

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if any(keyword in line.lower() for keyword in ["error", "fail", "oom", "corrupt", "kernel panic"]):
            explanation = analyze_kernel_event(line)
            with open(LOG_FILE, "a") as f:
                f.write(f"[KERNEL_ALERT] {line}\n")
                if explanation:
                    f.write(f"[AI_DIAGNOSIS] {explanation}\n")

if __name__ == "__main__":
    main()
