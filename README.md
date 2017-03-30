# envdiff

Compare dotenv-style `NAME=value` files while reporting keys, never values.

Blank lines and whole-line comments are ignored. An assignment may be preceded
by `export`, and surrounding assignment whitespace is ignored. Each remaining
line must contain one assignment and duplicate keys are invalid input. Names start with a letter or underscore and
may otherwise contain letters, digits, and underscores.
The value is everything after the first `=`; it may itself contain `=`.

Files are decoded as UTF-8. Read and decoding failures use the same safe error
status and do not copy file contents into diagnostics.

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
written: an unreadable or invalid source returns status `2` and no partial
normal report.

Use `envdiff --help` for the positional file arguments and `envdiff --version`
to identify the installed command in build logs.

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
