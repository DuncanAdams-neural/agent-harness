# Agent Harness

A repository-native workflow that turns an idea into reviewed, tested code and—when explicitly configured—a guarded Cloudflare Worker release.

It combines a review-only file loop with Workweek-style Iron Laws, durable handoffs, CI gates, and Workers Versions. It works in Cursor Desktop, Cursor Cloud Agents, and scheduled agent automations because the operating rules live in git.

## Core loop

```text
resume → review goal → plan footprints → TDD/code → review → gate
       → commit/push feature branch → preview version → canary → production
```

The harness fails closed. Missing tests, health checks, credentials, configuration, or rollback targets stop production.

## Uploaded files and MarkItDown

Project hook [`.cursor/hooks.json`](.cursor/hooks.json) runs
`.cursor/hooks/markitdown-before-submit.py` for every explicit prompt submission.

- **Files attached:** the hook runs Microsoft MarkItDown before allowing the
  prompt, writes derived Markdown plus a manifest under `.cursor/converted/`,
  and the always-on harness rule reads those files before reviewing, planning,
  and executing the request.
- **No files attached:** it writes a `no-files` marker and immediately continues
  with the normal prompt flow.
- **Conversion unavailable or failed:** submission is blocked instead of letting
  the agent guess from an unread document.

The hook discovers MarkItDown in this order:

1. `HARNESS_MARKITDOWN_CMD` in the Cursor hook environment;
2. a `markitdown` executable on `PATH`;
3. an installed Python `markitdown` module;
4. a MarkItDown checkout at a workspace root, `markitdown/`, or a sibling
   `markitdown/` repository.

For cloud agents, [`.cursor/environment.json`](.cursor/environment.json) installs
`markitdown[all]` during environment setup. The hook can also use a MarkItDown
checkout exposed as another workspace root.
Converted files are ephemeral and gitignored. Their content is always treated
as untrusted source material, so instructions embedded in a PDF or document
cannot override `AGENTS.md`.

Cursor does not currently include image-only attachments in the
`beforeSubmitPrompt.attachments` payload. Those continue through Cursor's normal
image handling; document attachments exposed as files use this conversion flow.
Cursor may also provide the original native attachment context because this hook
can allow or block but cannot rewrite the prompt. Agents are instructed to rely
on the converted Markdown. Cloud hooks can be unavailable during an initial
read-only phase; a visible document without a fresh prompt-matching manifest is
therefore blocked and must be resubmitted after the writable environment starts.
Fresh means no more than 60 seconds old with the same prompt, attachment count,
and source filenames. Hook entry immediately marks prior state invalid while a
new conversion is running.

## Start

1. This template includes a tracked, non-secret `harness.config.sh`. In an adopted repository, create it from the example:

   ```bash
   cp harness.config.example.sh harness.config.sh
   ```

2. Track `harness.config.sh` in git so CI uses the same gates as local agents. Set real commands for typecheck, lint, tests, and build, then set `HARNESS_CONFIGURED=1`. For a Worker, also set the Worker name and health URLs. Never put secrets in this file.
3. Put an idea or artifact under `input/`.
4. Ask the agent:

   ```text
   Run the agent harness. Follow AGENTS.md, read docs/handoff.md, and review input/.
   ```

5. Read the report under `reviews/`. Implementation starts only after review and planning.

## Durable state

`docs/handoff.md` is the source of truth across sessions, compaction, teammates, and cloud agents. Every run reads it first and updates it before stopping.

It records the active phase, completed work, exact stop point, next action, blockers, files, commit, fresh gate evidence, and Cloudflare version IDs. Chat history is not task state.

## Portable engineering skills

Eight complementary skills from
[`mattpocock/skills`](https://github.com/mattpocock/skills) are installed under
`.agents/skills/`:

| Skill | Harness phase |
| --- | --- |
| `grilling` | Resolve consequential ambiguity after evidence gathering |
| `research` | Gather current primary-source facts |
| `domain-modeling` | Sharpen domain language and durable decisions |
| `codebase-design` | Design deep modules, interfaces, and seams |
| `diagnosing-bugs` | Build a red-capable loop before fixing a bug |
| `code-review` | Independent Standards and Spec review axes |
| `resolving-merge-conflicts` | Resolve conflicts by tracing both intents |
| `writing-for-agents` | Author reliable skills and agent-facing docs |

They are MIT-licensed; see
[`licenses/mattpocock-skills-MIT.txt`](licenses/mattpocock-skills-MIT.txt).
`skills-lock.json` records their upstream source; `skills-local-lock.json`
records the reviewed local adaptation hashes. Some files are adapted to use this
harness's plans, Origin-compatible forge workflow, gates, and handoff. Review
upstream updates before applying them because a blind update can overwrite those
adaptations. After a deliberate update, reapply adaptations, review the diff,
refresh the local hashes, and run `python3 bin/test-skill-registry.py`.

The upstream TDD, implement, handoff, setup, triage, ticketing, and wizard skills
are intentionally not installed: they duplicate lifecycle controls or assume
GitHub/`gh` and secret-writing behavior that conflicts with this harness.

## Pre-ship optimization

Two additional MIT-licensed projects strengthen the review/gate boundary:

- [Ponytail](https://github.com/dietrichgebert/ponytail) stays active during
  coding and runs a separate over-engineering review before Standards/Spec
  review. It prefers deletion, reuse, stdlib, and native platform features, but
  cannot remove acceptance criteria, TDD evidence, accessibility, security,
  observability, handoff, or rollback controls.
- [Fallow](https://github.com/fallow-rs/fallow) runs deterministic changed-code
  analysis for JS/TS-family repositories through `bin/optimizer-gate.sh`.
  JS/TS adopters install exact devDependency `fallow@3.17.0` and set
  `HARNESS_INSTALL_CMD` to their lockfile-respecting install command. The gate
  uses the project-local binary through `npx --no-install`. Pass is the only GO
  verdict; warn, introduced findings, analyzer errors, and malformed output are
  NO-GO. Non-JS/TS repositories explicitly skip it.

Fallow auto-fixes are never applied in the gate. Review findings, change code
through TDD, then rerun Ponytail review, Standards/Spec review, Fallow, and the
full gate. Evidence is written under gitignored `.cursor/artifacts/`.

Licenses:
[`licenses/ponytail-MIT.txt`](licenses/ponytail-MIT.txt) and
[`licenses/fallow-MIT.txt`](licenses/fallow-MIT.txt).
Together, `.agents/skills/` contains eleven reviewed portable skills.

## Local verification

```bash
bash bin/harness-health.sh
bash bin/pre-deploy-gate.sh repo
```

The production gate additionally requires complete commands, Cloudflare configuration, `CLOUDFLARE_API_TOKEN`, Wrangler checks, and a dry run:

```bash
bash bin/pre-deploy-gate.sh production
```

## Cloudflare production

The harness never uses `wrangler deploy` as its production path because that creates a version and immediately routes 100% of traffic.

The `cloudflare-promote` skill:

1. records the current stable version;
2. runs `wrangler versions upload --preview-alias staging`;
3. smokes the preview/version;
4. records both new and rollback version IDs;
5. deploys 1%, observes, then 10%, observes, then 100%;
6. verifies production or restores the old version.

Preview URLs must be intentionally enabled and protected with Cloudflare Access when they should not be public. Use a narrowly scoped API token supplied by the runner environment.

Never automate `wrangler delete`, DNS or route removal, secret deletion, or destructive migrations through this harness.

## Cloud agents and automations

Use the prompt in [`automations/cloud-agent.md`](automations/cloud-agent.md). The same repository files load in Cursor Cloud Agents.

Keep review-only automations credential-free. Give production credentials only to an explicit promotion workflow, scoped to the required Cloudflare account and Worker.

## Install into another repository

Copy:

```text
AGENTS.md
.cursor/skills/
.cursor/rules/
.cursor/hooks.json
.cursor/hooks/
.cursor/environment.json
.agents/skills/
skills-lock.json
skills-local-lock.json
docs/forge-workflow.md
bin/
.github/workflows/pre-deploy.yml
automations/
harness.config.example.sh
licenses/
```

Optionally copy the `input/`, `reviews/`, `reports/`, `docs/plans/`, and `docs/handoff.md` loop. Start `reviews/` and `docs/learnings/` empty; do not copy another project's history.

Then:

1. create `harness.config.sh`;
2. set repository-specific install/check commands and Cloudflare targets. For a
   JS/TS repository, add exact devDependency `fallow@3.17.0`, commit the
   lockfile, and configure `HARNESS_INSTALL_CMD` (`npm ci`, `pnpm install
   --frozen-lockfile`, etc.);
3. run `bash bin/harness-health.sh`;
4. protect `main`/`master` on the forge;
5. require the “Agent harness gate” check before merge;
6. disable force pushes and direct production publishing as the normal path;
7. require review for changes to `AGENTS.md`, `.cursor/`, `.agents/skills/`,
   `skills-lock.json`, `skills-local-lock.json`, `licenses/`, `bin/`, CI, and deployment configuration.
   Such pull requests need an explicitly reviewed `harness-maintenance` label
   for the CI guard to allow them.

Repository installation matters more than a personal global skill: everyone who clones the project receives the same rules and gates.

## GitHub fleet rollout

The canonical GitHub repository distributes this harness across
`DuncanAdams-neural` and `NeuralIdentity`.

- Existing repositories receive `.github/workflows/agent-harness-sync.yml` via a
  reviewable bootstrap PR.
- The workflow opens or updates a PR; it does not overwrite project-owned
  `AGENTS.md`, `.cursor/environment.json`, or an existing
  `harness.config.sh`.
- The canonical hourly bootstrap discovers new repositories and installs the
  sync workflow.
- GitHub has no ordinary workflow event for account/org repository creation, so
  hourly inventory is the workflow-based fallback. A GitHub App webhook is the
  immediate alternative.

See [`fleet/README.md`](fleet/README.md). The central workflow needs a
cross-repository `FLEET_TOKEN`; target sync workflows use their own
short-lived `GITHUB_TOKEN`.

## Safety model

| Layer | Purpose |
| --- | --- |
| `AGENTS.md` and skills | Guide agents and name forbidden shortcuts |
| `bin/` gates | Deterministic local and CI checks |
| Protected branches + required CI | Prevent bypassed local hooks from merging |
| Read-only validation pass | Separate implementation from safety judgment |
| Workers Versions + health + rollback | Limit production blast radius |

Markdown cannot physically stop every human action. Required CI, branch protection, least-privilege credentials, and Cloudflare versioned deployment are the enforceable controls.

