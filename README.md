# envdiff

Compare simple `NAME=value` files while reporting keys, never values.

Blank lines are ignored. Each nonblank line must contain one assignment and
duplicate keys are invalid input.

```sh
envdiff reference.env target.env
```

Exit status is `0` for equal files, `1` for differences, and `2` for invalid input.
Input errors are written to standard error and never include a parsed value.
