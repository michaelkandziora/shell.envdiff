import unittest
import os
import tempfile
import json
import subprocess
import sys

from envdiff import (ComparisonError, ComparisonResult, Difference, TargetResult,
                     compare_files, compare_mappings, result_document)


class PublicResultTests(unittest.TestCase):
    def test_public_file_api_returns_result_for_layered_sources(self):
        directory = tempfile.mkdtemp()
        try:
            paths = [os.path.join(directory, name) for name in ("reference", "base", "target")]
            for path, text in zip(paths, ("A=one\n", "B=base\n", "A=two\n")):
                with open(path, "w") as stream:
                    stream.write(text)
            result = compare_files(paths[0], [paths[2]], [paths[1]])
            self.assertIsInstance(result, ComparisonResult)
            self.assertEqual(result.targets[0].difference, Difference((), ("B",), ("A",)))
        finally:
            for path in paths:
                os.unlink(path)
            os.rmdir(directory)

    def test_public_file_api_returns_detail_free_input_error(self):
        result = compare_files("private-missing.env", ["private-target.env"])
        self.assertEqual(result, ComparisonError("input"))
        self.assertNotIn("private", repr(result))

    def test_public_file_api_matches_cli_json_for_layered_result(self):
        directory = tempfile.mkdtemp()
        try:
            paths = [os.path.join(directory, name) for name in ("reference", "base", "target")]
            for path, text in zip(paths, ("A=one\n", "B=base\n", "A=two\n")):
                with open(path, "w") as stream:
                    stream.write(text)
            result = compare_files(paths[0], [paths[2]], [paths[1]])
            command = subprocess.run([sys.executable, "-m", "envdiff", "--json", "--base",
                                      paths[1], paths[0], paths[2]], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, universal_newlines=True)
            document = json.loads(command.stdout)
            self.assertEqual(document["targets"][0]["changed"],
                             list(result.targets[0].difference.changed))
            self.assertEqual(document["targets"][0]["extra"],
                             list(result.targets[0].difference.extra))
        finally:
            for path in paths:
                os.unlink(path)
            os.rmdir(directory)
    def test_public_error_contract_does_not_retain_sensitive_detail(self):
        error = ComparisonError("input")
        self.assertEqual(error.kind, "input")
        self.assertNotIn("secret", repr(error))
        with self.assertRaises(AttributeError):
            error.kind = "other"

    def test_public_mapping_api_normalizes_malformed_input_to_detail_free_error(self):
        result = compare_mappings(None, [{"PRIVATE": "secret"}])
        self.assertEqual(result, ComparisonError("input"))
        self.assertNotIn("PRIVATE", repr(result))
        self.assertNotIn("secret", repr(result))
    def test_public_api_compares_one_mapping_target(self):
        result = compare_mappings({"A": "one", "B": "one"}, [{"A": "two", "C": "two"}])
        self.assertEqual(result.targets[0].difference,
                         Difference(("B",), ("C",), ("A",)))

    def test_public_api_preserves_multi_target_ordinals(self):
        result = compare_mappings({"A": "one"}, [{"A": "two"}, {"A": "one"}])
        self.assertEqual([item.target for item in result.targets], [1, 2])
        self.assertEqual(result.targets[1].difference, Difference())

    def test_public_api_retains_layer_source_metadata(self):
        result = compare_mappings({"A": "one"}, [{"A": "two"}], [{"B": "base"}])
        self.assertEqual(result.targets[0].sources,
                         (("B", "BASE", 1), ("A", "TARGET", 1)))

    def test_public_api_applies_filters_and_keys_only_like_cli(self):
        result = compare_mappings({"A": "one", "B": "one"}, [{"A": "two", "C": "two"}],
                                  includes=("A", "C"), keys_only=True)
        self.assertEqual(result.targets[0].difference, Difference((), ("C",), ()))

    def test_public_result_document_matches_versioned_cli_shape(self):
        result = compare_mappings({"A": "one"}, [{"A": "two"}])
        self.assertEqual(result_document(result), {"schema_version": 1,
                         "targets": [{"target": 1, "missing": [], "extra": [],
                                      "changed": ["A"]}]})
    def test_public_result_is_deeply_immutable(self):
        difference = Difference(("MISSING",), ("EXTRA",), ("CHANGED",))
        result = ComparisonResult((TargetResult(1, difference, ()),))
        self.assertEqual(result.targets[0].difference.changed, ("CHANGED",))
        with self.assertRaises(AttributeError):
            result.targets = ()
        with self.assertRaises(AttributeError):
            result.targets[0].difference.changed = ()

    def test_public_result_types_reject_mutable_nested_contract_values(self):
        with self.assertRaises(ValueError):
            Difference((["mutable"],), (), ())
        with self.assertRaises(ValueError):
            TargetResult([], Difference())

    def test_public_result_representation_contains_only_contract_metadata(self):
        result = ComparisonResult((TargetResult(1, Difference((), (), ("PORT",)), ()),))
        self.assertIn("PORT", repr(result))
        self.assertNotIn("secret", repr(result))
