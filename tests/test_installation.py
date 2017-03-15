import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class InstallationTests(unittest.TestCase):
    def test_built_wheel_provides_console_command(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temporary = tempfile.mkdtemp()
        try:
            wheel_directory = os.path.join(temporary, "wheel")
            target = os.path.join(temporary, "site")
            subprocess.check_call([sys.executable, "setup.py", "bdist_wheel",
                                   "--dist-dir", wheel_directory], cwd=root)
            wheel = os.path.join(wheel_directory, os.listdir(wheel_directory)[0])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-deps",
                                   "--target", target, wheel])
            result = subprocess.run([sys.executable, "-m", "envdiff", "--help"],
                                    env=dict(os.environ, PYTHONPATH=target),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("usage:", result.stdout)
        finally:
            shutil.rmtree(temporary)
