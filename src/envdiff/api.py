"""Immutable public comparison result contracts."""
from collections import namedtuple


class Difference(namedtuple("DifferenceBase", "missing extra changed")):
    """Sorted key-only difference categories, stored as immutable tuples."""
    __slots__ = ()

    def __new__(cls, missing=(), extra=(), changed=()):
        return super(Difference, cls).__new__(cls, tuple(missing), tuple(extra),
                                              tuple(changed))


class Source(namedtuple("SourceBase", "key role ordinal")):
    """Value-free provenance for a selected difference key."""
    __slots__ = ()


class TargetResult(namedtuple("TargetResultBase", "target difference sources")):
    """One target ordinal and its immutable key-only comparison."""
    __slots__ = ()

    def __new__(cls, target, difference, sources=()):
        return super(TargetResult, cls).__new__(cls, target, difference, tuple(sources))


class ComparisonResult(namedtuple("ComparisonResultBase", "targets")):
    """An ordered immutable multi-target comparison result."""
    __slots__ = ()

    def __new__(cls, targets=()):
        return super(ComparisonResult, cls).__new__(cls, tuple(targets))
