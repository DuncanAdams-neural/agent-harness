# Fleet distribution

GitHub does not natively inject arbitrary files into every newly created
repository. This fleet uses two workflows:

1. `fleet-bootstrap.yml` runs hourly in
   `DuncanAdams-neural/agent-harness`. It inventories repositories owned by
   `DuncanAdams-neural` and `NeuralIdentity` and adds or updates the small
   `agent-harness-sync.yml` workflow.
2. Each repository's sync workflow downloads the canonical bundle, merges it
   without overwriting project-owned `AGENTS.md`, Cursor environment, or
   `harness.config.sh`, and opens/updates a reviewable PR.

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

## Update procedure

1. Change and verify the canonical harness.
2. Run `python3 fleet/build-bundle.py`.
3. Commit the changed manifest and chunk files under `distribution/`.
4. Run the central workflow manually or wait for the hourly schedule.

Never hand-edit the manifest or base64 chunks.

Canonical-owned paths (harness skills, gates, locks, docs, and workflows) are
updated on each sync. Product-owned `AGENTS.md`, `.cursor/environment.json`,
`harness.config.sh`, `input/first-review.md`, and `docs/handoff.md` are merged
or preserved. Customize behavior through those product-owned surfaces; changes
inside canonical-owned files will be proposed for replacement in the next sync
PR.

