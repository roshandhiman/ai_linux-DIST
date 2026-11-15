"""Shared fakes. Run the suite from the repo root with:

    python3 -m unittest discover -s ai/tests -t ai
"""

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from mineos_agent.agent import Agent
from mineos_agent.config import AgentConfig
from mineos_agent.llm import LLMError
from mineos_agent.memory import GraphMemory
from mineos_agent.os_api import OsApi
from mineos_agent.router import HybridRouter
from mineos_agent.sandbox import Sandbox


@dataclass
class FakeModel:
    """Replies from a script, and records every window it was shown."""

    replies: list[str]
    windows: list[str] = field(default_factory=list)
    systems: list[str] = field(default_factory=list)
    temperatures: list = field(default_factory=list)

    @property
    def model_id(self) -> str:
        return "fake"

    def complete(self, *, system: str, user: str, temperature: float | None = None) -> str:
        self.temperatures.append(temperature)
        self.systems.append(system)
        self.windows.append(user)
        if not self.replies:
            raise LLMError("script ran out")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


@dataclass
class Spawned:
    argv: list[list[str]] = field(default_factory=list)

    def __call__(self, argv: list[str]) -> None:
        self.argv.append(argv)


def make_agent(replies, *, approve=False, home: Path | None = None):
    home = home or Path(tempfile.mkdtemp(prefix="mineos-home-"))
    memory = GraphMemory(":memory:")
    spawned = Spawned()
    approvals: list[str] = []

    def approver(action: str, detail: str) -> bool:
        approvals.append(action)
        return approve

    config = AgentConfig(home=home, runs_path=None, memory_path=Path(":memory:"))
    api = OsApi(home=home, memory=memory, approver=approver, spawn=spawned,
                app_dirs=())
    model = FakeModel(list(replies))
    agent = Agent(model=model, api=api, router=HybridRouter(), memory=memory,
                  config=config, sandbox=Sandbox(timeout=20, use_bwrap=False))
    return agent, model, spawned, approvals
