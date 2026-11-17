"""The agent: route, then either act directly or run the two-loop tool cycle.

Ported from clarkeAgent's ``onyx.agent``, with its outcome taxonomy and its
"never raises" contract, and restructured around one tool (Python) and two
nested loops:

    OUTER  while steps < max_steps:            one iteration = one step that RAN
        INNER  while attempts < max_attempts:  model call -> parse -> check -> run
            the model answers           -> turn ends, ANSWERED
            the reply is unreadable     -> hint, try again (same step)
            the code is refused/crashes -> show that error, try again (same step)
            the code runs               -> record the step, next OUTER iteration
        inner loop used up              -> CONFUSED (or STUCK if the same error kept coming)
    outer loop used up                  -> EXHAUSTED

Why two loops. A broken block is not progress: counting a syntax error as a
"step" spends the step budget on typos, and showing the model every failed
attempt fills a small window with wrong code it will then copy. So mistakes
are retried *inside* a step, with only the latest one in view, and the outer
loop counts only steps that actually did something.

One exception, for safety: if a block fails *after* it already changed
something (opened an app, wrote a file), it is recorded as a step anyway, so
the model sees what already happened and does not do it twice.
"""

import json
import re
import sqlite3
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable

from .config import AgentConfig
from .fastpath import run_fast
from .llm import ChatModel, LLMError, Truncated
from .memory import GraphMemory, TaskState
from .os_api import OsApi
from .prompt import (
    CHAT_SYSTEM, CONFUSED_HINT, Answer, Code, Confused, Failure, StepView,
    digest_step, estimate_tokens, parse_reply, render_chat, render_window,
    step_entities, task_system,
)
from .router import ACTIONS, Route, Router
from .sandbox import Sandbox, Session, drop_unused_imports
from .text import one_line

__all__ = ["Agent", "Outcome", "Step", "Turn"]


class Outcome(str, Enum):
    ANSWERED = "answered"
    EXHAUSTED = "exhausted"
    CONFUSED = "confused"
    STUCK = "stuck"
    OFFLINE = "offline"
    DECLINED = "declined"

    def __str__(self) -> str:
        return self.value


@dataclass(slots=True)
class Step:
    index: int
    code: str
    output: str
    error: str | None
    attempts: int
    calls: list[str]
    seconds: float

    def view(self) -> StepView:
        return StepView(self.code, self.output, self.error)


@dataclass(slots=True)
class Turn:
    request: str
    outcome: Outcome
    answer: str
    route: Route
    mode: str  # "fast", "chat" or "tools"
    steps: list[Step] = field(default_factory=list)
    model_calls: int = 0
    peak_tokens: int = 0
    seconds: float = 0.0
    actions: list[str] = field(default_factory=list)
    declined: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.outcome in (Outcome.ANSWERED, Outcome.DECLINED)

    def record(self) -> dict:
        data = asdict(self)
        data["outcome"] = str(self.outcome)
        data["route"] = str(self.route)
        return data


#: ``on_event(kind, text)`` -- live progress for the CLI. Kinds: route, think,
#: code, output, error, retry.
EventSink = Callable[[str, str], None]

#: "continue", "keep going", "ok go on", "finish it": a short message that only
#: asks for the unfinished task to be picked up again. Anything longer is a new
#: request, even if it starts with one of these words.
_CONTINUE = re.compile(
    r"^(?:ok(?:ay)?|yes|yeah|yep|sure|please|now)?[\s,.!]*"
    r"(?:continue|carry on|keep going|go on|go ahead|resume|proceed|try again|"
    r"finish (?:it|that|this|the task|the job)|pick (?:it|that) up)"
    r"(?:\s+(?:please|now|again|from there|where you left off))?[\s.!]*$",
    re.IGNORECASE,
)

#: What a finished request leaves its task as. Only "open" can be continued.
_TASK_STATUS = {
    Outcome.ANSWERED: "done",
    Outcome.DECLINED: "declined",
}


def _silent(kind: str, text: str) -> None:
    return None


@dataclass(slots=True)
class Agent:
    model: ChatModel
    api: OsApi
    router: Router
    memory: GraphMemory
    config: AgentConfig
    sandbox: Sandbox = field(default_factory=Sandbox)
    on_event: EventSink = _silent
    #: The last few (request, answer) pairs. Session memory, never stored.
    recent: list[tuple[str, str]] = field(default_factory=list)
    recent_limit: int = 3
    #: Stream CHAT replies through on_event("chunk", ...) as they arrive.
    stream: bool = False
    _system: str = field(default_factory=task_system)

    # -- public ------------------------------------------------------------

    def turn(self, request: str) -> Turn:
        """Answer one request. Never raises."""
        started = time.monotonic()
        self.api.actions.clear()
        self.api.declined.clear()
        route = self.router.route(request)
        self.on_event("route", str(route))

        turn: Turn | None = None
        resume = self._resumable(request)
        if resume is not None:
            # "continue" says nothing a router could classify; the unfinished
            # task is the request. Skip the fast and chat paths.
            self.on_event("route", f"continuing unfinished task #{resume.id}: {one_line(resume.request, 60)}")
            turn = self._tools(request, route, resume)
        if turn is None and route.intent in ACTIONS and route.confidence >= self.config.router.threshold:
            fast = run_fast(route, self.api)
            if fast is not None:
                turn = Turn(request, Outcome.ANSWERED, fast.answer, route, "fast")
            else:
                self.on_event("route", "fast path could not finish it; asking the model")
        if turn is None and route.intent == "CHAT" and route.confidence >= 0.75:
            turn = self._chat(request, route)
        if turn is None:
            turn = self._tools(request, route)

        turn.seconds = time.monotonic() - started
        turn.actions = list(self.api.actions)
        turn.declined = list(self.api.declined)
        self._finish(turn)
        return turn

    def remember_exchange(self, request: str, answer: str) -> None:
        self.recent.append((request, answer))
        del self.recent[: -self.recent_limit]

    def _resumable(self, request: str) -> TaskState | None:
        """The unfinished task this message asks to pick up, if it asks for one."""
        if len(request) > 60 or not _CONTINUE.match(request.strip()):
            return None
        try:
            return self.memory.open_task()
        except sqlite3.Error:
            return None

    # -- modes ---------------------------------------------------------------

    def _chat(self, request: str, route: Route) -> Turn:
        memory = self.memory.context_for(request)
        window = render_chat(request=request, memory=memory, recent=self.recent)
        tokens = estimate_tokens(CHAT_SYSTEM) + estimate_tokens(window)
        self.on_event("think", "answering")
        stream = getattr(self.model, "stream", None) if self.stream else None
        try:
            if stream is not None:
                pieces = []
                for piece in stream(system=CHAT_SYSTEM, user=window):
                    pieces.append(piece)
                    self.on_event("chunk", piece)
                reply = "".join(pieces)
            else:
                reply = self.model.complete(system=CHAT_SYSTEM, user=window)
        except LLMError as exc:
            return Turn(request, Outcome.OFFLINE, str(exc), route, "chat",
                        model_calls=1, peak_tokens=tokens, notes=[str(exc)])
        answer = reply.strip() or "I don't have an answer for that."
        return Turn(request, Outcome.ANSWERED, answer, route, "chat",
                    model_calls=1, peak_tokens=tokens)

    def _budget(self) -> int:
        llm = self.config.llm
        # What the user message may spend: the whole context, minus the
        # system prompt, minus room for the reply, minus a safety margin.
        return max(400, llm.context - llm.max_tokens - estimate_tokens(self._system) - 64)

    def _tools(self, request: str, route: Route, resume: TaskState | None = None) -> Turn:
        # One sandboxed Python per request: variables survive between steps,
        # and the process is gone when the request is. The *task* outlives it:
        # its steps and notes are in memory, so a task that runs out of steps
        # can be continued, and a window that cannot hold it loses nothing.
        task = self._begin_task(request, route, resume)
        self.api.task = task
        try:
            with self.sandbox.session(self.api.names(), self.api.dispatch) as session:
                return self._tool_loop(request, route, session, resume, task)
        finally:
            self.api.task = None

    def _begin_task(self, request: str, route: Route, resume: TaskState | None) -> int | None:
        if resume is not None:
            return resume.id
        try:
            return self.memory.begin_task(request, route.intent)
        except sqlite3.Error:
            return None  # working memory is a help, not a requirement

    def _close_task(self, task: int | None, outcome: Outcome, had_steps: bool) -> None:
        if task is None:
            return
        # Only a task that got somewhere stays open to be continued.
        status = _TASK_STATUS.get(outcome) or ("open" if had_steps else "failed")
        try:
            self.memory.end_task(task, status)
        except sqlite3.Error:
            pass

    def _tool_loop(self, request: str, route: Route, session: Session,
                   resume: TaskState | None = None, task: int | None = None) -> Turn:
        # On a continue, the window's request is the original one and the
        # steps already taken come back as one-line digests.
        goal = resume.request if resume is not None else request
        earlier = resume.steps if resume is not None else []
        offset = len(earlier)
        memory = self.memory.context_for(goal, exclude_task=task)
        steps: list[Step] = []
        calls = 0
        peak = 0
        notes: list[str] = []

        def done(outcome: Outcome, answer: str) -> Turn:
            had_steps = bool(steps) or bool(earlier)
            self._close_task(task, outcome, had_steps)
            if had_steps and task is not None:
                if outcome is Outcome.EXHAUSTED:
                    answer += " Say 'continue' and I'll pick it up where I left off."
                elif outcome is Outcome.OFFLINE:
                    answer += " My progress is saved; say 'continue' once the model is back."
            return Turn(request, outcome, answer, route, "tools", steps, calls, peak, notes=notes)

        def add_step(source: str, result, attempt: int) -> None:
            step = Step(len(steps) + 1, source, result.output, result.error, attempt,
                        result.calls, result.seconds)
            steps.append(step)
            if task is None:
                return
            try:
                self.memory.log_step(task, offset + step.index, digest_step(step.view()),
                                     step_entities(source))
            except sqlite3.Error as exc:
                notes.append(f"step not saved: {exc}")

        def pinned() -> list[str]:
            if task is None:
                return []
            try:
                return self.memory.task_notes(task)
            except sqlite3.Error:
                return []

        def progress() -> str:
            """The last real output, for answers that end early."""
            for step in reversed(steps):
                if step.output.strip():
                    return " Here's what I had so far: " + one_line(step.output, 240)
            return ""

        # ---- OUTER LOOP: one iteration per step that actually ran ----------
        while len(steps) < self.config.max_steps:
            failure: Failure | None = None
            errors: list[str] = []
            attempt = 0
            step_done = False

            # ---- INNER LOOP: model calls until a block runs (or we answer) --
            while attempt < self.config.max_attempts:
                attempt += 1
                window = render_window(
                    request=goal, steps=[s.view() for s in steps], memory=memory,
                    recent=self.recent, failure=failure, budget=self._budget(),
                    today=datetime.now().strftime("%A %d %B %Y, %H:%M"),
                    earlier=earlier, notes=pinned(), step_offset=offset,
                    resumed=resume is not None,
                )
                peak = max(peak, estimate_tokens(self._system) + estimate_tokens(window))
                self.on_event("think", f"step {len(steps) + 1}, try {attempt}")
                try:
                    # Retries sample hotter. At 0.2 the 1.5B model is nearly
                    # deterministic, and in testing a retry was the same
                    # failing line, word for word, three times running.
                    heat = min(1.0, self.config.llm.temperature + 0.35 * (attempt - 1))
                    reply = self.model.complete(system=self._system, user=window,
                                                temperature=heat)
                    calls += 1
                except Truncated as exc:
                    calls += 1
                    failure = Failure(f"{exc}; write a shorter block")
                    errors.append("truncated")
                    self.on_event("retry", str(exc))
                    continue
                except LLMError as exc:
                    notes.append(str(exc))
                    return done(Outcome.OFFLINE, str(exc))

                decision = parse_reply(reply)

                if (isinstance(decision, Confused) and steps
                        and decision.reason.startswith("the reply had neither")):
                    # Seen constantly with the 1.5B model: it has the output,
                    # and answers in plain prose without the ANSWER prefix.
                    # After a real step, prose with no code *is* the answer.
                    # (Before any step it is not: "I opened Firefox" with
                    # nothing run is a claim, not an answer.)
                    decision = Answer(one_line(reply))

                if isinstance(decision, Answer):
                    return done(Outcome.ANSWERED, decision.text)

                if isinstance(decision, Confused):
                    notes.append(decision.reason)
                    failure = Failure(f"{decision.reason}; {CONFUSED_HINT}")
                    errors.append(decision.reason)
                    self.on_event("retry", decision.reason)
                    continue

                assert isinstance(decision, Code)
                decision = Code(drop_unused_imports(decision.source))
                if steps and decision.source.strip() == steps[-1].code.strip():
                    # Escalate: stop offering code, ask only for the answer.
                    failure = Failure(
                        "You already ran that block; its output is above. Do not run it again.",
                        answer_now=True,
                    )
                    errors.append("repeat")
                    self.on_event("retry", "same block as the last step; asking for the answer")
                    continue

                self.on_event("code", decision.source)
                result = session.run(decision.source)
                if result.output:
                    self.on_event("output", result.output)

                if self.api.declined:
                    # The user said no. The turn ends here and the harness,
                    # not the model, says what did not happen.
                    if result.output or self.api.changed_something(result.calls):
                        add_step(decision.source, result, attempt)
                    return done(Outcome.DECLINED,
                                f"OK, I did not do that ({self.api.declined[0]})." + progress())

                if result.ok or self.api.changed_something(result.calls):
                    # Ran, or failed after it had already changed something
                    # (opened a window, wrote a file): either way it is
                    # history the model must see, or it will do it twice.
                    if result.error:
                        self.on_event("error", result.error)
                    add_step(decision.source, result, attempt)
                    step_done = True
                    break

                self.on_event("error", result.error or "failed")
                error = result.error or "the code failed"
                if failure is not None and failure.code == decision.source:
                    error = ("this is exactly the code that just failed; change it. " + error)
                failure = Failure(error, decision.source)
                errors.append(result.error or "failed")

            if not step_done:
                # ---- inner loop used up without a block that ran ----------
                if steps and errors and errors[-1] == "repeat" and steps[-1].output.strip():
                    # The model has the result and will not stop re-running
                    # it. The output is real, so hand it over rather than fail.
                    notes.append("answer taken from the last output")
                    return done(Outcome.ANSWERED,
                                "Here's what I found: " + one_line(steps[-1].output, 300))
                repeated = [e for e, n in Counter(errors).items() if n >= 2 and e != "repeat"]
                if repeated:
                    # Not necessarily back to back: in testing a missing
                    # sound server failed, then an unreadable reply, then
                    # the same failure again. The user should hear the cause.
                    notes.append(f"repeated: {repeated[0]}")
                    return done(Outcome.STUCK,
                                "I kept hitting the same problem, so I stopped: "
                                f"{repeated[0][:160]}." + progress())
                return done(Outcome.CONFUSED,
                            "I couldn't work out how to do that. Try rephrasing it, "
                            "or break it into smaller steps." + progress())

        return done(Outcome.EXHAUSTED, "I ran out of steps before finishing." + progress())

    # -- bookkeeping -------------------------------------------------------

    def _finish(self, turn: Turn) -> None:
        try:
            self.memory.log_episode(turn.request, turn.answer, str(turn.outcome), turn.mode)
        except Exception as exc:  # noqa: BLE001 - a log must not fail a turn
            turn.notes.append(f"episode not logged: {exc}")
        if turn.outcome is Outcome.ANSWERED:
            self.remember_exchange(turn.request, turn.answer)
        runs = self.config.runs_path
        if runs is None:
            return
        try:
            runs.mkdir(parents=True, exist_ok=True)
            path = Path(runs) / time.strftime("%Y-%m-%d.jsonl")
            record = turn.record()
            record["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            record["model"] = self.model.model_id
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, default=str) + "\n")
        except OSError as exc:
            turn.notes.append(f"trace not written: {exc.strerror}")
