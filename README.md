# envdiff

Compare simple `NAME=value` files while reporting keys, never values.

```sh
envdiff reference.env target.env
```

Exit status is `0` for equal files, `1` for differences, and `2` for invalid input.
