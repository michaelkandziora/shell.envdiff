# envdiff

Compare simple `NAME=value` files while reporting keys, never values.

Blank lines are ignored. Each nonblank line must contain one assignment and
duplicate keys are invalid input. Names start with a letter or underscore and
may otherwise contain letters, digits, and underscores.

```sh
envdiff reference.env target.env
```

The included examples demonstrate the report without exposing either file's
values:

```text
MISSING REQUIRED
EXTRA EXTRA
CHANGED PORT
```

Exit status is `0` for equal files, `1` for differences, and `2` for invalid input.
Input errors are written to standard error and never include a parsed value.
An equal comparison has no normal output, so scripts can use the exit status
without parsing prose.
