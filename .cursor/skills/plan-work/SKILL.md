---
name: plan-work
description: Use when a reviewed goal needs an implementation plan before code changes.
user-invocable: true
tier: flexible
kind: process
---

# Plan Work

Write the plan under `docs/plans/`.

Before fixing the plan:

- use `.agents/skills/grilling/SKILL.md` when product decisions remain unresolved;
- use `.agents/skills/research/SKILL.md` for facts owned by current primary sources;
- use `.agents/skills/domain-modeling/SKILL.md` when canonical terms or durable trade-offs change;
- use `.agents/skills/codebase-design/SKILL.md` when the work creates or moves an interface/seam.

Each plan must include:

- goal and linked review;
- acceptance criteria and a customer-visible demo of done;
- assumptions, boundaries, and explicit non-goals;
- risk surfaces (auth, data, schema, bindings, routes, secrets, production);
- ordered tasks and dependencies;
- exact file footprints for every task;
- verification commands and expected outcomes;
- deployment and rollback strategy when production can be affected.

Parallel work is permitted only when file footprints do not overlap and shared contracts are settled first. If two tasks touch the same file, execute them sequentially or use isolated worktrees and reconcile deliberately.

Before implementation, mechanically check for placeholders, ambiguous verbs, missing failure behavior, unowned migrations, and acceptance criteria without a test.

