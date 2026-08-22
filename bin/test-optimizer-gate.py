#!/usr/bin/env python3
"""Integration checks for the language-aware optimizer gate."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(root: Path, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if environment:
        merged.update(environment)
    return subprocess.run(
        ["bash", "bin/optimizer-gate.sh"],
        cwd=root,
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )


def git(root: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=root, check=True, capture_output=True)


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary)
        (project / "bin").mkdir()
        shutil.copy2(ROOT / "bin" / "optimizer-gate.sh", project / "bin")
        fake = project / "fake-fallow.sh"
        fake.write_text(
            "#!/usr/bin/env bash\n"
            "if [[ -n \"${EXPECT_FALLOW_BASE:-}\" && \" $* \" != *\" --base $EXPECT_FALLOW_BASE \"* ]]; then\n"
            "  printf '%s\\n' '{\"error\":true,\"exit_code\":2}'\n"
            "  exit 2\n"
            "fi\n"
            "if [[ -n \"${FAKE_FALLOW_JSON:-}\" ]]; then\n"
            "  printf '%s\\n' \"$FAKE_FALLOW_JSON\"\n"
            "else\n"
            "  printf '%s\\n' '{\"kind\":\"audit\",\"verdict\":\"pass\"}'\n"
            "fi\n"
            "exit \"${FAKE_FALLOW_EXIT:-0}\"\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        (project / "harness.config.sh").write_text(
            'HARNESS_FALLOW_ENABLED="1"\n'
            f'HARNESS_FALLOW_CMD="{fake}"\n',
            encoding="utf-8",
        )

        git(project, "init", "-q")
        git(project, "config", "user.name", "Harness Test")
        git(project, "config", "user.email", "harness@example.invalid")
        (project / "README.md").write_text("No JS yet.\n", encoding="utf-8")
        git(project, "add", ".")
        git(project, "commit", "-qm", "base")

        skipped = run(project)
        assert skipped.returncode == 0
        assert "no tracked JS/TS-family" in skipped.stdout

        (project / "index.mts").write_text("export const value = 1;\n", encoding="utf-8")
        git(project, "add", "index.mts")
        git(project, "commit", "-qm", "add TypeScript")

        without_manifest = run(project, {"FAKE_FALLOW_EXIT": "0"})
        assert without_manifest.returncode == 0
        assert "PASS: Fallow" in without_manifest.stdout

        (project / "package.json").write_text('{"name":"fixture"}\n', encoding="utf-8")
        git(project, "add", "package.json")
        git(project, "commit", "-qm", "add package manifest")

        passed = run(project, {"FAKE_FALLOW_EXIT": "0"})
        assert passed.returncode == 0
        assert "PASS: Fallow" in passed.stdout

        based = run(
            project,
            {
                "EXPECT_FALLOW_BASE": "main",
                "HARNESS_BASE_REF": "main",
                "HARNESS_CI": "1",
            },
        )
        assert based.returncode == 0
        assert "--base main" in based.stdout

        warned = run(
            project,
            {
                "FAKE_FALLOW_EXIT": "0",
                "FAKE_FALLOW_JSON": '{"kind":"audit","verdict":"warn"}',
            },
        )
        assert warned.returncode == 1
        assert "warn verdict" in warned.stderr

        findings = run(project, {"FAKE_FALLOW_EXIT": "1"})
        assert findings.returncode == 1
        assert "introduced quality issues" in findings.stderr

        analyzer_error = run(project, {"FAKE_FALLOW_EXIT": "2"})
        assert analyzer_error.returncode == 1
        assert "configuration/runtime error" in analyzer_error.stderr

        malformed = run(
            project,
            {"FAKE_FALLOW_EXIT": "0", "FAKE_FALLOW_JSON": "not-json"},
        )
        assert malformed.returncode == 1
        assert "valid JSON" in malformed.stderr

        (project / "harness.config.sh").write_text(
            'HARNESS_FALLOW_CMD=""\n', encoding="utf-8"
        )
        missing_command = run(project)
        assert missing_command.returncode == 1
        assert "HARNESS_FALLOW_CMD is required" in missing_command.stderr

    print(
        "PASS: optimizer skip, pass, base, warn, findings, error, malformed, "
        "and missing-command paths."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

