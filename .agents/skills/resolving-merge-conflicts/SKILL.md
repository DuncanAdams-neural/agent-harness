---
name: resolving-merge-conflicts
description: "Use when you need to resolve an in-progress git merge/rebase conflict."
---

1. **See the current state** of the merge/rebase. Check git history, and the conflicting files.

2. **Find the primary sources** for each conflict. Understand deeply why each
change was made and what the original intent was. Read commits, plans, reviews,
the active handoff, and forge context through
[`docs/forge-workflow.md`](../../../docs/forge-workflow.md).

3. **Resolve each hunk.** Preserve both intents where possible. Where
incompatible, pick the one matching the merge's stated goal and note the
trade-off. Do **not** invent new behaviour. Continue the requested resolution;
abort only when the user explicitly redirects or the primary sources prove the
operation itself is unsafe.

4. Run `bin/pre-deploy-gate.sh repo` when the harness is installed; otherwise
discover the project's checks. Fix anything the merge broke and rerun the full
gate.

5. **Finish the merge/rebase.** Stage only the resolved scope and commit. If
rebasing, continue until all commits are rebased. Update `docs/handoff.md` with
the resolved intents, verification evidence, and resulting commit.
