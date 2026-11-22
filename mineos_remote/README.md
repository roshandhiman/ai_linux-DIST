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
cd mineos_remote
flutter pub get
dart run tool/init_local_secrets.dart
cd mineos_remote_server
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

## Android MVP

The same Flutter UI runs on Android. Install the Android SDK, then build:

```bash
cd mineos_remote/mineos_remote_flutter
flutter build apk --release --dart-define=SERVER_URL=https://YOUR_API_HOST/
```

The output is `build/app/outputs/flutter-apk/app-release.apk`. This is a demo APK signed with the scaffold's debug key, not a Play Store release. Internet permission is enabled in the release manifest. In the app, open **Server connection**, enter a hosted HTTPS API root, then **Test and connect**. The address is saved only after a successful sessions API call. A phone cannot reach the laptop through `localhost`.

If a temporary host drops WebSockets, the timeline falls back to real Serverpod HTTP snapshots every two seconds while the stream reconnects.

The root GitHub Actions workflow builds Android and web artifacts on changes to this project. Configure `MINEOS_REMOTE_SERVER_URL` as a repository variable to supply its default API address. The older workflows inside `mineos_remote/.github/` are scaffold examples and are not discovered by GitHub from this nested directory.

## Temporary demo hosting

When a temporary public demo has been explicitly approved, start the Serverpod runner, note its API port, and run from `mineos_remote/`:

```bash
dart run tool/demo_gateway.dart http://127.0.0.1:API_PORT/
# In another terminal, using the official Cloudflare CLI:
cloudflared tunnel --url http://127.0.0.1:54600 --protocol http2
```

Tunnel the gateway, never the full Serverpod API. It checks the four public fixture identities, limits HTTP to sessions.list/get, limits WebSocket frames to sessions.watch for those four IDs, forwards no credentials, and blocks all authentication, storage and Insights routes. Build web/Android with the resulting HTTPS URL as `SERVER_URL`. Only the app frontend is static-hosted; the backend remains the real local Serverpod service. This demo stops working when the laptop, runner, gateway or tunnel stops. A restarted tunnel may get a new address; change the API URL in app Settings.

## Permanent deployment (account login required)

Run `serverpod cloud auth login`, then `serverpod cloud launch` with the database enabled, then `serverpod cloud deploy`. When the server serves the app, `/assets/assets/config.json` gives the app the server's own public API URL, so no URL is hard-coded. No secrets are in Git: `config/passwords.yaml` is ignored, and production secrets go in Serverpod Cloud's secret store.

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
- [ ] Serverpod Cloud launch and deploy (deferred)

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
