"""The ``ai`` command.

    ai                          interactive session
    ai code                     workspace coding session
    ai "open the browser"       one request, then exit
    ai --status                 is the model up, which router, which sandbox
    ai --memory                 what the assistant remembers about you
    ai --forget "priya"         delete what it remembers about something
    ai --quiet ...              hide the step-by-step trace

The trace is on by default because this is the build where the features get
tested: it shows the route, every block of code the model wrote, what it
printed, and the cost. ``--quiet`` hides it for normal use.
"""

import argparse
import os
import shutil
import subprocess
import sys
from functools import partial
from pathlib import Path

from . import __version__
from .agent import Agent, Outcome, Turn
from .coding import CodingProviders, build_coding_agent, project_root
from .config import AgentConfig, load_config
from .memory import GraphMemory
from .os_api import OsApi
from .providers import PRESETS, build_model, check_health, describe
from .router import HybridRouter, LayaRouter
from .sandbox import Sandbox
from .text import fold_ascii, quote_block

_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.name != "nt"


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def _out(text: str = "", *, end: str = "\n") -> None:
    sys.stdout.write(fold_ascii(text) + end)
    sys.stdout.flush()


def _deal_review(request: str, options: list[str] | None = None) -> int | None:
    try:
        from dealreview.intent import matches
    except ImportError:
        return None
    if options is None and not matches(request):
        return None
    binary = shutil.which("mino-review")
    if not binary:
        _out("Install Deal Review with scripts/install-dealreview.sh.")
        return 1
    arguments = options if options is not None else ["--prompt", request, "--autorun"]
    return subprocess.call([binary, *arguments])


def _indent(text: str, mark: str = "|", limit: int = 14) -> str:
    lines = text.rstrip().splitlines() or [""]
    shown = lines[:limit]
    body = "\n".join(f"    {mark} {line}" for line in shown)
    if len(lines) > limit:
        body += f"\n    {mark} ... {len(lines) - limit} more line(s)"
    return body


class Trace:
    """Prints agent events as they happen."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.streamed = False

    def __call__(self, kind: str, text: str) -> None:
        if kind == "chunk":
            self.streamed = True
            sys.stdout.write(fold_ascii(text))
            sys.stdout.flush()
            return
        if kind == "provider":
            _out(_c("33", f"  ~ {text}"))
            return
        if not self.enabled:
            return
        if kind == "route":
            _out(_c("2", f"  > route  {text}"))
        elif kind == "think":
            _out(_c("2", f"  . thinking ({text})"))
        elif kind == "code":
            _out(_c("36", "  > code") + "\n" + _c("36", _indent(text)))
        elif kind == "output":
            _out(_c("2", "  < output") + "\n" + _c("2", _indent(text)))
        elif kind == "error":
            _out(_c("33", f"  ! {text}"))
        elif kind == "retry":
            _out(_c("33", f"  ~ retrying: {text}"))


def _approver(action: str, detail: str, *, full_detail: bool = False) -> bool:
    """Ask on the terminal. No terminal means no."""
    if not sys.stdin.isatty():
        _out(_c("33", f"  ! needs your OK, but this is not an interactive terminal: {action}"))
        return False
    _out(_c("1;33", f"\n  The assistant wants to: {action}"))
    if detail:
        if full_detail:
            sys.stdout.write(quote_block(detail, limit=1_000_000, max_lines=200_001,
                                         preserve_layout=True) + "\n")
            sys.stdout.flush()
        else:
            _out(_indent(detail, ">", 8))
    try:
        answer = input("  Allow this? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        _out()
        return False
    return answer in ("y", "yes")


def build_agent(config: AgentConfig, *, trace: Trace) -> Agent:
    memory = GraphMemory(config.memory_path)
    laya = (LayaRouter(config.router.url, checkpoint=config.router.checkpoint,
                       timeout=config.router.timeout)
            if config.router.url else None)
    return Agent(
        model=build_model(config.llm),
        api=OsApi(home=config.home, memory=memory, approver=_approver),
        router=HybridRouter(laya=laya, threshold=config.router.threshold),
        memory=memory,
        config=config,
        sandbox=Sandbox(timeout=config.code_timeout),
        on_event=trace,
        stream=True,
    )


def _show_turn(turn: Turn, trace: Trace) -> None:
    if trace.streamed:
        _out()
        trace.streamed = False
    else:
        style = "1" if turn.outcome is Outcome.ANSWERED else "1;33"
        _out(_c(style, turn.answer))
    # What the harness actually did, independent of what the model said.
    for action in turn.declined:
        _out(_c("33", f"  not done (you said no): {action}"))
    if trace.enabled and turn.actions:
        _out(_c("2", "  done: " + "; ".join(turn.actions)))
    if trace.enabled:
        bits = [turn.mode]
        if turn.model_calls:
            bits.append(f"{turn.model_calls} model call(s)")
        if turn.steps:
            bits.append(f"{len(turn.steps)} step(s)")
        if turn.peak_tokens:
            bits.append(f"~{turn.peak_tokens} tokens")
        bits.append(f"{turn.seconds:.1f}s")
        if not turn.ok:
            bits.append(str(turn.outcome))
        _out(_c("2", "  (" + ", ".join(bits) + ")"))


def show_status(config: AgentConfig, agent: Agent) -> int:
    ok, detail = check_health(config.llm)
    stats = agent.memory.stats()
    _out(f"MineOS assistant {__version__}")
    _out(f"  model     {config.llm.model} at {config.llm.base_url}")
    _out(f"  provider  {describe(config.llm)}")
    _out(f"  server    {'OK' if ok else 'NOT REACHABLE'}: {detail}")
    _out(f"  router    {agent.router.describe()}")
    laya = getattr(agent.router, "laya", None)
    if laya is not None:
        up, said = laya.health()
        _out(f"  laya      {'OK' if up else 'NOT REACHABLE (rules still work)'}: {said}")
    _out(f"  sandbox   {agent.sandbox.describe()}")
    _out(f"  memory    {config.memory_path} ({stats['facts']} facts, "
         f"{stats['tasks']} tasks, {stats['episodes']} past requests)")
    _out(f"  context   {config.llm.context} tokens, {config.max_steps} steps x {config.max_attempts} tries")
    for warning in config.warnings:
        _out(_c("33", f"  warning   {warning}"))
    return 0 if ok else 1


def show_memory(agent: Agent) -> int:
    facts = agent.memory.facts(limit=50)
    _out("What I remember:" if facts else "I don't remember anything yet. Try: remember that my name is Sam")
    for fact in facts:
        _out(f"  {fact}")
    tasks = agent.memory.tasks(limit=5)
    if tasks:
        _out("\nTasks:")
        for task in tasks:
            mark = "unfinished - say 'continue'" if task.status == "open" else task.status
            _out(f"  [{mark}] {task.request[:70]} ({len(task.steps)} step(s))")
            for note in task.notes[-3:]:
                _out(f"      noted: {note}")
    episodes = agent.memory.episodes(limit=5)
    if episodes:
        _out("\nRecent requests:")
        for _, request, _answer, outcome in episodes:
            _out(f"  [{outcome}] {request}")
    return 0


def show_history(agent: Agent, before: int | None = None) -> int:
    rows = agent.memory.history(before=before)
    if not rows:
        _out("No further requests in shared history.")
        return 0
    for identifier, _, request, answer, channel in rows:
        _out(f"#{identifier} [{channel}] {request}")
        if answer:
            _out(answer)
        _out()
    if len(rows) == 15:
        _out(f"Earlier requests: ai --history --before {rows[-1][0]}")
    return 0


_HELP = """Type what you want in plain words. Examples:
  open the browser              volume 40
  what's using my disk space    search youtube for lofi music
  remember that my sister is Priya
  find my pdf files in downloads and tell me the biggest
  continue                      pick up a task that ran out of steps
Commands: /status  /memory  /forget <thing>  /clear  /trace  /quit"""


_CODING_HELP = """Ask MineOS Code to inspect the project, make a change, or run tests.
  Add input validation and test the error cases
  Review the authentication changes
  continue   resume the latest unfinished task in this project
Commands: /status  /memory  /history  /clear  /trace  /quit"""


def repl(agent: Agent, trace: Trace, config: AgentConfig, *,
         coding: CodingProviders | None = None) -> int:
    try:
        import readline  # noqa: F401 - line editing and history where available
    except ImportError:
        pass
    help_text = _CODING_HELP if coding else _HELP
    title = f"MineOS Code · {config.home}" if coding else "MineOS assistant"
    _out(_c("1", title) + "  (type /help for examples, /quit to leave)")
    if coding:
        _coding_status(config.home, coding)
    else:
        ok, detail = check_health(agent.config.llm, timeout=2)
        if not ok:
            _out(_c("33", f"  note: {detail}. Simple commands still work."))
    while True:
        try:
            line = input(_c("1;35", "code> " if coding else "mine> ")).strip()
        except (EOFError, KeyboardInterrupt):
            _out()
            return 0
        if not line:
            continue
        if not coding and _deal_review(line) is not None:
            continue
        if line.startswith("/"):
            command, _, arg = line.partition(" ")
            if command in ("/quit", "/exit", "/q"):
                return 0
            if command == "/help":
                _out(help_text)
            elif command == "/status":
                if coding:
                    _coding_status(config.home, coding)
                else:
                    show_status(config, agent)
            elif command == "/memory":
                show_memory(agent)
            elif command == "/history":
                if arg and not arg.isdecimal():
                    _out("Usage: /history [before-id]")
                else:
                    show_history(agent, int(arg) if arg else None)
            elif command == "/forget" and arg:
                _out(agent.api.forget(arg))
            elif command == "/clear":
                agent.recent.clear()
                _out("Conversation cleared (stored facts are kept; use /forget for those).")
            elif command == "/trace":
                trace.enabled = not trace.enabled
                _out(f"Trace {'on' if trace.enabled else 'off'}.")
            else:
                _out("Unknown command. " + help_text.splitlines()[-1])
            continue
        try:
            turn = agent.turn(line)
        except KeyboardInterrupt:
            _out(_c("33", "\n  stopped."))
            continue
        _show_turn(turn, trace)


def _coding_status(workspace: Path, providers: CodingProviders) -> int:
    _out(f"  Project: {workspace}")
    for line in providers.status():
        _out(f"  {line}")
    return 0 if any(providers.usable(model) for model in providers.models) else 1


def _code(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="ai code", description="The MineOS coding agent.")
    parser.add_argument("request", nargs="*", help="coding request, or omit for a session")
    parser.add_argument("--status", action="store_true", help="show project and provider key status")
    parser.add_argument("-q", "--quiet", action="store_true", help="hide the step-by-step trace")
    parser.add_argument("--local", action="store_true", help="use only the on-device model")
    from .code_session import ENGINE, run_session

    args = parser.parse_args(argv)
    has_engine = ENGINE.is_file() and os.access(ENGINE, os.X_OK)
    trace = Trace(enabled=not args.quiet and not has_engine)
    workspace = project_root(Path.cwd())
    try:
        providers = CodingProviders.from_environment(trace, include_local=True)
    except (OSError, ValueError) as exc:
        _out(str(exc))
        return 1
    if args.local:
        providers.selection = "local"
    if args.status:
        return _coding_status(workspace, providers)

    agent = build_coding_agent(workspace, providers, trace=trace,
                               approver=partial(_approver, full_detail=True))
    try:
        if has_engine:
            return run_session(agent, " ".join(args.request), quiet=args.quiet)
        if not args.request:
            return repl(agent, trace, agent.config, coding=providers)
        turn = agent.turn(" ".join(args.request))
        _show_turn(turn, trace)
        return 0 if turn.ok else 1
    finally:
        agent.memory.close()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["dealreview"]:
        result = _deal_review("", argv[1:])
        if result is None:
            _out("Install Deal Review with scripts/install-dealreview.sh.")
            return 1
        return result
    if argv and not argv[0].startswith("-") and argv[0] != "code":
        result = _deal_review(" ".join(argv))
        if result is not None:
            return result
    if argv[:1] == ["code"]:
        return _code(argv[1:])
    parser = argparse.ArgumentParser(
        prog="ai", description="The MineOS assistant. Run ai code for the coding agent."
    )
    parser.add_argument("request", nargs="*", help="what you want done; omit for a session")
    parser.add_argument("--status", action="store_true", help="check the model server and setup")
    parser.add_argument("--memory", action="store_true", help="show what the assistant remembers")
    parser.add_argument("--history", action="store_true", help="show shared IDE and Terminal history")
    parser.add_argument("--before", type=int, metavar="ID", help="show history before the given request ID")
    parser.add_argument("--forget", metavar="THING", help="delete what it remembers about THING")
    parser.add_argument("-q", "--quiet", action="store_true", help="hide the step-by-step trace")
    parser.add_argument("--provider", choices=sorted(PRESETS),
                        help="which model provider (default: local; hosted ones need a key)")
    parser.add_argument("--url", help="model server base URL")
    parser.add_argument("--model", help="model name to request")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    config = load_config(provider=args.provider)
    if args.url:
        config.llm.base_url = args.url.rstrip("/")
    if args.model:
        config.llm.model = args.model
    trace = Trace(enabled=not args.quiet)
    agent = build_agent(config, trace=trace)
    try:
        if args.status:
            return show_status(config, agent)
        if args.memory:
            return show_memory(agent)
        if args.history:
            return show_history(agent, args.before)
        if args.forget:
            _out(agent.api.forget(args.forget))
            return 0
        if args.request:
            turn = agent.turn(" ".join(args.request))
            _show_turn(turn, trace)
            return 0 if turn.ok else 1
        return repl(agent, trace, config)
    finally:
        agent.memory.close()


if __name__ == "__main__":
    sys.exit(main())
