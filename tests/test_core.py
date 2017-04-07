import unittest

from envdiff.core import (compare, compare_effective_targets, compare_targets, has_differences, merge_layers,
                          merge_layers_with_sources, parse)


class ParseTests(unittest.TestCase):
    def test_comment_only_lines_are_ignored(self):
        self.assertEqual(parse("# deployment settings\nA=one\n# end\n"),
                         {"A": "one"})

    def test_assignment_whitespace_is_not_part_of_name_or_value(self):
        self.assertEqual(parse("  A = one  \n"), {"A": "one"})

    def test_export_prefix_is_accepted(self):
        self.assertEqual(parse("export A=one\n"), {"A": "one"})

    def test_exported_name_still_participates_in_duplicate_detection(self):
        with self.assertRaises(ValueError):
            parse("export A=one\nA=two\n")

    def test_indented_comment_is_ignored(self):
        self.assertEqual(parse("  # note\nA=one\n"), {"A": "one"})

    def test_double_quoted_value_can_contain_spaces_and_markers(self):
        self.assertEqual(parse('A="one = # two"\n'), {"A": "one = # two"})

    def test_single_quoted_value_can_contain_comment_marker(self):
        self.assertEqual(parse("A='one # two'\n"), {"A": "one # two"})

    def test_unquoted_inline_comment_requires_a_whitespace_boundary(self):
        self.assertEqual(parse("A=one # note\nB=two#kept\n"),
                         {"A": "one", "B": "two#kept"})

    def test_known_escapes_are_decoded_inside_quotes(self):
        self.assertEqual(parse('A="one\\ntwo\\tend"\n'), {"A": "one\ntwo\tend"})

    def test_unknown_escape_is_preserved_inside_quotes(self):
        self.assertEqual(parse('A="one\\qtwo"\n'), {"A": "one\\qtwo"})

    def test_escaped_quote_does_not_close_quoted_value(self):
        self.assertEqual(parse('A="one \\" two"\n'), {"A": 'one " two'})

    def test_closed_quote_allows_only_a_comment_suffix(self):
        self.assertEqual(parse('A="one" # note\n'), {"A": "one"})

    def test_empty_quoted_value_is_distinct_valid_syntax(self):
        self.assertEqual(parse('A=""\nB=\'\'\n'), {"A": "", "B": ""})

    def test_escaped_backslash_is_decoded_inside_quotes(self):
        self.assertEqual(parse('A="one\\\\two"\n'), {"A": "one\\two"})

    def test_bom_is_removed_only_at_start_of_a_source(self):
        self.assertEqual(parse("A=one\nB=\ufefftwo\n"), {"A": "one", "B": "\ufefftwo"})

    def test_quoted_value_can_contain_assignment_markers(self):
        self.assertEqual(parse('A="left=right=final"\n'), {"A": "left=right=final"})

    def test_utf8_bom_and_crlf_are_normalized_before_assignments(self):
        self.assertEqual(parse("\ufeffA=one\r\nB=two\r\n"), {"A": "one", "B": "two"})

    def test_unterminated_quote_is_a_controlled_parse_error(self):
        with self.assertRaises(ValueError):
            parse('A="unfinished\n')

    def test_text_after_closed_quote_is_a_controlled_parse_error(self):
        with self.assertRaises(ValueError):
            parse('A="one" trailing\n')

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
    def test_later_layers_override_earlier_layers(self):
        self.assertEqual(merge_layers([{"A": "base", "B": "one"},
                                       {"A": "target", "C": "two"}]),
                         {"A": "target", "B": "one", "C": "two"})

    def test_empty_layer_does_not_change_effective_mapping(self):
        self.assertEqual(merge_layers([{"A": "one"}, {}]), {"A": "one"})

    def test_layer_merge_records_only_the_winning_source_metadata(self):
        values, sources = merge_layers_with_sources([
            ("BASE", 1, {"A": "base", "B": "one"}),
            ("TARGET", 1, {"A": "target"}),
        ])
        self.assertEqual(values, {"A": "target", "B": "one"})
        self.assertEqual(sources, {"A": ("TARGET", 1), "B": ("BASE", 1)})

    def test_changed_name_has_no_value(self):
        self.assertEqual(compare({"A": "one"}, {"A": "two"})["changed"], ["A"])

    def test_equivalent_escaped_and_literal_values_do_not_change_key(self):
        reference = parse('A="one\\ntwo"\n')
        target = {"A": "one\ntwo"}
        self.assertEqual(compare(reference, target)["changed"], [])

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

    def test_effective_targets_keep_reference_unchanged(self):
        reports = compare_effective_targets({"A": "reference"},
                                            [{"A": "base"}], [{"A": "target"}])
        self.assertEqual(reports[0]["report"]["changed"], ["A"])

    def test_effective_target_report_keeps_winning_source_per_target_key(self):
        reports = compare_effective_targets({"A": "one"}, [{"B": "base"}],
                                            [{"A": "two"}])
        self.assertEqual(reports[0]["sources"],
                         {"A": ("TARGET", 1), "B": ("BASE", 1)})

    def test_aggregate_difference_status_is_false_only_when_all_match(self):
        matching = compare_targets({"A": "1"}, [{"A": "1"}, {"A": "1"}])
        mixed = compare_targets({"A": "1"}, [{"A": "1"}, {"A": "2"}])
        self.assertFalse(has_differences(matching))
        self.assertTrue(has_differences(mixed))
