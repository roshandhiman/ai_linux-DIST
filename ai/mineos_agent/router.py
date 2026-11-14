"""Tier one: decide what kind of request this is, in milliseconds.

The two-tier design: something cheap reads every request first. When it is
sure the request is one of a handful of simple actions -- open an app, set
the volume, what time is it -- the agent does it directly and the 1.5B
language model is never woken. Only requests that need reasoning, several
steps, or a reply in words reach tier two.

On a VM's CPU that is the difference between "instant" and "eight seconds",
for the requests people make most.

* :class:`RuleRouter` -- regular expressions. Always available, no model.
  When a rule matches it also pulls out the details (which app, what level).
* :class:`LayaRouter` -- the Laya encoder, served locally by ``laya-serve``.
  It answers a multiple-choice question about the request with calibrated
  probabilities, in any of 100+ languages, without generating text.
* :class:`HybridRouter` -- rules first, Laya for what the rules are unsure
  about. A missing Laya service costs accuracy on unusual phrasings, never
  correctness.
"""

import re
from dataclasses import dataclass, field
from typing import Final, Protocol

__all__ = ["HybridRouter", "INTENTS", "LAYA_QUESTION", "LayaRouter", "Route", "RuleRouter"]

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


#: The confidence of the rules' fallback: "no rule recognised this, so send it
#: to the tool loop". Only these requests are ever shown to Laya.
UNSURE: Final[float] = 0.5


class RuleRouter:
    """Regular expressions. Conservative: when unsure, say TASK."""

    def describe(self) -> str:
        return "rules (no encoder model configured)"

    def route(self, request: str) -> Route:
        text = normalise(request)
        words = len(text.split())
        if not text:
            return Route("CHAT", UNSURE)

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
        if _THING_HERE.search(text):
            # It names a file, folder, app or device on this computer: whatever
            # the wording, it is a job for the tool loop. Measured on Laya, these
            # were the requests it most often misread as chat or memory.
            return Route("TASK", 0.9)
        return Route("TASK", UNSURE)


#: Things that live on this computer. Narrower than _LOCAL: no "my" (that
#: is also "my sister") and no verbs, only nouns a request can act on.
_THING_HERE = re.compile(
    r"\b(?:files?|folders?|director(?:y|ies)|apps?|programs?|downloads?|documents|desktop|pictures|"
    r"photos|screenshots?|videos|music|pdfs?|todo(?:\s+list)?|settings|dark\s+mode|wi-?fi|bluetooth|"
    r"usb|esp32|arduino|serial|device|printer|terminal|command|process(?:es)?|"
    r"फ़ोल्डर|फोल्डर|फ़ाइल|फाइल|डाउनलोड)",
    re.IGNORECASE,
)
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


#: The one question Laya is asked. The keys are what comes back; the text is
#: what the encoder reads. Only intents that need no slots are offered -- an
#: "open" or "volume" verdict with no app name or level could not be executed,
#: so those stay with the rules, which extract the details exactly.
LAYA_QUESTION: Final[dict] = {
    "type": "choice",
    "instructions": "What kind of request did the user type into their computer's assistant?",
    "criteria": {
        "chat": "a greeting, small talk, or a general knowledge question that needs nothing from this computer",
        "status": "asks how this computer is doing: battery, CPU, memory, disk space or uptime",
        "time": "asks for the current time, date or day",
        "memory": "asks about something personal the user told the assistant before, such as their "
                  "name, family, friends or preferences",
        "action": "asks the computer to do something, or to look at files, folders, apps, settings, "
                  "the web or connected devices",
    },
}
_LAYA_INTENTS: Final[dict[str, str]] = {
    "chat": "CHAT", "status": "STATUS", "time": "TIME", "memory": "RECALL", "action": "TASK",
}


def _post_json(url: str, payload: dict, timeout: float) -> dict:
    import json
    import urllib.request

    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - local URL from config
        return json.loads(response.read().decode("utf-8"))


class LayaRouter:
    """Tier one's model: Laya, a non-autoregressive decision encoder.

    Laya (convaiinnovations/laya, Apache-2.0) never generates text. It reads
    the request and a typed question, and returns a probability for every
    option in one forward pass -- about 0.2-0.5 s on a CPU, against several
    seconds for the 1.5B model to write anything. It runs as its own service
    (``laya-serve``, see mineos-router.service) and this class talks to it
    over HTTP with the standard library, so the agent itself still needs no
    third-party packages.

    The ``multilingual`` checkpoint is the default: it reads 100+ languages,
    so a request typed in Hindi still reaches the right route.

    Any failure is remembered for ``backoff`` seconds and the rules carry on
    alone, so a stopped service costs one failed connection a minute, never
    a broken assistant.
    """

    def __init__(self, url: str, *, checkpoint: str = "multilingual", timeout: float = 3.0,
                 backoff: float = 60.0, post=None, clock=None) -> None:
        import time

        self.url = url.rstrip("/")
        self.checkpoint = checkpoint
        self.timeout = timeout
        self.backoff = backoff
        self._post = post or _post_json
        self._clock = clock or time.monotonic
        self._down_until = 0.0
        self.error: str | None = None

    def describe(self) -> str:
        where = f"laya {self.checkpoint} at {self.url}"
        if self.error:
            return f"rules only for now ({where} unavailable: {self.error})"
        return f"rules, then {where} when the rules are unsure"

    def health(self) -> tuple[bool, str]:
        """For ``ai --status``: is laya-serve up? Never raises."""
        import json
        import urllib.request

        try:
            with urllib.request.urlopen(self.url + "/health", timeout=self.timeout) as response:  # noqa: S310
                body = json.loads(response.read().decode("utf-8") or "{}")
        except Exception as exc:  # noqa: BLE001
            return False, (f"{type(exc).__name__}: {str(exc)[:80]}; "
                           "start it with: sudo systemctl start mineos-router")
        status = body.get("status", "ok") if isinstance(body, dict) else "ok"
        return True, f"laya-serve answered ({status})"

    def classify(self, request: str) -> tuple[str, float] | None:
        """``(intent, confidence)``, or None when the service cannot answer."""
        if self._clock() < self._down_until:
            return None
        payload = {"state": {"request": request.strip()[:2000]},
                   "questions": {"intent": LAYA_QUESTION}, "model": self.checkpoint}
        try:
            answer = self._post(self.url + "/v1/systemone", payload, self.timeout)["answers"]["intent"]
            choice = str(answer["choice"])
            probabilities = answer.get("probabilities") or {}
            confidence = float(probabilities.get(choice, answer.get("confidence", 0.0)))
        except Exception as exc:  # noqa: BLE001 - network and service boundary
            self.error = f"{type(exc).__name__}: {str(exc)[:80]}"
            self._down_until = self._clock() + self.backoff
            return None
        self.error = None
        return _LAYA_INTENTS.get(choice, "TASK"), confidence


@dataclass(slots=True)
class HybridRouter:
    """Rules first; Laya only for what the rules are unsure about.

    A rule that matched is exact *and* carries the slots the fast path needs
    ("open firefox" -> target=firefox), so a confident rule is never second-
    guessed and Laya is not even called -- the common requests stay instant.
    Laya decides the rest -- only requests no rule recognised (confidence
    ``UNSURE``): whether it is chat, a status or time question, a memory
    question, or a job for the tool loop. A Laya verdict below ``threshold``
    is ignored and the request goes to the tool loop, which handles anything,
    just more slowly.

    Laya can only choose a *route*. It cannot reach a gated action: every
    path it can pick is read-only, or goes through the tool loop with its
    approval prompts.
    """
    rules: RuleRouter = field(default_factory=RuleRouter)
    laya: LayaRouter | None = None
    threshold: float = 0.85

    def describe(self) -> str:
        return self.laya.describe() if self.laya else self.rules.describe()

    def route(self, request: str) -> Route:
        by_rules = self.rules.route(request)
        if self.laya is None or by_rules.confidence > UNSURE:
            return by_rules
        verdict = self.laya.classify(request)
        if verdict is None:
            return by_rules
        intent, confidence = verdict
        if confidence < self.threshold:
            return Route(by_rules.intent, by_rules.confidence, by_rules.slots,
                         f"rules (laya unsure: {intent} {confidence:.2f})")
        slots = {"query": normalise(request)} if intent == "RECALL" else {}
        return Route(intent, confidence, slots, "laya")
