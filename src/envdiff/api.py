"""Immutable public comparison result contracts."""
from collections import namedtuple

from .core import compare_effective_targets, compare_targets


class Difference(namedtuple("DifferenceBase", "missing extra changed")):
    """Sorted key-only difference categories, stored as immutable tuples."""
    __slots__ = ()

    def __new__(cls, missing=(), extra=(), changed=()):
        categories = tuple(tuple(category) for category in (missing, extra, changed))
        if not all(isinstance(key, str) for category in categories for key in category):
            raise ValueError("invalid result contract")
        return super(Difference, cls).__new__(cls, *categories)


class Source(namedtuple("SourceBase", "key role ordinal")):
    """Value-free provenance for a selected difference key."""
    __slots__ = ()

    def __new__(cls, key, role, ordinal):
        if not isinstance(key, str) or not isinstance(role, str) or not isinstance(ordinal, int):
            raise ValueError("invalid result contract")
        return super(Source, cls).__new__(cls, key, role, ordinal)


class TargetResult(namedtuple("TargetResultBase", "target difference sources")):
    """One target ordinal and its immutable key-only comparison."""
    __slots__ = ()

    def __new__(cls, target, difference, sources=()):
        sources = tuple(sources)
        if not isinstance(target, int) or not isinstance(difference, Difference) or not all(
                isinstance(source, Source) for source in sources):
            raise ValueError("invalid result contract")
        return super(TargetResult, cls).__new__(cls, target, difference, sources)


class ComparisonResult(namedtuple("ComparisonResultBase", "targets")):
    """An ordered immutable multi-target comparison result."""
    __slots__ = ()

    def __new__(cls, targets=()):
        targets = tuple(targets)
        if not all(isinstance(target, TargetResult) for target in targets):
            raise ValueError("invalid result contract")
        return super(ComparisonResult, cls).__new__(cls, targets)


class ComparisonError(namedtuple("ComparisonErrorBase", "kind")):
    """Stable, detail-free public failure category for comparison boundaries."""
    __slots__ = ()


def compare_mappings(reference, targets, bases=()):
    """Compare mapping inputs through the same ordered comparison core as the CLI."""
    try:
        reports = (compare_effective_targets(reference, bases, targets)
                   if bases else compare_targets(reference, targets))
        return result_from_reports(reports)
    except (AttributeError, KeyError, TypeError, ValueError):
        return ComparisonError("input")


def compare_files(reference_path, target_paths, base_paths=(), max_bytes=None,
                  encoding="utf-8", total_bytes=None):
    """Compare file sources once, returning a value-free public input error."""
    from .cli import DEFAULT_TOTAL_BYTES, _read_layered_inputs
    if total_bytes is None:
        total_bytes = DEFAULT_TOTAL_BYTES
    try:
        reference, bases, targets = _read_layered_inputs(
            reference_path, base_paths, target_paths, max_bytes, encoding, total_bytes)
    except (IOError, UnicodeError, ValueError):
        return ComparisonError("input")
    return compare_mappings(reference, targets, bases)


def result_from_reports(reports):
    """Freeze completed internal reports into the public result contract."""
    targets = []
    for item in reports:
        report = item["report"]
        difference = Difference(report["missing"], report["extra"], report["changed"])
        sources = []
        if "sources" in item:
            for kind in ("missing", "extra", "changed"):
                for key in report[kind]:
                    role, ordinal = item["sources"].get(key, ("REFERENCE", 1))
                    sources.append(Source(key, role, ordinal))
        targets.append(TargetResult(item["target"], difference, sources))
    return ComparisonResult(targets)
