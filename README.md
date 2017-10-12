# envdiff

Compare dotenv-style `NAME=value` files while reporting keys, never values.

Blank lines and whole-line comments are ignored. An assignment may be preceded
by `export`, and surrounding assignment whitespace is ignored. Each remaining
line must contain one assignment and duplicate keys are invalid input. Names start with a letter or underscore and
may otherwise contain letters, digits, and underscores.
The value is everything after the first `=`; it may itself contain `=`.
Single- and double-quoted values preserve spaces and `#` markers. Within a
quoted value, `\\n`, `\\r`, `\\t`, a quoted delimiter, and `\\\\` are decoded;
unknown escapes remain unchanged. An unquoted `#` starts a comment only after
whitespace (including a tab). UTF-8 BOMs and CRLF line endings are accepted consistently.
`examples/quoted.env` contains syntax-only quoted assignments for inspection.

```sh
envdiff examples/quoted-reference.env examples/quoted-target.env
```

Files are decoded as UTF-8 by default. Use `--encoding NAME` when a complete
comparison uses another Python codec, and `--max-bytes BYTES` to cap every
reference, base, and target independently. Read, limit, and decoding failures
use the same safe error status and do not copy file contents into diagnostics.

Every invocation also has a 64 MiB raw-input budget across its reference,
bases, and targets, including BOMs and line endings. Use `--total-bytes BYTES`
to select another positive shared budget. Sources are charged once in read
order, so a limit failure produces no partial report.

```sh
envdiff examples/reference.env examples/target.env examples/target-two.env
```

The reference is compared unchanged with each target in argument order. A
report for multiple targets identifies them only as `TARGET 1`, `TARGET 2`, and
so on; input paths and values are not reported. Repeating a target path requests
another comparison at its new ordinal.

Use a repeated `--base FILE` to compose each target from common files. Bases
are applied from left to right and the target is applied last; the reference is
never part of that merge. A duplicate key inside one source is invalid, while a
later source may replace a key from an earlier base. Layered difference lines
add only `SOURCE BASE 1`, `SOURCE TARGET 2`, or `SOURCE REFERENCE 1` metadata;
they never show a source path or a value.

```sh
envdiff --base examples/base.env examples/reference.env examples/target.env
```

The included examples demonstrate the report without exposing either file's
values:

```text
TARGET 1
MISSING REQUIRED
EXTRA EXTRA
CHANGED PORT
TARGET 2
```

Exit status is `0` for equal files, `1` for differences, and `2` for invalid input.
Input errors are written to standard error and never include a parsed value.
An equal comparison has no normal output, so scripts can use the exit status
without parsing prose.

At least one target is required. All sources are read before any report is
written: an unreadable or invalid reference, base, or target returns status `2`
and no partial normal report. Invalid command arguments use a fixed diagnostic,
so command input is not copied to standard error.

Use `envdiff --help` for the positional file arguments and `envdiff --version`
to identify the installed command in build logs.

`-` may be used for exactly one source to read standard input. It cannot stand
for both a reference and target (or for repeated targets), avoiding ambiguity
about a consumed stream.

## Selecting keys

Repeat `--include GLOB` to select report keys and `--exclude GLOB` to remove
them; exclusions win when patterns overlap. Filtering occurs after every input
has been parsed, layered, and compared, so an invalid source still returns
status `2` even when its differences would not be selected. If no difference
remains selected, the command returns `0`. With one target there is no normal
output; with multiple targets the `TARGET N` headings remain as normal
comparison structure even when no difference is selected.

`--keys-only` is a comparison mode: it ignores changed values while retaining
missing and extra keys. It is not a redaction switch—normal reports already
never print values.

```sh
envdiff --include "APP_*" --exclude "*_TOKEN" reference.env target.env
envdiff --keys-only reference.env target.env
```

## Automation output

Use `--json` for a stable, value-free document with `schema_version: 1` and a
`targets` array in input order. Each target has its ordinal plus sorted
`missing`, `extra`, and `changed` key arrays. Layered reports add source
records containing only a key, source role, and ordinal. `--quiet` suppresses
normal output while preserving exit status and error diagnostics. It cannot be
combined with `--json`.

For example, a single-target JSON report has this shape (keys only):

```json
{"schema_version": 1, "targets": [{"changed": ["PORT"], "extra": [], "missing": [], "target": 1}]}
```

Use `--output FILE` to replace a report destination only after all inputs have
parsed and the complete report is ready. It works with text or `--json`; a
write failure returns status `2` without reflecting the destination path.
New report files are private (mode 0600); ordinary rwx permissions of an
existing regular file are retained. If FILE is a symlink, envdiff atomically
replaces that link entry rather than writing through it.
Output destinations are limited to a missing path, an existing regular file,
or a symlink. A FIFO, socket, device, or directory is rejected with status 2
and left unchanged. On an existing regular file only ordinary rwx permission
bits are preserved; setuid, setgid, and sticky bits are deliberately removed.
Ownership and ACL preservation, and crash-durability guarantees, are outside
this contract. Failures during fchmod, fdopen, write, flush, close, or
replacement return status 2 and preserve the destination; normal failure
handling attempts to remove temporary files and close descriptors, without a
stronger guarantee if a cleanup operation itself fails.

## Public API

`envdiff` also exposes `compare_mappings` and `compare_files`. Both return an
immutable `ComparisonResult` containing ordered immutable `TargetResult`,
`Difference`, and `Source` records; each record contains only key names,
roles, and ordinals. `compare_mappings` accepts reference and target mappings
plus optional bases, include/exclude globs, and `keys_only`. `compare_files`
uses the same read, decode, layer, compare, and filter core as the command.
Malformed public input or unreadable sources return `ComparisonError("input")`;
the error contract never retains paths, values, or source contents.

```python
from envdiff import compare_mappings

result = compare_mappings({"PORT": "one"}, [{"PORT": "two"}])
assert result.targets[0].difference.changed == ("PORT",)
```

## Development

From a source checkout, run the suite with the source package on the import
path:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Build distributable archives with `python3 setup.py sdist bdist_wheel`.
Argument errors use fixed, value- and path-free diagnostics; `--help` remains
the way to obtain usage information.

MIT licensed.
