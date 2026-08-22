#!/usr/bin/env bash
set -euo pipefail

mode="${1:-repo}"
if [[ "$mode" != "repo" && "$mode" != "production" ]]; then
  printf 'Usage: %s [repo|production]\n' "$0" >&2
  exit 2
fi

root="$(git rev-parse --show-toplevel)"
cd "$root"

config="$root/harness.config.sh"
if [[ ! -f "$config" ]]; then
  if [[ "$mode" == "production" ]]; then
    printf 'FAIL: harness.config.sh is required for production.\n' >&2
    exit 1
  fi
  config="$root/harness.config.example.sh"
fi

# shellcheck disable=SC1090
source "$config"

failures=0

if [[ "${HARNESS_CONFIGURED:-0}" != "1" ]]; then
  printf 'FAIL: set HARNESS_CONFIGURED=1 only after replacing example commands with repository checks.\n' >&2
  exit 1
fi

run_gate() {
  local label="$1"
  local command="$2"

  if [[ -z "$command" ]]; then
    if [[ "$mode" == "production" ]]; then
      printf 'FAIL: %s command is not configured.\n' "$label" >&2
      failures=$((failures + 1))
    else
      printf 'SKIP: %s is not configured.\n' "$label"
    fi
    return
  fi

  printf '\n== %s ==\n%s\n' "$label" "$command"
  if ! bash -o pipefail -c "$command"; then
    printf 'FAIL: %s\n' "$label" >&2
    failures=$((failures + 1))
  else
    printf 'PASS: %s\n' "$label"
  fi
}

HARNESS_ALLOW_GUARD_CHANGES="${HARNESS_ALLOW_GUARD_CHANGES:-0}" bash bin/bash-guard-check.sh || failures=$((failures + 1))

run_gate "typecheck" "${HARNESS_TYPECHECK_CMD:-}"
run_gate "lint" "${HARNESS_LINT_CMD:-}"
run_gate "tests" "${HARNESS_TEST_CMD:-}"
run_gate "build" "${HARNESS_BUILD_CMD:-}"
run_gate "optimization" "bash bin/optimizer-gate.sh"

if git ls-files | rg -q '(^|/)(\.env($|\.)|\.dev\.vars($|\.))'; then
  printf 'FAIL: protected environment file is tracked by git.\n' >&2
  failures=$((failures + 1))
else
  printf 'PASS: protected environment files are not tracked.\n'
fi

if [[ "$mode" == "production" ]]; then
  required=(HARNESS_WORKER_NAME HARNESS_HEALTH_URL HARNESS_WRANGLER_CMD HARNESS_WRANGLER_CHECK_CMD)
  for variable in "${required[@]}"; do
    if [[ -z "${!variable:-}" ]]; then
      printf 'FAIL: %s is required for production.\n' "$variable" >&2
      failures=$((failures + 1))
    fi
  done

  if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
    printf 'FAIL: CLOUDFLARE_API_TOKEN is absent from the environment.\n' >&2
    failures=$((failures + 1))
  fi

  if (( failures == 0 )) && [[ -n "${HARNESS_WRANGLER_CMD:-}" ]]; then
    wrangler_target="--name \"$HARNESS_WORKER_NAME\""
    if [[ -n "${HARNESS_PRODUCTION_ENV:-}" ]]; then
      wrangler_target="$wrangler_target --env \"$HARNESS_PRODUCTION_ENV\""
    fi
    run_gate "Wrangler version" "$HARNESS_WRANGLER_CMD --version"
    run_gate "Wrangler check" "${HARNESS_WRANGLER_CHECK_CMD:-}"
    run_gate "Wrangler dry run" "$HARNESS_WRANGLER_CMD deploy --dry-run $wrangler_target"
  else
    printf 'SKIP: Wrangler validation blocked by earlier production gate failures.\n'
  fi
fi

if (( failures > 0 )); then
  printf '\nNO-GO: %d gate(s) failed.\n' "$failures" >&2
  exit 1
fi

printf '\nGO: all required %s gates passed for %s.\n' "$mode" "$(git rev-parse --short HEAD)"

