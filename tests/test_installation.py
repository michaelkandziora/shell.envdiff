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
            prefix = os.path.join(temporary, "prefix")
            subprocess.check_call([sys.executable, "setup.py", "bdist_wheel",
                                   "--dist-dir", wheel_directory], cwd=root)
            wheel = os.path.join(wheel_directory, os.listdir(wheel_directory)[0])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-deps",
                                   "--prefix", prefix, wheel],
                                  env=dict(os.environ, PYTHONPATH=""))
            site = None
            for base, directories, files in os.walk(prefix):
                if base.endswith("site-packages"):
                    site = base
            script = os.path.join(prefix, "bin", "envdiff")
            self.assertIsNotNone(site)
            self.assertTrue(os.path.isfile(script))
            result = subprocess.run([script, "--help"],
                                    env=dict(os.environ, PYTHONPATH=site),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("usage:", result.stdout)
        finally:
            shutil.rmtree(temporary)

    def test_source_distribution_contains_examples(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temporary = tempfile.mkdtemp()
        try:
            subprocess.check_call([sys.executable, "setup.py", "sdist",
                                   "--dist-dir", temporary], cwd=root)
            archive = os.path.join(temporary, os.listdir(temporary)[0])
            import tarfile
            with tarfile.open(archive) as bundle:
                names = bundle.getnames()
            self.assertTrue(any(name.endswith("examples/reference.env") for name in names))
            self.assertTrue(any(name.endswith("examples/target-two.env") for name in names))
            self.assertTrue(any(name.endswith("tests/test_core.py") for name in names))
        finally:
            shutil.rmtree(temporary)

    def test_package_metadata_identifies_project(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run([sys.executable, "setup.py", "--name", "--version"],
                                cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["envdiff", "0.1.0"])

    def test_package_declares_supported_python_baseline(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run([sys.executable, "setup.py", "--requires-python"],
                                cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), ">=3.6")
