"""Graph memory: what the agent knows about the user, as triples in SQLite.

Why a graph and not a list of notes. "My sister is Priya" and "Priya lives in
Pune" are two facts; a question about "my sister's city" needs both, and a flat
note search finds only the one with "sister" in it. Stored as nodes and edges::

    (user) -sister-> (priya) -lives in-> (pune)

recall matches the question against node names and then walks one hop, so the
second fact comes along with the first. That is the whole trick, and it is why
the window gets a handful of *relevant* lines instead of the user's life story.

Three kinds of memory, kept apart because they cost differently:

* **facts** (this graph) -- durable, small, injected only when relevant;
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
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable

from .text import sanitise

__all__ = ["Fact", "GraphMemory"]

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
"""

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


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if len(t) > 1 and t not in _STOP}


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


class GraphMemory:
    """A small knowledge graph. ``path=":memory:"`` for tests."""

    def __init__(self, path: Path | str) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(_SCHEMA)
        self._db.commit()

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
        now = time.time()
        src, dst = self._node(s, now), self._node(o, now)
        if r not in _MULTI:
            self._db.execute(
                "DELETE FROM edges WHERE src = ? AND relation = ? AND dst != ?", (src, r, dst)
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

    def _all_facts(self, limit: int = 2000) -> list[Fact]:
        rows = self._db.execute(
            """SELECT s.name, e.relation, d.name, e.updated, e.weight
               FROM edges e JOIN nodes s ON s.id = e.src JOIN nodes d ON d.id = e.dst
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

    def context_for(self, request: str, *, limit: int = 8) -> list[str]:
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
            "facts": one("SELECT COUNT(*) FROM edges"),
            "episodes": one("SELECT COUNT(*) FROM episodes"),
        }


def render_facts(facts: Iterable[Fact | str]) -> str:
    return "\n".join(f"  {fact}" for fact in facts)
