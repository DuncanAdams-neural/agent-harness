# Forge workflow

This harness may run in an Origin-backed repository.

## Source of truth

- Use repository-native tools exposed by the current environment.
- In Origin-backed repos, use the authenticated `origin` CLI for read-only PR
  context: `origin pr view`, `origin pr checks`, `origin pr diff`, and
  `origin pr view --comments`.
- Use the platform's pull-request management tool only when the user explicitly
  asks to create, update, comment on, label, close, or reopen a PR.
- Never substitute `gh` in an Origin-backed repository.

## Reviews and conflicts

For a spec or intent source, prefer:

1. the active `reviews/` report and `docs/plans/` plan;
2. `docs/handoff.md`;
3. local PR/commit messages;
4. forge PR/issue context when accessible.

Authentication failure is a blocker, not permission to guess. Continue with
local primary sources when they are sufficient; otherwise record the missing
context in the handoff and stop.

