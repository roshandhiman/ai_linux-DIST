"""Tier one: decide what kind of request this is, in milliseconds.

The two-tier design: a small *encoder* classifier (an encoder-only model with
a classification head) reads every request first. When it is confident the
request is one of a handful of simple actions -- open an app, set the volume,
what time is it -- the agent does it directly and the 1.5B language model is
never woken. Only requests that need reasoning, several steps, or a reply in
words reach tier two.

On a VM's CPU that is the difference between "instant" and "eight seconds",
for the requests people make most.

Two routers share one interface:

* :class:`RuleRouter` -- regular expressions. Always available, no model.
* :class:`EncoderRouter` -- loads the classifier named in the config
  (``router.model``, a Hugging Face id or a local folder) and maps its labels
  to intents with ``router.labels``. It decides the *intent*; the slots (which
  app, what volume) are still pulled out by the rules, because extraction is
  exact work a classifier is not built for.

:class:`HybridRouter` uses the encoder when it loads and the rules when it
does not, so a missing model degrades speed, never correctness.
"""

import re
from dataclasses import dataclass, field
from typing import Final, Protocol

__all__ = ["EncoderRouter", "HybridRouter", "INTENTS", "Route", "RuleRouter"]

INTENTS: Final[tuple[str, ...]] = (
    "OPEN", "SEARCH", "VOLUME", "STATUS", "TIME", "REMEMBER", "RECALL", "CHAT", "TASK",
)

#: Intents the fast path can complete without the language model.
ACTIONS: Final[frozenset[str]] = frozenset(
    {"OPEN", "SEARCH", "VOLUME", "STATUS", "TIME", "REMEMBER", "RECALL"}
)


@dataclass(frozen=True, slots=True)
class Route:
    intent: str
    confidence: float
    slots: dict[str, str] = field(default_factory=dict)
    backend: str = "rules"

    def __str__(self) -> str:
        detail = ", ".join(f"{k}={v}" for k, v in self.slots.items())
        return f"{self.intent} {self.confidence:.2f} via {self.backend}" + (f" ({detail})" if detail else "")


class Router(Protocol):
    def route(self, request: str) -> Route: ...

    def describe(self) -> str: ...


_POLITE = re.compile(
    r"^(?:(?:hey|hi|ok|okay)\s+(?:mine|jarvis|computer)[,\s]*|please\s+|can you\s+|could you\s+|"
    r"would you\s+|will you\s+|i want you to\s+|i'd like you to\s+)+",
    re.IGNORECASE,
)
_COMPOUND = re.compile(r"\b(?:and|then|after that|also)\b|[;,]", re.IGNORECASE)

_OPEN = re.compile(
    r"^(?:open|launch|start|show)\s+(?:up\s+)?(?:the\s+|my\s+|a\s+)?(?P<target>.+?)"
    r"(?:\s+(?:app|application|program|folder|website|site))?$",
    re.IGNORECASE,
)
_SEARCH = re.compile(
    r"^(?:search\s+(?:the\s+web\s+|online\s+|the\s+internet\s+)?for|search|google|look\s+up)\s+"
    r"(?P<query>.+?)(?:\s+on\s+(?P<site>youtube|github|wikipedia|google))?$",
    re.IGNORECASE,
)
_SEARCH_SITE = re.compile(
    r"^search\s+(?P<site>youtube|github|wikipedia|google)\s+for\s+(?P<query>.+)$", re.IGNORECASE
)
_PLAY = re.compile(r"^play\s+(?P<query>.+?)(?:\s+on\s+youtube)?$", re.IGNORECASE)
_VOLUME = re.compile(
    r"^(?:(?:set|turn|change|put)\s+(?:the\s+)?)?(?:volume|sound)\b(?:\s+(?:to|at))?\s*(?P<value>\d{1,3})?\s*%?"
    r"(?:\s*(?:percent))?(?:\s+(?P<dir>up|down))?$|^(?P<mute>mute|unmute)(?:\s+(?:the\s+)?(?:sound|audio|volume|speakers?))?$|"
    r"^(?:turn\s+(?:the\s+)?(?:volume|sound)\s+(?P<dir2>up|down))$|^(?P<word>louder|quieter)$",
    re.IGNORECASE,
)
_STATUS = re.compile(
    r"\b(?:system\s+status|status\s+of\s+(?:my\s+)?(?:system|computer|pc)|cpu(?:\s+usage)?|ram(?:\s+usage)?|"
    r"memory\s+usage|disk\s+(?:space|usage)|storage|battery|uptime|how(?:'s|\s+is)\s+my\s+"
    r"(?:system|computer|pc|laptop)(?:\s+doing)?)\b",
    re.IGNORECASE,
)
_TIME = re.compile(
    r"^(?:what(?:'s|\s+is)\s+the\s+(?:time|date|day)(?:\s+today)?|what\s+time\s+is\s+it|"
    r"what\s+day\s+is\s+(?:it|today)|today'?s\s+date|time|date)$",
    re.IGNORECASE,
)
_REMEMBER = re.compile(r"^remember(?:\s+that)?\s+(?P<fact>.+)$", re.IGNORECASE)
_RECALL = re.compile(
    r"^(?:what\s+do\s+you\s+(?:know|remember)\s+about|do\s+you\s+remember|"
    r"what(?:'s|\s+is)\s+my|who(?:'s|\s+is)\s+my|where\s+do\s+i)\s+(?P<query>.+)$",
    re.IGNORECASE,
)
_GREETING = re.compile(
    r"^(?:hi|hello|hey|yo|hiya|good\s+(?:morning|afternoon|evening|night)|thanks|thank\s+you|"
    r"who\s+are\s+you|what\s+can\s+you\s+do|what\s+are\s+you|how\s+are\s+you|help)\b",
    re.IGNORECASE,
)
_QUESTION = re.compile(
    r"^(?:what\s+(?:is|are|was|were|does)|explain|why|how\s+(?:does|do|did|can|is)|tell\s+me\s+about|"
    r"define|who\s+(?:was|is|were)|write\s+(?:a|an|me)\s+(?:poem|story|joke|email|haiku)|"
    r"tell\s+me\s+a\s+joke|translate|summari[sz]e\s+this)\b",
    re.IGNORECASE,
)
#: Words that mean "this question is about *this computer*", so it needs the
#: tool even though it is phrased like a general question.
_LOCAL = re.compile(
    r"\b(?:my|file|files|folder|folders|directory|app|apps|installed|open|cpu|ram|battery|disk|"
    r"volume|download|downloads|documents|desktop|run|command|process|wifi|bluetooth|usb|"
    r"esp32|arduino|device|screen|this\s+(?:pc|computer|laptop|machine))\b",
    re.IGNORECASE,
)


def normalise(request: str) -> str:
    text = " ".join(request.strip().split())
    text = _POLITE.sub("", text)
    return text.rstrip(" ?!.").strip()


def parse_fact(fact: str) -> tuple[str, str, str]:
    """Turn "my wifi password is hunter2" into ("user", "wifi password", "hunter2")."""
    text = fact.strip().rstrip(".")
    patterns = (
        (r"^my\s+(?P<rel>.+?)\s+(?:is|are)\s+(?P<obj>.+)$", lambda m: ("user", m["rel"], m["obj"])),
        (r"^(?P<subj>.+?)\s+is\s+my\s+(?P<rel>.+)$", lambda m: ("user", m["rel"], m["subj"])),
        (r"^i\s+(?P<rel>like|love|hate|dislike|use|prefer|live\s+in|work\s+at|work\s+as|study\s+at|"
         r"am\s+from|speak)\s+(?P<obj>.+)$",
         lambda m: ("user", m["rel"], m["obj"])),
        (r"^i\s+am\s+(?P<obj>.+)$", lambda m: ("user", "is", m["obj"])),
        (r"^i'm\s+(?P<obj>.+)$", lambda m: ("user", "is", m["obj"])),
        (r"^(?P<subj>.+?)\s+(?P<rel>is|are|lives\s+in|works\s+at|likes)\s+(?P<obj>.+)$",
         lambda m: (m["subj"], m["rel"], m["obj"])),
    )
    for pattern, build in patterns:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            return build(match)
    return ("user", "note", text)


class RuleRouter:
    """Regular expressions. Conservative: when unsure, say TASK."""

    def describe(self) -> str:
        return "rules (no encoder model configured)"

    def route(self, request: str) -> Route:
        text = normalise(request)
        words = len(text.split())
        if not text:
            return Route("CHAT", 0.5)

        if words <= 8 and _GREETING.match(text):
            return Route("CHAT", 0.9)
        if (m := _REMEMBER.match(text)):
            subject, relation, obj = parse_fact(m["fact"])
            return Route("REMEMBER", 0.95, {"subject": subject, "relation": relation, "object": obj})

        compound = bool(_COMPOUND.search(text))
        if not compound:
            if (m := _TIME.match(text)):
                return Route("TIME", 0.95)
            if (m := _VOLUME.match(text)):
                return Route("VOLUME", 0.95, _volume_slots(m))
            if (m := _SEARCH_SITE.match(text)):
                return Route("SEARCH", 0.95, {"query": m["query"], "site": m["site"].lower()})
            if (m := _SEARCH.match(text)) and not _LOCAL_SEARCH.search(m["query"]):
                slots = {"query": m["query"]}
                if m["site"]:
                    slots["site"] = m["site"].lower()
                return Route("SEARCH", 0.92, slots)
            if (m := _PLAY.match(text)):
                return Route("SEARCH", 0.9, {"query": m["query"], "site": "youtube"})
            if (m := _OPEN.match(text)) and words <= 6:
                return Route("OPEN", 0.93, {"target": m["target"].strip()})
            if words <= 8 and _STATUS.search(text):
                return Route("STATUS", 0.9)
            if (m := _RECALL.match(text)):
                return Route("RECALL", 0.86, {"query": m["query"]})

        if _QUESTION.match(text) and not _LOCAL.search(text):
            return Route("CHAT", 0.8)
        return Route("TASK", 0.5)


_LOCAL_SEARCH = re.compile(r"\b(?:my\s+files?|my\s+folders?|my\s+computer|this\s+(?:pc|computer))\b", re.I)


def _volume_slots(m: re.Match[str]) -> dict[str, str]:
    if m["mute"]:
        return {"mute": "on" if m["mute"].lower() == "mute" else "off"}
    direction = m["dir"] or m["dir2"]
    if m["word"]:
        direction = "up" if m["word"].lower() == "louder" else "down"
    if m["value"]:
        return {"level": m["value"]}
    if direction:
        return {"level": "+10" if direction.lower() == "up" else "-10"}
    return {}


class EncoderRouter:
    """An encoder classifier from Hugging Face or a local folder.

    Loaded lazily and only if ``transformers`` is installed; any failure is
    remembered and reported by :meth:`describe` instead of raised, so a broken
    model never breaks the assistant.
    """

    def __init__(self, model: str, labels: dict[str, str], *, classify=None) -> None:
        self.model = model
        self.labels = {k: v.upper() for k, v in labels.items()}
        self._classify = classify
        self.error: str | None = None

    def describe(self) -> str:
        if self.error:
            return f"rules (encoder {self.model} unavailable: {self.error})"
        return f"encoder {self.model} + rules for slots"

    def _load(self):
        if self._classify is not None or self.error:
            return self._classify
        try:
            from transformers import pipeline  # type: ignore[import-not-found]

            pipe = pipeline("text-classification", model=self.model, top_k=1)

            def classify(text: str) -> tuple[str, float]:
                result = pipe(text)
                best = result[0][0] if isinstance(result[0], list) else result[0]
                return str(best["label"]), float(best["score"])

            self._classify = classify
        except Exception as exc:  # noqa: BLE001 - optional dependency boundary
            self.error = f"{type(exc).__name__}: {str(exc)[:80]}"
        return self._classify

    def classify(self, request: str) -> tuple[str, float] | None:
        classify = self._load()
        if classify is None:
            return None
        try:
            label, score = classify(normalise(request))
        except Exception as exc:  # noqa: BLE001
            self.error = f"{type(exc).__name__}: {str(exc)[:80]}"
            return None
        intent = self.labels.get(label, label.upper())
        return (intent if intent in INTENTS else "TASK"), score


@dataclass(slots=True)
class HybridRouter:
    rules: RuleRouter = field(default_factory=RuleRouter)
    encoder: EncoderRouter | None = None

    def describe(self) -> str:
        return self.encoder.describe() if self.encoder else self.rules.describe()

    def route(self, request: str) -> Route:
        by_rules = self.rules.route(request)
        verdict = self.encoder.classify(request) if self.encoder else None
        if verdict is None:
            return by_rules
        intent, score = verdict
        if intent == by_rules.intent:
            return Route(intent, max(score, by_rules.confidence), by_rules.slots, "encoder+rules")
        if intent in ACTIONS:
            # The encoder says "simple action" but the rules could not pull the
            # details out, so there is nothing safe to execute directly.
            return Route("TASK", min(score, 0.6), {}, "encoder")
        return Route(intent, score, {}, "encoder")
