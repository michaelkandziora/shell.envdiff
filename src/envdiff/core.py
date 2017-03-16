"""The initial NAME=value parser and key comparison primitives."""


def parse(text):
    """Return a mapping parsed from simple NAME=value assignments."""
    values = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not line:
            continue
        name, marker, value = line.partition("=")
        if not marker:
            raise ValueError("line {0}: expected assignment".format(number))
        if not _is_name(name):
            raise ValueError("line {0}: invalid name".format(number))
        if name in values:
            raise ValueError("line {0}: duplicate name".format(number))
        values[name] = value
    return values


def _is_name(name):
    """Recognize portable environment variable names for the base grammar."""
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if not name or not (name[0] in letters or name[0] == "_"):
        return False
    return all(character in letters + "0123456789_" for character in name)


def compare(reference, target):
    """Return sorted changed, missing and extra names only."""
    return {
        "missing": sorted(set(reference) - set(target)),
        "extra": sorted(set(target) - set(reference)),
        "changed": sorted(name for name in set(reference) & set(target)
                          if reference[name] != target[name]),
    }


def compare_targets(reference, targets):
    """Compare every target in argument order against one unchanged reference."""
    return [
        {"target": ordinal, "report": compare(reference, target)}
        for ordinal, target in enumerate(targets, 1)
    ]
