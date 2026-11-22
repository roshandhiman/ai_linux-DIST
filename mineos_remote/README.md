# MineOS Remote

A phone-first Flutter web app, with a Serverpod 4 backend, for watching MineOS agent sessions. This round it streams **replays of recorded sessions** and labels them "Demo replay" everywhere.

## Architecture

```
mineos_remote/
  mineos_remote_server/    Serverpod 4.1.2 server (Postgres)
    lib/src/sessions/
      protocol/*.spy.yaml  models: AgentSession 1─n AgentStep, ReplayEvent, SessionDetail, enums
      demo_recordings.dart the 4 recorded sessions (mirrors the real run log, see below)
      seed.dart            idempotent seed, run once on every server start
      replay_plan.dart     replay timing (model calls slow, sandbox runs fast)
      sessions_endpoint.dart  list() / get() / watch() — read-only
    test/integration/sessions_endpoint_test.dart
  mineos_remote_client/    generated client (never edit)
  mineos_remote_flutter/   Flutter web app (Riverpod 3)
    lib/main.dart          ProviderScope + theme
    lib/client.dart        server URL: --dart-define=SERVER_URL, else assets/config.json, else localhost:8080
    lib/src/providers.dart sessions, session detail, TimelineNotifier (stream + reconnect backoff 1/2/4/8/15 s)
    lib/src/*_screen.dart  Sessions, Session detail, About
```

**Endpoint `sessions`** (no auth, read-only):

| Method | Returns |
| --- | --- |
| `list()` | All sessions, newest first. A running session's step count and times reflect where its replay is now. |
| `get(sessionId)` | The session plus the steps revealed so far. |
| `watch(sessionId, resumeFrom)` | `Stream<ReplayEvent>`: `restart`, then `step` events 1–3 s apart (4.5–8 s before a model call, with a `thinking` event first). A **running** session loops forever on a shared clock, so two phones see the same step at the same time. An **awaiting** session ends with `holding` at the approval step. Done/failed end with `finished`. |

Unknown ids throw `SessionNotFoundException`.

## Running locally

Needs Flutter (3.50+) and the Serverpod CLI 4.1.2. No Docker: the dev and test databases are embedded Postgres.

```
cd mineos_remote/mineos_remote_server
serverpod start            # server + embedded Postgres + the Flutter app; migrations apply on start
```

Or step by step:

```
cd mineos_remote/mineos_remote_server
serverpod run flutter_build              # builds the web app into web/app
dart bin/main.dart --apply-migrations    # API :8080, app at http://localhost:8082/
dart test                                # server tests
cd ../mineos_remote_flutter && flutter analyze
```

The demo sessions are seeded on first start. Restarting never duplicates them.

## Deployed

Serverpod Cloud project **`mineos-remote`** (starter plan, with a database). `mineos_remote_server/scloud.yaml` links the server folder to it, so the cloud commands below need no `--project`.

| What | URL |
| --- | --- |
| App (open this on a phone) | https://mineos-remote.serverpod.space/ |
| API | https://mineos-remote.api.serverpod.space/ |
| Insights | https://mineos-remote.insights.serverpod.space/ |

The server serves the Flutter web app itself. `/assets/assets/config.json` gives the app the server's own public API URL, so no URL is hard-coded.

## For teammates: improve the Flutter app and deploy

### One-time setup

1. Install Flutter 3.50+ and the Serverpod CLI 4.1.2, following [docs.flutter.dev](https://docs.flutter.dev/get-started/install) and [docs.serverpod.dev](https://docs.serverpod.dev/). Check with `flutter --version` and `serverpod version`.
   - Windows: if a command is "not recognised", its `bin` folder isn't on your PATH yet. Add it under *Edit environment variables for your account*, then open a **new** terminal (restart VS Code completely; a new tab inside it keeps the old PATH).
2. Get the code and fetch the packages:
   ```
   git fetch
   git checkout flutter-remote
   cd mineos_remote/mineos_remote_server && dart pub get
   cd ../mineos_remote_flutter && flutter pub get
   ```
3. Deploy access:
   - The project owner invites you once: `serverpod cloud project user invite <your email>`.
   - Then, from `mineos_remote_server`, run `serverpod cloud auth login`. It opens a browser.
   - You don't need `project link`, because `scloud.yaml` is already in Git.

### Where to change things

| To change | Edit |
| --- | --- |
| Screens | `mineos_remote_flutter/lib/src/sessions_screen.dart`, `session_detail_screen.dart`, `about_screen.dart` |
| Timeline cards, shared widgets | `mineos_remote_flutter/lib/src/step_card.dart`, `widgets.dart` |
| Data loading, the live stream, reconnect | `mineos_remote_flutter/lib/src/providers.dart` |
| Theme, colours, fonts | `mineos_remote_flutter/lib/src/theme.dart` |
| Which server the app talks to | `mineos_remote_flutter/lib/client.dart` (don't hard-code the production URL; the deployed app reads `config.json`) |
| Demo data | `mineos_remote_server/lib/src/sessions/demo_recordings.dart` |

Ground rules:

- Keep the **Demo replay** label visible. Never present replayed data as live.
- Never edit generated code by hand: `mineos_remote_client/` and `mineos_remote_server/lib/src/generated/`.
- If you change a model (`*.spy.yaml`) or an endpoint's signature, regenerate with `serverpod generate`.
- If you change a model that has a `table`, also run `serverpod create-migration` and commit the new folder under `migrations/`. Pending migrations are applied when the server starts, locally and on Cloud.
- No secrets in Git. `config/passwords.yaml` is ignored and must stay that way. Production secrets go in Serverpod Cloud (`serverpod cloud password …` / `serverpod cloud variable set --secret …`).

### Work locally

```
cd mineos_remote/mineos_remote_server
serverpod start        # server + embedded Postgres + the app, with hot reload
```

Before you deploy, check that nothing is broken:

```
cd mineos_remote/mineos_remote_flutter && flutter analyze     # expect 0 errors, 0 warnings (see Known issues)
cd ../mineos_remote_server && dart test                       # expect all tests to pass
```

### Deploy

Always run these from `mineos_remote_server`:

```
cd mineos_remote/mineos_remote_server
serverpod run flutter_build      # REQUIRED if you changed the app: builds it into web/app
serverpod cloud deploy           # uploads the server + web/app, builds and restarts on Cloud
```

**Why the build step matters:**

- Serverpod Cloud does **not** build the Flutter app (`scloud.yaml` has no `pre_deploy` script). It ships whatever is in `web/app` on your machine.
- `web/app` is git-ignored, so on a fresh clone it doesn't exist. Without `flutter_build`, you deploy an old app, or no app at all.

To see what would be uploaded without deploying, run `serverpod cloud deploy --wet-run --show-files`.

### Check the deploy

```
serverpod cloud status deployment show    # did the latest deploy succeed?
serverpod cloud log --since 15m           # recent server logs (or: serverpod cloud log --tail)
curl -X POST https://mineos-remote.api.serverpod.space/sessions -H "Content-Type: application/json" -d '{"method":"list"}'
```

- The `curl` call should print the 4 demo sessions as JSON.
- In Windows PowerShell, write `curl.exe` and escape the quotes: `-d '{\"method\":\"list\"}'`.
- Finally, open https://mineos-remote.serverpod.space/ on a phone. Open the running session on two devices; both should show the same step at the same time.

### Undo a bad deploy

Check out the last good commit, rebuild and deploy again:

```
git checkout <good-commit> -- mineos_remote
cd mineos_remote/mineos_remote_server
serverpod run flutter_build
serverpod cloud deploy
```

If you only changed Cloud passwords or variables, `serverpod cloud deploy --redeploy` restarts the current build with them, without uploading anything.

## Next round: live mode

- A small agent-side bridge on the MineOS machine tails `~/.local/state/mineos/runs/*.jsonl`. It also needs a per-step hook, because the real log is written only when a turn ends. The bridge pushes steps to the server, which already has the right models and the `watch()` stream.
- Approve/Deny from the phone: the agent's `approver(action, detail)` callback waits on the server for an answer, with sign-in (the scaffold's email auth is already wired) and a timeout that defaults to **no**, just like a non-interactive terminal today.
- Keep "Local" honest: show it only when the run's provider was `local`.

## Checklist

- [x] Serverpod quickstart project in `mineos_remote/`, nothing outside it touched
- [x] Models with a one-to-many relation, migration, idempotent seed on startup
- [x] `list()` newest first, `get()`, streaming `watch()` (looping running session, holding awaiting session)
- [x] Server tests for `list()` and for `watch()` ordering, looping and holding (7/7 pass)
- [x] Sessions screen: "Demo replay" chip, status badges, model, elapsed time, step count, Local badge with tooltip, pull to refresh
- [x] Detail screen: live timeline, kind icons, expandable monospace detail, durations, animate-in, auto-scroll, "thinking…" indicator
- [x] Approval banner with the exact action; Approve/Deny disabled, "Coming next: approve from your phone"
- [x] About screen
- [x] Loading, empty, error-with-retry and stream-reconnect states
- [x] `flutter analyze`: 0 errors, 0 warnings (9 infos, see Known issues)
- [x] Serverpod Cloud project `mineos-remote` created and deployed (web, API and seeded demo data verified)

## Known issues

- `flutter analyze` reports 9 infos: Flutter 3.50 deprecates `package:flutter/material.dart` in favour of the separate `material_ui` package. The project keeps `flutter/material.dart` because the scaffold's Serverpod auth widgets still use it, and mixing the two copies of Material risks type clashes.
- Opening an awaiting, done or failed session replays it from step 1. Only the running session follows a shared clock.
- The scaffold's example `greeting` endpoint and screens are still in the project, unused by the app.

## 3-minute demo script

1. **(0:00) Open the app on a phone.** Point at the **Demo replay** chip: "These are recorded MineOS agent sessions, replayed. Nothing here is pretending to be live."
2. **(0:20) The list.** Four sessions, newest first: Running (pulsing), Awaiting approval (amber), Done, Failed. Tap the **Local** badge: "Ran on-device. No data left the machine." Every one used Qwen2.5 1.5B on llama.cpp, on the CPU.
3. **(0:45) Open the running session.** Steps arrive one by one. Model calls take longest, which is honest for a 1.5B model on a laptop CPU. Point at the "thinking…" line. Expand a `tool_call`: the real Python block, its output, and the `mine.*` calls. Expand the `error` step: the agent refused its own block (too many calls) and retried.
4. **(1:30) Open a second phone or tab** on the same session. Both show the same step at the same time.
5. **(1:50) Back, then open Awaiting approval.** It replays up to the y/N prompt and stops. The amber banner says exactly what it wants to do: `create ~/Documents/weekly-summary.md`. Approve/Deny are disabled: "Coming next: approve from your phone." Nothing is written until someone answers.
6. **(2:20) Open Failed.** The model tried `sudo`, the sandbox refused it, three attempts later the agent stopped as STUCK instead of guessing.
7. **(2:40) Pull the plug.** Stop the server: the reconnect banner counts down. Start it again and the stream resumes. Close on About: live mode next round, with approvals from the phone.

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
