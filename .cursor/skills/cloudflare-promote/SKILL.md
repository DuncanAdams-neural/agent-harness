---
name: cloudflare-promote
description: Use when a green release candidate must be promoted to Cloudflare production.
user-invocable: true
tier: rigid
kind: verification
---

# Cloudflare Promote

Use Wrangler v4.x and retrieve current Cloudflare documentation before changing traffic.

## Iron Law

```
NO PRODUCTION TRAFFIC WITHOUT A VERIFIED VERSION AND A ROLLBACK ID
```

Never use `wrangler deploy` as this harness's production path.

## Promotion

1. Run `bin/pre-deploy-gate.sh production`; require GO. Read `harness.config.sh` and append `--env "$HARNESS_PRODUCTION_ENV"` to every Wrangler command when that value is non-empty.
2. Record the active stable version from `npx wrangler deployments status --name "$HARNESS_WORKER_NAME" --json`. `versions list` is upload history, not production state.
3. Upload without traffic: `npx wrangler versions upload --preview-alias staging --name "$HARNESS_WORKER_NAME"`.
4. Record the new version ID and preview URL printed by Wrangler in `docs/handoff.md`.
5. Smoke `HARNESS_PREVIEW_HEALTH_URL` or the returned preview URL plus `HARNESS_HEALTH_PATH`. Check status and critical read-only journeys.
6. If preview URLs are unavailable, add the new version to the current deployment at 0%, then smoke it with `curl "$HARNESS_HEALTH_URL" -H 'Cloudflare-Workers-Version-Overrides: worker-name="version-id"'`. Version overrides only work for a version in the current deployment. Do not expose unverified traffic.
7. Canary non-interactively with both IDs: `npx wrangler versions deploy NEW@1% OLD@99% --name "$HARNESS_WORKER_NAME" -y`.
8. Observe for `HARNESS_CANARY_SECONDS`; check health, 5xx, exceptions, binding/auth errors, and critical responses.
9. Repeat at configured percentages (default 10%, then 100%) only while healthy.
10. Recheck production health and record the deployment, stable ID, and rollback ID.

Rollback immediately on a failed health check, 5xx increase, unhandled exception, missing binding, auth/secret failure, or corrupt/empty critical response. Restore the previous version with `wrangler versions deploy OLD@100% --name "$HARNESS_WORKER_NAME" -y` or `wrangler rollback`, then verify health.

## Hard stops

- Missing token, account, worker name, health URL, or previous stable version.
- Red/stale gate evidence.
- `wrangler delete`, route/DNS removal, secret deletion, or destructive migration.
- First Worker upload without an existing rollback target requires explicit human approval.

## Common rationalizations

Read `rationalizations.md` before moving beyond each percentage.

## Self-review

- [ ] Gate is green for current `HEAD`.
- [ ] Preview/version was tested before traffic.
- [ ] Previous and new version IDs are recorded.
- [ ] Each percentage passed health and observability checks.
- [ ] Production health passed or rollback completed.

