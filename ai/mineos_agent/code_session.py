"""MineOS terminal host for the Freebuff-based coding engine."""

import json
import os
import re
import subprocess
from pathlib import Path

from .code_providers import add_provider, command_environment, private_write, remove_provider
from .coding import CodingProviders
from .llm import LLMError, ProviderUnavailable, ToolCallRejected

ENGINE = Path("/opt/ai/code/mineos-code-engine")
_TOOL_LABELS = {
    "list_dir": "List", "find_files": "Find", "file_info": "Inspect", "read_file": "Read",
    "write_file": "Create", "replace_text": "Edit", "delete_file": "Trash",
    "create_environment": "Environment", "run": "Run",
}
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def _display(value: str) -> str:
    return _CONTROL.sub("", value)


def _format_target(args: dict) -> str:
    return str(next((args[key] for key in ("path", "name", "command", "kind") if key in args), "."))


def _complete(model, original: dict) -> dict:
    payload = {**original, "model": model.model_id, "stream": False}
    payload.pop("stream_options", None)
    hint = payload.pop("max_completion_tokens", None) or payload.get("max_tokens") or 2048
    payload["max_tokens"] = min(hint, 1024 if model.config.provider == "local" else 2048)
    try:
        try:
            body = model.request_completion(payload)
        except ToolCallRejected:
            correction = {
                "role": "system",
                "content": "Use exactly one available tool per call. Encode its arguments as valid JSON.",
            }
            payload["messages"] = [correction, *payload["messages"]]
            payload["temperature"] = 0.2
            body = model.request_completion(payload)
        choices = body["choices"]
        if not choices or not isinstance(choices[0]["message"], dict):
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        if isinstance(exc, LLMError):
            raise
        raise ProviderUnavailable("invalid model response") from exc
    return body


def _send(process, packet: dict) -> None:
    process.stdin.write(json.dumps(packet, ensure_ascii=True) + "\n")
    process.stdin.flush()


def _engine_turn(process, agent, mode: str, previous: dict | None, prompt: str,
                 *, quiet: bool) -> tuple[bool, dict | None]:
    _send(process, {"type": "run", "cwd": str(agent.config.home), "prompt": prompt,
                    **({"previous": previous} if previous else {})})
    agent.api.declined.clear()
    saw_model = False
    for line in process.stdout:
        try:
            packet = json.loads(line)
        except ValueError:
            continue
        kind = packet["type"]
        if kind == "done":
            error = packet.get("error")
            if error:
                print(_display(error), flush=True)
                print("Use /resume to continue from the saved session.", flush=True)
            elif packet.get("answer"):
                print("\n" + _display(packet["answer"]), flush=True)
            return not error, packet.get("state") or previous
        if kind == "model":
            if not saw_model and not quiet:
                print(f"  · Working ({mode})", flush=True)
            saw_model = True
            try:
                if agent.api.declined:
                    result = {"error": "Tool action declined. The session is saved."}
                else:
                    body = agent.model.attempt(lambda model: _complete(model, packet["payload"]))
                    result = {"body": body}
            except LLMError as exc:
                result = {"error": str(exc)}
        elif kind == "tool":
            name, args = packet["name"], packet["args"]
            if name not in _TOOL_LABELS or not isinstance(args, dict):
                result = {"ok": False, "error": "Unknown project tool"}
            else:
                if not quiet:
                    print(f"  · {_TOOL_LABELS[name]}  {_display(_format_target(args))}", flush=True)
                if agent.api.declined:
                    result = {"ok": False, "error": "Tool action declined"}
                else:
                    ok, value = agent.api.dispatch(name, [], args)
                    result = {"ok": ok, "result" if ok else "error": value}
        else:
            continue
        _send(process, {"type": "result", "id": packet["id"], "data": result})
    print("The coding engine closed before the task finished.", flush=True)
    return False, previous


def _restore(path: Path) -> dict | None:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) and state.get("sessionState") else None


def _state_file(agent, mode: str) -> Path:
    return agent.config.memory_path.with_name(f"freebuff-{mode}.json")


def run_session(agent, prompt: str, *, quiet: bool, engine: Path = ENGINE) -> int:
    """Keep model credentials and approval UI in Python, outside the engine."""
    workspace = agent.config.home
    single = bool(prompt)
    mode = agent.model.selection
    state_path = _state_file(agent, mode)
    previous = _restore(state_path)
    if not single:
        try:
            import readline  # noqa: F401 - terminal history and line editing
        except ImportError:
            pass
        print(f"\n  MineOS Code  |  {workspace}\n"
              f"  {mode} · /providers · /model · /apiadd · /help\n", flush=True)
    environment = {key: value for key, value in command_environment().items()
                   if key in {"HOME", "PATH", "LANG", "LC_ALL", "TERM", "TMPDIR"}}
    with subprocess.Popen(
        [str(engine)], cwd=engine.parent, env=environment,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8",
    ) as process:
        try:
            while True:
                if not prompt:
                    try:
                        prompt = input("mineos> ").strip()
                    except (EOFError, KeyboardInterrupt):
                        return 0
                    if not prompt:
                        continue
                if prompt.startswith("/") or prompt.lower() == "continue":
                    command, _, argument = prompt.partition(" ")
                    argument = argument.strip()
                    try:
                        if command in ("/exit", "/quit"):
                            return 0
                        if command == "/help":
                            print("  /providers   Show models         /model NAME   Switch model\n"
                                  "  /apiadd      Add provider        /apiremove NAME\n"
                                  "  /resume      Continue task       /new          Clear session\n"
                                  "  /compact     Summarize context    /quit")
                        elif command in ("/providers", "/status"):
                            print(f"  Active: {mode}")
                            print("\n".join("  " + line for line in agent.model.status()))
                        elif command == "/model":
                            names = {"auto", *(model.config.provider for model in agent.model.models)}
                            if argument not in names:
                                print("  Select " + ", ".join(sorted(names)))
                            else:
                                mode = agent.model.selection = argument
                                state_path = _state_file(agent, mode)
                                previous = _restore(state_path)
                                print(f"  Model mode: {mode}")
                        elif command in ("/apiadd", "/apiremove"):
                            if command == "/apiadd":
                                name = add_provider()
                                print(f"  Saved {name}. Use /model {name} to select it.")
                            else:
                                remove_provider(argument)
                                if mode == argument:
                                    mode = "auto"
                                    state_path = _state_file(agent, mode)
                                    previous = _restore(state_path)
                                print(f"  Removed {argument}.")
                            refreshed = CodingProviders.from_environment(agent.on_event, include_local=True)
                            agent.model.models = refreshed.models
                            agent.model.selection = mode
                        elif command == "/new":
                            state_path.unlink(missing_ok=True)
                            previous = None
                            print("  New session.")
                        elif command in ("/resume", "/compact", "continue"):
                            if previous is None:
                                print("  There is no saved session.")
                            else:
                                prompt = ("/compact" if command == "/compact" else
                                          "Continue the previous task. Use the recorded tool results and do not repeat completed edits.")
                                command = ""
                        else:
                            print("  Unknown command. Type /help for commands.")
                    except (OSError, ValueError, EOFError, KeyboardInterrupt) as exc:
                        print("  " + (_display(str(exc)) or "Cancelled."))
                    if command:
                        if single:
                            return 0
                        prompt = ""
                        continue
                ok, previous = _engine_turn(process, agent, mode, previous, prompt, quiet=quiet)
                if previous and previous.get("sessionState"):
                    private_write(state_path, json.dumps(previous))
                if single:
                    return 0 if ok else 1
                prompt = ""
        except (BrokenPipeError, KeyboardInterrupt):
            return 1
        finally:
            process.stdin.close()
            if process.poll() is None:
                process.terminate()
