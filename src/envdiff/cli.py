"""Command-line interface for envdiff."""
import argparse
import sys

from .core import compare, parse


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare environment-file keys.")
    parser.add_argument("reference")
    parser.add_argument("target")
    args = parser.parse_args(argv)
    try:
        with open(args.reference, "r") as stream:
            reference = parse(stream.read())
        with open(args.target, "r") as stream:
            target = parse(stream.read())
    except (IOError, ValueError) as exc:
        print("envdiff: {0}".format(exc), file=sys.stderr)
        return 2
    report = compare(reference, target)
    for kind in ("missing", "extra", "changed"):
        for name in report[kind]:
            print("{0} {1}".format(kind.upper(), name))
    return 1 if any(report.values()) else 0
