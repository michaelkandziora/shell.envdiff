import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class InstallationTests(unittest.TestCase):
    def test_source_distribution_installs_console_command(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temporary = tempfile.mkdtemp()
        try:
            subprocess.check_call([sys.executable, "setup.py", "sdist",
                                   "--dist-dir", temporary], cwd=root)
            archive = os.path.join(temporary, os.listdir(temporary)[0])
            prefix = os.path.join(temporary, "prefix")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-deps",
                                   "--prefix", prefix, archive],
                                  env=dict(os.environ, PYTHONPATH=""))
            site = next(directory for directory, _, _ in os.walk(prefix)
                        if directory.endswith("site-packages"))
            script = os.path.join(prefix, "bin", "envdiff")
            result = subprocess.run([script, "--version"],
                                    env=dict(os.environ, PYTHONPATH=site),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "0.3.0")
        finally:
            shutil.rmtree(temporary)

    def test_built_wheel_console_command_accepts_base_option(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temporary = tempfile.mkdtemp()
        try:
            wheel_directory = os.path.join(temporary, "wheel")
            prefix = os.path.join(temporary, "prefix")
            subprocess.check_call([sys.executable, "setup.py", "bdist_wheel",
                                   "--dist-dir", wheel_directory], cwd=root)
            wheel = os.path.join(wheel_directory, os.listdir(wheel_directory)[0])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-deps",
                                   "--prefix", prefix, wheel], env=dict(os.environ, PYTHONPATH=""))
            base = os.path.join(temporary, "base.env")
            reference = os.path.join(temporary, "reference.env")
            target = os.path.join(temporary, "target.env")
            for path, contents in ((base, "A=base\n"), (reference, "A=reference\n"),
                                   (target, "")):
                with open(path, "w") as stream:
                    stream.write(contents)
            script = os.path.join(prefix, "bin", "envdiff")
            site = next(directory for directory, _, _ in os.walk(prefix)
                        if directory.endswith("site-packages"))
            result = subprocess.run([script, "--base", base, reference, target],
                                    env=dict(os.environ, PYTHONPATH=site), stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "CHANGED A SOURCE BASE 1\n")
        finally:
            shutil.rmtree(temporary)

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
            self.assertTrue(any(name.endswith("examples/base.env") for name in names))
            self.assertTrue(any(name.endswith("examples/quoted.env") for name in names))
            self.assertTrue(any(name.endswith("examples/quoted-reference.env") for name in names))
            self.assertTrue(any(name.endswith("examples/quoted-target.env") for name in names))
            self.assertTrue(any(name.endswith("examples/target-two.env") for name in names))
            self.assertTrue(any(name.endswith("tests/test_core.py") for name in names))
        finally:
            shutil.rmtree(temporary)

    def test_fresh_source_archive_runs_documented_test_command(self):
        if os.environ.get("ENVDIFF_ARCHIVE_SMOKE"):
            self.skipTest("avoid recursively archiving the archive smoke")
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temporary = tempfile.mkdtemp()
        try:
            subprocess.check_call([sys.executable, "setup.py", "sdist",
                                   "--dist-dir", temporary], cwd=root)
            archive = os.path.join(temporary, os.listdir(temporary)[0])
            import tarfile
            with tarfile.open(archive) as bundle:
                bundle.extractall(temporary)
            source = os.path.join(temporary, "envdiff-0.3.0")
            environment = dict(os.environ, PYTHONPATH=os.path.join(source, "src"),
                               ENVDIFF_ARCHIVE_SMOKE="1")
            result = subprocess.run([sys.executable, "-m", "unittest", "discover",
                                     "-s", "tests", "-v"], cwd=source, env=environment,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK", result.stderr)
        finally:
            shutil.rmtree(temporary)

    def test_package_metadata_identifies_project(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run([sys.executable, "setup.py", "--name", "--version"],
                                cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["envdiff", "0.3.0"])

    def test_package_declares_supported_python_baseline(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.check_call([sys.executable, "setup.py", "egg_info"], cwd=root)
        metadata = os.path.join(root, "src", "envdiff.egg-info", "PKG-INFO")
        with open(metadata, "r") as stream:
            contents = stream.read()
        self.assertIn("Requires-Python: >=3.6", contents)
