"""Command-line interface for envdiff."""
import argparse
import json
import os
import stat
import sys
import tempfile

from . import __version__
from .core import (compare_effective_targets, compare_targets, filter_reports,
                   has_differences, key_set_reports, parse)

DEFAULT_TOTAL_BYTES = 64 * 1024 * 1024


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
    parser.add_argument("--total-bytes", type=_positive_bytes, metavar="BYTES",
                        default=DEFAULT_TOTAL_BYTES,
                        help="limit all input sources to BYTES (default: 64 MiB)")
    parser.add_argument("--encoding", default="utf-8", metavar="NAME",
                        help="decode every input using NAME")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="write a JSON report")
    output.add_argument("--quiet", action="store_true", help="write no normal report")
    parser.add_argument("--output", metavar="FILE", help="write report to FILE")
    parser.add_argument("reference")
    parser.add_argument("target", nargs="+", help="one or more files to compare")
    args = parser.parse_args(argv)
    try:
        reference, bases, targets = _read_layered_inputs(args.reference, args.base,
                                                         args.target, args.max_bytes,
                                                         args.encoding, args.total_bytes)
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
    content = ""
    if args.json:
        content = json.dumps(_json_report(reports), sort_keys=True) + "\n"
    elif not args.quiet:
        content = _render_reports(reports)
    try:
        if args.output:
            _write_output(args.output, content)
        elif content:
            sys.stdout.write(content)
    except IOError:
        print("envdiff: cannot write report", file=sys.stderr)
        return 2
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
    chunks = []
    remaining = max_bytes + 1
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b"".join(chunks)
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
                         encoding="utf-8", total_bytes=DEFAULT_TOTAL_BYTES):
    """Load reference, bases, and targets before emitting a report."""
    paths = [reference_path] + list(base_paths) + list(target_paths)
    if paths.count("-") > 1:
        raise ValueError("standard input may be used once")
    reader = _InputReader(max_bytes, total_bytes, encoding)
    reference = reader.read(reference_path)
    bases = [reader.read(path) for path in base_paths]
    targets = [reader.read(path) for path in target_paths]
    return reference, bases, targets


class _InputReader(object):
    """Read each source once while enforcing source and shared byte budgets."""

    def __init__(self, max_bytes, total_bytes, encoding):
        self.max_bytes = max_bytes
        self.remaining = total_bytes
        self.encoding = encoding

    def read(self, path):
        if path == "-":
            stream = getattr(sys.stdin, "buffer", sys.stdin)
            return self._decode(stream)
        with open(path, "rb") as stream:
            return self._decode(stream)

    def _decode(self, stream):
        limit = self.remaining
        if self.max_bytes is not None and self.max_bytes < limit:
            limit = self.max_bytes
        data = _read_bytes(stream, limit)
        if self.max_bytes is not None and len(data) > self.max_bytes:
            raise ValueError("input exceeds byte limit")
        if len(data) > self.remaining:
            raise ValueError("input exceeds total byte limit")
        self.remaining -= len(data)
        try:
            return parse(data.decode(self.encoding))
        except LookupError:
            raise ValueError("unsupported input encoding")
        except UnicodeError:
            raise ValueError("cannot decode input")


def _write_reports(reports):
    """Render complete reports only after every input was read successfully."""
    for line in _report_lines(reports):
        print(line)


def _render_reports(reports):
    """Render all normal report lines before a destination is opened."""
    lines = _report_lines(reports)
    return "".join(line + "\n" for line in lines)


def _write_output(path, content):
    """Replace an output file only after the complete report has been written."""
    directory = os.path.dirname(path) or "."
    mode = None
    try:
        existing = os.lstat(path)
        if stat.S_ISREG(existing.st_mode):
            mode = stat.S_IMODE(existing.st_mode)
    except OSError:
        pass
    descriptor, temporary = tempfile.mkstemp(prefix=".envdiff-", dir=directory)
    try:
        if mode is not None:
            os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


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
