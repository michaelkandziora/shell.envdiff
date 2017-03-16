import unittest

from envdiff.core import compare, compare_targets, parse


class ParseTests(unittest.TestCase):
    def test_assignment(self):
        self.assertEqual(parse("A=one\n"), {"A": "one"})

    def test_value_can_contain_assignment_marker(self):
        self.assertEqual(parse("URL=a=b=c"), {"URL": "a=b=c"})

    def test_final_line_need_not_end_in_newline(self):
        self.assertEqual(parse("A=one"), {"A": "one"})

    def test_empty_input(self):
        self.assertEqual(parse("\n\n"), {})

    def test_assignment_requires_separator(self):
        with self.assertRaises(ValueError):
            parse("A")

    def test_duplicate_names_are_rejected(self):
        with self.assertRaises(ValueError):
            parse("A=one\nA=two\n")

    def test_names_follow_environment_convention(self):
        self.assertEqual(parse("_A=1\nA2=2\n"), {"_A": "1", "A2": "2"})
        for line in ("1A=x", "A-B=x", "A B=x", "A\tB=x", "Ä=x"):
            with self.subTest(line=line):
                with self.assertRaises(ValueError):
                    parse(line)


class CompareTests(unittest.TestCase):
    def test_changed_name_has_no_value(self):
        self.assertEqual(compare({"A": "one"}, {"A": "two"})["changed"], ["A"])

    def test_missing_and_extra_are_sorted(self):
        report = compare({"B": "1", "A": "1"}, {"B": "1", "C": "1"})
        self.assertEqual(report["missing"], ["A"])
        self.assertEqual(report["extra"], ["C"])

    def test_empty_mappings_have_no_differences(self):
        self.assertEqual(compare({}, {}), {"missing": [], "extra": [], "changed": []})

    def test_multiple_targets_keep_argument_ordinals(self):
        reports = compare_targets({"A": "1"}, [{"A": "1"}, {"A": "2"}])
        self.assertEqual([item["target"] for item in reports], [1, 2])
        self.assertEqual(reports[0]["report"]["changed"], [])
        self.assertEqual(reports[1]["report"]["changed"], ["A"])

    def test_repeated_target_mapping_is_a_separate_comparison(self):
        reports = compare_targets({"A": "1"}, [{"A": "2"}, {"A": "2"}])
        self.assertEqual([item["target"] for item in reports], [1, 2])
        self.assertEqual([item["report"]["changed"] for item in reports], [["A"], ["A"]])
