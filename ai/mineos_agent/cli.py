"""The ``ai`` command.

    ai                          interactive session
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
import sys

from . import __version__
from .agent import Agent, Outcome, Turn
from .config import AgentConfig, load_config
from .llm import OpenAIChat, health
from .memory import GraphMemory
from .os_api import OsApi
from .router import HybridRouter, LayaRouter
from .sandbox import Sandbox
from .text import fold_ascii

_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.name != "nt"


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def _out(text: str = "", *, end: str = "\n") -> None:
    sys.stdout.write(fold_ascii(text) + end)
    sys.stdout.flush()


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


def _approver(action: str, detail: str) -> bool:
    """Ask on the terminal. No terminal means no."""
    if not sys.stdin.isatty():
        _out(_c("33", f"  ! needs your OK, but this is not an interactive terminal: {action}"))
        return False
    _out(_c("1;33", f"\n  The assistant wants to: {action}"))
    if detail:
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
        model=OpenAIChat(config.llm),
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
    ok, detail = health(config.llm)
    key = "set (hosted model)" if config.llm.api_key else "none (local model, nothing leaves this machine)"
    stats = agent.memory.stats()
    _out(f"MineOS assistant {__version__}")
    _out(f"  model     {config.llm.model} at {config.llm.base_url}")
    _out(f"  server    {'OK' if ok else 'NOT REACHABLE'}: {detail}")
    _out(f"  api key   {key}")
    _out(f"  router    {agent.router.describe()}")
    laya = getattr(agent.router, "laya", None)
    if laya is not None:
        up, said = laya.health()
        _out(f"  laya      {'OK' if up else 'NOT REACHABLE (rules still work)'}: {said}")
    _out(f"  sandbox   {agent.sandbox.describe()}")
    _out(f"  memory    {config.memory_path} ({stats['facts']} facts, {stats['episodes']} past requests)")
    _out(f"  context   {config.llm.context} tokens, {config.max_steps} steps x {config.max_attempts} tries")
    for warning in config.warnings:
        _out(_c("33", f"  warning   {warning}"))
    return 0 if ok else 1


def show_memory(agent: Agent) -> int:
    facts = agent.memory.facts(limit=50)
    _out("What I remember:" if facts else "I don't remember anything yet. Try: remember that my name is Sam")
    for fact in facts:
        _out(f"  {fact}")
    episodes = agent.memory.episodes(limit=5)
    if episodes:
        _out("\nRecent requests:")
        for _, request, _answer, outcome in episodes:
            _out(f"  [{outcome}] {request}")
    return 0


_HELP = """Type what you want in plain words. Examples:
  open the browser              volume 40
  what's using my disk space    search youtube for lofi music
  remember that my sister is Priya
  find my pdf files in downloads and tell me the biggest
Commands: /status  /memory  /forget <thing>  /clear  /trace  /quit"""


def repl(agent: Agent, trace: Trace, config: AgentConfig) -> int:
    try:
        import readline  # noqa: F401 - line editing and history where available
    except ImportError:
        pass
    ok, detail = health(agent.config.llm, timeout=2)
    _out(_c("1", "MineOS assistant") + "  (type /help for examples, /quit to leave)")
    if not ok:
        _out(_c("33", f"  note: {detail}. Simple commands still work."))
    while True:
        try:
            line = input(_c("1;35", "mine> ")).strip()
        except (EOFError, KeyboardInterrupt):
            _out()
            return 0
        if not line:
            continue
        if line.startswith("/"):
            command, _, arg = line.partition(" ")
            if command in ("/quit", "/exit", "/q"):
                return 0
            if command == "/help":
                _out(_HELP)
            elif command == "/status":
                show_status(config, agent)
            elif command == "/memory":
                show_memory(agent)
            elif command == "/forget" and arg:
                _out(agent.api.forget(arg))
            elif command == "/clear":
                agent.recent.clear()
                _out("Conversation cleared (stored facts are kept; use /forget for those).")
            elif command == "/trace":
                trace.enabled = not trace.enabled
                _out(f"Trace {'on' if trace.enabled else 'off'}.")
            else:
                _out("Unknown command. " + _HELP.splitlines()[-1])
            continue
        try:
            turn = agent.turn(line)
        except KeyboardInterrupt:
            _out(_c("33", "\n  stopped."))
            continue
        _show_turn(turn, trace)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai", description="The MineOS assistant.")
    parser.add_argument("request", nargs="*", help="what you want done; omit for a session")
    parser.add_argument("--status", action="store_true", help="check the model server and setup")
    parser.add_argument("--memory", action="store_true", help="show what the assistant remembers")
    parser.add_argument("--forget", metavar="THING", help="delete what it remembers about THING")
    parser.add_argument("-q", "--quiet", action="store_true", help="hide the step-by-step trace")
    parser.add_argument("--url", help="model server base URL (OpenAI-compatible)")
    parser.add_argument("--model", help="model name to request")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    config = load_config()
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
