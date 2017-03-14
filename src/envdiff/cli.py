"""Command-line interface for envdiff."""
import argparse
import sys

from . import __version__
from .core import compare, parse


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare environment-file keys.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("reference")
    parser.add_argument("target")
    args = parser.parse_args(argv)
    try:
        reference = _read_assignments(args.reference)
        target = _read_assignments(args.target)
    except IOError:
        print("envdiff: cannot read input", file=sys.stderr)
        return 2
    except ValueError as exc:
        print("envdiff: {0}".format(exc), file=sys.stderr)
        return 2
    report = compare(reference, target)
    for kind in ("missing", "extra", "changed"):
        for name in report[kind]:
            print("{0} {1}".format(kind.upper(), name))
    return 1 if any(report.values()) else 0


def _read_assignments(path):
    """Read a complete text input without including it in diagnostics."""
    with open(path, "r") as stream:
        return parse(stream.read())
