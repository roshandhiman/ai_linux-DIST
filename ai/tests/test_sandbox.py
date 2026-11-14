import unittest

from mineos_agent.sandbox import Sandbox, validate


class ValidateTests(unittest.TestCase):
    def assertRefused(self, code: str, fragment: str = "") -> None:
        problem = validate(code)
        self.assertIsNotNone(problem, code)
        if fragment:
            self.assertIn(fragment, problem)

    def test_plain_code_is_allowed(self):
        self.assertIsNone(validate("import math\nprint(math.sqrt(16))"))
        self.assertIsNone(validate("from collections import Counter\nprint(Counter('aab'))"))
        self.assertIsNone(validate("for _ in range(2):\n    print(mine.now())"))

    def test_dangerous_imports_are_refused(self):
        self.assertRefused("import os", "mine")
        self.assertRefused("import subprocess")
        self.assertRefused("from os import system")
        self.assertRefused("from . import x")
        self.assertRefused("import math as m, socket")

    def test_classic_escapes_are_refused(self):
        self.assertRefused("().__class__.__bases__[0].__subclasses__()")
        self.assertRefused("print(open('/etc/passwd').read())")
        self.assertRefused("eval('1+1')")
        self.assertRefused("getattr(mine, 'x')")
        self.assertRefused("__builtins__")
        self.assertRefused("'{0.__class__}'.format(1)", "f-string")
        self.assertRefused("g = (x for x in [1])\nprint(g.gi_frame)")
        self.assertRefused("match 1:\n    case int(__class__=c):\n        pass")
        self.assertRefused("type(1)")

    def test_syntax_error_names_the_line(self):
        self.assertIn("line 2", validate("x = 1\nprint(x"))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = Sandbox(timeout=15, use_bwrap=False)
        self.calls = []

    def dispatch(self, name, args, kwargs):
        self.calls.append((name, args, kwargs))
        if name == "fail":
            return False, "no such thing; try another"
        return True, {"echo": args}

    def run_code(self, code, fns=("echo", "fail")):
        return self.sandbox.run(code, list(fns), self.dispatch)

    def test_print_is_captured(self):
        result = self.run_code("import math\nprint('root', math.sqrt(9))")
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.output.strip(), "root 3.0")

    def test_mine_calls_round_trip_through_the_parent(self):
        result = self.run_code("r = mine.echo(1, 2)\nprint(r['echo'])")
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.output.strip(), "[1, 2]")
        self.assertEqual(self.calls, [("echo", [1, 2], {})])
        self.assertEqual(result.calls, ["echo"])

    def test_refused_call_becomes_a_readable_error(self):
        result = self.run_code("print('before')\nmine.fail()")
        self.assertFalse(result.ok)
        self.assertIn("mine.fail: no such thing", result.error)
        self.assertIn("line 2", result.error)
        self.assertEqual(result.output.strip(), "before")

    def test_runtime_error_is_data(self):
        result = self.run_code("x = 1 / 0")
        self.assertFalse(result.ok)
        self.assertIn("ZeroDivisionError", result.error)

    def test_modules_are_filtered_views(self):
        # re.enum.sys would reach os through public names only.
        result = self.run_code("import re\nprint(re.enum)")
        self.assertFalse(result.ok)
        self.assertIn("AttributeError", result.error)

    def test_no_open_even_without_the_static_check(self):
        result = self.run_code("f = [o for o in [1]]\nprint(len(f))")
        self.assertTrue(result.ok)

    def test_infinite_loop_is_stopped(self):
        sandbox = Sandbox(timeout=2, use_bwrap=False)
        result = sandbox.run("while True:\n    pass", [], self.dispatch)
        self.assertFalse(result.ok)
        self.assertIn("longer than", result.error)

    def test_output_is_bounded(self):
        result = self.run_code("for i in range(100000):\n    print('spam spam spam')")
        self.assertTrue(result.ok)
        self.assertLess(len(result.output), 4200)
        self.assertIn("output cut", result.output)

    def test_unknown_mine_function_is_not_exposed(self):
        result = self.run_code("mine.shutdown()")
        self.assertFalse(result.ok)
        self.assertIn("AttributeError", result.error)


if __name__ == "__main__":
    unittest.main()
