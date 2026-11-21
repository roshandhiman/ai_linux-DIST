import json
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from mineos_agent.os_api import ApiError
from mino.agent import Mino, Tool, direct
from mino.config import Settings
from mino.desk import SOURAV_CHANNEL, SOURAV_FEED, Desktop
from mino.voice import Recognizer


class MinoTest(unittest.TestCase):
    def test_stalled_speech_is_killed_and_reaped(self):
        child = Mock()
        child.communicate.side_effect = [subprocess.TimeoutExpired("recognizer", 12), (b"", b"")]
        recognizer = Recognizer(Settings())
        with patch("mino.voice.subprocess.Popen", return_value=child), self.assertRaises(RuntimeError):
            recognizer.transcribe(b"\0" * 640)
        child.kill.assert_called_once()
        self.assertEqual(child.communicate.call_count, 2)
        self.assertIsNone(recognizer.process)

    def test_cancelled_model_reply_never_executes_tools(self):
        agent = Mino(self.desk, self.settings)
        with patch.object(Mino, "plan", return_value=("create_file", {"path": "late.txt"})):
            reply, tool = agent.respond("a new document please", cancelled=lambda: True)
        self.assertEqual(reply, "Stopped.")
        self.assertFalse((self.docs / "late.txt").exists())

    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.home = Path(work.name).resolve()
        self.docs = self.home / "Documents"
        self.docs.mkdir()
        self.settings = Settings(wake_word=False)
        self.approve = Mock(return_value=False)
        self.desk = Desktop(self.home, self.settings, self.approve, allow_launch=False)

    def test_common_requests_skip_the_model(self):
        self.assertEqual(direct("Mino, open V S Code."), ("open_app", {"name": "VS Code"}))
        self.assertEqual(direct("Now open VS Code"), ("open_app", {"name": "VS Code"}))
        self.assertEqual(direct("create a file notes dot txt and write hello."),
                         ("create_file", {"path": "notes.txt", "text": "hello"}))
        self.assertEqual(direct("open https://example.com"), ("open_url", {"url": "https://example.com"}))
        self.assertEqual(direct("isko samjhao"), ("read_screen", {}))
        self.assertEqual(direct("Mino, meri screen-deko aur ise samjau."), ("read_screen", {}))
        self.assertEqual(direct("ab isse close kar do"), ("close_app", {}))

    def test_arguments_are_explicit_and_typed(self):
        tool = Tool(lambda *, path: path, {"path": str}, {}, "Open.")
        self.assertEqual(tool({"path": "notes.txt"}), "notes.txt")
        for args in ({}, {"path": True}, {"path": "notes.txt", "text": "excess"}, {"path": "a\0b"}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                tool(args)

    def test_model_uses_the_tool_schema_and_excludes_terminal(self):
        agent = Mino(self.desk, self.settings)
        with patch.object(type(agent.local_model), "request_completion",
                          return_value={"choices": [{"message": {"content":
                                        '{"tool":"open_app","args":{"name":"Firefox"}}'}}]}) as request:
            self.assertEqual(agent.plan("Start Firefox when you can."), ("open_app", {"name": "Firefox"}))
        forms = request.call_args.args[0]["response_format"]["schema"]["anyOf"]
        tools = {form["properties"]["tool"]["const"]: form for form in forms if "tool" in form["properties"]}
        self.assertNotIn("terminal", tools)
        self.assertEqual(tools["open_app"]["properties"]["args"]["required"], ["name"])

    def test_create_and_overwrite_approval(self):
        app = Mino(self.desk, self.settings)
        reply, name = app.respond("create a file notes.txt and write hello")
        self.assertEqual(name, "create_file")
        self.assertIn("Created", reply)
        file = self.docs / "notes.txt"
        self.assertEqual(file.read_text(), "hello")
        with self.assertRaises(FileExistsError):
            self.desk.create("notes.txt", "replacement")
        with self.assertRaises(ApiError):
            self.desk.write("notes.txt", "replacement")
        with self.assertRaises(ApiError):
            self.desk.remove("notes.txt")
        self.assertEqual(file.read_text(), "hello")
        self.assertEqual(self.approve.call_count, 2)
        self.approve.return_value = True
        self.desk.write("notes.txt", "replacement")
        self.assertEqual(file.read_text(), "replacement")

    def test_home_scope_and_move(self):
        self.desk.create("notes.txt", "hello")
        self.desk.move("notes.txt", "renamed.txt")
        self.assertFalse((self.docs / "notes.txt").exists())
        self.assertEqual((self.docs / "renamed.txt").read_text(), "hello")
        with self.assertRaises(ApiError):
            self.desk.create(str(self.home.parent / "escaped.txt"), "no")

    def test_screen_explain_uses_evidence_then_opens_reference(self):
        order = []
        with patch.object(Desktop, "read_screen", return_value="ModuleNotFoundError: No module named 'pandas'"), \
                patch.object(Desktop, "url", side_effect=lambda url: order.append(url)):
            reply, name = Mino(self.desk, self.settings).respond(
                "read my screen and explain this error", speak=order.append)
        self.assertEqual(name, "read_screen")
        self.assertIn("cannot find a module", reply)
        self.assertEqual(order[0], reply)
        self.assertIn("docs.python.org", order[1])

    def test_screen_speech_starts_before_last_token(self):
        app = Mino(self.desk, self.settings)
        spoken = []

        def tokens(**kwargs):
            yield "First sentence. "
            self.assertEqual(spoken, ["First sentence."])
            yield "Second sentence."

        app.local_model = Mock()
        app.local_model.stream.side_effect = tokens
        reply, _ = app.explain("A visible message", "samjhao", spoken.append)
        self.assertEqual(reply, "First sentence. Second sentence.")
        self.assertEqual(spoken, ["First sentence.", "Second sentence."])

    def test_media_selects_the_latest_available_upload(self):
        entries = {"entries": [{"id": "abcdefghijk", "live_status": "is_upcoming"},
                               {"id": "01234567890", "title": "New vlog"},
                               {"id": "zyxwvutsrqp", "title": "Old vlog"}]}
        with patch("mino.desk.accomplish", side_effect=[ApiError("Unavailable"), json.dumps(entries).encode()]) as lookup, \
                patch.object(Desktop, "url") as opened:
            self.assertEqual(self.desk.media("Sourav Joshi latest vlog"), "Opening New vlog.")
        self.assertEqual(lookup.call_args.args[0][-1], SOURAV_CHANNEL + "/videos")
        opened.assert_called_once_with("https://www.youtube.com/watch?v=01234567890")

    def test_sourav_feed_supplies_latest_video_without_yt_dlp(self):
        feed = """<feed xmlns="http://www.w3.org/2005/Atom"
                   xmlns:yt="http://www.youtube.com/xml/schemas/2015">
                   <entry><yt:videoId>abcdefghijk</yt:videoId><title>Old vlog</title>
                     <published>2026-11-20T10:00:00Z</published></entry>
                   <entry><yt:videoId>01234567890</yt:videoId><title>New vlog</title>
                     <published>2026-11-21T10:00:00Z</published></entry>
                   </feed>"""
        with patch("mino.desk.accomplish", return_value=feed.encode()) as fetch, \
                patch.object(Desktop, "url") as opened:
            self.assertEqual(self.desk.media("Sourav Joshi latest vlog"), "Opening New vlog.")
        self.assertEqual(fetch.call_args.args[0][-1], SOURAV_FEED)
        opened.assert_called_once_with("https://www.youtube.com/watch?v=01234567890")

    def test_hinglish_screen_explanation_uses_hindi_speech(self):
        with patch.object(Desktop, "read_screen", return_value="Permission denied"):
            reply, name = Mino(self.desk, self.settings).respond("isko samjhao")
        self.assertEqual(name, "read_screen")
        self.assertIn("अनुमति", reply)

    def test_app_launch_and_close_followup(self):
        with patch.object(Desktop, "_desktop_entries",
                          return_value=[("MineOS IDE", "org.mineos.IDE", ["mineos-ide"])]):
            self.assertEqual(self.desk.app("VS Code"), "Opening MineOS IDE.")
        with patch("mino.desk.accomplish", side_effect=[b"0x0012 0 mineos-ide.code localhost IDE", b""]) as call:
            self.desk.close()
            call.assert_called_with(["wmctrl", "-ic", "0x0012"], 1)


if __name__ == "__main__":
    unittest.main()
