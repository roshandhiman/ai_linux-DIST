"""Model providers: which host, which wire format, which key.

Modelled on Hermes Agent's provider layer. Hermes has only four wire formats
("api_modes") and dozens of providers; most providers are a base URL and a
key variable on top of the same OpenAI-style ``/chat/completions``. So there
are two things here:

* **presets** -- a table of provider name -> wire format, base URL, key
  variable. Picking ``provider = "groq"`` fills in the URL and finds
  ``GROQ_API_KEY``. Anything you set yourself still wins.
* **adapters** -- one small class per wire format that is *not* chat
  completions: :class:`AnthropicMessages` and :class:`OpenAIResponses`. Each
  keeps the same one-method shape as :class:`~mineos_agent.llm.OpenAIChat`
  (system string + user string in, text out), so the agent loop does not know
  or care which one it was given.

Nothing here calls out by itself. A hosted provider is only used when the user
picks it, and its key is only read from the user's own config or environment.
Bedrock (AWS request signing) is not implemented.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Mapping

from .config import LLMConfig
from .llm import (ChatModel, LLMError, OpenAIChat, Truncated, _http_message,
                  _reach_message, health)

__all__ = [
    "AnthropicMessages", "OpenAIResponses", "PRESETS", "Preset",
    "apply_provider", "build_model", "check_health", "describe",
]

CHAT = "chat_completions"
ANTHROPIC = "anthropic_messages"
RESPONSES = "openai_responses"


@dataclass(frozen=True, slots=True)
class Preset:
    api_mode: str
    base_url: str
    #: Environment variables checked, in order, when no key was configured.
    key_env: tuple[str, ...] = ()
    #: Model used when the user did not name one. Empty means "you must say".
    model: str = ""
    needs_key: bool = True
    #: Hosted models take far more context than a 1.5B on a laptop CPU.
    context: int = 32768
    max_tokens: int = 1024


PRESETS: dict[str, Preset] = {
    # Local: llama-server, Ollama, LM Studio -- whatever is at base_url.
    "local": Preset(CHAT, "http://127.0.0.1:8080/v1", needs_key=False, context=4096, max_tokens=512),
    "anthropic": Preset(ANTHROPIC, "https://api.anthropic.com/v1", ("ANTHROPIC_API_KEY",),
                        model="claude-haiku-5-5"),
    "openai": Preset(CHAT, "https://api.openai.com/v1", ("OPENAI_API_KEY",)),
    "openai-responses": Preset(RESPONSES, "https://api.openai.com/v1", ("OPENAI_API_KEY",)),
    "openrouter": Preset(CHAT, "https://openrouter.ai/api/v1", ("OPENROUTER_API_KEY",)),
    "groq": Preset(CHAT, "https://api.groq.com/openai/v1", ("GROQ_API_KEY",)),
    "deepseek": Preset(CHAT, "https://api.deepseek.com/v1", ("DEEPSEEK_API_KEY",)),
    "together": Preset(CHAT, "https://api.together.xyz/v1", ("TOGETHER_API_KEY",)),
    "fireworks": Preset(CHAT, "https://api.fireworks.ai/inference/v1", ("FIREWORKS_API_KEY",)),
    "nvidia": Preset(CHAT, "https://integrate.api.nvidia.com/v1", ("NVIDIA_API_KEY",)),
    "mistral": Preset(CHAT, "https://api.mistral.ai/v1", ("MISTRAL_API_KEY",)),
    "xai": Preset(CHAT, "https://api.x.ai/v1", ("XAI_API_KEY",)),
    "gemini": Preset(CHAT, "https://generativelanguage.googleapis.com/v1beta/openai",
                     ("GEMINI_API_KEY", "GOOGLE_API_KEY")),
}

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_ANTHROPIC_VERSION = "2023-06-01"


# -- choosing -----------------------------------------------------------------


def apply_provider(llm: LLMConfig, environ: Mapping[str, str] | None = None) -> str | None:
    """Fill in what the chosen provider implies, without overriding the user.

    A field still at its built-in default takes the preset's value; a field
    the user set (file, env, flag) is left alone. Returns a warning, or None.
    """
    env = os.environ if environ is None else environ
    name = (llm.provider or "local").strip().lower()
    preset = PRESETS.get(name)
    if preset is None:
        llm.provider = "local"
        return f"unknown provider {name!r}; using the local model. Known: {', '.join(PRESETS)}"
    llm.provider = name
    default = LLMConfig()
    if llm.base_url == default.base_url:
        llm.base_url = preset.base_url
    if llm.model == default.model and preset.model:
        llm.model = preset.model
    if llm.context == default.context:
        llm.context = preset.context
    if llm.max_tokens == default.max_tokens:
        llm.max_tokens = preset.max_tokens
    if not llm.api_key:
        for var in preset.key_env:
            if env.get(var, "").strip():
                llm.api_key = env[var].strip()
                break
    return None


def build_model(config: LLMConfig) -> ChatModel:
    """The model object for this configuration."""
    mode = PRESETS.get(config.provider, PRESETS["local"]).api_mode
    if mode == ANTHROPIC:
        return AnthropicMessages(config)
    if mode == RESPONSES:
        return OpenAIResponses(config)
    if config.provider != "local" and PRESETS.get(config.provider, PRESETS["local"]).needs_key:
        return HostedChat(config)
    return OpenAIChat(config)


def describe(config: LLMConfig) -> str:
    """One line for ``--status``: provider, wire format, key state."""
    preset = PRESETS.get(config.provider, PRESETS["local"])
    if not preset.needs_key and not config.api_key:
        key = "none (local model, nothing leaves this machine)"
    elif config.api_key:
        key = "set (hosted model: your requests go to " + config.base_url.split("/")[2] + ")"
    else:
        key = "MISSING: set " + " or ".join(("MINEOS_API_KEY",) + preset.key_env)
    note = ""
    if config.provider != "local" and config.model == LLMConfig().model:
        note = "; NO MODEL CHOSEN: pass --model <name>"
    return f"{config.provider} via {preset.api_mode}; api key {key}{note}"


def check_health(config: LLMConfig, *, timeout: float = 3.0) -> tuple[bool, str]:
    """Is the provider reachable and does it accept the key?"""
    preset = PRESETS.get(config.provider, PRESETS["local"])
    if preset.needs_key and not config.api_key:
        return False, "no API key set for " + config.provider
    if preset.api_mode != ANTHROPIC:
        return health(config, timeout=timeout)
    request = urllib.request.Request(f"{config.base_url}/models", headers=_anthropic_headers(config))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return False, _http_message(exc, config.base_url)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, _reach_message(exc, config.base_url)
    except json.JSONDecodeError:
        return False, "the server answered, but not with JSON"
    names = [str(m.get("id")) for m in body.get("data") or [] if isinstance(m, dict) and m.get("id")]
    return True, ("serving " + ", ".join(names[:3])) if names else "answering"


# -- shared plumbing ----------------------------------------------------------


def _anthropic_headers(config: LLMConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "User-Agent": "mineos-agent",
               "anthropic-version": _ANTHROPIC_VERSION}
    if config.api_key:
        headers["x-api-key"] = config.api_key
    return headers


def _detail(exc: urllib.error.HTTPError) -> str:
    """The provider's own explanation, short. Error bodies never hold our key."""
    try:
        body = json.loads(exc.read().decode("utf-8", "replace"))
        error = body.get("error")
        text = error.get("message") if isinstance(error, dict) else error
        return " ".join(str(text or "").split())[:200]
    except (ValueError, AttributeError, OSError):
        return ""


def _problem(exc: urllib.error.HTTPError, url: str, detail: str) -> LLMError:
    if exc.code == 429:
        message = "the provider is rate-limiting this key; wait a moment and retry"
    elif exc.code in (500, 502, 503, 529):
        message = f"the provider is overloaded or down (HTTP {exc.code}); try again shortly"
    else:
        message = _http_message(exc, url)
    if detail and exc.code not in (401, 403, 429):
        message += f": {detail}"
    return LLMError(message)


def _post(url: str, headers: Mapping[str, str], payload: dict, timeout: float) -> dict:
    """POST JSON, return the JSON reply, or raise LLMError a human can read."""
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        problem = _problem(exc, url, _detail(exc))
        exc.close()
        raise problem from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LLMError(_reach_message(exc, url)) from exc
    except json.JSONDecodeError as exc:
        raise LLMError("the model server sent something that is not JSON") from exc


def _post_dropping_temperature(url: str, headers: Mapping[str, str], payload: dict,
                               timeout: float) -> dict:
    """Some newer models refuse a temperature outright. Retry once without it."""
    try:
        return _post(url, headers, payload, timeout)
    except LLMError as exc:
        if "temperature" in str(exc).lower() and "temperature" in payload:
            return _post(url, headers, {k: v for k, v in payload.items() if k != "temperature"}, timeout)
        raise


def _need_key(config: LLMConfig) -> None:
    if not config.api_key:
        preset = PRESETS.get(config.provider, PRESETS["local"])
        names = " or ".join(("MINEOS_API_KEY",) + preset.key_env)
        raise LLMError(f"no API key for {config.provider}; set {names}")


def _need_model(config: LLMConfig) -> None:
    if config.provider != "local" and config.model == LLMConfig().model:
        raise LLMError(f"{config.provider} needs a model name: run with --model <name>")


class HostedChat(OpenAIChat):
    """Chat completions on a hosted provider: same wire, but refuse to send
    anything until a key and a model are set, rather than let the provider
    answer 401 to a request that should never have left the machine."""

    def _request(self, payload: dict) -> urllib.request.Request:
        _need_key(self.config)
        _need_model(self.config)
        return super()._request(payload)


# -- adapters -----------------------------------------------------------------


@dataclass(slots=True)
class AnthropicMessages:
    """Anthropic's Messages API (``POST /v1/messages``)."""

    config: LLMConfig
    last_usage: dict | None = None
    last_seconds: float = 0.0

    @property
    def model_id(self) -> str:
        return self.config.model

    def complete(self, *, system: str, user: str, temperature: float | None = None) -> str:
        _need_key(self.config)
        _need_model(self.config)
        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            # The system prompt is identical on every call, so mark it cacheable:
            # the hosted analogue of llama-server's prompt cache. Below the
            # provider's minimum size this is silently ignored.
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": user}],
            "temperature": min(1.0, self.config.temperature if temperature is None else temperature),
        }
        started = time.monotonic()
        try:
            body = _post_dropping_temperature(f"{self.config.base_url}/messages",
                                              _anthropic_headers(self.config), payload,
                                              self.config.timeout)
        finally:
            self.last_seconds = time.monotonic() - started
        blocks = body.get("content")
        if not isinstance(blocks, list):
            raise LLMError("the provider's reply had no message in it")
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        self.last_usage = {"prompt_tokens": usage.get("input_tokens"),
                           "completion_tokens": usage.get("output_tokens")} if usage else None
        stop = body.get("stop_reason")
        if stop == "max_tokens":
            raise Truncated(f"the reply was cut off at {self.config.max_tokens} tokens")
        if stop == "refusal":
            raise LLMError("the model declined to answer that")
        text = "".join(b.get("text", "") for b in blocks
                       if isinstance(b, dict) and b.get("type") == "text")
        return _THINK.sub("", text).strip()


@dataclass(slots=True)
class OpenAIResponses:
    """OpenAI's Responses API (``POST /v1/responses``)."""

    config: LLMConfig
    last_usage: dict | None = None
    last_seconds: float = 0.0

    @property
    def model_id(self) -> str:
        return self.config.model

    def complete(self, *, system: str, user: str, temperature: float | None = None) -> str:
        _need_key(self.config)
        _need_model(self.config)
        headers = {"Content-Type": "application/json", "User-Agent": "mineos-agent",
                   "Authorization": f"Bearer {self.config.api_key}"}
        payload = {
            "model": self.config.model,
            "instructions": system,
            "input": user,
            "max_output_tokens": max(16, self.config.max_tokens),
            "temperature": self.config.temperature if temperature is None else temperature,
            "store": False,
        }
        started = time.monotonic()
        try:
            body = _post_dropping_temperature(f"{self.config.base_url}/responses", headers,
                                              payload, self.config.timeout)
        finally:
            self.last_seconds = time.monotonic() - started
        output = body.get("output")
        if not isinstance(output, list):
            raise LLMError("the provider's reply had no message in it")
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        self.last_usage = {"prompt_tokens": usage.get("input_tokens"),
                           "completion_tokens": usage.get("output_tokens")} if usage else None
        parts = [p for item in output if isinstance(item, dict) and item.get("type") == "message"
                 for p in item.get("content") or [] if isinstance(p, dict)]
        if any(p.get("type") == "refusal" for p in parts):
            raise LLMError("the model declined to answer that")
        details = body.get("incomplete_details")
        if body.get("status") == "incomplete" and isinstance(details, dict) \
                and details.get("reason") == "max_output_tokens":
            raise Truncated(f"the reply was cut off at {self.config.max_tokens} tokens")
        text = "".join(p.get("text", "") for p in parts if p.get("type") == "output_text")
        return _THINK.sub("", text).strip()
