"""The one place a language model is spoken to over HTTP.

Ported from clarkeAgent's ``onyx.connectors.nvidia`` and narrowed to the
OpenAI-compatible wire format, because that is what ``llama-server`` speaks --
and what OpenAI, NVIDIA NIM, Groq, OpenRouter and most other hosts speak too.
So "local llama.cpp" and "the user pasted a key for a hosted model" are the
same code path with a different ``base_url``.

The protocol is one method wide: a system string and a user string in, text
out. No message history, on purpose -- the agent re-renders the whole window
every call from the trajectory it owns (see :mod:`mineos_agent.prompt`).

A failure is an :class:`LLMError` with a short message for a human. No retries
and no fallback model: a silent retry loop is the failure mode to design
against on a slow CPU, not to implement.
"""

import ipaddress
import json
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from dataclasses import dataclass
from typing import Iterator, Protocol

from .config import LLMConfig

__all__ = ["ChatModel", "LLMError", "OpenAIChat", "Truncated", "health"]


class LLMError(ValueError):
    """The model could not be reached, or its reply could not be used."""


class Truncated(LLMError):
    """The model hit max_tokens before it finished.

    Refused rather than returned: half a Python block is a syntax error at
    best, and at worst a block that parses and does half of what was meant.
    """


class ChatModel(Protocol):
    @property
    def model_id(self) -> str: ...

    def complete(self, *, system: str, user: str, temperature: float | None = None) -> str: ...


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(slots=True)
class OpenAIChat:
    """A chat model behind an OpenAI-compatible ``/chat/completions``."""

    config: LLMConfig
    #: Tokens the server reported for the last call, for the trace.
    last_usage: dict | None = None
    last_seconds: float = 0.0
    loopback_only: bool = False

    def _open(self, request):
        if not self.loopback_only:
            return urllib.request.urlopen(request, timeout=self.config.timeout)
        try:
            url = urlsplit(self.config.base_url)
            local = url.scheme == "http" and not url.username and ipaddress.ip_address(url.hostname).is_loopback
        except ValueError:
            local = False
        if not local:
            raise LLMError("desktop context requires a local model on a numeric loopback address")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        return opener.open(request, timeout=self.config.timeout)

    @property
    def model_id(self) -> str:
        return self.config.model

    def _request(self, payload: dict) -> urllib.request.Request:
        headers = {"Content-Type": "application/json", "User-Agent": "mineos-agent"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

    def _payload(self, system: str, user: str, *, stream: bool) -> dict:
        return {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": stream,
        }

    def complete(self, *, system: str, user: str, temperature: float | None = None) -> str:
        started = time.monotonic()
        payload = self._payload(system, user, stream=False)
        if temperature is not None:
            payload["temperature"] = temperature
        request = self._request(payload)
        try:
            with self._open(request) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise LLMError(_http_message(exc, self.config.base_url)) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LLMError(_reach_message(exc, self.config.base_url)) from exc
        except json.JSONDecodeError as exc:
            raise LLMError("the model server sent something that is not JSON") from exc
        finally:
            self.last_seconds = time.monotonic() - started

        try:
            choice = body["choices"][0]
            content = choice["message"].get("content") or ""
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise LLMError("the model server's reply had no message in it") from exc
        self.last_usage = body.get("usage") if isinstance(body.get("usage"), dict) else None
        if choice.get("finish_reason") == "length":
            raise Truncated(
                f"the reply was cut off at {self.config.max_tokens} tokens"
            )
        return _THINK.sub("", content).strip()

    def stream(self, *, system: str, user: str) -> Iterator[str]:
        """Yield text as it arrives. For plain chat, where waiting is the UX."""
        yield from self.stream_messages(self._payload(system, user, stream=True)["messages"])

    def stream_messages(self, messages: list[dict], *, max_tokens: int | None = None) -> Iterator[str]:
        """Stream a reply to a full message list. For callers that keep their
        own history, like the desktop assistant window."""
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }
        request = self._request(payload)
        try:
            response = self._open(request)
        except urllib.error.HTTPError as exc:
            raise LLMError(_http_message(exc, self.config.base_url)) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LLMError(_reach_message(exc, self.config.base_url)) from exc
        with response:
            in_think = False
            for raw in response:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    delta = json.loads(data)["choices"][0].get("delta", {})
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    continue
                piece = delta.get("content") or ""
                if "<think>" in piece:
                    in_think = True
                if in_think:
                    if "</think>" in piece:
                        in_think = False
                        piece = piece.split("</think>", 1)[1]
                    else:
                        continue
                if piece:
                    yield piece


def health(config: LLMConfig, *, timeout: float = 3.0) -> tuple[bool, str]:
    """Whether the server answers, and a one-line description either way.

    ``GET /models`` works on llama-server and on hosted APIs alike, so this
    does not need to know which one it is talking to.
    """
    headers = {"User-Agent": "mineos-agent"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    request = urllib.request.Request(f"{config.base_url}/models", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return False, _http_message(exc, config.base_url)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, _reach_message(exc, config.base_url)
    except json.JSONDecodeError:
        return False, "the server answered, but not with JSON"
    names = [
        str(item.get("id"))
        for item in (body.get("data") or [])
        if isinstance(item, dict) and item.get("id")
    ]
    if names:
        return True, "serving " + ", ".join(names[:3])
    return True, "answering"


def _http_message(exc: urllib.error.HTTPError, url: str) -> str:
    if exc.code in (401, 403):
        return f"{url} refused the API key (HTTP {exc.code})"
    if exc.code == 404:
        return f"{url} has no such endpoint or model (HTTP 404); check base_url and model"
    if exc.code == 503:
        return "the model server is still loading the model; try again in a moment"
    return f"the model server returned HTTP {exc.code}"


def _reach_message(exc: BaseException, url: str) -> str:
    if isinstance(exc, TimeoutError) or "timed out" in str(exc):
        return "the model took too long to answer"
    if "127.0.0.1" in url or "localhost" in url:
        return (
            "the local model server is not running; "
            "start it with: sudo systemctl start mineos-llm"
        )
    return f"could not reach {url}"
