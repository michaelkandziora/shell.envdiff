import unittest

from envdiff import ComparisonResult, Difference, TargetResult, compare_mappings


class PublicResultTests(unittest.TestCase):
    def test_public_api_compares_one_mapping_target(self):
        result = compare_mappings({"A": "one", "B": "one"}, [{"A": "two", "C": "two"}])
        self.assertEqual(result.targets[0].difference,
                         Difference(("B",), ("C",), ("A",)))

    def test_public_api_preserves_multi_target_ordinals(self):
        result = compare_mappings({"A": "one"}, [{"A": "two"}, {"A": "one"}])
        self.assertEqual([item.target for item in result.targets], [1, 2])
        self.assertEqual(result.targets[1].difference, Difference())
    def test_public_result_is_deeply_immutable(self):
        difference = Difference(("MISSING",), ("EXTRA",), ("CHANGED",))
        result = ComparisonResult((TargetResult(1, difference, ()),))
        self.assertEqual(result.targets[0].difference.changed, ("CHANGED",))
        with self.assertRaises(AttributeError):
            result.targets = ()
        with self.assertRaises(AttributeError):
            result.targets[0].difference.changed = ()

    def test_public_result_representation_contains_only_contract_metadata(self):
        result = ComparisonResult((TargetResult(1, Difference((), (), ("PORT",)), ()),))
        self.assertIn("PORT", repr(result))
        self.assertNotIn("secret", repr(result))
