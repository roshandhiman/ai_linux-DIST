"""Run the project agent across scripted provider outages."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mineos_agent.agent import Outcome
from mineos_agent.coding import CodingProviders, build_coding_agent
from mineos_agent.config import LLMConfig
from mineos_agent.llm import LLMError
from mineos_agent.os_api import ApiError
from mineos_agent.providers import HostedChat
from mineos_agent.sandbox import Sandbox

from .test_providers import served


def answer(text):
    return (200, {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]})


class CodingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        self.project = base / "project"
        self.project.mkdir()
        self.file = self.project / "example.py"
        self.file.write_text("def value():\n    return 1\n")
        env = patch.dict(os.environ, {
            "XDG_DATA_HOME": str(base / "data"),
            "XDG_STATE_HOME": str(base / "state"),
            "ZAI_API_KEY": "fake-zai",
            "GROQ_API_KEY": "fake-groq",
        })
        env.start()
        self.addCleanup(env.stop)
        self.events = []
        self.approvals = []

    def event(self, kind, text):
        self.events.append((kind, text))

    def approve(self, action, detail):
        self.approvals.append((action, detail))
        return True

    def providers(self, primary, backup):
        return CodingProviders(tuple(
            HostedChat(LLMConfig(provider=name, base_url=server.url,
                                 model=f"{name}-model", api_key=f"{name}-key", timeout=5),
                       no_redirect=True)
            for name, server in (("zai", primary), ("groq", backup))
        ), self.event)

    def agent(self, providers):
        agent = build_coding_agent(self.project, providers, trace=self.event,
                                   approver=self.approve)
        self.addCleanup(agent.memory.close)
        agent.sandbox = Sandbox(use_bwrap=False)
        return agent

    def test_429_switches_after_edit_without_replaying_it(self):
        edit = answer('''```python
print(mine.replace_text("example.py", "    return 1", "    return 2"))
```''')
        primary = served(self, [edit, (429, {}, {"Retry-After": "3600"})])
        backup = served(self, [
            answer('''```python
print(mine.read_file("example.py"))
```'''),
            answer("ANSWER Updated example.py and verified the new return value."),
        ])
        providers = self.providers(primary, backup)
        agent = self.agent(providers)

        result = agent.turn("Set the return value to 2.")

        self.assertEqual(result.outcome, Outcome.ANSWERED)
        self.assertEqual(len(self.approvals), 1)
        self.assertIn("-    return 1\n+    return 2", self.approvals[0][1])
        self.assertEqual(self.file.read_text(), "def value():\n    return 2\n")
        self.assertEqual(len(primary.seen), 2)
        self.assertEqual(len(backup.seen), 2)
        self.assertEqual(primary.seen[1]["body"]["messages"], backup.seen[0]["body"]["messages"])
        self.assertIn("edited ~/example.py", backup.seen[0]["body"]["messages"][1]["content"])
        self.assertIn("  |     return 2", backup.seen[1]["body"]["messages"][1]["content"])
        self.assertEqual(primary.seen[0]["headers"]["authorization"], "Bearer zai-key")
        self.assertEqual(backup.seen[0]["headers"]["authorization"], "Bearer groq-key")
        self.assertTrue(any(kind == "provider" and "groq" in message for kind, message in self.events))
        self.assertIn("retry in", providers.status()[0])
        self.assertNotIn("ZAI_API_KEY", agent.api.command_env)
        self.assertNotIn("GROQ_API_KEY", agent.api.command_env)

    def test_both_limited_then_resume_saved_request_in_new_session(self):
        edit = answer('''```python
print(mine.replace_text("example.py", "return 1", "return 2"))
```''')
        primary = served(self, [edit, (429, {}), answer("ANSWER The return value is now 2.")])
        backup = served(self, [(429, {})])
        agent = self.agent(self.providers(primary, backup))

        paused = agent.turn("Update example.py, then report the result.")
        self.assertEqual(paused.outcome, Outcome.OFFLINE)
        self.assertIn("say 'continue'", paused.answer)
        self.assertEqual(len(agent.memory.open_task().steps), 1)

        resumed = self.agent(self.providers(primary, backup)).turn("continue")
        self.assertEqual(resumed.outcome, Outcome.ANSWERED)
        self.assertIn("Update example.py", primary.seen[-1]["body"]["messages"][1]["content"])
        self.assertIn("edited ~/example.py", primary.seen[-1]["body"]["messages"][1]["content"])
        self.assertEqual(len(self.approvals), 1)

    def test_permanent_http_error_is_reported(self):
        primary = served(self, [(400, {})])
        backup = served(self, [])
        with self.assertRaisesRegex(LLMError, "HTTP 400"):
            self.providers(primary, backup).complete(system="system", user="request")
        self.assertEqual(backup.seen, [])

    def test_exact_edit_refuses_ambiguous_and_stale_source(self):
        api = self.agent(CodingProviders((), self.event)).api
        self.file.write_text("aaa\n")
        with self.assertRaisesRegex(ApiError, "exactly one match"):
            api.replace_text("example.py", "aa", "b")
        self.assertEqual(self.approvals, [])

        def change_before_approval(action, detail):
            self.file.write_text("external edit\n")
            return True

        api.approver = change_before_approval
        with self.assertRaisesRegex(ApiError, "changed since the preview"):
            api.replace_text("example.py", "aaa", "b")
        self.assertEqual(self.file.read_text(), "external edit\n")
