# Copy to harness.config.sh and customize for each repository.
# Do not put secrets in this file.

HARNESS_CONFIGURED="${HARNESS_CONFIGURED:-0}"
HARNESS_SOURCE_DIRS="src|app|lib|workers"
HARNESS_INSTALL_CMD=""
HARNESS_TYPECHECK_CMD=""
HARNESS_LINT_CMD=""
HARNESS_TEST_CMD="bash bin/harness-health.sh && bash bin/test-guards.sh && python3 bin/test-upload-hook.py && python3 bin/test-optimizer-gate.py"
HARNESS_BUILD_CMD=""
HARNESS_FALLOW_CMD="npx --no-install fallow audit --format json --quiet"

# Cloudflare production settings. Production gate fails closed until populated.
HARNESS_WRANGLER_CMD="npx wrangler"
HARNESS_WRANGLER_CHECK_CMD="npx wrangler check startup"
HARNESS_WORKER_NAME=""
HARNESS_STAGING_ENV="staging"
HARNESS_PRODUCTION_ENV="production"
HARNESS_HEALTH_URL=""
HARNESS_PREVIEW_HEALTH_URL=""
HARNESS_HEALTH_PATH="/health"
HARNESS_CANARY_PERCENTAGES="1 10 100"
HARNESS_CANARY_SECONDS="60"

