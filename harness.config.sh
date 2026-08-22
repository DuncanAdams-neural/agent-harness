# Tracked, non-secret configuration for this harness template.
# Product repositories replace these commands with their real checks.

HARNESS_CONFIGURED="1"
HARNESS_SOURCE_DIRS="src|app|lib|workers"
HARNESS_INSTALL_CMD=""
HARNESS_TYPECHECK_CMD=""
HARNESS_LINT_CMD=""
HARNESS_TEST_CMD="bash bin/harness-health.sh && bash bin/test-guards.sh && python3 bin/test-upload-hook.py && python3 bin/test-optimizer-gate.py"
HARNESS_BUILD_CMD=""
HARNESS_FALLOW_CMD="npx --no-install fallow audit --format json --quiet"

HARNESS_WRANGLER_CMD="npx wrangler"
HARNESS_WRANGLER_CHECK_CMD="npx wrangler check startup"
HARNESS_WORKER_NAME=""
HARNESS_STAGING_ENV="staging"
HARNESS_PRODUCTION_ENV=""
HARNESS_HEALTH_URL=""
HARNESS_PREVIEW_HEALTH_URL=""
HARNESS_HEALTH_PATH="/health"
HARNESS_CANARY_PERCENTAGES="1 10 100"
HARNESS_CANARY_SECONDS="60"

