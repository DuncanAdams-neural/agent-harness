# Fallow CLI Reference

Complete command and flag specifications for all fallow CLI commands.

---

## Table of Contents

- [`dead-code`: Dead Code Analysis](#dead-code-dead-code-analysis)
- [`dupes`: Duplication Detection](#dupes-duplication-detection)
- [`fix`: Auto-Remove Unused Code](#fix-auto-remove-unused-code)
- [`list`: Project Introspection](#list-project-introspection)
- [`init`: Config Generation](#init-config-generation)
- [`migrate`: Config Migration](#migrate-config-migration)
- [`health`: Function Complexity and File Health Analysis](#health-function-complexity-and-file-health-analysis)
- [`audit`: Changed-File Quality Gate](#audit-changed-file-quality-gate)
- [`flags`: Feature Flag Detection](#flags-feature-flag-detection)
- [`explain`: Rule Explanation](#explain-rule-explanation)
- [`schema`: CLI Introspection](#schema-cli-introspection)
- [`config-schema`: Config JSON Schema](#config-schema-config-json-schema)
- [`plugin-schema`: Plugin JSON Schema](#plugin-schema-plugin-json-schema)
- [`config`: Show Resolved Config](#config-show-resolved-config)
- [Global Flags](#global-flags)
- [Environment Variables](#environment-variables)
- [Output Formats](#output-formats)
- [JSON Output Structure](#json-output-structure)
- [Configuration File Format](#configuration-file-format)
- [Inline Suppression Comments](#inline-suppression-comments)

---

## `dead-code`: Dead Code Analysis

Analyzes the project for unused files, exports, dependencies, types, members, and more. Running `fallow` with no subcommand runs all analyses (dead code + duplication + complexity). Use `fallow dead-code` for dead code only.

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | `human\|json\|sarif\|compact\|markdown\|codeclimate\|gitlab-codequality\|pr-comment-github\|pr-comment-gitlab\|review-github\|review-gitlab` | `human` | Output format |
| `--quiet` | bool | `false` | Suppress progress bars and timing on stderr |
| `--changed-since` | string | — | Only analyze files changed since a git ref (e.g., `main`, `HEAD~3`) |
| `--production` | bool | `false` | Exclude test/dev files, only start/build scripts (applies to every analysis) |
| `--production-dead-code` | bool | `false` | Per-analysis production mode for dead-code. Bare combined runs and `fallow audit` only. |
| `--production-health` | bool | `false` | Per-analysis production mode for health. Bare combined runs and `fallow audit` only. |
| `--production-dupes` | bool | `false` | Per-analysis production mode for duplication. Bare combined runs and `fallow audit` only. |
| `--baseline` | path | — | Compare against a saved baseline |
| `--save-baseline` | path | — | Save current results as a baseline |
| `--workspace` | string | — | Scope to one or more workspaces. Comma-separated values, globs (`apps/*`, `@scope/*`), and `!`-prefixed negation (`!apps/legacy`) supported. Matched against package name AND workspace path relative to repo root. |
| `--changed-workspaces` | string (git ref) | — | Git-derived monorepo CI scoping: scope to workspaces containing any file changed since `REF` (e.g. `origin/main`). Auto-derives the workspace set from `git diff`. Mutually exclusive with `--workspace`. Missing ref is a hard error (exit 2), not silent full-scope fallback. |
| `--include-dupes` | bool | `false` | Cross-reference with duplication findings |
| `--file` | path (multiple) | — | Scope output to specific files. Only issues in the specified files are reported. Project-wide dependency issues are suppressed. Warns on non-existent paths. Useful for lint-staged |
| `--include-entry-exports` | bool | `false` | Report unused exports in entry files (package.json `main`/`exports`, framework pages). Catches typos like `meatdata` vs `metadata`. Global flag, also accepted on combined mode (`fallow --include-entry-exports`) and `fallow audit`. Also configurable as `includeEntryExports: true` in fallow config |
| `--trace` | `FILE:EXPORT` | — | Trace export usage chain |
| `--trace-file` | path | — | Show all edges for a file |
| `--trace-dependency` | string | — | Trace where a dependency is used |

### Issue Type Filters

| Flag | Issue Type |
|------|------------|
| `--unused-files` | Unused files |
| `--unused-exports` | Unused exports |
| `--unused-types` | Unused types |
| `--private-type-leaks` | Opt-in API hygiene check (default `off`) for exported signatures that reference same-file private types. Storybook `*.stories.*` story files and framework routing convention files (Next.js App + Pages Router, Gatsby, Remix v2, TanStack Router, Expo Router) are skipped to avoid noise. Enable via this flag or `private-type-leaks: "warn"` / `"error"` in [`rules`](#configuration-file-format). |
| `--unused-deps` | Unused dependencies, devDependencies, optionalDependencies, type-only production deps, and test-only production deps |
| `--unused-enum-members` | Unused enum members |
| `--unused-class-members` | Unused class members |
| `--unresolved-imports` | Unresolved imports |
| `--unlisted-deps` | Unlisted dependencies |
| `--duplicate-exports` | Duplicate exports |
| `--circular-deps` | Circular dependencies |
| `--re-export-cycles` | Re-export cycles (`kind: multi-node` for barrel files re-exporting from each other in a loop, `kind: self-loop` for a barrel re-exporting from itself). File-scoped finding; chain propagation through the loop is a no-op so imports may silently come up empty. Distinct from `--circular-deps` (runtime cycles). |
| `--boundary-violations` | Boundary violations (imports crossing architecture zone boundaries) |
| `--stale-suppressions` | Stale suppression comments or `@expected-unused` JSDoc tags |
| `--unused-catalog-entries` | Unused pnpm catalog entries |
| `--empty-catalog-groups` | Empty named pnpm catalog groups |
| `--unresolved-catalog-references` | Package references to missing pnpm catalog entries |
| `--unused-dependency-overrides` | Unused pnpm dependency overrides |
| `--misconfigured-dependency-overrides` | Malformed pnpm dependency overrides |

### Examples

```bash
# Full analysis with JSON output
fallow dead-code --format json --quiet

# Only unused exports
fallow dead-code --format json --quiet --unused-exports

# PR check: only changed files
fallow dead-code --format json --quiet --changed-since main --fail-on-issues

# CI mode with SARIF upload
fallow dead-code --ci

# Production-only analysis
fallow dead-code --format json --quiet --production

# Single workspace package
fallow dead-code --format json --quiet --workspace my-package

# Multiple workspaces: comma-separated
fallow dead-code --format json --quiet --workspace web,admin

# Glob (matches package name OR relative path)
fallow dead-code --format json --quiet --workspace 'apps/*'

# Exclude a workspace from the set
fallow dead-code --format json --quiet --workspace 'apps/*,!apps/legacy'

# Monorepo CI: auto-scope to workspaces containing any file changed since origin/main
fallow dead-code --format json --quiet --changed-workspaces origin/main

# Debug: trace an export
fallow dead-code --format json --quiet --trace src/utils.ts:myFunction

# Incremental adoption with baseline
fallow dead-code --format json --quiet --save-baseline fallow-baselines/dead-code.json
fallow dead-code --format json --quiet --baseline fallow-baselines/dead-code.json --fail-on-issues

# Regression detection: save baseline on main, compare on PRs
fallow dead-code --format json --quiet --save-regression-baseline
fallow dead-code --format json --quiet --fail-on-regression --tolerance 2%

# Scope to specific files (e.g., lint-staged)
fallow dead-code --format json --quiet --file src/utils.ts --file src/helpers.ts

# Catch typos in entry file exports
fallow dead-code --format json --quiet --include-entry-exports
```

---

## `dupes`: Duplication Detection

Finds code duplication and clones across the project.

By default, `fallow dupes` skips generated framework output matching `**/.next/**`, `**/.nuxt/**`, `**/.svelte-kit/**`, `**/.turbo/**`, `**/.parcel-cache/**`, `**/.vite/**`, `**/.cache/**`, `**/out/**`, and `**/storybook-static/**`. These defaults merge with `duplicates.ignore`. Set `duplicates.ignoreDefaults = false` to opt out and use only your configured ignore list. If the reported duplication percentage drops after upgrading, this generated-output filtering is the expected reason.

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | `human\|json\|sarif\|compact\|markdown\|codeclimate\|gitlab-codequality\|pr-comment-github\|pr-comment-gitlab\|review-github\|review-gitlab` | `human` | Output format |
| `--quiet` | bool | `false` | Suppress progress bars |
| `--top` | number | - | Show only the N highest-ranked clone groups. Ranking multiplies token count and occurrences, then adds a capped spread boost for distant files or same-file locations. Summary stats reflect the scoped project. |
| `--mode` | `strict\|mild\|weak\|semantic` | `mild` | Detection mode |
| `--near` | bool | `false` | Also detect function-scoped near-miss clones with small structural edits. Near matching always uses semantic shingles while exact matching keeps the selected mode. |
| `--min-tokens` | number | `50` | Minimum token count for a clone |
| `--min-lines` | number | `5` | Minimum line count for a clone |
| `--min-occurrences` | number | `2` | Minimum number of occurrences before a clone group is reported (must be ≥ 2). Raise to skip pair-only clones and focus on widespread copy-paste worth refactoring. `fallow init` writes `minOccurrences: 3` into new projects. |
| `--threshold` | number | `0` | Fail if duplication exceeds this percentage |
| `--skip-local` | bool | `false` | Only report cross-directory duplicates |
| `--cross-language` | bool | `false` | Strip type annotations for TS↔JS matching |
| `--ignore-imports` | bool | `false` | Exclude import declarations from clone detection |
| `--explain-skipped` | bool | `false` | Human/markdown only: show per-pattern counts for files skipped by default duplicates ignores |
| `--trace` | `FILE:LINE` \| `dup:<fp>` | — | Deep-dive clones. `FILE:LINE` traces all clones at a location; `dup:<id>` traces a clone group by the stable fingerprint shown in the listing and on `clone_groups[].fingerprint` in JSON. Fingerprints are usually `dup:<8hex>` and widen only on rare report collisions. Trace output adds an extract-function suggestion, estimated savings, and a best-effort proposed name per group |
| `--changed-since` | string | — | Only report duplication in files changed since a git ref |
| `--baseline` | path | — | Compare against baseline |
| `--save-baseline` | path | — | Save results as baseline |
| `--workspace` | string | — | Scope to one or more workspaces. Comma-separated values, globs (`apps/*`, `@scope/*`), and `!`-prefixed negation (`!apps/legacy`) supported. Matched against package name AND workspace path relative to repo root. |
| `--changed-workspaces` | string (git ref) | — | Git-derived monorepo CI scoping: scope to workspaces containing any file changed since `REF`. Mutually exclusive with `--workspace`. Missing ref is a hard error. |
| `--group-by` | `owner\|directory\|package\|section` | — | Partition the report into per-group sections. Each clone group is attributed to its **largest owner** (most instances; alphabetical tiebreak): a group split 2 src / 1 lib appears under `src`. JSON adds `grouped_by` plus a `groups` array; each bucket carries dedup-aware `stats`, `clone_groups` (every group tagged with `primary_owner` and per-instance `owner`), and `clone_families`. SARIF results carry `properties.group`, CodeClimate issues a top-level `group` field. Compact and markdown fall back to ungrouped with a stderr note. |

### Detection Modes

| Mode | Behavior |
|------|----------|
| `strict` | Exact token match (no normalization) |
| `mild` | Syntax normalized (whitespace, semicolons) |
| `weak` | Different literal values treated as equivalent |
| `semantic` | Renamed variables also treated as equivalent |

Near-miss detection is an independent opt-in, not another normalization mode.
Near groups include `similarity`; every clone-group finding includes `spread`.

### Examples

```bash
# Default duplication scan
fallow dupes --format json --quiet

# Semantic mode (detects renames)
fallow dupes --format json --quiet --mode semantic

# Cross-directory only, fail at 5%
fallow dupes --format json --quiet --skip-local --threshold 5

# Trace clones at a specific location
fallow dupes --format json --quiet --trace src/utils.ts:42

# Deep-dive a clone group by its dup:<id> fingerprint (from the listing or JSON)
fallow dupes --format json --quiet --trace dup:7f3a2c1e

# Only check duplication in changed files
fallow dupes --format json --quiet --changed-since main

# Incremental CI
fallow dupes --format json --quiet --save-baseline fallow-baselines/dupes.json
fallow dupes --format json --quiet --baseline fallow-baselines/dupes.json --threshold 5
```

---

## `fix`: Auto-Remove Unused Code

Auto-removes unused exports, dependencies, enum members, and pnpm catalog entries.

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--dry-run` | bool | `false` | Show what would be removed without modifying files. For `add-to-config` actions, prints a unified-diff preview of the proposed config write; JSON mode includes the diff under a `proposed_diff` field on the fix entry. |
| `--yes` | bool | `false` | Skip confirmation prompt (**required** in non-TTY) |
| `--force` | bool | `false` | Alias for `--yes` |
| `--no-create-config` | bool | `false` | Refuse to create a new `.fallowrc.json` when none exists. The duplicate-export config-add path is skipped with `skip_reason: "no_create_config"`; source-file edits proceed normally. Use in pre-commit hooks, CI bots, and `fallow watch` where silently materialising a new top-level file would surprise the user. |
| `--format` | `human\|json` | `human` | Output format |
| `--quiet` | bool | `false` | Suppress progress bars |

### What gets fixed

- Unused exports (removes the `export` keyword; whole-enum block when every member is unused)
- Unused dependencies (removed from `package.json`)
- Unused enum members (removed from the declaration)
- Unused pnpm catalog entries (removed from `pnpm-workspace.yaml` by line-aware deletion). Object-form entries are removed as one block. By default, fallow also removes a contiguous YAML comment block immediately above the entry when it clearly belongs to that entry; configure this with `fix.catalog.deletePrecedingComments` (`"auto"`, `"always"`, or `"never"`). Two escape hatches keep curated comments safe regardless of policy: a `# fallow-keep` marker on any line in the block preserves it, and the `auto` policy additionally preserves section-banner blocks whose body starts with three or more `=`, `-`, `*`, `_`, `~`, `+`, or `#` characters (e.g. `# === React 18 production pins ===`). Other comments and stylistic choices are preserved. When the last entry of a catalog group is removed, the header is rewritten to `catalog: {}` / `<name>: {}` so pnpm doesn't reject the resulting null value. Entries with non-empty `hardcoded_consumers` are skipped to avoid breaking `pnpm install`; the skip is surfaced in the JSON fix output as `{"type": "remove_catalog_entry", "applied": false, "skipped": true, "skip_reason": "hardcoded_consumers", "consumers": [...]}`. The JSON action carries both `line` (first deleted line, the leading comment when policy absorbs one) and `entry_line` (the catalog entry's original 1-based line); use `entry_line` as a stable anchor across policy changes. After a successful catalog edit the CLI emits a one-line `Run pnpm install to refresh pnpm-lock.yaml` reminder, and the human stderr summary appends `(+M catalog comment lines)` to the fixed-issue count when comment lines were absorbed. The JSON envelope carries a top-level `"skipped"` count alongside `"total_fixed"` for partial-fix gating.
- Duplicate exports (appends an `ignoreExports` rule to your fallow config file). When no fallow config file exists, `.fallowrc.json` is created using the same scaffolding `fallow init` would emit (framework detection, `$schema`, `entry`, `ignorePatterns`, etc.) and the rules are layered on top. Inside a monorepo subpackage (`pnpm-workspace.yaml`, `package.json#workspaces`, `turbo.json`, `lerna.json`, or `rush.json` above the invocation directory) the create-fallback refuses to fire and emits `skip_reason: "monorepo_subpackage"` with a relative `workspace_root` path pointing at the workspace root. The applied entry carries `created_files: [".fallowrc.json"]` so consumers can detect file-creation side effects programmatically.

### On-disk drift protection

`fallow fix` captures every parsed source file's xxh3 content hash during the in-process analysis and recomputes it at fix time. Files whose hash drifted between analysis and write (parallel editor save, CI rebase, concurrent tool) are skipped with `{"type": "skipped", "path": "...", "skipped": true, "skip_reason": "content_changed"}` in the JSON output and `Skipping <path>: file content changed since fallow check ran. Re-run fallow fix to refresh the analysis first.` on stderr (gated on non-quiet). A run with any content-changed skip exits with code 2 so CI does not treat the partial run as a clean no-op. The JSON envelope's top-level `skipped_content_changed: number` is always present and disjoint from `skipped` (which still tallies catalog / YAML guard skips only). Per-file writes are batched: each rewrite is staged to a sibling temp file, and the orchestrator promotes the batch only after every stage succeeds. A stage failure leaves every target file at its original content. Hash precondition covers source files (TS, JS, Vue, Svelte, Astro, MDX); `package.json` and `pnpm-workspace.yaml` are not in the captured hash map because the extract layer does not parse them, but the dep and catalog fixers re-parse those files at fix time as the natural safety net.

### Low-confidence export removals

Issue #602: `fallow fix` withholds unused-export removals when the consumer may be invisible to static analysis, because stripping a real export breaks `tsc` and the build. Two cases are skipped:

- **Off-graph consumer directories.** The file is under any of `__mocks__`, `__fixtures__`, `fixtures`, `e2e`, `e2e-tests`, `cypress`, `playwright`, `examples`, `evals`, `golden` (matched on any path segment). Catches Vitest mock aliases, off-workspace e2e suites, and fixture / golden harnesses. Plain `test` / `tests` / `__tests__` are deliberately NOT on the list, so genuinely-dead test helpers still auto-remove.
- **Files with an unresolved import.** The file itself imports something fallow could not resolve, so its local usage graph is incomplete.

JSON output carries `{"type": "skipped", "path": "...", "skipped": true, "skip_reason": "low_confidence_off_graph"}` (or `"low_confidence_unresolved_imports"`) plus a top-level counter `skipped_low_confidence_exports: number` (always present), disjoint from `skipped`. Unlike the drift and encoding skips this is INTENTIONAL and does NOT change the exit code; the export stays reported by `fallow check` for manual review. High-confidence exports in normal source files are removed unchanged. The AI agent should report kept exports to the user and let them decide whether the export is truly unused before removing it by hand.

### File encoding contract

`fallow fix` is UTF-8 only. Two encoding shapes that previously caused silent corruption are handled explicitly (issue #475):

- **UTF-8 BOM round-trip.** Files with a leading UTF-8 byte-order mark (`EF BB BF`, common on Windows-authored TypeScript) are read with the BOM stripped before line-offset computation and parsing, so reported line numbers do not shift by the BOM codepoint, and the BOM is re-prepended on write so the file's encoding is preserved on round-trip. fallow neither adds nor removes a BOM; if your input has one, the output has one.

- **Mixed CRLF / LF rejection.** Files containing both `\r\n` and bare-LF line endings (common after cross-platform edits without `core.autocrlf`) are skipped instead of silently rewritten to the wrong offsets. The stderr message names the remediation: `Skipping <path>: file has mixed CRLF/LF line endings. Normalize with dos2unix or set git config core.autocrlf input, then re-run fallow fix.`. JSON output carries `{"type": "skipped", "path": "...", "skipped": true, "skip_reason": "mixed_line_endings"}` plus a top-level counter `skipped_mixed_line_endings: number` (always present) disjoint from `skipped_content_changed`. Any non-zero mixed-EOL count exits the run with code 2.

  **The skip is NOT self-healing**. Re-running `fallow fix` produces the same skip; the AI agent or user must run `dos2unix <path>` (or set `git config core.autocrlf input` and re-checkout) before fallow can act on the file. When the same file carries findings for multiple fixers (e.g. an unused export AND an unused enum member), the skip is reported once per file, not once per fixer.

### Examples

```bash
# Preview changes
fallow fix --dry-run --format json --quiet

# Apply changes (--yes required in agent/CI environments)
fallow fix --yes --format json --quiet
```

---

## `list`: Project Introspection

Inspect discovered files, entry points, detected frameworks, and architecture boundary zones.

### Flags

| Flag | Type | Description |
|------|------|-------------|
| `--files` | bool | List all discovered files |
| `--entry-points` | bool | List detected entry points |
| `--plugins` | bool | List active framework plugins |
| `--boundaries` | bool | Show architecture boundary zones, rules, per-zone file counts, and `logical_groups[]` for `autoDiscover` parents |
| `--workspaces` | bool | Show discovered monorepo workspaces plus any workspace-discovery diagnostics (malformed `package.json`, unreachable glob matches, missing tsconfig references). Available as the `fallow workspaces` alias too. |
| `--format` | `human\|json` | Output format |
| `--quiet` | bool | Suppress progress bars |

### Examples

```bash
fallow list --files --format json --quiet
fallow list --entry-points --format json --quiet
fallow list --plugins --format json --quiet
fallow list --boundaries --format json --quiet
fallow list --workspaces --format json --quiet
fallow workspaces --format json --quiet  # alias of `fallow list --workspaces`
```

The `--workspaces` JSON output carries `workspaces[]` (name, project-root-relative path, `is_internal_dependency` bool) plus `workspace_diagnostics[]`. Each diagnostic has a `kind` discriminator (`undeclared-workspace`, `malformed-package-json`, `glob-matched-no-package-json`, `malformed-tsconfig`, `tsconfig-reference-dir-missing`) with a typed payload (`error`, `pattern`, or none). The same `workspace_diagnostics[]` array is also surfaced on `fallow check --format json`, `fallow dupes --format json`, and `fallow health --format json` envelopes (omitted when empty). A malformed ROOT `package.json` exits 2 at config load; everything else warns and continues.

The `--boundaries` JSON output carries `boundaries.logical_groups[]` alongside the existing `zones[]` / `rules[]` arrays. Each logical-group entry surfaces a user-authored `autoDiscover` parent zone (which expansion otherwise flattens into per-child zones like `features/auth` / `features/billing`): `name`, `children`, `auto_discover` (verbatim user strings), `status` (`ok` / `empty` / `invalid_path`), `source_zone_index`, summed `file_count`, optional `authored_rule` (the pre-expansion `{ allow, allowTypeOnly }` keyed on the parent), optional `fallback_zone` cross-reference when the parent also kept its own `patterns` (Bulletproof case), optional `merged_from` (parent zone indices when the user declared the same parent name twice; surfaces the duplicate in JSON instead of only in `tracing::warn!`), optional `original_zone_root` (echo of the parent's `root` subtree scope for monorepo patchers), and optional `child_source_indices` (parallel to `children`, attributing each child to a specific `auto_discover` entry when multiple paths were authored). The full shape is documented in `docs/output-schema.json` under `ListBoundariesOutput`.

---

## `init`: Config Generation

Creates a config file in the project root.

### Flags

| Flag | Type | Description |
|------|------|-------------|
| `--toml` | bool | Create `fallow.toml` instead of `.fallowrc.json` |
| `--hooks` | bool | Scaffold a pre-commit git hook that runs `fallow audit --base <ref> --quiet`. Alias for `fallow hooks install --target git` |
| `--branch` | string | Fallback base branch for the pre-commit hook when no upstream is set (default: `main`). Only used with `--hooks` |

### Examples

```bash
fallow init              # creates .fallowrc.json with $schema
fallow init --toml       # creates fallow.toml
fallow hooks install --target git
fallow hooks install --target git --branch develop  # fallback base branch when no upstream is set
```

---

## `migrate`: Config Migration

Migrates configuration from knip and/or jscpd to fallow. Auto-detects config files.

### Flags

| Flag | Type | Description |
|------|------|-------------|
| `--toml` | bool | Output as `fallow.toml` (mutually exclusive with `--jsonc`) |
| `--jsonc` | bool | Write to `.fallowrc.jsonc` instead of `.fallowrc.json`. Same JSONC content either way; the `.jsonc` extension lets editors auto-detect JSON-with-comments syntax highlighting |
| `--dry-run` | bool | Preview without writing |
| `--from` | path | Specify source config file path |

Without `--jsonc` or `--toml`, fallow auto-mirrors the source extension: a `knip.jsonc` migration writes `.fallowrc.jsonc`, a `knip.json` migration writes `.fallowrc.json`.

### Detected Source Configs

- `knip.json`, `knip.jsonc`, `.knip.json`, `.knip.jsonc`
- `package.json` embedded `knip` field
- `.jscpd.json`
- `package.json` embedded `jscpd` field

### Examples

```bash
fallow migrate --dry-run        # preview
fallow migrate                  # auto-detect; mirrors source extension
fallow migrate --jsonc          # force .fallowrc.jsonc output
fallow migrate --toml           # output as fallow.toml
fallow migrate --from knip.jsonc
```

---

## `health`: Function Complexity and File Health Analysis

Analyzes function complexity across the project using cyclomatic and cognitive complexity metrics. By default all sections are included (health score, complexity findings, file scores, hotspots, and refactoring targets). Use `--complexity`, `--file-scores`, `--hotspots`, `--targets`, or `--score` to show only specific sections.

Angular templates contribute synthetic `<template>` complexity findings whenever they use `@if`/`@for`/`@switch`/`@case`/`@defer (when ...)`/`@let` blocks, legacy structural directives (`*ngIf`, `*ngFor`), bound attributes (`[x]`, `(x)`, `bind-x`, `on-x`), or `{{ }}` interpolations. Both standalone external `.html` files referenced via `templateUrl` AND inline `@Component({ template: \`...\` })` literals are scanned. Inline-template findings anchor at the host `.ts` file's `@Component` decorator line and emit a `suppress-line` action with `// fallow-ignore-next-line complexity` (place the comment directly above the `@Component` decorator). External-template findings emit a `suppress-file` action with `<!-- fallow-ignore-file complexity -->` (place at the top of the `.html` file; HTML cannot express line-level comments). Tagged template literals containing `${...}` interpolations and `template:` properties bound to a variable are skipped (out of scope for the first cut). Vue, Svelte, and Astro single-file components contribute synthetic `<template>` findings too, each scored against its own control-flow vocabulary; those findings emit a `suppress-line` action with the markup comment `<!-- fallow-ignore-next-line complexity -->` placed on the line immediately above the reported line (`placement: "above-template-anchor-line"`), because the synthetic template unit anchors at its first contributing construct rather than the top of the file.

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format` | `human\|json\|sarif\|compact\|markdown\|codeclimate\|gitlab-codequality\|pr-comment-github\|pr-comment-gitlab\|review-github\|review-gitlab\|badge` | `human` | Output format |
| `--quiet` | bool | `false` | Suppress progress bars |
| `--max-cyclomatic` | number | `20` | Fail if any function exceeds this cyclomatic complexity |
| `--max-cognitive` | number | `15` | Fail if any function exceeds this cognitive complexity |
| `--max-crap` | number | `30.0` | Fail if any function has CRAP score >= threshold. CRAP combines complexity with coverage (`CC^2 * (1 - cov/100)^3 + CC`). Pair with `--coverage` for accurate per-function CRAP; without Istanbul data fallow estimates coverage from the module graph. |
| `--top` | number | — | Only show the top N most complex functions (and file scores/hotspots/targets) |
| `--sort` | `cyclomatic\|cognitive\|lines\|severity` | `cyclomatic` | Sort order for complexity findings |
| `--complexity` | bool | `false` | Show only function complexity findings. When no section flags are set, all sections are shown by default. |
| `--file-scores` | bool | `false` | Show only per-file health scores (maintainability index, LOC, fan-in, fan-out, dead code ratio, complexity density, CRAP risk). Runs the full analysis pipeline. Sorted by risk-aware triage concern: lower maintainability index and higher CRAP risk first. When no section flags are set, all sections are shown by default. |
| `--hotspots` | bool | `false` | Show only hotspots: files that are both complex and frequently changing. Combines git churn history with complexity data. Requires a git repository. When no section flags are set, all sections are shown by default. |
| `--targets` | bool | `false` | Show only refactoring targets: ranked recommendations based on complexity, coupling, churn, and dead code signals. Categories: churn+complexity, circular dep, high impact, dead code, complexity, coupling. When no section flags are set, all sections are shown by default. |
| `--effort` | `low\|medium\|high` | — | Filter refactoring targets by effort level. Implies `--targets`. |
| `--score` | bool | `false` | Show only the project health score (0-100) with letter grade (A/B/C/D/F). The score is included by default when no section flags are set. JSON includes `health_score` object with `score`, `grade`, and `penalties` breakdown. As of v2.55.0, plain `--score` skips the churn-backed hotspot penalty so it does not run a `git log` shell-out per invocation; pass `--hotspots` (or `--targets` with `--score`) to include the hotspot penalty. Snapshot (`--save-snapshot`) and trend (`--trend`) flows still trigger hotspot vital signs so saved data stays complete. |
| `--min-score` | number | — | Fail (exit 1) only when the health score is below this threshold. Implies `--score`. Authoritative CI quality gate: when set, complexity findings are demoted to informational and the exit code is driven solely by the score, so `--min-score 0` always exits 0. Composes with `--min-severity`. |
| `--min-severity` | `moderate\|high\|critical` | — | Only exit with an error for findings at or above this severity. Composes with `--min-score` (the run fails if either gate trips). |
| `--report-only` | bool | `false` | Print the score and findings but never fail CI (always exit 0). Advisory mode. Mutually exclusive with `--min-score` and `--min-severity`. |
| `--since` | string | `6m` | Git history window for hotspot analysis. Accepts durations (`6m`, `90d`, `1y`, `2w`) or ISO dates (`2025-06-01`). |
| `--min-commits` | number | `3` | Minimum number of commits for a file to be included in hotspot ranking. |
| `--ownership` | bool | `false` | Attach ownership signals to hotspot entries: bus factor (Avelino truck factor), contributor count, top contributor with stale-days, recent contributors (top-3), `suggested_reviewers`, declared CODEOWNERS owner, `ownership_state`, ownership drift, unowned-hotspot detection. Human output gains a project-level summary line. JSON adds `low-bus-factor`, `unowned-hotspot`, `ownership-drift` action types. Test files get a `[test]` tag. Implies `--hotspots`. Requires git. |
| `--ownership-emails` | `raw\|handle\|anonymized\|hash` | `handle` | Privacy mode for author emails. `handle` shows the local-part only (default, with GitHub noreply unwrap and deterministic same-handle disambiguation). `anonymized` emits stable `xxh3:` pseudonyms; `hash` remains accepted as the legacy spelling. `raw` shows full addresses. Use `anonymized` in regulated environments. Implies `--ownership`. Configure default via `health.ownership.emailMode`. |
| `--changed-since` | string | — | Only analyze files changed since a git ref |
| `--workspace` | string | — | Scope to one or more workspaces. Comma-separated values, globs (`apps/*`, `@scope/*`), and `!`-prefixed negation (`!apps/legacy`) supported. Matched against package name AND workspace path relative to repo root. Vital signs, health score, hotspots, file scores, findings, and `summary.files_analyzed` are all recomputed against the scoped subset. |
| `--group-by` | `owner\|directory\|package\|section` | — | Partition the report into per-group sections. JSON adds `grouped_by` plus a `groups` array; each group contains its own `vital_signs`, `health_score`, `findings`, `file_scores`, `hotspots`, `large_functions`, and `targets` recomputed against the group's files. The top-level metrics stay project-wide so consumers that ignore grouping still see the project headline. Human output adds a per-group score / files / hot / p90 summary block (sorted worst-first when `--score`). SARIF results carry `properties.group` and CodeClimate issues carry a top-level `group` field so GitHub Code Scanning / GitLab Code Quality can partition per team / package. Compact, markdown, and badge fall back to ungrouped output with a stderr note. |
| `--baseline` | path | — | Compare against a saved baseline. When set, the JSON `actions` array on each finding omits `suppress-line` (the baseline already suppresses) and the report root carries an `actions_meta: { suppression_hints_omitted: true, reason: "baseline-active" }` breadcrumb. |
| `--baseline-mode` | `count\|identity` | `count` | How `--baseline` matches health findings: per file and category (`count`, the default) or per function identity (`identity`, strict). `identity` comparison requires a baseline that was saved with `--baseline-mode identity`. |
| `--save-baseline` | path | — | Save current results as a baseline. Same `suppress-line` omission as `--baseline`. |
| `--save-snapshot` | path (optional) | `.fallow/snapshots/<timestamp>.json` | Save vital signs snapshot for trend tracking. Forces file-scores + hotspot computation. |
| `--trend` | bool | `false` | Compare current metrics against the most recent saved snapshot. Reads from `.fallow/snapshots/` and shows per-metric deltas with directional indicators (improving/declining/stable). Implies `--score`. |
| `--coverage-gaps` | bool | `false` | Show runtime files and exports that no test dependency path reaches. Opt-in (default off). Configure severity via the `coverage-gaps` rule (`error`/`warn`/`off`). |
| `--coverage` | path | none | Path to Istanbul-format coverage data (`coverage-final.json`) for accurate per-function CRAP scores. Uses `CC^2 * (1-cov/100)^3 + CC` instead of static binary model. Relative paths resolve against `--root`. |
| `--coverage-root` | path | none | Absolute prefix to strip from file paths in coverage data before prepending the project root. For CI/Docker environments where coverage was generated with different absolute paths. |
| `--runtime-coverage` | path | none | Merge runtime-coverage input into the health report. Accepts a V8 coverage directory (`NODE_V8_COVERAGE=...`), a single V8 coverage JSON file, or an Istanbul `coverage-final.json`. One local capture is free and does not require a license; continuous/cloud or multi-capture runtime monitoring requires an active license or trial (`fallow license activate --trial --email <addr>`). JSON output gains a `runtime_coverage` object with a top-level report verdict, per-finding `verdict` (`safe_to_delete` / `review_required` / `low_traffic` / `coverage_unavailable` / `active`), a per-finding suppression `id` (`fallow:prod:<hash>`, hashes the current line), an optional cross-surface `stable_id` join key (`fallow:fn:<hash>`, hashes file + name + start line; one value per function across findings / hot-paths / blast-radius / importance and across V8/Istanbul/oxc producers), an optional content-digest `source_hash` (line-move-immune, so baselines survive a pure line shift), an evidence block, and percentile-ranked hot paths. On protocol-0.3+ sidecars the `summary` also carries an optional `capture_quality` block (`window_seconds`, `instances_observed`, `lazy_parse_warning`, `untracked_ratio_percent`) that flags short-window captures where lazy-parsed scripts may not appear. |
| `--min-invocations-hot` | number | `100` | Invocation threshold for hot-path classification. Takes effect only when `--runtime-coverage` is set. |
| `--min-observation-volume` | number | `5000` | Minimum total trace volume before the sidecar may emit high-confidence `safe_to_delete` / `review_required` verdicts. Below this, confidence is capped at `medium`. |
| `--low-traffic-threshold` | number | `0.001` | Fraction of total trace count below which an invoked function is classified `low_traffic` rather than `active`. Expressed as a decimal (0.001 = 0.1%). |

### Exit Codes

The gate flag in play determines what drives the exit code. Plain `fallow health` (no gate flag) stays advisory but still fails on any finding (back-compat).

| Invocation | Exit 0 when | Exit 1 when |
|------------|-------------|-------------|
| `fallow health` (no gate flag) | no function exceeds a threshold | any function exceeds a threshold |
| `--min-score N` | score >= N (findings informational) | score < N |
| `--min-severity LEVEL` | no finding at or above LEVEL | any finding at or above LEVEL |
| `--min-score N --min-severity LEVEL` | score >= N AND no finding >= LEVEL | score < N OR a finding >= LEVEL |
| `--report-only` | always | never |

`--report-only` with `--min-score` / `--min-severity` exits 2 (mutually exclusive). The `--runtime-coverage` and coverage-gap gates stay independent and are not demoted by `--min-score`. For gating only newly-introduced complexity, use `fallow audit --gate new-only`.

### Examples

```bash
# Full complexity analysis with JSON output
fallow health --format json --quiet

# Project health score with letter grade
fallow health --format json --quiet --score

# CI gate: fail if score below 70
fallow health --format json --quiet --min-score 70

# Top 10 most complex functions
fallow health --format json --quiet --top 10

# Sort by cognitive complexity
fallow health --format json --quiet --sort cognitive

# Custom thresholds
fallow health --format json --quiet --max-cyclomatic 15 --max-cognitive 10

# Per-file health scores
fallow health --format json --quiet --file-scores

# Top 20 files by triage concern
fallow health --format json --quiet --file-scores --top 20

# Only analyze files changed since main
fallow health --format json --quiet --changed-since main

# Single workspace package
fallow health --format json --quiet --workspace my-package

# Incremental adoption with baseline
fallow health --format json --quiet --save-baseline fallow-baselines/health.json
fallow health --format json --quiet --baseline fallow-baselines/health.json

# Strict adoption: a hotspot that replaces a baselined hotspot is reported
fallow health --format json --quiet --save-ba