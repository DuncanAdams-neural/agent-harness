# Fallow: Critical Gotchas

Common pitfalls and their correct solutions when working with fallow.

---

## `fix` Requires `--yes` in Non-TTY Environments

The `fix` command prompts for confirmation in interactive terminals. In agent subprocesses, CI pipelines, or piped input (non-TTY), the `--yes` flag is mandatory. Without it, `fix` exits with code 2 and an error.

```bash
# WRONG: fix exits with code 2 in non-TTY
fallow fix --format json --quiet

# CORRECT: always use --dry-run first, then --yes
fallow fix --dry-run --format json --quiet   # preview
fallow fix --yes --format json --quiet       # apply
```

Always preview with `--dry-run` before applying. This is a destructive operation that modifies source files.
