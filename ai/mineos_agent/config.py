"""Where the agent's settings come from, in one documented order.

    built-in defaults
      < /etc/mineos/agent.json          (what the ISO ships)
      < ~/.config/mineos/agent.json     (what the user changed)
      < environment variables           (MINEOS_PROVIDER, MINEOS_LLM_URL, MINEOS_LLM_MODEL,
                                         MINEOS_API_KEY, MINEOS_ROUTER_URL)
      < command-line flags

Later wins. A provider preset (``"provider": "anthropic"``) then fills in whatever
is still at its default, and finds the provider's own key variable if no key was
given. The default talks to the local ``llama-server`` on 127.0.0.1:8080,
so a fresh install works offline with no key. An API key is only ever used when
the user provides one, and a hosted endpoint is only used when the user points
``base_url`` at it -- nothing in here phones anywhere by itself.
"""

import json
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

__all__ = ["AgentConfig", "LLMConfig", "RouterConfig", "load_config", "user_paths"]

SYSTEM_FILE = Path("/etc/mineos/agent.json")


def user_paths() -> dict[str, Path]:
    """XDG locations for this user, created lazily by whoever writes them."""
    home = Path.home()
    config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    data = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    state = Path(os.environ.get("XDG_STATE_HOME") or home / ".local" / "state")
    return {
        "config": config / "mineos" / "agent.json",
        "memory": data / "mineos" / "memory.db",
        "runs": state / "mineos" / "runs",
    }


@dataclass(slots=True)
class LLMConfig:
    #: Which provider: "local" (default) or a name from providers.PRESETS, such as
    #: "anthropic" or "groq". A preset fills in the URL, context and key variable
    #: for anything left at its default.
    provider: str = "local"
    #: OpenAI-compatible base URL. llama-server serves /v1/chat/completions.
    base_url: str = "http://127.0.0.1:8080/v1"
    #: Model name sent in the request. llama-server answers to its --alias.
    model: str = "qwen2.5-1.5b-instruct"
    #: Only sent when set. Never logged, never printed, never put in a window.
    api_key: str | None = None
    #: Must match llama-server's -c. The window is budgeted against it.
    context: int = 4096
    max_tokens: int = 512
    temperature: float = 0.2
    #: Seconds. A 1.5B model on a VM's CPU is slow; a hung server is not.
    timeout: float = 120.0


@dataclass(slots=True)
class RouterConfig:
    #: Base URL of the local laya-serve (mineos-router.service), or None for
    #: the rule-based router only.
    url: str | None = None
    #: Which Laya checkpoint answers: "multilingual" (100+ languages, the
    #: faster one) or "english".
    checkpoint: str = "multilingual"
    #: Seconds to wait for Laya before carrying on with the rules alone.
    timeout: float = 3.0
    #: Below this confidence a route is not trusted: the fast path is not
    #: taken, and a Laya verdict is ignored in favour of the rules.
    threshold: float = 0.85


@dataclass(slots=True)
class AgentConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    router: RouterConfig = field(default_factory=RouterConfig)
    max_steps: int = 6
    max_attempts: int = 3
    code_timeout: float = 20.0
    memory_path: Path = field(default_factory=lambda: user_paths()["memory"])
    runs_path: Path | None = field(default_factory=lambda: user_paths()["runs"])
    #: Where file tools may read and write. The user's home by default.
    home: Path = field(default_factory=Path.home)
    warnings: list[str] = field(default_factory=list)


def _read_json(path: Path, warnings: list[str]) -> Mapping[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        warnings.append(f"could not read {path}: {exc.strerror}")
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        warnings.append(f"{path} is not valid JSON (line {exc.lineno}); ignored")
        return {}
    if not isinstance(data, dict):
        warnings.append(f"{path} must hold a JSON object; ignored")
        return {}
    return data


def _apply(config: AgentConfig, data: Mapping[str, Any], origin: str) -> None:
    llm = data.get("llm", {})
    if isinstance(llm, dict):
        for key in ("provider", "base_url", "model", "api_key"):
            if isinstance(llm.get(key), str) and llm[key].strip():
                setattr(config.llm, key, llm[key].strip())
        for key in ("context", "max_tokens"):
            if isinstance(llm.get(key), int) and llm[key] > 0:
                setattr(config.llm, key, llm[key])
        for key in ("temperature", "timeout"):
            if isinstance(llm.get(key), (int, float)):
                setattr(config.llm, key, float(llm[key]))
        if "api_key" in llm and origin == str(SYSTEM_FILE) and llm.get("api_key"):
            config.warnings.append(
                f"{SYSTEM_FILE} holds an API key that every user can read; "
                "put it in ~/.config/mineos/agent.json instead"
            )
    router = data.get("router", {})
    if isinstance(router, dict):
        if "url" in router:
            url = router["url"]
            config.router.url = url.strip() if isinstance(url, str) and url.strip() else None
        if isinstance(router.get("checkpoint"), str) and router["checkpoint"].strip():
            config.router.checkpoint = router["checkpoint"].strip()
        for key in ("timeout", "threshold"):
            if isinstance(router.get(key), (int, float)) and not isinstance(router.get(key), bool):
                setattr(config.router, key, float(router[key]))
    agent = data.get("agent", {})
    if isinstance(agent, dict):
        for key in ("max_steps", "max_attempts"):
            if isinstance(agent.get(key), int) and agent[key] > 0:
                setattr(config, key, agent[key])
        if isinstance(agent.get("code_timeout"), (int, float)):
            config.code_timeout = float(agent["code_timeout"])


def _check_private(path: Path, warnings: list[str]) -> None:
    """Warn when a file holding a key is readable by other users."""
    if os.name != "posix":
        return
    try:
        mode = path.stat().st_mode
    except OSError:
        return
    if mode & (stat.S_IRGRP | stat.S_IROTH):
        warnings.append(f"{path} holds an API key and is readable by others; run: chmod 600 {path}")


def load_config(
    *,
    files: tuple[Path, ...] | None = None,
    environ: Mapping[str, str] | None = None,
    provider: str | None = None,
) -> AgentConfig:
    """Build the effective configuration. Never raises on a bad file."""
    config = AgentConfig()
    env = os.environ if environ is None else environ
    sources = files if files is not None else (SYSTEM_FILE, user_paths()["config"])
    for path in sources:
        data = _read_json(path, config.warnings)
        if data:
            _apply(config, data, str(path))
            if isinstance(data.get("llm"), dict) and data["llm"].get("api_key"):
                _check_private(path, config.warnings)
    if env.get("MINEOS_PROVIDER", "").strip():
        config.llm.provider = env["MINEOS_PROVIDER"].strip()
    if env.get("MINEOS_LLM_URL", "").strip():
        config.llm.base_url = env["MINEOS_LLM_URL"].strip()
    if env.get("MINEOS_LLM_MODEL", "").strip():
        config.llm.model = env["MINEOS_LLM_MODEL"].strip()
    if env.get("MINEOS_API_KEY", "").strip():
        config.llm.api_key = env["MINEOS_API_KEY"].strip()
    if "MINEOS_ROUTER_URL" in env:  # set but empty means "rules only"
        config.router.url = env["MINEOS_ROUTER_URL"].strip() or None
    if provider:  # the --provider flag outranks every file and variable
        config.llm.provider = provider
    from .providers import apply_provider  # late: providers imports this module
    problem = apply_provider(config.llm, env)
    if problem:
        config.warnings.append(problem)
    config.llm.base_url = config.llm.base_url.rstrip("/")
    if config.router.url:
        config.router.url = config.router.url.rstrip("/")
    return config
