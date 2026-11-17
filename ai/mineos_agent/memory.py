"""Graph memory: what the agent knows about the user, as triples in SQLite.

Why a graph and not a list of notes. "My sister is Priya" and "Priya lives in
Pune" are two facts; a question about "my sister's city" needs both, and a flat
note search finds only the one with "sister" in it. Stored as nodes and edges::

    (user) -sister-> (priya) -lives in-> (pune)

recall matches the question against node names and then walks one hop, so the
second fact comes along with the first. That is the whole trick, and it is why
the window gets a handful of *relevant* lines instead of the user's life story.

Four kinds of memory, kept apart because they cost differently:

* **facts** (the graph's ``fact`` edges) -- durable, small, injected only when
  relevant;
* **tasks** (the graph's ``task`` edges plus two small tables) -- the working
  memory of a multi-step request: a one-line summary of every step, notes the
  model pinned, and the files and apps it touched. This is what lets a long
  task survive a window that cannot hold it, and be resumed after the step
  budget runs out. A task node ``task#7`` links to the *same* nodes the facts
  use, so "what did we do with shopping.txt" is a walk, not a search;
* **episodes** -- a log of every request and outcome, never put in a window,
  there for ``ai --memory`` and for debugging;
* **session** -- the last few exchanges, held by the CLI, not stored at all.

Everything stored is sanitised: memory is written from user requests and from
model output, and is read back into future windows, so it is exactly the place
an injected instruction would try to persist itself.
"""

import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Iterable

from .text import sanitise

__all__ = ["Fact", "GraphMemory", "TaskState", "TASK_PREFIX"]

#: Task nodes are named ``task#<id>``. The prefix is reserved: a fact cannot
#: use it, so a user (or an injected instruction) cannot forge a task.
TASK_PREFIX: Final[str] = "task#"
#: Closed tasks kept; older ones are deleted with their edges.
_KEEP_TASKS: Final[int] = 60
#: An unfinished task nobody continued for this long is let go.
_OPEN_TASK_DAYS: Final[float] = 3.0
#: Pinned notes kept per task. The oldest goes when a ninth is pinned.
_MAX_NOTES: Final[int] = 8

_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS nodes (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created REAL NOT NULL,
    updated REAL NOT NULL,
    hits    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS edges (
    id       INTEGER PRIMARY KEY,
    src      INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    dst      INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    created  REAL NOT NULL,
    updated  REAL NOT NULL,
    weight   REAL NOT NULL DEFAULT 1.0,
    source   TEXT NOT NULL DEFAULT 'user',
    UNIQUE (src, relation, dst)
);
CREATE INDEX IF NOT EXISTS edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS edges_dst ON edges(dst);
CREATE TABLE IF NOT EXISTS episodes (
    id      INTEGER PRIMARY KEY,
    at      REAL NOT NULL,
    request TEXT NOT NULL,
    answer  TEXT NOT NULL,
    outcome TEXT NOT NULL,
    route   TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS tasks (
    id      INTEGER PRIMARY KEY,
    started REAL NOT NULL,
    updated REAL NOT NULL,
    request TEXT NOT NULL,
    status  TEXT NOT NULL DEFAULT 'open',
    route   TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS task_steps (
    task    INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    idx     INTEGER NOT NULL,
    digest  TEXT NOT NULL,
    at      REAL NOT NULL,
    PRIMARY KEY (task, idx)
);
"""

#: Added to ``edges`` after the first release. ``fact`` is what the user told
#: the assistant; ``task`` is working memory. They share nodes, never rows.
_MIGRATIONS: Final[tuple[tuple[str, str], ...]] = (
    ("edges.kind", "ALTER TABLE edges ADD COLUMN kind TEXT NOT NULL DEFAULT 'fact'"),
)

#: Relations that hold many objects at once. Anything else is treated as
#: single-valued: telling it "my wifi password is X" twice with different X
#: should replace the old value, not keep both and guess later.
_MULTI: Final[frozenset[str]] = frozenset(
    {"likes", "like", "loves", "knows", "has", "owns", "uses", "visited",
     "wants", "dislikes", "plays", "speaks", "friend", "note", "notes"}
)

_STOP: Final[frozenset[str]] = frozenset(
    "a an and are as at be by can could do does for from had has have how i if "
    "in is it its me my of on or our please should so tell than that the their "
    "them then there these they this to us was we what when where which who why "
    "will with would you your about know remember recall".split()
)

_TOKEN = re.compile(r"[a-z0-9][a-z0-9_.@+-]*")


_PART = re.compile(r"[._@+-]+")


def _tokens(text: str) -> set[str]:
    """Words worth matching on. ``shopping.txt`` yields itself and ``shopping``,
    so a question about "the shopping list" finds the file it is about."""
    found: set[str] = set()
    for token in _TOKEN.findall(text.lower()):
        for part in (token, *_PART.split(token)):
            if len(part) > 1 and part not in _STOP:
                found.add(part)
    return found


def _clean(text: str, limit: int) -> str:
    return sanitise(str(text), limit=limit).strip(" .").lower()


@dataclass(frozen=True, slots=True)
class Fact:
    subject: str
    relation: str
    object: str
    updated: float
    score: float = 0.0

    def __str__(self) -> str:
        return f"{self.subject} -{self.relation}-> {self.object}"


@dataclass(slots=True)
class TaskState:
    """One multi-step request as memory holds it."""
    id: int
    request: str
    status: str  # open | done | declined | failed | expired
    started: float
    updated: float
    #: "3. find_files('pdf') -> ['~/Downloads/a.pdf']" -- numbered, oldest first.
    steps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    touched: list[str] = field(default_factory=list)


_STATUS_WORDS: Final[dict[str, str]] = {
    "done": "finished",
    "open": "unfinished; the user can say continue",
    "declined": "the user said no to part of it",
    "failed": "did not work out",
    "expired": "unfinished and old",
}


def _label(text: str, limit: int) -> str:
    """Like ``_clean`` but keeps case: for notes, which are read by people."""
    return sanitise(str(text), limit=limit).strip()


class GraphMemory:
    """A small knowledge graph. ``path=":memory:"`` for tests."""

    def __init__(self, path: Path | str) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(_SCHEMA)
        self._migrate()
        self._db.commit()

    def _migrate(self) -> None:
        """Bring a database written by an older release up to date."""
        have = {row[1] for row in self._db.execute("PRAGMA table_info(edges)")}
        for marker, sql in _MIGRATIONS:
            if marker == "edges.kind" and "kind" not in have:
                self._db.execute(sql)
        self._db.execute("CREATE INDEX IF NOT EXISTS edges_kind ON edges(kind)")

    def close(self) -> None:
        self._db.close()

    # -- writing ----------------------------------------------------------

    def _node(self, name: str, now: float) -> int:
        row = self._db.execute("SELECT id FROM nodes WHERE name = ?", (name,)).fetchone()
        if row:
            self._db.execute("UPDATE nodes SET updated = ? WHERE id = ?", (now, row[0]))
            return int(row[0])
        cursor = self._db.execute(
            "INSERT INTO nodes(name, created, updated) VALUES (?, ?, ?)", (name, now, now)
        )
        return int(cursor.lastrowid or 0)

    def remember(self, subject: str, relation: str, obj: str, *, source: str = "user") -> str:
        """Store one fact. Returns the sentence the caller can show."""
        s, r, o = _clean(subject, 60), _clean(relation, 40), _clean(obj, 120)
        if not s or not r or not o:
            raise ValueError("a fact needs a subject, a relation and an object")
        if s.startswith(TASK_PREFIX) or o.startswith(TASK_PREFIX):
            raise ValueError(f"'{TASK_PREFIX}' is reserved for the assistant's own task notes")
        now = time.time()
        src, dst = self._node(s, now), self._node(o, now)
        if r not in _MULTI:
            self._db.execute(
                "DELETE FROM edges WHERE src = ? AND relation = ? AND dst != ? AND kind = 'fact'",
                (src, r, dst),
            )
        self._db.execute(
            """INSERT INTO edges(src, relation, dst, created, updated, source)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(src, relation, dst)
               DO UPDATE SET updated = excluded.updated, weight = weight + 1""",
            (src, r, dst, now, now, source),
        )
        self._prune_orphans()
        self._db.commit()
        return f"remembered: {s} -{r}-> {o}"

    def forget(self, name: str) -> int:
        """Remove a node and every fact touching it. Returns facts removed."""
        target = _clean(name, 120)
        row = self._db.execute("SELECT id FROM nodes WHERE name = ?", (target,)).fetchone()
        if not row:
            return 0
        count = self._db.execute(
            "SELECT COUNT(*) FROM edges WHERE src = ? OR dst = ?", (row[0], row[0])
        ).fetchone()[0]
        self._db.execute("DELETE FROM nodes WHERE id = ?", (row[0],))
        self._prune_orphans()
        self._db.commit()
        return int(count)

    def _prune_orphans(self) -> None:
        self._db.execute(
            """DELETE FROM nodes WHERE id NOT IN (SELECT src FROM edges)
               AND id NOT IN (SELECT dst FROM edges)"""
        )

    def log_episode(self, request: str, answer: str, outcome: str, route: str = "") -> None:
        self._db.execute(
            "INSERT INTO episodes(at, request, answer, outcome, route) VALUES (?, ?, ?, ?, ?)",
            (time.time(), sanitise(request, limit=300), sanitise(answer, limit=300),
             outcome, route),
        )
        # Episodes are a log, not a memory: keep the last thousand.
        self._db.execute(
            "DELETE FROM episodes WHERE id <= (SELECT MAX(id) FROM episodes) - 1000"
        )
        self._db.commit()

    # -- reading ----------------------------------------------------------

    # -- tasks: working memory for a multi-step request -------------------

    def begin_task(self, request: str, route: str = "") -> int:
        """Open a task. Returns its id. Old unfinished tasks are let go here."""
        now = time.time()
        self._db.execute(
            "UPDATE tasks SET status = 'expired' WHERE status = 'open' AND updated < ?",
            (now - _OPEN_TASK_DAYS * 86400,),
        )
        cursor = self._db.execute(
            "INSERT INTO tasks(started, updated, request, route) VALUES (?, ?, ?, ?)",
            (now, now, _label(request, 600), route),
        )
        self._trim_tasks()
        self._db.commit()
        return int(cursor.lastrowid or 0)

    def log_step(self, task: int, index: int, digest: str,
                 touched: Iterable[str] = ()) -> None:
        """One finished step: its summary, and what it touched as graph edges."""
        now = time.time()
        self._db.execute(
            "INSERT OR REPLACE INTO task_steps(task, idx, digest, at) VALUES (?, ?, ?, ?)",
            (task, index, _label(digest, 200), now),
        )
        self._db.execute("UPDATE tasks SET updated = ? WHERE id = ?", (now, task))
        for thing in touched:
            name = _clean(thing, 80)
            if name and not name.startswith(TASK_PREFIX):
                self._link_task(task, "touched", name, now)
        self._db.commit()

    def pin_note(self, task: int, text: str) -> str:
        """Pin a finding to a task. It stays in the window after steps are summarised."""
        note = _label(text, 160)
        if not note:
            raise ValueError("a note needs some text")
        now = time.time()
        self._link_task(task, "note", note, now)
        src = f"{TASK_PREFIX}{task}"
        rows = self._db.execute(
            """SELECT e.id FROM edges e JOIN nodes s ON s.id = e.src
               WHERE s.name = ? AND e.relation = 'note' AND e.kind = 'task'
               ORDER BY e.id DESC""",
            (src,),
        ).fetchall()
        for (old,) in rows[_MAX_NOTES:]:
            self._db.execute("DELETE FROM edges WHERE id = ?", (old,))
        self._prune_orphans()
        self._db.commit()
        return f"noted: {note}"

    def end_task(self, task: int, status: str) -> None:
        self._db.execute(
            "UPDATE tasks SET status = ?, updated = ? WHERE id = ?", (status, time.time(), task)
        )
        self._db.commit()

    def _link_task(self, task: int, relation: str, obj: str, now: float) -> None:
        src = self._node(f"{TASK_PREFIX}{task}", now)
        dst = self._node(obj, now)
        self._db.execute(
            """INSERT INTO edges(src, relation, dst, created, updated, source, kind)
               VALUES (?, ?, ?, ?, ?, 'agent', 'task')
               ON CONFLICT(src, relation, dst)
               DO UPDATE SET updated = excluded.updated, weight = weight + 1""",
            (src, relation, dst, now, now),
        )

    def _trim_tasks(self) -> None:
        old = self._db.execute(
            "SELECT id FROM tasks ORDER BY id DESC LIMIT -1 OFFSET ?", (_KEEP_TASKS,)
        ).fetchall()
        for (task,) in old:
            self._db.execute("DELETE FROM nodes WHERE name = ?", (f"{TASK_PREFIX}{task}",))
            self._db.execute("DELETE FROM tasks WHERE id = ?", (task,))
        if old:
            self._prune_orphans()

    def _task_state(self, row: tuple) -> TaskState:
        task = TaskState(int(row[0]), row[1], row[2], row[3], row[4])
        task.steps = [f"{idx}. {digest}" for idx, digest in self._db.execute(
            "SELECT idx, digest FROM task_steps WHERE task = ? ORDER BY idx", (task.id,))]
        for relation, name in self._db.execute(
            """SELECT e.relation, d.name FROM edges e
               JOIN nodes s ON s.id = e.src JOIN nodes d ON d.id = e.dst
               WHERE s.name = ? AND e.kind = 'task' ORDER BY e.id""",
            (f"{TASK_PREFIX}{task.id}",),
        ):
            (task.notes if relation == "note" else task.touched).append(name)
        return task

    _TASK_COLUMNS = "id, request, status, started, updated"

    def task(self, task: int) -> TaskState | None:
        row = self._db.execute(
            f"SELECT {self._TASK_COLUMNS} FROM tasks WHERE id = ?", (task,)
        ).fetchone()
        return self._task_state(row) if row else None

    def task_notes(self, task: int) -> list[str]:
        """Just the pinned notes: cheap enough to ask before every model call."""
        return [row[0] for row in self._db.execute(
            """SELECT d.name FROM edges e
               JOIN nodes s ON s.id = e.src JOIN nodes d ON d.id = e.dst
               WHERE s.name = ? AND e.relation = 'note' AND e.kind = 'task' ORDER BY e.id""",
            (f"{TASK_PREFIX}{task}",))]

    def open_task(self) -> TaskState | None:
        """The newest unfinished task that got at least one step done."""
        row = self._db.execute(
            f"""SELECT {self._TASK_COLUMNS} FROM tasks
                WHERE status = 'open' AND updated >= ?
                  AND EXISTS (SELECT 1 FROM task_steps WHERE task = tasks.id)
                ORDER BY id DESC LIMIT 1""",
            (time.time() - _OPEN_TASK_DAYS * 86400,),
        ).fetchone()
        return self._task_state(row) if row else None

    def tasks(self, *, limit: int = 10) -> list[TaskState]:
        rows = self._db.execute(
            f"""SELECT {self._TASK_COLUMNS} FROM tasks
                WHERE EXISTS (SELECT 1 FROM task_steps WHERE task = tasks.id)
                ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [self._task_state(row) for row in rows]

    def recall_tasks(self, query: str, *, limit: int = 2,
                     exclude: int | None = None) -> list[str]:
        """Past tasks that look like ``query``, as one line each.

        Scored like facts: words shared with what was asked (x2), with what was
        touched (x2) and with the pinned notes (x1), then a small recency bonus.
        """
        wanted = _tokens(query)
        if not wanted:
            return []
        now = time.time()
        ranked: list[tuple[float, TaskState]] = []
        for task in self.tasks(limit=_KEEP_TASKS):
            if task.id == exclude:
                continue
            score = (2.0 * len(wanted & _tokens(task.request))
                     + 2.0 * len(wanted & _tokens(" ".join(task.touched)))
                     + 1.0 * len(wanted & _tokens(" ".join(task.notes))))
            if score >= 2.0:
                ranked.append((score + 0.5 / (1.0 + (now - task.updated) / 86400), task))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        lines = []
        for _, task in ranked[:limit]:
            line = (f'earlier task ({_STATUS_WORDS.get(task.status, task.status)}): '
                    f'"{task.request[:80]}"')
            if task.touched:
                line += " | touched " + ", ".join(task.touched[-3:])
            if task.notes:
                line += " | noted: " + "; ".join(task.notes[-2:])
            lines.append(line)
        return lines

    def _all_facts(self, limit: int = 2000) -> list[Fact]:
        rows = self._db.execute(
            """SELECT s.name, e.relation, d.name, e.updated, e.weight
               FROM edges e JOIN nodes s ON s.id = e.src JOIN nodes d ON d.id = e.dst
               WHERE e.kind = 'fact'
               ORDER BY e.updated DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [Fact(r[0], r[1], r[2], r[3], r[4]) for r in rows]

    def recall(self, query: str, *, limit: int = 8) -> list[Fact]:
        """Facts relevant to ``query``: direct matches, then one hop out."""
        wanted = _tokens(query)
        facts = self._all_facts()
        if not wanted or not facts:
            return []
        now = time.time()

        def direct(fact: Fact) -> float:
            return 2.0 * len(wanted & _tokens(fact.subject)) + 2.0 * len(
                wanted & _tokens(fact.object)
            ) + 1.0 * len(wanted & _tokens(fact.relation))

        scored: dict[tuple[str, str, str], float] = {}
        seeds: set[str] = set()
        for fact in facts:
            score = direct(fact)
            if score:
                scored[(fact.subject, fact.relation, fact.object)] = score
                seeds.update((fact.subject, fact.object))
        # One hop: facts touching a node that a direct match touched.
        for fact in facts:
            key = (fact.subject, fact.relation, fact.object)
            if key not in scored and (fact.subject in seeds or fact.object in seeds):
                scored[key] = 0.75
        ranked = []
        for fact in facts:
            key = (fact.subject, fact.relation, fact.object)
            if key in scored:
                age_days = (now - fact.updated) / 86400
                bonus = 0.5 / (1.0 + age_days) + 0.1 * min(fact.score, 5)
                ranked.append(Fact(*key, fact.updated, scored[key] + bonus))
        ranked.sort(key=lambda f: f.score, reverse=True)
        top = ranked[:limit]
        if top:
            names = {f.subject for f in top} | {f.object for f in top}
            self._db.executemany(
                "UPDATE nodes SET hits = hits + 1 WHERE name = ?", [(n,) for n in names]
            )
            self._db.commit()
        return top

    def context_for(self, request: str, *, limit: int = 8,
                    exclude_task: int | None = None) -> list[str]:
        """The memory lines worth spending window on for this request."""
        lines: list[str] = []
        for fact in self.recall(request, limit=limit):
            lines.append(str(fact))
        # A couple of facts about the user ride along regardless -- their name
        # is relevant to almost everything and costs ten tokens.
        for fact in self.about("user", limit=3):
            line = str(fact)
            if line not in lines and len(lines) < limit:
                lines.append(line)
        # Up to two earlier tasks that resemble this one. They ride on top of
        # the fact budget: a past task is a pointer, not a story.
        lines.extend(self.recall_tasks(request, limit=2, exclude=exclude_task))
        return lines

    def about(self, name: str, *, limit: int = 20) -> list[Fact]:
        target = _clean(name, 120)
        return [f for f in self._all_facts() if target in (f.subject, f.object)][:limit]

    def facts(self, *, limit: int = 50) -> list[Fact]:
        return self._all_facts(limit)

    def episodes(self, *, limit: int = 10) -> list[tuple[float, str, str, str]]:
        rows = self._db.execute(
            "SELECT at, request, answer, outcome FROM episodes ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [(r[0], r[1], r[2], r[3]) for r in rows]

    def stats(self) -> dict[str, int]:
        one = lambda sql: int(self._db.execute(sql).fetchone()[0])  # noqa: E731
        return {
            "nodes": one("SELECT COUNT(*) FROM nodes"),
            "facts": one("SELECT COUNT(*) FROM edges WHERE kind = 'fact'"),
            "episodes": one("SELECT COUNT(*) FROM episodes"),
            "tasks": one("SELECT COUNT(*) FROM tasks"),
        }


def render_facts(facts: Iterable[Fact | str]) -> str:
    return "\n".join(f"  {fact}" for fact in facts)
