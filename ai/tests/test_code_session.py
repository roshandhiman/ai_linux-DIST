"""Regression coverage for Freebuff tool results and MineOS project tools."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mineos_agent.code_session import run_session
from mineos_agent.coding import CodingProviders, build_coding_agent
from mineos_agent.llm import ProviderUnavailable
from mineos_agent.os_api import ApiError


class ScriptedModel:
    config = SimpleNamespace(provider="groq", api_key="fixture")
    model_id = "fixture"

    def __init__(self):
        self.requests = []

    def request_completion(self, payload):
        self.requests.append(payload)
        turn = len(self.requests)
        calls = [
            ("list_dir", {}),
            ("read_file", {"path": "calculator.py"}),
            ("replace_text", {"path": "calculator.py", "old": "2 + 2", "new": "2 * 2"}),
            ("write_file", {"path": "index.html", "text": "<h1>Calculator</h1>\n"}),
        ]
        if turn <= len(calls):
            name, args = calls[turn - 1]
            message = {"role": "assistant", "tool_calls": [{
                "id": f"call_{turn}", "type": "function",
                "function": {"name": f"project_{name}", "arguments": json.dumps(args)},
            }]}
            finish = "tool_calls"
        else:
            message = {"role": "assistant", "content": "Created the calculator page."}
            finish = "stop"
        return {"id": f"completion-{turn}", "created": 1, "model": self.model_id,
                "choices": [{"index": 0, "message": message, "finish_reason": finish}]}


class CodeSessionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        self.work = base / "project"
        self.work.mkdir()
        self.sample = self.work / "calculator.py"
        self.sample.write_text("print(2 + 2)\n")
        env = patch.dict(os.environ, {"XDG_DATA_HOME": str(base), "XDG_STATE_HOME": str(base)})
        env.start()
        self.addCleanup(env.stop)
        self.approvals = []
        self.model = ScriptedModel()

        def approve(action, detail):
            self.approvals.append((action, detail))
            return True

        def event(*_):
            pass

        self.host = build_coding_agent(
            self.work, CodingProviders((self.model,), event), trace=event, approver=approve,
        )
        self.addCleanup(self.host.memory.close)

    @unittest.skipUnless(os.environ.get("MINEOS_TEST_CODE_ENGINE"), "compiled engine not provided")
    def test_freebuff_sees_directory_result_and_applies_edits(self):
        engine = Path(os.environ["MINEOS_TEST_CODE_ENGINE"]).resolve()
        attempts = []
        backup = self.model

        class Primary:
            config = SimpleNamespace(provider="zai", api_key="fixture")
            model_id = "primary-fixture"

            def request_completion(self, payload):
                attempts.append(payload)
                if len(attempts) > 1:
                    raise ProviderUnavailable("HTTP 429", retry_after=300)
                return backup.request_completion(payload)

        self.host.model.models = (Primary(), backup)
        self.assertEqual(run_session(self.host, "Turn this into a web calculator.",
                                     quiet=True, engine=engine), 0)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[-1]["messages"], self.model.requests[1]["messages"])
        self.assertEqual(self.sample.read_text(), "print(2 * 2)\n")
        self.assertEqual((self.work / "index.html").read_text(), "<h1>Calculator</h1>\n")
        self.assertEqual(len(self.approvals), 2)
        self.assertIn("calculator.py", json.dumps(self.model.requests[1]["messages"]))
        self.assertIn("print(2 + 2)", json.dumps(self.model.requests[2]["messages"]))

    def test_dotenv_can_be_created_without_exposing_it_to_the_model(self):
        path = self.work / ".env"
        self.host.api.create_environment("dotenv", text="CALC_MODE=development\n")
        self.assertEqual(path.read_text(), "CALC_MODE=development\n")
        with self.assertRaisesRegex(ApiError, "private"):
            self.host.api.read_file(".env")
        with self.assertRaisesRegex(ApiError, "already exists"):
            self.host.api.create_environment("dotenv", text="CALC_MODE=override\n")
