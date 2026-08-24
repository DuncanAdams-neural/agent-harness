# Fleet distribution

GitHub does not natively inject arbitrary files into every newly created
repository. This fleet uses two workflows:

1. `fleet-bootstrap.yml` runs hourly in
   `DuncanAdams-neural/agent-harness`. It inventories repositories owned by
   `DuncanAdams-neural` and `NeuralIdentity` and adds or updates the small
   `agent-harness-sync.yml` workflow.
2. Each repository's sync workflow shallow-clones this public repository at a
   pinned commit SHA, verifies the checkout with the canonical
   `bin/harness-health.sh`, merges it without overwriting project-owned
   `AGENTS.md`, Cursor environment, or `harness.config.sh`, and opens or
   updates a reviewable PR.

## Required secret

Add repository secret `FLEET_TOKEN` to the canonical `agent-harness` repository.
Use a fine-grained token or GitHub App installation token with:

- both configured owners/repository sets;
- Contents: read and write;
- Pull requests: read and write;
- Workflows: read and write (required for `.github/workflows/*`);
- Metadata: read.

The central token opens bootstrap PRs containing only the sync workflow; it
does not write directly to default branches. Each target workflow uses its own
short-lived `GITHUB_TOKEN` to create the harness branch and PR.

Organization/repository settings must allow GitHub Actions to create pull
requests. If policy blocks PR creation, the target workflow fails visibly after
pushing the sync branch.

## Bootstrap run outcomes

Until `FLEET_TOKEN` exists the hourly bootstrap has nothing to distribute, so it
records a warning annotation plus a job summary and succeeds. That keeps the
schedule usable as a signal instead of a permanent red mark.

Once the secret exists:

- every repository in the inventory is attempted, and one failing repository no
  longer aborts the rest of the fleet;
- per-repository permission (`403`), empty-repository (`409`), and policy
  rejection (`422`) answers are reported as `::warning` skips and summarized;
- a token that cannot inventory the fleet at all, an unresolvable canonical
  commit, and any unclassified API failure fail the run;
- rate limits and `5xx` answers are retried with backoff before they count.

Read the counts and any failure list in the run's job summary.

## Update procedure

1. Change and verify the canonical harness, then push it to `main`.
2. Run the central workflow manually or wait for the hourly schedule.

The bootstrap replaces `__CANONICAL_SHA__` in `fleet/agent-harness-sync.yml`
with the canonical commit it ran from (`GITHUB_SHA`), so no one hand-edits the
pin. Targets receive an update PR whenever that commit advances.

Targets always fetch an immutable commit, never a moving branch. A truncated or
incomplete canonical checkout fails the health check and aborts the sync before
any target file is written.

## Offline checks

- `python3 fleet/test-bootstrap.py` — token gating, canonical-SHA pinning,
  eligibility rules, and per-repository failure isolation.
- `python3 fleet/test-fleet.py` — canonical checkout application and
  target-file safety.

Canonical-owned paths (harness skills, gates, locks, docs, and workflows) are
updated on each sync. Product-owned `AGENTS.md`, `.cursor/environment.json`,
`harness.config.sh`, `input/first-review.md`, and `docs/handoff.md` are merged
or preserved. Customize behavior through those product-owned surfaces; changes
inside canonical-owned files will be proposed for replacement in the next sync
PR.

