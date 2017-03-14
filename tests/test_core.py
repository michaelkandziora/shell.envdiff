import unittest

from envdiff.core import compare, parse


class ParseTests(unittest.TestCase):
    def test_assignment(self):
        self.assertEqual(parse("A=one\n"), {"A": "one"})

    def test_empty_input(self):
        self.assertEqual(parse("\n\n"), {})

    def test_assignment_requires_separator(self):
        with self.assertRaises(ValueError):
            parse("A")

    def test_duplicate_names_are_rejected(self):
        with self.assertRaises(ValueError):
            parse("A=one\nA=two\n")


class CompareTests(unittest.TestCase):
    def test_changed_name_has_no_value(self):
        self.assertEqual(compare({"A": "one"}, {"A": "two"})["changed"], ["A"])

    def test_missing_and_extra_are_sorted(self):
        report = compare({"B": "1", "A": "1"}, {"B": "1", "C": "1"})
        self.assertEqual(report["missing"], ["A"])
        self.assertEqual(report["extra"], ["C"])
