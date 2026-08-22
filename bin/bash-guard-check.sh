#!/usr/bin/env bash
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
cd "$root"

branch="$(git symbolic-ref --quiet --short HEAD || true)"
case "$branch" in
  "")
    if [[ "${HARNESS_CI:-0}" != "1" ]]; then
      printf 'FAIL: detached HEAD is unsafe outside CI.\n' >&2
      exit 1
    fi
    ;;
  main|master|production|prod)
    printf 'FAIL: unsafe branch for agent changes: %s\n' "${branch:-detached HEAD}" >&2
    exit 1
    ;;
esac

if [[ "${HARNESS_CI:-0}" == "1" && -n "${GITHUB_BASE_REF:-}" ]]; then
  base_ref="${HARNESS_BASE_REF:-origin/$GITHUB_BASE_REF}"
  if ! git rev-parse --verify "$base_ref" >/dev/null 2>&1; then
    printf 'FAIL: CI base ref is unavailable: %s\n' "$base_ref" >&2
    exit 1
  fi
  changed="$(git diff --name-only "$base_ref"...HEAD)"
  secret_diff_command=(git diff --no-ext-diff "$base_ref"...HEAD)
else
  changed="$(git diff --name-only --cached)"
  secret_diff_command=(git diff --cached --no-ext-diff)
fi

if [[ -n "$changed" ]]; then
  if printf '%s\n' "$changed" | rg -q '(^|/)(\.env($|\.)|\.dev\.vars($|\.))'; then
    printf 'FAIL: staged files include protected environment/config material.\n' >&2
    exit 1
  fi

  if printf '%s\n' "$changed" | rg -q '(^|/)(AGENTS\.md|\.agents/skills/|\.cursor/|bin/|\.github/workflows/|automations/|harness\.config(\.example)?\.sh|skills(-local)?-lock\.json)'; then
    if [[ "${HARNESS_ALLOW_GUARD_CHANGES:-0}" != "1" ]]; then
      printf 'FAIL: safety controls changed without an approved harness-maintenance override.\n' >&2
      exit 1
    fi
  fi
fi

if "${secret_diff_command[@]}" | rg -i -q '(export[[:space:]]+)?(api[_-]?key|secret|token|password)[[:space:]]*[:=][[:space:]]*["'"'"']?[[:alnum:]_+./=-]{8,}'; then
  printf 'FAIL: staged diff resembles a hard-coded secret.\n' >&2
  exit 1
fi

printf 'PASS: branch and staged-change guard checks.\n'

