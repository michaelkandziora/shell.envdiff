import unittest

from envdiff import ComparisonResult, Difference, TargetResult


class PublicResultTests(unittest.TestCase):
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
