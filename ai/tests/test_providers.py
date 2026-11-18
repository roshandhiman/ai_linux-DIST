"""Provider adapters, tested against fake servers that speak each wire format.

No network and no keys: a throwaway HTTP server on 127.0.0.1 plays Anthropic,
OpenAI Responses and OpenAI chat completions, records what it was sent, and
answers from a script. That proves our requests and our reading of replies,
not that a real provider still behaves this way -- the live smoke test does.
"""

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from mineos_agent.config import LLMConfig, load_config
from mineos_agent.llm import LLMError, OpenAIChat, Truncated
from mineos_agent.providers import (PRESETS, AnthropicMessages, OpenAIResponses,
                                    apply_provider, build_model, check_health, describe)


class FakeProvider:
    """Serves scripted (status, body[, headers]) replies and records each request."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _answer(self, payload):
                outer.seen.append({"method": self.command, "path": self.path,
                                   "headers": {k.lower(): v for k, v in self.headers.items()},
                                   "body": payload})
                status, body, *headers = outer.replies.pop(0)
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for name, value in (headers[0] if headers else {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                self._answer(json.loads(self.rfile.read(length)))

            def do_GET(self):
                self._answer(None)

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def served(test, replies):
    fake = FakeProvider(replies)
    test.addCleanup(fake.close)
    return fake


def cfg(fake, provider, **extra):
    return LLMConfig(provider=provider, base_url=fake.url, model="m1", api_key="sk-test",
                     timeout=5, **extra)


def anthropic_ok(text="hello", stop="end_turn"):
    return (200, {"content": [{"type": "text", "text": text}], "stop_reason": stop,
                  "usage": {"input_tokens": 11, "output_tokens": 3}})


def responses_ok(text="hello", status="completed", details=None):
    return (200, {"status": status, "incomplete_details": details,
                  "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
                  "usage": {"input_tokens": 9, "output_tokens": 2}})


class AnthropicTests(unittest.TestCase):
    def test_request_shape_and_reply(self):
        fake = served(self, [anthropic_ok("ANSWER hi")])
        model = AnthropicMessages(cfg(fake, "anthropic", max_tokens=300))
        self.assertEqual(model.complete(system="SYS", user="USR", temperature=0.5), "ANSWER hi")
        sent = fake.seen[0]
        self.assertEqual(sent["path"], "/v1/messages")
        self.assertEqual(sent["headers"]["x-api-key"], "sk-test")
        self.assertEqual(sent["headers"]["anthropic-version"], "2023-06-01")
        self.assertNotIn("authorization", sent["headers"])
        body = sent["body"]
        self.assertEqual(body["model"], "m1")
        self.assertEqual(body["max_tokens"], 300)
        self.assertEqual(body["system"][0]["text"], "SYS")
        self.assertEqual(body["messages"], [{"role": "user", "content": "USR"}])
        self.assertEqual(body["temperature"], 0.5)
        self.assertEqual(model.last_usage, {"prompt_tokens": 11, "completion_tokens": 3})

    def test_text_blocks_joined_and_think_stripped(self):
        reply = (200, {"stop_reason": "end_turn", "content": [
            {"type": "thinking", "thinking": "hmm"},
            {"type": "text", "text": "<think>x</think>one "}, {"type": "text", "text": "two"}]})
        fake = served(self, [reply])
        out = AnthropicMessages(cfg(fake, "anthropic")).complete(system="s", user="u")
        self.assertEqual(out, "one two")

    def test_truncation_and_refusal(self):
        fake = served(self, [anthropic_ok("half", "max_tokens"), anthropic_ok("", "refusal")])
        model = AnthropicMessages(cfg(fake, "anthropic"))
        with self.assertRaises(Truncated):
            model.complete(system="s", user="u")
        with self.assertRaisesRegex(LLMError, "declined"):
            model.complete(system="s", user="u")

    def test_temperature_clamped_to_one(self):
        fake = served(self, [anthropic_ok()])
        AnthropicMessages(cfg(fake, "anthropic")).complete(system="s", user="u", temperature=1.4)
        self.assertEqual(fake.seen[0]["body"]["temperature"], 1.0)

    def test_retries_once_without_temperature_when_refused(self):
        refusal = (400, {"error": {"message": "`temperature` is deprecated for this model"}})
        fake = served(self, [refusal, anthropic_ok("fine")])
        out = AnthropicMessages(cfg(fake, "anthropic")).complete(system="s", user="u")
        self.assertEqual(out, "fine")
        self.assertIn("temperature", fake.seen[0]["body"])
        self.assertNotIn("temperature", fake.seen[1]["body"])

    def test_http_errors_are_readable(self):
        fake = served(self, [(401, {"error": {"message": "bad key sk-xyz"}}),
                             (429, {"error": {"message": "slow down"}}),
                             (400, {"error": {"message": "model: nope"}})])
        model = AnthropicMessages(cfg(fake, "anthropic"))
        with self.assertRaisesRegex(LLMError, "refused the API key") as ctx:
            model.complete(system="s", user="u")
        self.assertNotIn("sk-", str(ctx.exception))
        with self.assertRaisesRegex(LLMError, "rate-limiting"):
            model.complete(system="s", user="u")
        with self.assertRaisesRegex(LLMError, "model: nope"):
            model.complete(system="s", user="u")

    def test_no_key_never_touches_the_network(self):
        fake = served(self, [])
        config = cfg(fake, "anthropic")
        config.api_key = None
        with self.assertRaisesRegex(LLMError, "ANTHROPIC_API_KEY"):
            AnthropicMessages(config).complete(system="s", user="u")
        self.assertEqual(fake.seen, [])

    def test_health_uses_anthropic_headers(self):
        fake = served(self, [(200, {"data": [{"id": "claude-x"}]})])
        ok, detail = check_health(cfg(fake, "anthropic"))
        self.assertTrue(ok)
        self.assertIn("claude-x", detail)
        self.assertEqual(fake.seen[0]["headers"]["x-api-key"], "sk-test")
        self.assertEqual(fake.seen[0]["path"], "/v1/models")


class ResponsesTests(unittest.TestCase):
    def test_request_shape_and_reply(self):
        fake = served(self, [responses_ok("ANSWER ok")])
        model = OpenAIResponses(cfg(fake, "openai-responses", max_tokens=200))
        self.assertEqual(model.complete(system="SYS", user="USR"), "ANSWER ok")
        sent = fake.seen[0]
        self.assertEqual(sent["path"], "/v1/responses")
        self.assertEqual(sent["headers"]["authorization"], "Bearer sk-test")
        body = sent["body"]
        self.assertEqual((body["instructions"], body["input"]), ("SYS", "USR"))
        self.assertEqual(body["max_output_tokens"], 200)
        self.assertIs(body["store"], False)
        self.assertEqual(model.last_usage, {"prompt_tokens": 9, "completion_tokens": 2})

    def test_truncation_refusal_and_temperature_retry(self):
        fake = served(self, [
            responses_ok("half", "incomplete", {"reason": "max_output_tokens"}),
            (200, {"status": "completed", "output": [{"type": "message", "content": [
                {"type": "refusal", "refusal": "no"}]}]}),
            (400, {"error": {"message": "Unsupported parameter: 'temperature'"}}),
            responses_ok("fine"),
        ])
        model = OpenAIResponses(cfg(fake, "openai-responses"))
        with self.assertRaises(Truncated):
            model.complete(system="s", user="u")
        with self.assertRaisesRegex(LLMError, "declined"):
            model.complete(system="s", user="u")
        self.assertEqual(model.complete(system="s", user="u"), "fine")
        self.assertNotIn("temperature", fake.seen[3]["body"])


class ChatCompletionsViaFactory(unittest.TestCase):
    def test_hosted_openai_style_uses_bearer_and_chat_path(self):
        body = {"choices": [{"message": {"content": "yo"}, "finish_reason": "stop"}]}
        fake = served(self, [(200, body)])
        model = build_model(cfg(fake, "groq"))
        self.assertIsInstance(model, OpenAIChat)
        self.assertEqual(model.complete(system="s", user="u"), "yo")
        self.assertEqual(fake.seen[0]["path"], "/v1/chat/completions")
        self.assertEqual(fake.seen[0]["headers"]["authorization"], "Bearer sk-test")


class SelectionTests(unittest.TestCase):
    def test_factory_picks_adapter_by_provider(self):
        self.assertIsInstance(build_model(LLMConfig()), OpenAIChat)
        self.assertIsInstance(build_model(LLMConfig(provider="anthropic")), AnthropicMessages)
        self.assertIsInstance(build_model(LLMConfig(provider="openai-responses")), OpenAIResponses)
        for name in PRESETS:
            build_model(LLMConfig(provider=name))

    def test_preset_fills_defaults_and_finds_the_provider_key(self):
        config = load_config(files=(), environ={"MINEOS_PROVIDER": "anthropic",
                                                "ANTHROPIC_API_KEY": "k1"})
        llm = config.llm
        self.assertEqual((llm.base_url, llm.model, llm.api_key),
                         ("https://api.anthropic.com/v1", PRESETS["anthropic"].model, "k1"))
        self.assertEqual(llm.context, 32768)
        self.assertEqual(config.warnings, [])

    def test_what_the_user_set_beats_the_preset(self):
        env = {"MINEOS_PROVIDER": "anthropic", "MINEOS_LLM_URL": "http://proxy.local/v1",
               "MINEOS_LLM_MODEL": "mine", "MINEOS_API_KEY": "mine-key",
               "ANTHROPIC_API_KEY": "other"}
        llm = load_config(files=(), environ=env).llm
        self.assertEqual((llm.base_url, llm.model, llm.api_key),
                         ("http://proxy.local/v1", "mine", "mine-key"))

    def test_flag_outranks_environment_provider(self):
        config = load_config(files=(), environ={"MINEOS_PROVIDER": "groq"}, provider="anthropic")
        self.assertEqual(config.llm.provider, "anthropic")
        self.assertEqual(config.llm.base_url, "https://api.anthropic.com/v1")

    def test_default_is_local_and_unchanged(self):
        llm = load_config(files=(), environ={"ANTHROPIC_API_KEY": "ignored"}).llm
        self.assertEqual((llm.provider, llm.base_url, llm.context, llm.api_key),
                         ("local", "http://127.0.0.1:8080/v1", 4096, None))

    def test_unknown_provider_warns_and_stays_local(self):
        config = load_config(files=(), environ={"MINEOS_PROVIDER": "anthropik"})
        self.assertEqual(config.llm.provider, "local")
        self.assertIn("unknown provider", config.warnings[0])

    def test_hosted_provider_without_model_is_told_so(self):
        llm = LLMConfig(provider="groq", api_key="k")
        apply_provider(llm, {})
        self.assertIn("--model", describe(llm))
        with self.assertRaisesRegex(LLMError, "needs a model name"):
            build_model(llm).complete(system="s", user="u")

    def test_describe_never_prints_the_key(self):
        llm = LLMConfig(provider="anthropic", api_key="sk-secret-123")
        apply_provider(llm, {})
        self.assertNotIn("sk-secret", describe(llm))


if __name__ == "__main__":
    unittest.main()
