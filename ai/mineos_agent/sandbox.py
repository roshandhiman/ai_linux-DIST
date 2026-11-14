"""The model's one tool: run a block of Python, safely.

Three layers, each of which would be insufficient alone:

1. **Static check** (:func:`validate`). Before anything runs, the code is
   parsed and refused if it imports outside a short allowlist, names a
   dangerous builtin, or touches any attribute starting with ``_`` (which is
   how every classic Python sandbox escape begins: ``().__class__...``). The
   refusal is one sentence the model can act on, and it costs no process.
2. **A separate process with nothing in it** (``_child.py``). Restricted
   builtins, no ``open``, no ``os``; modules are handed over as filtered
   namespaces. The only way out is the ``mine`` object, whose every call is a
   message to *this* process, checked against :mod:`mineos_agent.os_api`.
3. **The kernel.** On Linux the child runs under ``bubblewrap`` with no
   network, a read-only ``/usr`` and an empty ``/tmp``, plus CPU, memory and
   file-size limits. If a clever escape beat layers 1 and 2, it would land in
   a box that cannot see the user's files or the internet.

Layer 3 is the real boundary. Layers 1 and 2 exist so that the honest mistakes
of a 1.5B model get a fast, readable error instead of a kernel refusal.
"""

import ast
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Final

__all__ = [
    "ALLOWED_IMPORTS",
    "RunResult",
    "Sandbox",
    "validate",
]

ALLOWED_IMPORTS: Final[frozenset[str]] = frozenset(
    {
        "math", "json", "re", "datetime", "statistics", "random",
        "itertools", "collections", "textwrap",
    }
)

_BANNED_NAMES: Final[frozenset[str]] = frozenset(
    {
        "eval", "exec", "compile", "open", "__import__", "globals", "locals",
        "vars", "getattr", "setattr", "delattr", "hasattr", "input", "breakpoint",
        "exit", "quit", "type", "object", "super", "memoryview", "help", "dir",
        "classmethod", "staticmethod", "property",
    }
)

_BANNED_ATTRS: Final[frozenset[str]] = frozenset(
    {
        "gi_frame", "gi_code", "gi_yieldfrom", "cr_frame", "cr_code", "cr_await",
        "ag_frame", "ag_code", "ag_await", "f_back", "f_globals", "f_locals",
        "f_builtins", "f_code", "tb_frame", "tb_next", "format", "format_map",
        "mro",
    }
)

#: What the model is told when it reaches for something it cannot have.
_USE_MINE = "use the mine functions for anything that touches the computer"

#: Calls to ``mine`` per run. A loop that opens forty windows is a bug, not a
#: request, and is stopped here rather than discovered on the user's screen.
MAX_CALLS_PER_RUN: Final[int] = 12

#: Characters of printed output kept from one run.
MAX_OUTPUT: Final[int] = 4000

_CHILD: Final[Path] = Path(__file__).with_name("_child.py")


def validate(code: str) -> str | None:
    """``None`` if the code may run, else one actionable sentence."""
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg} (line {exc.lineno})"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Small models "import mine" out of habit. It is already
                # there, so the import is allowed and does nothing.
                if alias.name == "mine" and alias.asname in (None, "mine"):
                    continue
                if alias.name not in ALLOWED_IMPORTS:
                    return (
                        f"import {alias.name} is not allowed; {_USE_MINE}. "
                        f"Allowed imports: {', '.join(sorted(ALLOWED_IMPORTS))}"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module not in ALLOWED_IMPORTS:
                return f"from {node.module} import is not allowed; {_USE_MINE}"
            for alias in node.names:
                if alias.name == "*" or alias.name.startswith("_"):
                    return f"from {node.module} import {alias.name} is not allowed"
        elif isinstance(node, ast.Name):
            if node.id in _BANNED_NAMES:
                return f"{node.id}() is not available here; {_USE_MINE}"
            if node.id.startswith("__"):
                return f"the name {node.id} is not available here"
        elif isinstance(node, ast.Attribute):
            if node.attr in ("format", "format_map"):
                # str.format can walk attributes from inside the string
                # ("{0.__class__}"), which no AST check can see.
                return "str.format is not available here; use an f-string instead"
            if node.attr.startswith("_") or node.attr in _BANNED_ATTRS:
                return f"the attribute .{node.attr} is not available here"
        elif isinstance(node, ast.MatchClass):
            for attr in node.kwd_attrs:
                if attr.startswith("_") or attr in _BANNED_ATTRS:
                    return f"the attribute {attr} is not available here"
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            return "global and nonlocal are not needed here; return values instead"
    return None


@dataclass(slots=True)
class RunResult:
    ok: bool
    output: str = ""
    error: str | None = None
    #: ``mine`` functions that were called *and succeeded*, in order.
    calls: list[str] = field(default_factory=list)
    seconds: float = 0.0


#: ``dispatch(fn, args, kwargs) -> (ok, value_or_error)``, provided by os_api.
Dispatch = Callable[[str, list, dict], tuple[bool, object]]


def _limits() -> None:  # pragma: no cover - runs in the child on POSIX only
    import resource

    for name, value in (
        ("RLIMIT_CPU", 15),
        ("RLIMIT_AS", 1 << 30),
        ("RLIMIT_FSIZE", 1 << 20),
        ("RLIMIT_CORE", 0),
    ):
        try:
            limit = getattr(resource, name)
            resource.setrlimit(limit, (value, value))
        except (AttributeError, ValueError, OSError):
            pass
    os.setsid()


@dataclass(slots=True)
class Sandbox:
    """Starts one child per run. Stateless between runs on purpose."""

    timeout: float = 20.0
    #: None means "decide on first use": bubblewrap if it works, else plain.
    use_bwrap: bool | None = None
    python: str = field(default_factory=lambda: sys.executable or "python3")

    def describe(self) -> str:
        if self._bwrap_ok():
            return "bubblewrap (no network, read-only system, private /tmp)"
        if os.name == "posix":
            return "separate process with resource limits (bubblewrap not available)"
        return "separate process (development mode: no kernel isolation on this OS)"

    def _bwrap_ok(self) -> bool:
        if self.use_bwrap is not None:
            return self.use_bwrap
        self.use_bwrap = False
        if os.name == "posix" and shutil.which("bwrap"):
            try:
                probe = subprocess.run(
                    [*self._bwrap_prefix(), "true"],
                    capture_output=True,
                    timeout=5,
                )
                self.use_bwrap = probe.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                self.use_bwrap = False
        return self.use_bwrap

    def _bwrap_prefix(self) -> list[str]:
        prefix = [
            "bwrap", "--unshare-all", "--die-with-parent", "--new-session",
            "--ro-bind", "/usr", "/usr",
            "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/bin", "/bin",
        ]
        if Path("/lib64").exists():
            prefix += ["--symlink", "usr/lib64", "/lib64"]
        return prefix + [
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--ro-bind", str(_CHILD.parent), "/sandbox",
            "--chdir", "/tmp", "--clearenv",
            "--setenv", "PATH", "/usr/bin", "--setenv", "LANG", "C.UTF-8",
        ]

    def _argv(self) -> list[str]:
        flags = ["-I", "-B", "-S", "-X", "utf8"]
        if self._bwrap_ok():
            python = self.python if self.python.startswith("/usr/") else "/usr/bin/python3"
            return [*self._bwrap_prefix(), python, *flags, "/sandbox/_child.py"]
        return [self.python, *flags, str(_CHILD)]

    def run(self, code: str, functions: list[str], dispatch: Dispatch) -> RunResult:
        """Run ``code``; never raises. ``dispatch`` answers each ``mine`` call."""
        problem = validate(code)
        if problem:
            return RunResult(ok=False, error=problem)

        started = time.monotonic()
        env = {"PATH": os.environ.get("PATH", "/usr/bin"), "LANG": "C.UTF-8",
               "PYTHONIOENCODING": "utf-8"}
        if os.name == "nt":
            env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\Windows")
        try:
            proc = subprocess.Popen(
                self._argv(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                preexec_fn=_limits if os.name == "posix" else None,  # noqa: PLW1509
            )
        except OSError as exc:
            return RunResult(ok=False, error=f"could not start Python: {exc.strerror}")

        lines: queue.Queue[str | None] = queue.Queue()
        errors: list[str] = []

        def pump_out() -> None:
            assert proc.stdout is not None
            for line in proc.stdout:
                lines.put(line)
            lines.put(None)

        def pump_err() -> None:
            assert proc.stderr is not None
            for line in proc.stderr:
                if sum(map(len, errors)) < 2000:
                    errors.append(line)

        threading.Thread(target=pump_out, daemon=True).start()
        threading.Thread(target=pump_err, daemon=True).start()

        calls: list[str] = []
        attempted = 0
        deadline = started + self.timeout

        def send(message: dict) -> bool:
            try:
                assert proc.stdin is not None
                proc.stdin.write(json.dumps(message) + "\n")
                proc.stdin.flush()
                return True
            except (OSError, ValueError):
                return False

        send({"code": code, "fns": functions, "imports": sorted(ALLOWED_IMPORTS),
              "max_out": MAX_OUTPUT})
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return self._finish(proc, started, calls, error=(
                        f"the code took longer than {self.timeout:.0f}s and was stopped; "
                        "avoid long loops"))
                try:
                    line = lines.get(timeout=remaining)
                except queue.Empty:
                    continue
                if line is None:
                    detail = "".join(errors).strip().splitlines()
                    tail = detail[-1] if detail else f"exit status {proc.wait()}"
                    return self._finish(proc, started, calls,
                                        error=f"the code crashed: {tail[:200]}")
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if message.get("t") == "done":
                    error = message.get("error")
                    return self._finish(proc, started, calls,
                                        output=str(message.get("out", "")),
                                        error=str(error) if error else None)
                if message.get("t") != "call":
                    continue
                name = str(message.get("fn", ""))
                attempted += 1
                if attempted > MAX_CALLS_PER_RUN:
                    send({"ok": False, "error": f"more than {MAX_CALLS_PER_RUN} mine "
                          "calls in one block; do less per block"})
                    continue
                args = message.get("args") if isinstance(message.get("args"), list) else []
                kwargs = message.get("kwargs") if isinstance(message.get("kwargs"), dict) else {}
                paused = time.monotonic()
                ok, value = dispatch(name, args, kwargs)
                if ok:
                    calls.append(name)
                # Time spent in the OS call (and waiting for the user to say
                # yes) is not the code's time, so it does not use up the budget.
                deadline += time.monotonic() - paused
                reply = {"ok": True, "value": value} if ok else {"ok": False, "error": str(value)}
                try:
                    json.dumps(reply)
                except (TypeError, ValueError):
                    reply = {"ok": True, "value": str(value)}
                send(reply)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                try:
                    if stream is not None:
                        stream.close()
                except OSError:
                    pass

    @staticmethod
    def _finish(proc: subprocess.Popen, started: float, calls: list[str], *,
                output: str = "", error: str | None = None) -> RunResult:
        if proc.poll() is None:
            proc.kill()
        return RunResult(ok=error is None, output=output, error=error, calls=calls,
                         seconds=time.monotonic() - started)
