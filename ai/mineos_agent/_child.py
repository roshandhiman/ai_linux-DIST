"""The sandboxed process that runs the model's Python. Self-contained on purpose.

It is started with ``python3 -I -B -S`` (inside bubblewrap when available), so
it imports nothing from the agent package and nothing from the user's
site-packages. It has no direct way to touch the system: no ``open``, no ``os``,
no ``subprocess``. The only door out is the ``mine`` object, and every call on
it is a JSON line to the parent, which decides -- see ``os_api.py``.

Wire protocol, one JSON object per line:

    parent -> child   {"fns": [str], "imports": [str], "max_out": int}     once
    parent -> child   {"code": str}                                      per block
    child  -> parent  {"t": "call", "fn": str, "args": [...], "kwargs": {...}}
    parent -> child   {"ok": true, "value": ...} | {"ok": false, "error": str}
    child  -> parent  {"t": "done", "out": str, "error": str | null}  end of block
    parent -> child   {"t": "exit"}                                      end of request
"""

import json
import sys
import types

# Kept before anything else runs: user code never sees these names.
_PROTO_OUT = sys.stdout
_PROTO_IN = sys.stdin
_SAFE_BUILTIN_NAMES = (
    "abs all any ascii bin bool bytes callable chr dict divmod enumerate filter "
    "float format frozenset hash hex int isinstance issubclass iter len list map max "
    "min next oct ord pow range repr reversed round set slice sorted str sum "
    "tuple zip ArithmeticError AssertionError AttributeError Exception "
    "IndexError KeyError LookupError NameError NotImplementedError OverflowError "
    "RuntimeError StopIteration TypeError ValueError ZeroDivisionError"
).split()


class MineError(Exception):
    """A ``mine`` call the parent refused or could not complete."""


def _send(message):
    _PROTO_OUT.write(json.dumps(message) + "\n")
    _PROTO_OUT.flush()


def _receive():
    line = _PROTO_IN.readline()
    if not line:
        raise SystemExit(3)
    return json.loads(line)


def _make_call(name):
    def call(*args, **kwargs):
        _send({"t": "call", "fn": name, "args": list(args), "kwargs": kwargs})
        reply = _receive()
        if reply.get("ok"):
            return reply.get("value")
        raise MineError(f"mine.{name}: {reply.get('error') or 'failed'}")

    call.__name__ = name
    return call


def _public_view(module):
    """A module with its submodules and private names removed.

    ``re.enum.sys.modules['os']`` is a real escape made only of public names;
    exposing a filtered namespace instead of the module object closes it.
    """
    return types.SimpleNamespace(
        **{
            key: value
            for key, value in vars(module).items()
            if not key.startswith("_") and not isinstance(value, types.ModuleType)
        }
    )


def main():
    setup = _receive()
    allowed = frozenset(setup.get("imports", ()))
    max_out = int(setup.get("max_out", 4000))
    captured = []
    size = [0]

    def safe_print(*args, sep=" ", end="\n", **_ignored):
        text = str(sep).join(str(a) for a in args) + str(end)
        if size[0] >= max_out:
            return
        captured.append(text[: max_out - size[0]])
        size[0] += len(text)

    real_import = __import__

    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "mine" and not level:
            return mine
        root = name.partition(".")[0]
        if level or name != root or root not in allowed:
            raise ImportError(f"import of {name!r} is not allowed here")
        for item in fromlist or ():
            if str(item).startswith("_"):
                raise ImportError(f"cannot import {item!r}")
        return _public_view(real_import(name))

    import builtins as _b

    safe_builtins = {name: getattr(_b, name) for name in _SAFE_BUILTIN_NAMES}
    safe_builtins["print"] = safe_print
    safe_builtins["__import__"] = safe_import
    safe_builtins["MineError"] = MineError
    safe_builtins["True"], safe_builtins["False"], safe_builtins["None"] = True, False, None

    mine = types.SimpleNamespace(**{name: _make_call(name) for name in setup["fns"]})
    # One namespace for the whole request, so a variable from step one is
    # still there in step two -- the way a notebook works.
    scope = {"__builtins__": safe_builtins, "__name__": "__mine__", "mine": mine}

    while True:
        request = _receive()
        if request.get("t") == "exit" or "code" not in request:
            return
        captured.clear()
        size[0] = 0
        _run_block(request["code"], scope, captured, size, max_out)


def _run_block(code, scope, captured, size, max_out):
    error = None
    try:
        exec(compile(code, "<mine>", "exec"), scope)
    except BaseException as exc:  # noqa: BLE001 - everything becomes data
        line = None
        tb = exc.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code.co_filename == "<mine>":
                line = tb.tb_lineno
            tb = tb.tb_next
        where = f" (line {line})" if line else ""
        if isinstance(exc, MineError):
            error = f"{exc}{where}"
        elif isinstance(exc, MemoryError):
            error = "MemoryError: the code used too much memory"
        else:
            error = f"{type(exc).__name__}: {exc}{where}"
    out = "".join(captured)
    if size[0] > max_out:
        out += f"\n[output cut at {max_out} characters]"
    _send({"t": "done", "out": out, "error": error})


if __name__ == "__main__":
    main()
