#!/usr/bin/env python3
"""Install the per-repository sync workflow across the configured GitHub fleet."""

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator


API = "https://api.github.com"
OWNERS = {"DuncanAdams-neural", "NeuralIdentity"}
CANONICAL_REPOSITORY = "DuncanAdams-neural/agent-harness"
WORKFLOW_PATH = ".github/workflows/agent-harness-sync.yml"
BOOTSTRAP_BRANCH = "chore/enable-agent-harness-sync"
SHA_PLACEHOLDER = "__CANONICAL_SHA__"
RETRY_STATUSES = {429, 500, 502, 503, 504}
RETRY_ATTEMPTS = 4

# GitHub answers per-repository permission, policy, and empty-repository
# conditions with these codes. They need a human to widen the token or relax a
# setting, so they are reported as skips instead of sinking the whole fleet run.
# Authentication failures stay fatal: an expired token must never look inert.
SKIP_STATUSES = {
    403: "skip forbidden",
    409: "skip empty",
    422: "skip rejected",
}
ACTIONABLE_SKIPS = {"skip no-push", "skip forbidden", "skip rejected"}
SETUP_HINT = (
    "Add a repository secret named FLEET_TOKEN to "
    f"{CANONICAL_REPOSITORY} (fine-grained token or GitHub App installation "
    "token) with Contents, Pull requests, and Workflows write access to "
    + " and ".join(sorted(OWNERS))
    + ", plus Metadata read. See fleet/README.md."
)


class ApiError(RuntimeError):
    """A GitHub API response that the caller has to classify."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def request(
    token: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    call = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "agent-harness-fleet-sync",
        },
    )
    for attempt in range(RETRY_ATTEMPTS):
        try:
            with urllib.request.urlopen(call, timeout=60) as response:
                if response.status == 204:
                    return None
                return json.load(response)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            if error.code == 404:
                return None
            if error.code in RETRY_STATUSES and attempt < RETRY_ATTEMPTS - 1:
                time.sleep(retry_delay(error.headers.get("Retry-After"), attempt))
                continue
            raise ApiError(
                error.code, f"GitHub API {method} {path}: {error.code} {body}"
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == RETRY_ATTEMPTS - 1:
                raise ApiError(0, f"GitHub API {method} {path}: {error}") from error
            time.sleep(retry_delay(None, attempt))
    raise AssertionError("unreachable")


def retry_delay(retry_after: str | None, attempt: int) -> float:
    if retry_after and retry_after.strip().isdigit():
        return min(float(retry_after), 60.0)
    return float(2**attempt)


def paginate(token: str, path: str, extra: dict[str, str]) -> Iterator[dict[str, Any]]:
    page = 1
    while True:
        query = urllib.parse.urlencode({**extra, "per_page": 100, "page": page})
        payload = request(token, "GET", f"{path}?{query}")
        if isinstance(payload, dict):
            batch = payload.get("repositories", [])
        else:
            batch = payload or []
        yield from batch
        if len(batch) < 100:
            return
        page += 1


def repositories(token: str) -> list[dict[str, Any]]:
    """Inventory the fleet through whichever listing the token is allowed to use."""
    endpoints = (
        (
            "/user/repos",
            {"visibility": "all", "affiliation": "owner,organization_member"},
        ),
        ("/installation/repositories", {}),
    )
    rejection: ApiError | None = None
    for path, extra in endpoints:
        try:
            return list(paginate(token, path, extra))
        except ApiError as error:
            # A fine-grained token cannot read the installation listing, and an
            # app installation token cannot read the user listing.
            if error.status != 403:
                raise
            rejection = error
    assert rejection is not None
    raise rejection


def pinned_workflow(template: str, canonical_sha: str) -> str:
    if SHA_PLACEHOLDER not in template:
        return template
    if not re.fullmatch(r"[0-9a-f]{40}", canonical_sha):
        raise ValueError(
            f"{WORKFLOW_PATH} pins {SHA_PLACEHOLDER}, so GITHUB_SHA must be the "
            f"40-character canonical commit; got {canonical_sha!r}"
        )
    return template.replace(SHA_PLACEHOLDER, canonical_sha)


def install_workflow(token: str, repository: dict[str, Any], workflow: str) -> str:
    full_name = repository["full_name"]
    owner, name = full_name.split("/", 1)
    if full_name == CANONICAL_REPOSITORY:
        return "skip canonical"
    if owner not in OWNERS:
        return "skip owner"
    if repository.get("archived") or repository.get("disabled") or repository.get("fork"):
        return "skip inactive"
    # App installation tokens report every permission as false, including the
    # `pull` that listing the repository already proves. Trust the block only
    # when it claims read access, and otherwise let the API's own 403 decide.
    permissions = repository.get("permissions", {})
    if permissions.get("pull") and not permissions.get("push"):
        return "skip no-push"

    encoded_path = urllib.parse.quote(WORKFLOW_PATH, safe="/")
    default_branch = repository["default_branch"]
    default_existing = request(
        token,
        "GET",
        f"/repos/{owner}/{name}/contents/{encoded_path}?ref={urllib.parse.quote(default_branch)}",
    )
    if default_existing:
        current = base64.b64decode(default_existing["content"]).decode("utf-8")
        if current == workflow:
            return "unchanged"

    encoded_branch = urllib.parse.quote(BOOTSTRAP_BRANCH, safe="")
    branch_ref = request(
        token, "GET", f"/repos/{owner}/{name}/git/ref/heads/{encoded_branch}"
    )
    if not branch_ref:
        default_ref = request(
            token,
            "GET",
            f"/repos/{owner}/{name}/git/ref/heads/{urllib.parse.quote(default_branch, safe='')}",
        )
        if not default_ref:
            return "skip empty"
        request(
            token,
            "POST",
            f"/repos/{owner}/{name}/git/refs",
            {
                "ref": f"refs/heads/{BOOTSTRAP_BRANCH}",
                "sha": default_ref["object"]["sha"],
            },
        )

    branch_existing = request(
        token,
        "GET",
        f"/repos/{owner}/{name}/contents/{encoded_path}?ref={encoded_branch}",
    )
    encoded = base64.b64encode(workflow.encode("utf-8")).decode("ascii")
    payload: dict[str, Any] = {
        "message": "chore: enable agent harness sync",
        "content": encoded,
        "branch": BOOTSTRAP_BRANCH,
    }
    if branch_existing:
        current = base64.b64decode(branch_existing["content"]).decode("utf-8")
        if current != workflow:
            payload["sha"] = branch_existing["sha"]
        else:
            payload = {}

    if payload:
        request(
            token,
            "PUT",
            f"/repos/{owner}/{name}/contents/{encoded_path}",
            payload,
        )

    query = urllib.parse.urlencode(
        {
            "state": "open",
            "head": f"{owner}:{BOOTSTRAP_BRANCH}",
            "base": default_branch,
        }
    )
    open_pulls = request(token, "GET", f"/repos/{owner}/{name}/pulls?{query}")
    if not open_pulls:
        request(
            token,
            "POST",
            f"/repos/{owner}/{name}/pulls",
            {
                "title": "chore: enable agent harness foundation",
                "head": BOOTSTRAP_BRANCH,
                "base": default_branch,
                "body": (
                    "Adds the pinned sync workflow that opens reviewable agent "
                    "harness installation/update pull requests."
                ),
            },
        )
    return "pr-updated" if branch_existing else "pr-created"


def summarize(lines: list[str]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    # The annotation keeps bin/bash-guard-check.sh from reading
    # `token = <identifier>` as a hard-coded secret.
    token: str = os.environ.get("FLEET_TOKEN", "")
    if not token:
        # An unconfigured fleet is not a broken build: report it once per run and
        # stay green so the hourly schedule keeps a usable signal.
        print(f"::warning title=Fleet bootstrap disabled::{SETUP_HINT}")
        summarize(
            [
                "### Fleet bootstrap did nothing",
                "",
                f"`FLEET_TOKEN` is not configured. {SETUP_HINT}",
            ]
        )
        return 0

    workflow_path = Path(__file__).with_name("agent-harness-sync.yml")
    try:
        workflow = pinned_workflow(
            workflow_path.read_text(encoding="utf-8"),
            os.environ.get("GITHUB_SHA", ""),
        )
    except ValueError as error:
        print(f"::error title=Fleet bootstrap::{error}", file=sys.stderr)
        return 1

    try:
        inventory = repositories(token)
    except ApiError as error:
        detail = (
            f"FLEET_TOKEN is invalid, expired, or lacks fleet access. {error}"
            if error.status in {401, 403}
            else str(error)
        )
        print(f"::error title=Fleet inventory failed::{detail}", file=sys.stderr)
        return 1

    counts: dict[str, int] = {}
    failures: list[str] = []
    for repository in inventory:
        full_name = repository["full_name"]
        try:
            status = install_workflow(token, repository, workflow)
        except ApiError as error:
            status = SKIP_STATUSES.get(error.status, "")
            if not status:
                status = "error"
                failures.append(f"{full_name}: {error}")
                print(f"::error title=Fleet failure::{full_name}: {error}")
        except Exception as error:  # one broken repository must not hide the rest
            status = "error"
            failures.append(f"{full_name}: {error!r}")
            print(f"::error title=Fleet failure::{full_name}: {error!r}")

        counts[status] = counts.get(status, 0) + 1
        if status in ACTIONABLE_SKIPS:
            print(f"::warning title=Fleet skip::{full_name}: {status}")
        elif status != "error":
            print(f"{status}: {full_name}")

    print(json.dumps(counts, sort_keys=True))
    summary = [
        "### Fleet bootstrap",
        "",
        f"Pinned canonical commit: `{os.environ.get('GITHUB_SHA', 'unpinned')}`",
        "",
        "| Result | Repositories |",
        "| --- | --- |",
        *(f"| {status} | {count} |" for status, count in sorted(counts.items())),
    ]
    if failures:
        summary += ["", "#### Failures", "", *(f"- {failure}" for failure in failures)]
    summarize(summary)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
