#!/usr/bin/env bash
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
cd "$root"

if ! git ls-files | rg -q '\.(cjs|cts|js|jsx|mjs|mts|ts|tsx|vue|svelte|astro)$'; then
  printf 'SKIP: no tracked JS/TS-family source for Fallow.\n'
  exit 0
fi

config="$root/harness.config.sh"
if [[ ! -f "$config" ]]; then
  config="$root/harness.config.example.sh"
fi
if [[ ! -f "$config" ]]; then
  printf 'FAIL: harness config is required for Fallow.\n' >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$config"

command="${HARNESS_FALLOW_CMD:-}"
if [[ -z "$command" ]]; then
  printf 'FAIL: HARNESS_FALLOW_CMD is required for JS/TS-family repositories.\n' >&2
  exit 1
fi

artifact_dir="${HARNESS_ARTIFACT_DIR:-$root/.cursor/artifacts}"
mkdir -p "$artifact_dir"
output="$artifact_dir/fallow-audit.json"
errors="$artifact_dir/fallow-audit.stderr.log"

base_ref="${HARNESS_FALLOW_BASE_REF:-}"
if [[ -z "$base_ref" && -n "${HARNESS_BASE_REF:-}" ]]; then
  base_ref="$HARNESS_BASE_REF"
fi
if [[ -z "$base_ref" && "${HARNESS_CI:-0}" == "1" && -n "${GITHUB_BASE_REF:-}" ]]; then
  base_ref="${HARNESS_BASE_REF:-origin/$GITHUB_BASE_REF}"
fi
if [[ -n "$base_ref" ]]; then
  printf -v quoted_base '%q' "$base_ref"
  command="$command --base $quoted_base"
fi

printf 'RUN: %s\n' "$command"
set +e
bash -o pipefail -c "$command" >"$output" 2>"$errors"
status=$?
set -e

if ! python3 -m json.tool "$output" >/dev/null 2>&1; then
  printf 'FAIL: Fallow did not produce valid JSON (exit %d). See %s and %s.\n' \
    "$status" "$output" "$errors" >&2
  exit 1
fi

case "$status" in
  0)
    if rg -q '"verdict"[[:space:]]*:[[:space:]]*"warn"' "$output"; then
      printf 'FAIL: Fallow returned a warn verdict requiring review. Evidence: %s\n' \
        "$output" >&2
      exit 1
    fi
    if ! rg -q '"verdict"[[:space:]]*:[[:space:]]*"pass"' "$output"; then
      printf 'FAIL: Fallow success output has no recognized audit verdict. Evidence: %s\n' \
        "$output" >&2
      exit 1
    fi
    printf 'PASS: Fallow changed-code audit. Evidence: %s\n' "$output"
    ;;
  1)
    printf 'FAIL: Fallow found introduced quality issues. Evidence: %s\n' "$output" >&2
    exit 1
    ;;
  2)
    printf 'FAIL: Fallow configuration/runtime error. Evidence: %s and %s\n' \
      "$output" "$errors" >&2
    exit 1
    ;;
  *)
    printf 'FAIL: Fallow exited unexpectedly (%d). Evidence: %s and %s\n' \
      "$status" "$output" "$errors" >&2
    exit 1
    ;;
esac

