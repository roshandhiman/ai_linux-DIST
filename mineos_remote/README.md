# MineOS Remote

A phone-first Flutter web app, with a Serverpod 4 backend, for watching MineOS agent sessions. This round it streams **replays of recorded sessions** and labels them "Demo replay" everywhere.

## The real MineOS run log this app mirrors

Source (read-only): `ai/mineos_agent/agent.py` (`Agent._finish`, `Turn.record`), `os_api.py` (`_approve`, the gated `write_file` / `trash` / `run` / `device_send`), `cli.py` (`_approver`, the trace markers), `sandbox.py` (limits).

**Where.** Every request the `ai` agent handles appends one JSON line to `~/.local/state/mineos/runs/YYYY-MM-DD.jsonl` (`AgentConfig.runs_path`). The line is written once, **when the turn ends**. Nothing is written per step while the turn is running.

**One line = one turn:**

| Field | Meaning |
| --- | --- |
| `request` | What the user typed |
| `outcome` | `answered`, `exhausted`, `confused`, `stuck`, `offline` or `declined` |
| `answer` | The final reply shown to the user |
| `route` | The router's decision as text, e.g. `TASK 0.50 via rules` (intent, confidence, backend `rules` or Laya) |
| `mode` | `fast` (rules ran it directly), `chat` (one model call) or `tools` (the two-loop Python tool cycle) |
| `steps[]` | One entry per step that ran: `index`, `code` (the Python block), `output`, `error`, `attempts` (inner-loop tries), `calls` (the `mine.*` functions it called), `seconds` |
| `model_calls` | How many times the model was called |
| `peak_tokens` | The largest estimated prompt window |
| `seconds` | Wall time for the whole turn |
| `actions[]` | What it changed, e.g. `create ~/notes.md`, `ran ls -la`, `trashed ~/old.zip` |
| `declined[]` | Gated actions the user said no to |
| `notes[]` | Internal notes (retries, parse problems) |
| `at` | Local timestamp, `YYYY-MM-DDTHH:MM:SS` |
| `model` | The model id, `qwen2.5-1.5b-instruct` by default |

The provider is not in the log line. It comes from `/etc/mineos/agent.json` and `~/.config/mineos/agent.json` (`llm.provider`, default `local`, which is llama.cpp's `llama-server` on `127.0.0.1:8080`). The demo stores it per session so the app can prove a session never left the machine.

**The approval prompt.** Gated `mine` functions call `approver(action, detail)` before doing anything: `write_file`, `trash`, `run` and `device_send`. In the terminal this prints

```
  The assistant wants to: create ~/Documents/weekly-summary.md
        > (the first 160 characters of the text)
  Allow this? [y/N]
```

and only `y` or `yes` allows it. A non-interactive terminal always means no. A "no" ends the turn with outcome `declined`, and the action is listed in `declined[]`.

**Limits the demo data respects.** At most 12 `mine.*` calls per block. `find_files` returns at most 25 paths. `read_file` refuses files over 2 MB. `sudo` and friends are always refused. Each step gets 3 attempts (temperature 0.2, then 0.55, then 0.90). If a step uses up its attempts and the same error came at least twice, the turn ends as `stuck`. The default budget is 6 steps.

**How the demo maps it.** The app splits each real step into two timeline cards: a `model_call` (the model writing the block, the slow part on a CPU) and a `tool_call` (the sandboxed run with its code, output and `mine` calls). `plan` is the route, `error` is a refused block that was retried, `approval_request` is the y/N prompt, and `result` is the outcome and answer. The card text uses the CLI's own trace markers (`> route`, `. thinking`, `> code`, `< output`, `! ...`, `~ retrying`).
