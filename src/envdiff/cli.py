"""Command-line interface for envdiff."""
import argparse
import json
import sys

from . import __version__
from .core import (compare_effective_targets, compare_targets, filter_reports,
                   has_differences, key_set_reports, parse)


class SafeArgumentParser(argparse.ArgumentParser):
    """Keep command-line diagnostics useful without reflecting input text."""

    def error(self, message):
        if "target" in message and "required" in message:
            self.exit(2, "envdiff: target input required\n")
        self.exit(2, "envdiff: invalid command arguments\n")


def main(argv=None):
    parser = SafeArgumentParser(description="Compare environment-file keys.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--base", action="append", default=[], metavar="FILE",
                        help="apply FILE before every target")
    parser.add_argument("--include", action="append", default=[], metavar="GLOB",
                        help="report only matching keys")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="omit matching keys")
    parser.add_argument("--keys-only", action="store_true",
                        help="ignore value-only differences")
    parser.add_argument("--max-bytes", type=_positive_bytes, metavar="BYTES",
                        help="limit each input source to BYTES")
    parser.add_argument("--encoding", default="utf-8", metavar="NAME",
                        help="decode every input using NAME")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="write a JSON report")
    output.add_argument("--quiet", action="store_true", help="write no normal report")
    parser.add_argument("reference")
    parser.add_argument("target", nargs="+", help="one or more files to compare")
    args = parser.parse_args(argv)
    try:
        reference, bases, targets = _read_layered_inputs(args.reference, args.base,
                                                         args.target, args.max_bytes,
                                                         args.encoding)
    except (IOError, UnicodeError):
        print("envdiff: cannot read UTF-8 input", file=sys.stderr)
        return 2
    except ValueError as exc:
        print("envdiff: {0}".format(exc), file=sys.stderr)
        return 2
    reports = (compare_effective_targets(reference, bases, targets)
               if bases else compare_targets(reference, targets))
    reports = filter_reports(reports, args.include, args.exclude)
    if args.keys_only:
        reports = key_set_reports(reports)
    if args.json:
        print(json.dumps(_json_report(reports), sort_keys=True))
    elif not args.quiet:
        _write_reports(reports)
    return 1 if has_differences(reports) else 0


def _json_report(reports):
    """Return the stable, value-free JSON representation of target reports."""
    targets = []
    for item in reports:
        report = {"target": item["target"]}
        report.update(item["report"])
        if "sources" in item:
            sources = []
            for kind in ("missing", "extra", "changed"):
                for name in item["report"][kind]:
                    role, ordinal = item["sources"].get(name, ("REFERENCE", 1))
                    sources.append({"key": name, "role": role, "ordinal": ordinal})
            report["sources"] = sources
        targets.append(report)
    return {"schema_version": 1, "targets": targets}


def _positive_bytes(value):
    """Accept a positive byte count without exposing an invalid argument."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("invalid byte count")
    if number < 1:
        raise argparse.ArgumentTypeError("invalid byte count")
    return number


def _read_assignments(path, max_bytes=None, encoding="utf-8", stdin=None):
    """Read and decode one bounded source without preserving its location."""
    if path == "-":
        stream = stdin if stdin is not None else getattr(sys.stdin, "buffer", sys.stdin)
        data = _read_bytes(stream, max_bytes)
    else:
        with open(path, "rb") as stream:
            data = _read_bytes(stream, max_bytes)
    try:
        return parse(data.decode(encoding))
    except LookupError:
        raise ValueError("unsupported input encoding")
    except UnicodeError:
        raise ValueError("cannot decode input")


def _read_bytes(stream, max_bytes):
    """Read at most one source limit plus a sentinel byte."""
    if max_bytes is None:
        return stream.read()
    data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("input exceeds byte limit")
    return data


def _read_inputs(reference_path, target_paths, max_bytes=None, encoding="utf-8"):
    """Load all inputs before comparison so output remains atomic on failure."""
    reference = _read_assignments(reference_path, max_bytes, encoding)
    targets = []
    for path in target_paths:
        targets.append(_read_assignments(path, max_bytes, encoding))
    return reference, targets


def _read_layered_inputs(reference_path, base_paths, target_paths, max_bytes=None,
                         encoding="utf-8"):
    """Load reference, bases, and targets before emitting a report."""
    reference = _read_assignments(reference_path, max_bytes, encoding)
    bases = [_read_assignments(path, max_bytes, encoding) for path in base_paths]
    targets = [_read_assignments(path, max_bytes, encoding) for path in target_paths]
    return reference, bases, targets


def _write_reports(reports):
    """Render complete reports only after every input was read successfully."""
    for line in _report_lines(reports):
        print(line)


def _report_lines(reports):
    """Build deterministic, key-only lines without retaining input paths."""
    lines = []
    multiple = len(reports) > 1
    for item in reports:
        if multiple:
            lines.append("TARGET {0}".format(item["target"]))
        for kind in ("missing", "extra", "changed"):
            for name in item["report"][kind]:
                line = "{0} {1}".format(kind.upper(), name)
                if "sources" in item:
                    role, ordinal = item["sources"].get(name, ("REFERENCE", 1))
                    line += " SOURCE {0} {1}".format(role, ordinal)
                lines.append(line)
    return lines
