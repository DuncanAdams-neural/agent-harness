# Cloud agent automation

Use this prompt in Cursor Cloud Agents, Cursor Automations, or Codex Automations:

```text
Run the repository agent harness.

Follow AGENTS.md and .cursor/skills/agent-harness/SKILL.md strictly.
Read docs/handoff.md before choosing work. If it contains an active goal, continue
from next_action instead of starting over. Otherwise review new files in input/
without editing them.

For implementation, require a reviewed goal, a plan with file footprints, tests,
a full diff review, and a fresh green bin/pre-deploy-gate.sh repo run. Work only
on a feature branch. Never use --no-verify, force-push, edit secrets, or deploy
with stale evidence.

Update docs/handoff.md before stopping, including completed work, exact stop point,
next action, blockers, files, commit, and latest gate evidence. Commit and push
the handoff with the work.

If production deployment is part of the active goal, use the cloudflare-promote
skill. Secrets must come from the runner environment. Missing credentials, health
URL, tests, rollback ID, or any failed gate means stop before production.
```

## Suggested schedules

- **Daily review-only:** use the same prompt but end after `review-goal`.
- **On demand delivery:** use the full prompt.
- **Production promotion:** prefer an explicit on-demand run with Cloudflare credentials scoped to the target Worker.

Do not give a daily review automation production credentials.

