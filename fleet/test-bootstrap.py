#!/usr/bin/env python3
"""Offline tests for fleet bootstrap eligibility, SHA pinning, and failure isolation."""

import base64
import importlib.util
import io
import json
import os
import re
import tempfile
import urllib.parse
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SHA = "a" * 40


def load_bootstrap() -> Any:
    path = ROOT / "fleet" / "bootstrap-repositories.py"
    spec = importlib.util.spec_from_file_location("fleet_bootstrap", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeGitHub:
    """Minimal in-memory GitHub for the endpoints the bootstrap touches."""

    def __init__(self, module: Any, repositories: list[dict[str, Any]]) -> None:
        self.module = module
        self.repositories = repositories
        self.refs: dict[tuple[str, str], str] = {}
        self.contents: dict[tuple[str, str], str] = {}
        self.pulls: list[dict[str, str]] = []
        self.status_overrides: dict[str, int] = {}

    def __call__(
        self, token: str, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> Any:
        assert token, "the bootstrap must not call the API without a token"
        for prefix, status in self.status_overrides.items():
            if path.startswith(prefix):
                raise self.module.ApiError(status, f"forced {status} for {path}")
        return self.route(method, path, payload)

    def route(self, method: str, path: str, payload: dict[str, Any] | None) -> Any:
        if path.startswith("/user/repos"):
            return self.repositories
        if path.startswith("/installation/repositories"):
            return {"repositories": self.repositories}

        match = re.match(r"^/repos/([^/]+/[^/]+)/(.+)$", path)
        assert match, f"unrouted path: {path}"
        full_name, rest = match.group(1), match.group(2)

        if rest.startswith("contents/"):
            if method == "GET":
                content = self.contents.get((full_name, query(rest, "ref")))
                if content is None:
                    return None
                return {
                    "content": base64.b64encode(content.encode()).decode(),
                    "sha": "blob-sha",
                }
            assert payload is not None
            self.contents[(full_name, payload["branch"])] = base64.b64decode(
                payload["content"]
            ).decode()
            return {"commit": {"sha": "commit-sha"}}

        if rest.startswith("git/ref/heads/"):
            branch = urllib.parse.unquote(rest.split("git/ref/heads/", 1)[1])
            sha = self.refs.get((full_name, branch))
            return {"object": {"sha": sha}} if sha else None

        if rest == "git/refs":
            assert payload is not None
            self.refs[(full_name, payload["ref"].split("refs/heads/", 1)[1])] = payload[
                "sha"
            ]
            return {"ref": payload["ref"]}

        if rest.startswith("pulls"):
            if method == "GET":
                head = query(rest, "head")
                return [pull for pull in self.pulls if pull["head"] == head]
            assert payload is not None
            owner = full_name.split("/", 1)[0]
            self.pulls.append(
                {"repository": full_name, "head": f"{owner}:{payload['head']}"}
            )
            return {"number": len(self.pulls)}

        raise AssertionError(f"unrouted path: {path}")


def query(rest: str, key: str) -> str:
    match = re.search(rf"[?&]{key}=([^&]+)", rest)
    return urllib.parse.unquote(match.group(1)) if match else ""


def repository(
    full_name: str,
    *,
    push: bool = True,
    archived: bool = False,
    fork: bool = False,
) -> dict[str, Any]:
    return {
        "full_name": full_name,
        "default_branch": "main",
        "archived": archived,
        "fork": fork,
        "permissions": {"push": push},
    }


def run_main(module: Any, environment: dict[str, str]) -> tuple[int, str, str]:
    """Run the entry point with a scratch step summary and restore the environment."""
    with tempfile.TemporaryDirectory() as temporary:
        summary = Path(temporary) / "summary.md"
        saved = dict(os.environ)
        os.environ.update({**environment, "GITHUB_STEP_SUMMARY": str(summary)})
        try:
            output = io.StringIO()
            with redirect_stdout(output):
                code = module.main()
            written = summary.read_text(encoding="utf-8") if summary.exists() else ""
            return code, output.getvalue(), written
        finally:
            os.environ.clear()
            os.environ.update(saved)


def counts_of(output: str) -> dict[str, int]:
    return json.loads(output.strip().splitlines()[-1])


def test_missing_token_is_inert(module: Any) -> None:
    def forbidden(*_arguments: Any, **_keywords: Any) -> Any:
        raise AssertionError("the API must not be called without FLEET_TOKEN")

    module.request = forbidden
    code, output, summary = run_main(module, {"FLEET_TOKEN": ""})
    assert code == 0, "an unconfigured fleet must not fail the hourly schedule"
    assert "::warning title=Fleet bootstrap disabled::" in output
    assert "FLEET_TOKEN" in summary


def test_unresolvable_canonical_commit_fails(module: Any) -> None:
    code, _, _ = run_main(module, {"FLEET_TOKEN": "t", "GITHUB_SHA": "not-a-commit"})
    assert code == 1
    assert module.pinned_workflow("already pinned", "") == "already pinned"


def test_whole_fleet_is_attempted(module: Any, template: str) -> None:
    api = FakeGitHub(
        module,
        [
            repository("DuncanAdams-neural/agent-harness"),
            repository("SomeoneElse/other-repo"),
            repository("NeuralIdentity/archived-repo", archived=True),
            repository("NeuralIdentity/read-only-repo", push=False),
            repository("NeuralIdentity/empty-repo"),
            repository("NeuralIdentity/forbidden-repo"),
            repository("NeuralIdentity/broken-repo"),
            repository("DuncanAdams-neural/fresh-repo"),
            repository("NeuralIdentity/already-synced-repo"),
        ],
    )
    for name in ("forbidden-repo", "broken-repo", "already-synced-repo"):
        api.refs[(f"NeuralIdentity/{name}", "main")] = "base-sha"
    api.refs[("DuncanAdams-neural/fresh-repo", "main")] = "base-sha"
    api.contents[("NeuralIdentity/already-synced-repo", "main")] = template.replace(
        module.SHA_PLACEHOLDER, CANONICAL_SHA
    )
    api.status_overrides = {
        "/repos/NeuralIdentity/forbidden-repo": 403,
        "/repos/NeuralIdentity/broken-repo": 500,
    }
    module.request = api

    code, output, summary = run_main(
        module, {"FLEET_TOKEN": "t", "GITHUB_SHA": CANONICAL_SHA}
    )
    assert counts_of(output) == {
        "skip canonical": 1,
        "skip owner": 1,
        "skip inactive": 1,
        "skip no-push": 1,
        "skip empty": 1,
        "skip forbidden": 1,
        "error": 1,
        "pr-created": 1,
        "unchanged": 1,
    }, output
    assert code == 1, "an unclassified API failure must stay visible"
    assert "NeuralIdentity/broken-repo" in summary
    assert [pull["repository"] for pull in api.pulls] == ["DuncanAdams-neural/fresh-repo"]

    installed = api.contents[("DuncanAdams-neural/fresh-repo", module.BOOTSTRAP_BRANCH)]
    assert module.SHA_PLACEHOLDER not in installed
    assert f'CANONICAL_SHA: "{CANONICAL_SHA}"' in installed


def test_permission_skips_stay_green(module: Any) -> None:
    api = FakeGitHub(module, [repository("NeuralIdentity/forbidden-repo")])
    api.status_overrides = {"/repos/": 403}
    module.request = api
    code, output, _ = run_main(
        module, {"FLEET_TOKEN": "t", "GITHUB_SHA": CANONICAL_SHA}
    )
    assert code == 0
    assert counts_of(output) == {"skip forbidden": 1}


def test_installation_token_listing_fallback(module: Any) -> None:
    class InstallationOnly(FakeGitHub):
        def route(self, method: str, path: str, payload: dict[str, Any] | None) -> Any:
            if path.startswith("/user/repos"):
                raise module.ApiError(403, "resource not accessible by integration")
            return super().route(method, path, payload)

    api = InstallationOnly(module, [repository("DuncanAdams-neural/app-repo")])
    api.refs[("DuncanAdams-neural/app-repo", "main")] = "base-sha"
    module.request = api
    code, output, _ = run_main(
        module, {"FLEET_TOKEN": "t", "GITHUB_SHA": CANONICAL_SHA}
    )
    assert code == 0, output
    assert counts_of(output) == {"pr-created": 1}


def test_rejected_token_is_fatal(module: Any) -> None:
    class Unauthorized(FakeGitHub):
        def route(self, method: str, path: str, payload: dict[str, Any] | None) -> Any:
            raise module.ApiError(403, "bad credentials")

    module.request = Unauthorized(module, [])
    code, _, _ = run_main(module, {"FLEET_TOKEN": "t", "GITHUB_SHA": CANONICAL_SHA})
    assert code == 1, "a token that cannot inventory the fleet must fail loudly"


def main() -> int:
    module = load_bootstrap()
    template = (ROOT / "fleet" / "agent-harness-sync.yml").read_text(encoding="utf-8")
    assert (
        module.SHA_PLACEHOLDER in template
    ), "the distributed sync workflow must keep the placeholder that bootstrap pins"

    test_missing_token_is_inert(module)
    test_unresolvable_canonical_commit_fails(module)
    test_whole_fleet_is_attempted(module, template)
    test_permission_skips_stay_green(module)
    test_installation_token_listing_fallback(module)
    test_rejected_token_is_fatal(module)

    print("PASS: bootstrap token gating, SHA pinning, eligibility, and isolation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
