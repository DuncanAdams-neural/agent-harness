---
name: resume
description: Use when starting, resuming, compacting, or handing off a work session.
user-invocable: true
tier: rigid
kind: process
---

# Resume and Handoff

## Iron Law

```
NEVER RESTART A LIVE TASK FROM MEMORY — READ HANDOFF FIRST
```

## Start

1. Read `docs/handoff.md`.
2. Verify its branch and commit against git.
3. Inspect working-tree changes and recent commits.
4. If git reports an in-progress merge/rebase, invoke
   `.agents/skills/resolving-merge-conflicts/SKILL.md` before other edits.
5. If phase is not `done` and the goal still applies, continue at `next_action`.
6. If state disagrees with git, repair the handoff before coding.

## Stop or phase change

Rewrite `docs/handoff.md` with:

- phase and goal;
- completed work;
- exact stop point and next action;
- blockers and decisions needed;
- files touched;
- branch and current commit;
- latest verification command, result, timestamp, and commit;
- new, stable, and rollback Worker version IDs when applicable.

Commit handoff changes with the work so cloud agents and teammates receive them. Do not claim `done` before post-production verification when deployment is part of the goal.

## Red flags

- “The chat still has the context.”
- “Starting over is faster.”
- A handoff that says green but names another commit.
- A vague next action such as “continue implementation.”

