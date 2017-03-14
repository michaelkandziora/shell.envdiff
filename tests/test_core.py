import unittest

from envdiff.core import compare, parse


class ParseTests(unittest.TestCase):
    def test_assignment(self):
        self.assertEqual(parse("A=one\n"), {"A": "one"})


class CompareTests(unittest.TestCase):
    def test_changed_name_has_no_value(self):
        self.assertEqual(compare({"A": "one"}, {"A": "two"})["changed"], ["A"])
