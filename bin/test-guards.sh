#!/usr/bin/env bash
set -euo pipefail

source_root="$(git rev-parse --show-toplevel)"
tmp="$(mktemp -d)"
trap 'rm -r "$tmp"' EXIT
unset HARNESS_CI GITHUB_BASE_REF HARNESS_BASE_REF HARNESS_ALLOW_GUARD_CHANGES

expect_failure() {
  if "$@" >/dev/null 2>&1; then
    printf 'FAIL: command unexpectedly passed: %s\n' "$*" >&2
    exit 1
  fi
}

cd "$tmp"
git init -q
git config user.name "Harness Test"
git config user.email "harness@example.invalid"
mkdir bin
cp "$source_root/bin/bash-guard-check.sh" bin/
chmod +x bin/bash-guard-check.sh
printf 'base\n' > app.txt
git add .
git commit -qm "base"
git branch -m main
git switch -qc feature/test

printf 'safe\n' >> app.txt
git add app.txt
bash bin/bash-guard-check.sh >/dev/null
git reset -q --hard HEAD

secret_name="API_""TOKEN"
secret_value="abcdefgh""12345678"
printf '%s=%s\n' "$secret_name" "$secret_value" > app.txt
git add app.txt
expect_failure bash bin/bash-guard-check.sh
git reset -q --hard HEAD

printf 'rules\n' > AGENTS.md
git add AGENTS.md
expect_failure bash bin/bash-guard-check.sh
HARNESS_ALLOW_GUARD_CHANGES=1 bash bin/bash-guard-check.sh >/dev/null
git commit -qm "change safety file"

GITHUB_BASE_REF=main HARNESS_BASE_REF=main HARNESS_CI=1 \
  expect_failure bash bin/bash-guard-check.sh

git switch -q main
expect_failure bash bin/bash-guard-check.sh

printf 'PASS: guard branch, secret, protected-file, override, and CI-diff cases.\n'

