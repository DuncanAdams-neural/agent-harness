---
name: ship
description: Use when verified changes are ready to commit and push to the repository.
user-invocable: true
tier: rigid
kind: verification
---

# Ship

## Iron Law

```
NO PUSH WITHOUT A GREEN PIPELINE
```

Shipping to the repository is not production promotion. Keep those gates separate.

## Pipeline

1. Inspect git state. If a merge or rebase is in progress, invoke
   `.agents/skills/resolving-merge-conflicts/SKILL.md` and complete its gate
   before continuing.
2. Run `bin/bash-guard-check.sh`.
3. Run `bin/pre-deploy-gate.sh repo`.
4. Review the staged file list; exclude secrets, unrelated changes, and generated noise.
5. Commit a focused logical change with a descriptive message.
6. Push the feature branch normally. Never force-push.
7. Confirm clean status and update `docs/handoff.md` with commit SHA and next phase.

## Red flags

- “Skip lint; the editor formatted it.”
- “Push now and test in CI.”
- “Use `--no-verify` just this once.”
- “Commit everything to avoid missing a file.”
- Pushing to `main`, `master`, or a production branch.

## Common rationalizations

See `rationalizations.md`.

## Self-review

- [ ] Current-HEAD repository gate is green.
- [ ] The staged list is intentional and secret-free.
- [ ] Commit is focused and descriptive.
- [ ] Push is a normal feature-branch push.
- [ ] Handoff contains the resulting SHA.

