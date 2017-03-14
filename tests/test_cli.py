import os
import subprocess
import sys
import tempfile
import unittest


class CommandTests(unittest.TestCase):
    def run_files(self, left, right):
        directory = tempfile.mkdtemp()
        try:
            first = os.path.join(directory, "first.env")
            second = os.path.join(directory, "second.env")
            with open(first, "w") as stream:
                stream.write(left)
            with open(second, "w") as stream:
                stream.write(right)
            return subprocess.run([sys.executable, "-m", "envdiff", first, second],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  universal_newlines=True)
        finally:
            for filename in ("first.env", "second.env"):
                path = os.path.join(directory, filename)
                if os.path.exists(path):
                    os.unlink(path)
            os.rmdir(directory)

    def test_difference_returns_one(self):
        result = self.run_files("A=secret", "A=new")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "CHANGED A\n")
        self.assertNotIn("secret", result.stdout + result.stderr)

    def test_invalid_input_returns_two(self):
        result = self.run_files("A", "A=value")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
