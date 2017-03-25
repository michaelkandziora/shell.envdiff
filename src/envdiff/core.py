"""The initial NAME=value parser and key comparison primitives."""


def parse(text):
    """Return a mapping parsed from the small dotenv assignment dialect."""
    values = {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, marker, value = line.partition("=")
        name = name.rstrip()
        value = value.strip()
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


def merge_layers(layers):
    """Merge mappings in source order, allowing a later source to override."""
    effective = {}
    for layer in layers:
        effective.update(layer)
    return effective


def merge_layers_with_sources(layers):
    """Merge source-tagged mappings and retain the winning source per key."""
    effective = {}
    sources = {}
    for role, ordinal, layer in layers:
        for name, value in layer.items():
            effective[name] = value
            sources[name] = (role, ordinal)
    return effective, sources


def compare_targets(reference, targets):
    """Compare every target in argument order against one unchanged reference."""
    return [
        {"target": ordinal, "report": compare(reference, target)}
        for ordinal, target in enumerate(targets, 1)
    ]


def has_differences(reports):
    """Return whether any ordinal target report contains a key difference."""
    return any(any(item["report"].values()) for item in reports)
