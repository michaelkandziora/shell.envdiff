"""Immutable public comparison result contracts."""
from collections import namedtuple

from .core import (compare_effective_targets, compare_targets, filter_reports,
                   key_set_reports)

_ERROR_KINDS = ("input", "output")
_SOURCE_ROLES = ("REFERENCE", "BASE", "TARGET")


def _replacement_values(record, changes):
    if set(changes) - set(record._fields):
        raise ValueError("invalid result contract")
    return [changes.get(field, getattr(record, field)) for field in record._fields]


class Difference(namedtuple("DifferenceBase", "missing extra changed")):
    """Sorted key-only difference categories, stored as immutable tuples."""
    __slots__ = ()

    def __new__(cls, missing=(), extra=(), changed=()):
        categories = tuple(tuple(category) for category in (missing, extra, changed))
        if not all(isinstance(key, str) for category in categories for key in category):
            raise ValueError("invalid result contract")
        return super(Difference, cls).__new__(cls, *categories)

    @classmethod
    def _make(cls, iterable):
        return cls(*tuple(iterable))

    def _replace(self, **changes):
        return self.__class__(*_replacement_values(self, changes))


class Source(namedtuple("SourceBase", "key role ordinal")):
    """Value-free provenance for a selected difference key."""
    __slots__ = ()

    def __new__(cls, key, role, ordinal):
        if (not isinstance(key, str) or role not in _SOURCE_ROLES or
                isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1):
            raise ValueError("invalid result contract")
        return super(Source, cls).__new__(cls, key, role, ordinal)

    @classmethod
    def _make(cls, iterable):
        return cls(*tuple(iterable))

    def _replace(self, **changes):
        return self.__class__(*_replacement_values(self, changes))


class TargetResult(namedtuple("TargetResultBase", "target difference sources")):
    """One target ordinal and its immutable key-only comparison."""
    __slots__ = ()

    def __new__(cls, target, difference, sources=()):
        sources = tuple(sources)
        if (isinstance(target, bool) or not isinstance(target, int) or target < 1 or
                not isinstance(difference, Difference) or not all(
                isinstance(source, Source) for source in sources)):
            raise ValueError("invalid result contract")
        return super(TargetResult, cls).__new__(cls, target, difference, sources)

    @classmethod
    def _make(cls, iterable):
        return cls(*tuple(iterable))

    def _replace(self, **changes):
        return self.__class__(*_replacement_values(self, changes))


class ComparisonResult(namedtuple("ComparisonResultBase", "targets")):
    """An ordered immutable multi-target comparison result."""
    __slots__ = ()

    def __new__(cls, targets=()):
        targets = tuple(targets)
        if not all(isinstance(target, TargetResult) for target in targets):
            raise ValueError("invalid result contract")
        return super(ComparisonResult, cls).__new__(cls, targets)

    @classmethod
    def _make(cls, iterable):
        return cls(*tuple(iterable))

    def _replace(self, **changes):
        return self.__class__(*_replacement_values(self, changes))


class ComparisonError(namedtuple("ComparisonErrorBase", "kind")):
    """Stable, detail-free public failure category for comparison boundaries."""
    __slots__ = ()

    def __new__(cls, kind):
        if kind not in _ERROR_KINDS:
            raise ValueError("invalid error contract")
        return super(ComparisonError, cls).__new__(cls, kind)

    @classmethod
    def _make(cls, iterable):
        return cls(*tuple(iterable))

    def _replace(self, **changes):
        return self.__class__(*_replacement_values(self, changes))


def compare_mappings(reference, targets, bases=(), includes=(), excludes=(),
                     keys_only=False):
    """Compare mapping inputs through the same ordered comparison core as the CLI."""
    try:
        targets = tuple(targets)
        bases = tuple(bases)
        includes = tuple(includes)
        excludes = tuple(excludes)
        if not targets:
            return ComparisonError("input")
        reports = (compare_effective_targets(reference, bases, targets)
                   if bases else compare_targets(reference, targets))
        reports = filter_reports(reports, includes, excludes)
        if keys_only:
            reports = key_set_reports(reports)
        return result_from_reports(reports)
    except (AttributeError, KeyError, TypeError, ValueError):
        return ComparisonError("input")


def compare_files(reference_path, target_paths, base_paths=(), max_bytes=None,
                  encoding="utf-8", total_bytes=None, includes=(), excludes=(),
                  keys_only=False):
    """Compare file sources once, returning a value-free public input error."""
    from .cli import DEFAULT_TOTAL_BYTES, _read_layered_inputs
    if total_bytes is None:
        total_bytes = DEFAULT_TOTAL_BYTES
    try:
        target_paths = tuple(target_paths)
        base_paths = tuple(base_paths)
        if not target_paths:
            return ComparisonError("input")
        reference, bases, targets = _read_layered_inputs(
            reference_path, base_paths, target_paths, max_bytes, encoding, total_bytes)
    except (AttributeError, IOError, TypeError, UnicodeError, ValueError):
        return ComparisonError("input")
    return compare_mappings(reference, targets, bases, includes, excludes, keys_only)


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


def result_document(result):
    """Return the stable value-free document shared by API and CLI JSON output."""
    targets = []
    for item in result.targets:
        report = {"target": item.target, "missing": list(item.difference.missing),
                  "extra": list(item.difference.extra),
                  "changed": list(item.difference.changed)}
        if item.sources:
            report["sources"] = [{"key": source.key, "role": source.role,
                                  "ordinal": source.ordinal}
                                 for source in item.sources]
        targets.append(report)
    return {"schema_version": 1, "targets": targets}
