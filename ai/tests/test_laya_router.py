"""The Laya tier: when it is asked, how its answer is used, and what happens
when the service is missing. A fake ``post`` stands in for laya-serve."""

import json
import tempfile
import unittest
from pathlib import Path

from mineos_agent.config import load_config
from mineos_agent.router import LAYA_QUESTION, HybridRouter, LayaRouter


def reply(choice: str, p: float) -> dict:
    rest = (1.0 - p) / (len(LAYA_QUESTION["criteria"]) - 1)
    probabilities = {key: (p if key == choice else rest) for key in LAYA_QUESTION["criteria"]}
    return {"answers": {"intent": {"type": "choice", "choice": choice,
                                   "probabilities": probabilities, "confidence": 0.5}}}


class FakeLaya:
    def __init__(self, answer=None, error=None):
        self.answer, self.error, self.calls = answer, error, []

    def __call__(self, url, payload, timeout):
        self.calls.append((url, payload, timeout))
        if self.error:
            raise self.error
        return self.answer


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def hybrid(fake, threshold=0.85, clock=None):
    laya = LayaRouter("http://127.0.0.1:8090/", post=fake, clock=clock)
    return HybridRouter(laya=laya, threshold=threshold)


class LayaRouterTests(unittest.TestCase):
    def test_confident_rules_never_call_laya(self):
        fake = FakeLaya(reply("chat", 0.99))
        route = hybrid(fake).route("open firefox")
        self.assertEqual((route.intent, route.slots), ("OPEN", {"target": "firefox"}))
        self.assertEqual(fake.calls, [])

    def test_naming_a_thing_on_this_computer_skips_laya(self):
        # Measured: Laya read these as chat or memory, with high confidence.
        fake = FakeLaya(reply("memory", 0.99))
        for request in ("send hello to the esp32", "what's in my notes file",
                        "how many photos are in my pictures folder", "मेरे डाउनलोड फ़ोल्डर में क्या है"):
            with self.subTest(request=request):
                self.assertEqual(hybrid(fake).route(request).intent, "TASK")
        self.assertEqual(fake.calls, [])

    def test_a_strict_threshold_never_lets_laya_override_a_rule(self):
        fake = FakeLaya(reply("memory", 1.0))
        route = hybrid(fake, threshold=0.99).route("how much battery do I have")
        self.assertEqual((route.intent, route.backend), ("STATUS", "rules"))
        self.assertEqual(fake.calls, [])

    def test_laya_decides_what_the_rules_cannot(self):
        fake = FakeLaya(reply("status", 0.93))
        route = hybrid(fake).route("am I about to run out of juice")
        self.assertEqual((route.intent, route.backend), ("STATUS", "laya"))
        self.assertAlmostEqual(route.confidence, 0.93)
        url, payload, _ = fake.calls[0]
        self.assertEqual(url, "http://127.0.0.1:8090/v1/systemone")
        self.assertEqual(payload["model"], "multilingual")
        self.assertEqual(payload["questions"]["intent"], LAYA_QUESTION)
        self.assertEqual(payload["state"], {"request": "am I about to run out of juice"})

    def test_a_non_english_request_can_reach_the_fast_path(self):
        route = hybrid(FakeLaya(reply("time", 0.9))).route("अभी कितने बजे हैं")
        self.assertEqual(route.intent, "TIME")

    def test_memory_questions_carry_the_request_as_query(self):
        route = hybrid(FakeLaya(reply("memory", 0.9))).route("which city does my sister live in")
        self.assertEqual((route.intent, route.slots["query"]), ("RECALL", "which city does my sister live in"))

    def test_action_means_the_tool_loop(self):
        route = hybrid(FakeLaya(reply("action", 0.95))).route("tidy up the screenshots on my desktop")
        self.assertEqual(route.intent, "TASK")

    def test_an_unsure_verdict_leaves_the_rules_in_charge(self):
        route = hybrid(FakeLaya(reply("status", 0.6))).route("am I about to run out of juice")
        self.assertEqual(route.intent, "TASK")
        self.assertIn("laya unsure", route.backend)

    def test_unknown_choice_is_a_task(self):
        bad ={"answers": {"intent": {"choice": "launch_missiles", "probabilities": {"launch_missiles": 1.0}}}}
        self.assertEqual(hybrid(FakeLaya(bad)).route("zzz").intent, "TASK")

    def test_a_down_service_falls_back_and_backs_off(self):
        clock = Clock()
        fake = FakeLaya(error=ConnectionRefusedError("refused"))
        router = hybrid(fake, clock=clock)
        self.assertEqual(router.route("sort out my week").intent, "TASK")
        self.assertEqual(router.route("plan my day").intent, "TASK")
        self.assertEqual(len(fake.calls), 1, "a down service is not retried on every request")
        self.assertIn("unavailable", router.describe())
        clock.now += 61
        fake.error, fake.answer = None, reply("chat", 0.95)
        self.assertEqual(router.route("plan my day").intent, "CHAT")
        self.assertEqual(len(fake.calls), 2)
        self.assertNotIn("unavailable", router.describe())

    def test_a_malformed_reply_is_a_failure_not_a_crash(self):
        route = hybrid(FakeLaya({"detail": "422 bad question"})).route("sort out my week")
        self.assertEqual(route.intent, "TASK")

    def test_no_laya_means_rules_only(self):
        route = HybridRouter().route("sort out my week")
        self.assertEqual((route.intent, route.backend), ("TASK", "rules"))


class RouterConfigTests(unittest.TestCase):
    def load(self, data=None, env=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.json"
            path.write_text(json.dumps(data or {}), encoding="utf-8")
            return load_config(files=(path,), environ=env or {})

    def test_default_is_rules_only(self):
        self.assertIsNone(self.load().router.url)

    def test_file_sets_laya(self):
        config = self.load({"router": {"url": "http://127.0.0.1:8090/", "checkpoint": "english",
                                       "timeout": 2, "threshold": 0.9}})
        self.assertEqual(config.router.url, "http://127.0.0.1:8090")
        self.assertEqual(config.router.checkpoint, "english")
        self.assertEqual((config.router.timeout, config.router.threshold), (2.0, 0.9))

    def test_env_can_turn_laya_off(self):
        config = self.load({"router": {"url": "http://127.0.0.1:8090"}}, {"MINEOS_ROUTER_URL": ""})
        self.assertIsNone(config.router.url)

    def test_null_url_in_user_file_turns_it_off(self):
        self.assertIsNone(self.load({"router": {"url": None}}).router.url)

    def test_shipped_config_is_valid(self):
        shipped = Path(__file__).resolve().parents[1] / "system" / "agent.json"
        config = load_config(files=(shipped,), environ={})
        self.assertEqual(config.router.url, "http://127.0.0.1:8090")
        self.assertEqual(config.warnings, [])


if __name__ == "__main__":
    unittest.main()
