---
name: pre-deploy
description: Use when a release candidate may be pushed or production traffic may change.
user-invocable: true
tier: rigid
kind: verification
---

# Pre-Deploy Gate

## Iron Law

```
NO DEPLOY APPROVAL WITHOUT FRESH GATE EVIDENCE
```

Run every configured gate against current `HEAD`. Any failure is NO-GO. A change after the run invalidates all evidence.

## Gate

1. Verify a feature branch and inspect git state.
2. Run `bin/bash-guard-check.sh`.
3. Confirm the separate Ponytail over-engineering and Standards/Spec review axes
   completed. Accepted simplifications must return through TDD and review.
4. Run `bin/pre-deploy-gate.sh repo` before commit, push, or merge. It invokes
   `bin/optimizer-gate.sh`, which runs Fallow for JS/TS-family repositories.
5. Run `bin/pre-deploy-gate.sh production` only immediately before `cloudflare-promote`.
6. Inspect full output; do not reduce FAIL to WARN.
7. If fixes are made, rerun the full sequence.
8. Record commands, result, timestamp, and `HEAD` in `docs/handoff.md`.

The production gate checks configured typecheck, lint, tests, build, Wrangler version/config, `wrangler deploy --dry-run`, health configuration, and secret hygiene. Risky auth or schema changes require focused security or migration review.

## Red flags

- “Tests passed earlier.”
- “Run only the cheap checks.”
- “The owner accepts the risk.”
- “We can harden after launch.”
- Treating an unexplained warning as harmless.

## Common rationalizations

Read `rationalizations.md` before approving a gate with any warning or skipped check.

## Self-review

- [ ] Every configured command ran against current `HEAD`.
- [ ] Full output was read.
- [ ] No failure or required check was skipped.
- [ ] Risk-specific review ran where needed.
- [ ] Evidence is recorded in the handoff.

