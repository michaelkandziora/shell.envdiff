"""Immutable public comparison result contracts."""
from collections import namedtuple

from .core import compare_effective_targets, compare_targets


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


class ComparisonError(namedtuple("ComparisonErrorBase", "kind")):
    """Stable, detail-free public failure category for comparison boundaries."""
    __slots__ = ()


def compare_mappings(reference, targets, bases=()):
    """Compare mapping inputs through the same ordered comparison core as the CLI."""
    reports = (compare_effective_targets(reference, bases, targets)
               if bases else compare_targets(reference, targets))
    return result_from_reports(reports)


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
        for kind in ("missing", "extra", "changed"):
            for key in report[kind]:
                role, ordinal = item.get("sources", {}).get(key, ("REFERENCE", 1))
                sources.append(Source(key, role, ordinal))
        targets.append(TargetResult(item["target"], difference, sources))
    return ComparisonResult(targets)
