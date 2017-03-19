"""Command-line interface for envdiff."""
import argparse
import sys

from . import __version__
from .core import compare_targets, has_differences, parse


class SafeArgumentParser(argparse.ArgumentParser):
    """Keep command-line diagnostics useful without reflecting input text."""

    def error(self, message):
        if "target" in message and "required" in message:
            self.exit(2, "envdiff: target input required\n")
        self.exit(2, "envdiff: invalid command arguments\n")


def main(argv=None):
    parser = SafeArgumentParser(description="Compare environment-file keys.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("reference")
    parser.add_argument("target", nargs="+", help="one or more files to compare")
    args = parser.parse_args(argv)
    try:
        reference, targets = _read_inputs(args.reference, args.target)
    except (IOError, UnicodeError):
        print("envdiff: cannot read UTF-8 input", file=sys.stderr)
        return 2
    except ValueError as exc:
        print("envdiff: {0}".format(exc), file=sys.stderr)
        return 2
    reports = compare_targets(reference, targets)
    _write_reports(reports)
    return 1 if has_differences(reports) else 0


def _read_assignments(path):
    """Read a complete text input without including it in diagnostics."""
    with open(path, "r", encoding="utf-8") as stream:
        return parse(stream.read())


def _read_inputs(reference_path, target_paths):
    """Load all inputs before comparison so output remains atomic on failure."""
    reference = _read_assignments(reference_path)
    targets = []
    for path in target_paths:
        targets.append(_read_assignments(path))
    return reference, targets


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
                lines.append("{0} {1}".format(kind.upper(), name))
    return lines
