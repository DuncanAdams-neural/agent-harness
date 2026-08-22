#!/usr/bin/env bash
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
cd "$root"

required=(
  AGENTS.md
  docs/forge-workflow.md
  docs/handoff.md
  harness.config.sh
  harness.config.example.sh
  .cursor/environment.json
  .cursor/hooks.json
  .cursor/hooks/markitdown-before-submit.py
  bin/bash-guard-check.sh
  bin/optimizer-gate.sh
  bin/pre-deploy-gate.sh
  bin/test-guards.sh
  bin/test-optimizer-gate.py
  bin/test-skill-registry.py
  bin/test-upload-hook.py
  skills-lock.json
  skills-local-lock.json
  licenses/mattpocock-skills-MIT.txt
  licenses/ponytail-MIT.txt
  licenses/fallow-MIT.txt
  .cursor/rules/agent-harness.mdc
  .cursor/skills/agent-harness/SKILL.md
  .cursor/skills/tdd/SKILL.md
  .cursor/skills/pre-deploy/SKILL.md
  .cursor/skills/ship/SKILL.md
  .cursor/skills/cloudflare-promote/SKILL.md
  .cursor/skills/review-goal/SKILL.md
  .cursor/skills/plan-work/SKILL.md
  .cursor/skills/resume/SKILL.md
)

for path in "${required[@]}"; do
  if [[ ! -f "$path" ]]; then
    printf 'FAIL: missing %s\n' "$path" >&2
    exit 1
  fi
done

for skill in .cursor/skills/*/SKILL.md; do
  folder="$(basename "$(dirname "$skill")")"
  declared="$(awk -F': ' '$1 == "name" { print $2; exit }' "$skill")"
  if [[ "$declared" != "$folder" ]]; then
    printf 'FAIL: %s declares name %s\n' "$skill" "$declared" >&2
    exit 1
  fi
  rg -q '^description: Use when ' "$skill" || { printf 'FAIL: bad trigger in %s\n' "$skill" >&2; exit 1; }
done

python3 -m py_compile .cursor/hooks/markitdown-before-submit.py bin/test-optimizer-gate.py bin/test-skill-registry.py bin/test-upload-hook.py
python3 -m json.tool .cursor/environment.json >/dev/null
python3 -m json.tool .cursor/hooks.json >/dev/null
python3 -m json.tool skills-lock.json >/dev/null
python3 -m json.tool skills-local-lock.json >/dev/null
python3 bin/test-skill-registry.py
bash -n bin/*.sh harness.config.example.sh harness.config.sh
printf 'PASS: harness files, skill names, triggers, and shell syntax.\n'

