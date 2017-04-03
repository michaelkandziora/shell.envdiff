import os
import subprocess
import sys
import tempfile
import unittest

from envdiff.cli import _read_inputs, _read_layered_inputs, _report_lines


class CommandTests(unittest.TestCase):
    def test_base_is_applied_before_target_without_changing_reference(self):
        directory = tempfile.mkdtemp()
        try:
            reference = os.path.join(directory, "reference.env")
            base = os.path.join(directory, "base.env")
            target = os.path.join(directory, "target.env")
            for path, contents in ((reference, "A=reference\nB=one\n"),
                                   (base, "B=base\nC=base\n"),
                                   (target, "A=target\n")):
                with open(path, "w") as stream:
                    stream.write(contents)
            result = subprocess.run([sys.executable, "-m", "envdiff", "--base", base,
                                     reference, target], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "EXTRA C SOURCE BASE 1\n"
                         "CHANGED A SOURCE TARGET 1\nCHANGED B SOURCE BASE 1\n")
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_no_base_retains_original_key_only_report(self):
        result = self.run_files("A=one\n", "A=two\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "CHANGED A\n")
        self.assertNotIn("SOURCE", result.stdout)

    def test_layered_multiple_targets_retain_target_ordinals(self):
        directory = tempfile.mkdtemp()
        try:
            paths = [os.path.join(directory, "source-{0}.env".format(number))
                     for number in range(4)]
            for path, contents in zip(paths, ("A=one\n", "B=base\n", "A=two\n", "A=one\n")):
                with open(path, "w") as stream:
                    stream.write(contents)
            result = subprocess.run([sys.executable, "-m", "envdiff", "--base", paths[1],
                                     paths[0], paths[2], paths[3]], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "TARGET 1\nEXTRA B SOURCE BASE 1\n"
                             "CHANGED A SOURCE TARGET 1\nTARGET 2\nEXTRA B SOURCE BASE 1\n")
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_invalid_later_base_suppresses_all_target_reports(self):
        directory = tempfile.mkdtemp()
        try:
            reference = os.path.join(directory, "reference.env")
            good_base = os.path.join(directory, "base-one.env")
            bad_base = os.path.join(directory, "secret-base.env")
            target = os.path.join(directory, "target.env")
            for path, contents in ((reference, "A=one\n"), (good_base, "B=two\n"),
                                   (bad_base, "INVALID"), (target, "A=two\n")):
                with open(path, "w") as stream:
                    stream.write(contents)
            result = subprocess.run([sys.executable, "-m", "envdiff", "--base", good_base,
                                     "--base", bad_base, reference, target],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("secret-base.env", result.stderr)
            self.assertNotIn("A=two", result.stderr)
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_duplicate_name_in_one_base_is_an_input_error(self):
        directory = tempfile.mkdtemp()
        try:
            reference = os.path.join(directory, "reference.env")
            base = os.path.join(directory, "base.env")
            target = os.path.join(directory, "target.env")
            for path, contents in ((reference, "A=one\n"),
                                   (base, "B=one\nB=two\n"), (target, "A=one\n")):
                with open(path, "w") as stream:
                    stream.write(contents)
            result = subprocess.run([sys.executable, "-m", "envdiff", "--base", base,
                                     reference, target], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("B=", result.stderr)
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_base_parse_diagnostic_does_not_reflect_assignment_value(self):
        directory = tempfile.mkdtemp()
        try:
            reference = os.path.join(directory, "reference.env")
            base = os.path.join(directory, "base.env")
            target = os.path.join(directory, "target.env")
            for path, contents in ((reference, "A=one\n"),
                                   (base, "BROKEN=confidential\nBROKEN=hidden\n"),
                                   (target, "A=one\n")):
                with open(path, "w") as stream:
                    stream.write(contents)
            result = subprocess.run([sys.executable, "-m", "envdiff", "--base", base,
                                     reference, target], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("confidential", result.stderr)
            self.assertNotIn("hidden", result.stderr)
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_later_base_overrides_earlier_base_with_its_own_ordinal(self):
        directory = tempfile.mkdtemp()
        try:
            names = ("reference.env", "base-one.env", "base-two.env", "target.env")
            paths = [os.path.join(directory, name) for name in names]
            for path, contents in zip(paths, ("A=reference\n", "A=one\n", "A=two\n", "")):
                with open(path, "w") as stream:
                    stream.write(contents)
            result = subprocess.run([sys.executable, "-m", "envdiff", "--base", paths[1],
                                     "--base", paths[2], paths[0], paths[3]],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "CHANGED A SOURCE BASE 2\n")
            self.assertNotIn("base-two.env", result.stdout + result.stderr)
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_layered_missing_key_identifies_only_reference_role(self):
        directory = tempfile.mkdtemp()
        try:
            reference = os.path.join(directory, "reference.env")
            target = os.path.join(directory, "target.env")
            for path, contents in ((reference, "A=one\n"), (target, "")):
                with open(path, "w") as stream:
                    stream.write(contents)
            result = subprocess.run([sys.executable, "-m", "envdiff", "--base", target,
                                     reference, target], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "MISSING A SOURCE REFERENCE 1\n")
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_repeated_base_path_is_applied_at_each_base_ordinal(self):
        directory = tempfile.mkdtemp()
        try:
            reference = os.path.join(directory, "reference.env")
            base = os.path.join(directory, "base.env")
            target = os.path.join(directory, "target.env")
            for path, contents in ((reference, "A=reference\n"), (base, "A=base\n"),
                                   (target, "")):
                with open(path, "w") as stream:
                    stream.write(contents)
            result = subprocess.run([sys.executable, "-m", "envdiff", "--base", base,
                                     "--base", base, reference, target],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "CHANGED A SOURCE BASE 2\n")
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

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

    def run_many(self, reference, *targets):
        directory = tempfile.mkdtemp()
        try:
            paths = []
            for ordinal, contents in enumerate((reference,) + targets):
                path = os.path.join(directory, "input-{0}.env".format(ordinal))
                with open(path, "w") as stream:
                    stream.write(contents)
                paths.append(path)
            return subprocess.run([sys.executable, "-m", "envdiff"] + paths,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  universal_newlines=True)
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
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

    def test_invalid_name_is_not_reflected_in_error_output(self):
        result = self.run_files("BAD NAME=private", "A=value")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("BAD NAME", result.stderr)
        self.assertNotIn("private", result.stderr)

    def test_all_categories_use_a_stable_order(self):
        result = self.run_files("Z=1\nA=1\nB=old", "Z=1\nC=1\nB=new")
        self.assertEqual(result.stdout, "MISSING A\nEXTRA C\nCHANGED B\n")

    def test_multiple_targets_are_reported_by_ordinal(self):
        result = self.run_many("A=one", "A=one", "A=two")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "TARGET 1\nTARGET 2\nCHANGED A\n")
        self.assertNotIn("input-", result.stdout + result.stderr)

    def test_all_matching_multiple_targets_return_zero(self):
        result = self.run_many("A=one", "A=one", "A=one", "A=one")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "TARGET 1\nTARGET 2\nTARGET 3\n")

    def test_three_targets_preserve_argument_order(self):
        result = self.run_many("A=one", "A=two", "A=one", "A=three")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout,
                         "TARGET 1\nCHANGED A\nTARGET 2\nTARGET 3\nCHANGED A\n")

    def test_input_error_suppresses_earlier_target_report(self):
        directory = tempfile.mkdtemp()
        try:
            reference = os.path.join(directory, "reference.env")
            good = os.path.join(directory, "good.env")
            bad = os.path.join(directory, "secret-target.env")
            with open(reference, "w") as stream:
                stream.write("A=one")
            with open(good, "w") as stream:
                stream.write("A=two")
            with open(bad, "w") as stream:
                stream.write("NOT AN ASSIGNMENT")
            result = subprocess.run([sys.executable, "-m", "envdiff", reference, good, bad],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("secret-target.env", result.stderr)
            self.assertNotIn("TARGET", result.stderr)
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_missing_later_target_suppresses_earlier_target_report(self):
        directory = tempfile.mkdtemp()
        try:
            reference = os.path.join(directory, "reference.env")
            good = os.path.join(directory, "good.env")
            missing = os.path.join(directory, "private-missing.env")
            with open(reference, "w") as stream:
                stream.write("A=one")
            with open(good, "w") as stream:
                stream.write("A=two")
            result = subprocess.run([sys.executable, "-m", "envdiff", reference, good, missing],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("private-missing.env", result.stderr)
            self.assertNotIn("A=two", result.stderr)
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_invalid_reference_suppresses_every_target_report(self):
        directory = tempfile.mkdtemp()
        try:
            reference = os.path.join(directory, "private-reference.env")
            target = os.path.join(directory, "target.env")
            with open(reference, "w") as stream:
                stream.write("NOT AN ASSIGNMENT")
            with open(target, "w") as stream:
                stream.write("A=value")
            result = subprocess.run([sys.executable, "-m", "envdiff", reference, target, target],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("private-reference.env", result.stderr)
            self.assertNotIn("TARGET", result.stderr)
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_repeated_target_path_has_two_ordinals(self):
        directory = tempfile.mkdtemp()
        try:
            reference = os.path.join(directory, "reference.env")
            target = os.path.join(directory, "target.env")
            with open(reference, "w") as stream:
                stream.write("A=one")
            with open(target, "w") as stream:
                stream.write("A=two")
            result = subprocess.run([sys.executable, "-m", "envdiff", reference, target, target],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "TARGET 1\nCHANGED A\nTARGET 2\nCHANGED A\n")
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_target_is_a_required_positional_argument(self):
        result = subprocess.run([sys.executable, "-m", "envdiff", "reference.env"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "envdiff: target input required\n")

    def test_unknown_argument_is_not_reflected_in_diagnostic(self):
        supplied = "--private-path=/srv/secret.env"
        result = subprocess.run([sys.executable, "-m", "envdiff", "reference.env",
                                 "target.env", supplied],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "envdiff: invalid command arguments\n")
        self.assertNotIn(supplied, result.stderr)

    def test_documented_multi_target_example(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run([sys.executable, "-m", "envdiff",
                                 os.path.join(root, "examples", "reference.env"),
                                 os.path.join(root, "examples", "target.env"),
                                 os.path.join(root, "examples", "target-two.env")],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout,
                         "TARGET 1\nMISSING REQUIRED\nEXTRA EXTRA\nCHANGED PORT\nTARGET 2\n")
        self.assertEqual(result.stderr, "")

    def test_documented_base_example_runs_without_leaking_example_path(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run([sys.executable, "-m", "envdiff", "--base",
                                 os.path.join(root, "examples", "base.env"),
                                 os.path.join(root, "examples", "reference.env"),
                                 os.path.join(root, "examples", "target.env")],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("SOURCE BASE 1", result.stdout)
        self.assertNotIn("base.env", result.stdout + result.stderr)

    def test_empty_target_contents_are_valid_multi_target_input(self):
        result = self.run_many("A=one", "", "A=one")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "TARGET 1\nMISSING A\nTARGET 2\n")

    def test_empty_reference_contents_are_valid_multi_target_input(self):
        result = self.run_many("", "A=one", "")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "TARGET 1\nEXTRA A\nTARGET 2\n")

    def test_loader_returns_reference_separately_from_targets(self):
        directory = tempfile.mkdtemp()
        try:
            paths = []
            for ordinal, contents in enumerate(("A=reference", "A=one", "A=two")):
                path = os.path.join(directory, "source-{0}.env".format(ordinal))
                with open(path, "w") as stream:
                    stream.write(contents)
                paths.append(path)
            reference, targets = _read_inputs(paths[0], paths[1:])
            self.assertEqual(reference, {"A": "reference"})
            self.assertEqual(targets, [{"A": "one"}, {"A": "two"}])
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_layered_loader_keeps_reference_and_bases_separate(self):
        directory = tempfile.mkdtemp()
        try:
            paths = []
            for ordinal, contents in enumerate(("A=reference", "A=base", "A=target")):
                path = os.path.join(directory, "layer-{0}.env".format(ordinal))
                with open(path, "w") as stream:
                    stream.write(contents)
                paths.append(path)
            reference, bases, targets = _read_layered_inputs(paths[0], [paths[1]], [paths[2]])
            self.assertEqual(reference, {"A": "reference"})
            self.assertEqual(bases, [{"A": "base"}])
            self.assertEqual(targets, [{"A": "target"}])
        finally:
            for name in os.listdir(directory):
                os.unlink(os.path.join(directory, name))
            os.rmdir(directory)

    def test_renderer_keeps_only_ordinal_and_keys(self):
        reports = [{"target": 2, "report": {"missing": ["B"], "extra": [], "changed": ["A"]}}]
        self.assertEqual(_report_lines(reports), ["MISSING B", "CHANGED A"])
        reports.append({"target": 3, "report": {"missing": [], "extra": ["C"], "changed": []}})
        self.assertEqual(_report_lines(reports),
                         ["TARGET 2", "MISSING B", "CHANGED A", "TARGET 3", "EXTRA C"])

    def test_equal_files_return_silently(self):
        result = self.run_files("A=value\n", "A=value\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_missing_file_does_not_echo_path(self):
        result = subprocess.run([sys.executable, "-m", "envdiff", "missing-secret.env", "other.env"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("missing-secret.env", result.stderr)

    def test_help_describes_file_pair(self):
        result = subprocess.run([sys.executable, "-m", "envdiff", "--help"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("reference", result.stdout)
        self.assertIn("target", result.stdout)

    def test_help_describes_repeatable_base_option(self):
        result = subprocess.run([sys.executable, "-m", "envdiff", "--help"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("--base FILE", result.stdout)

    def test_version_is_available_without_files(self):
        result = subprocess.run([sys.executable, "-m", "envdiff", "--version"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "0.2.0")

    def test_invalid_utf8_is_a_controlled_error(self):
        directory = tempfile.mkdtemp()
        try:
            first = os.path.join(directory, "first.env")
            second = os.path.join(directory, "second.env")
            with open(first, "wb") as stream:
                stream.write(b"A=" + bytes(bytearray([255])))
            with open(second, "wb") as stream:
                stream.write(b"A=value")
            result = subprocess.run([sys.executable, "-m", "envdiff", first, second],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("A=", result.stderr)
        finally:
            for filename in ("first.env", "second.env"):
                path = os.path.join(directory, filename)
                if os.path.exists(path):
                    os.unlink(path)
            os.rmdir(directory)
