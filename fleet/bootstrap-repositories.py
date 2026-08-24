#!/usr/bin/env python3
"""Install the per-repository sync workflow across the configured GitHub fleet."""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


API = "https://api.github.com"
OWNERS = {"DuncanAdams-neural", "NeuralIdentity"}
WORKFLOW_PATH = ".github/workflows/agent-harness-sync.yml"
BOOTSTRAP_BRANCH = "chore/enable-agent-harness-sync"


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
    try:
        with urllib.request.urlopen(call, timeout=60) as response:
            if response.status == 204:
                return None
            return json.load(response)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        if error.code == 404:
            return None
        raise RuntimeError(f"GitHub API {method} {path}: {error.code} {body}") from error


def repositories(token: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {"visibility": "all", "affiliation": "owner,organization_member", "per_page": 100, "page": page}
        )
        batch = request(token, "GET", f"/user/repos?{query}")
        if not batch:
            break
        results.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return results


def install_workflow(
    token: str, repository: dict[str, Any], workflow: str
) -> str:
    full_name = repository["full_name"]
    owner, name = full_name.split("/", 1)
    if full_name == "DuncanAdams-neural/agent-harness":
        return "skip canonical"
    if owner not in OWNERS:
        return "skip owner"
    if repository.get("archived") or repository.get("disabled") or repository.get("fork"):
        return "skip inactive"
    if not repository.get("permissions", {}).get("push"):
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


def main() -> int:
    token = os.environ.get("FLEET_TOKEN", "")
    if not token:
        print(
            "::warning title=Fleet bootstrap disabled::FLEET_TOKEN is not "
            "configured; no repositories were changed."
        )
        if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
            Path(summary_path).write_text(
                "## Fleet bootstrap skipped\n"
                "Configure the repository secret `FLEET_TOKEN` to enable "
                "cross-repository sync.\n",
                encoding="utf-8",
            )
        return 0

    workflow_path = Path(__file__).with_name("agent-harness-sync.yml")
    workflow = workflow_path.read_text(encoding="utf-8")
    counts: dict[str, int] = {}
    for repository in repositories(token):
        status = install_workflow(token, repository, workflow)
        counts[status] = counts.get(status, 0) + 1
        if status.startswith("skip"):
            print(f"::warning title=Fleet skip::{repository['full_name']}: {status}")
        elif status in {"pr-created", "pr-updated"}:
            print(f"{status}: {repository['full_name']}")
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

