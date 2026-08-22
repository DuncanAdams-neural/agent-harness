#!/usr/bin/env python3
"""Offline tests for canonical-checkout application and target-file safety."""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def apply_harness(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "fleet" / "apply-harness.py"),
            "--source",
            str(ROOT),
            "--target",
            str(target),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary) / "target"
        (target / ".cursor").mkdir(parents=True)
        (target / "AGENTS.md").write_text(
            "# Project instructions\n\nKeep this.\n", encoding="utf-8"
        )
        (target / ".cursor" / "hooks.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "hooks": {
                        "beforeSubmitPrompt": [
                            {"command": ".cursor/hooks/project-hook.py"}
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
        (target / ".cursor" / "environment.json").write_text(
            '{"name":"project-owned","install":"npm ci"}\n', encoding="utf-8"
        )
        (target / "package.json").write_text(
            '{"scripts":{"test":"vitest run","lint":"eslint .","build":"vite build"}}\n',
            encoding="utf-8",
        )
        (target / "package-lock.json").write_text("{}\n", encoding="utf-8")

        result = apply_harness(target)
        assert result.returncode == 0, result.stderr

        agents = (target / "AGENTS.md").read_text(encoding="utf-8")
        assert "Keep this." in agents
        assert "agent-harness:start" in agents
        assert (target / "AGENT-HARNESS.md").is_file()
        assert (target / ".cursor" / "skills" / "agent-harness" / "SKILL.md").is_file()
        assert (target / ".agents" / "skills" / "ponytail" / "SKILL.md").is_file()
        assert (target / "bin" / "optimizer-gate.sh").is_file()

        environment = json.loads(
            (target / ".cursor" / "environment.json").read_text(encoding="utf-8")
        )
        assert environment["name"] == "project-owned"

        hooks = json.loads(
            (target / ".cursor" / "hooks.json").read_text(encoding="utf-8")
        )
        commands = {entry["command"] for entry in hooks["hooks"]["beforeSubmitPrompt"]}
        assert commands == {
            ".cursor/hooks/project-hook.py",
            ".cursor/hooks/markitdown-before-submit.py",
        }

        config = (target / "harness.config.sh").read_text(encoding="utf-8")
        assert 'HARNESS_CONFIGURED="0"' in config
        assert 'HARNESS_TEST_CMD="npm run test"' in config
        assert "npx --no-install fallow" in config

        subprocess.run(
            [sys.executable, "bin/test-skill-registry.py"],
            cwd=target,
            check=True,
            capture_output=True,
            text=True,
        )

        before = tree_hash(target)
        assert apply_harness(target).returncode == 0
        assert tree_hash(target) == before

        incomplete = Path(temporary) / "incomplete"
        (incomplete / ".cursor").mkdir(parents=True)
        (incomplete / "AGENTS.md").write_text("stub\n", encoding="utf-8")
        broken = subprocess.run(
            [
                sys.executable,
                str(ROOT / "fleet" / "apply-harness.py"),
                "--source",
                str(incomplete),
                "--target",
                str(Path(temporary) / "unused"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert broken.returncode != 0
        assert "incomplete" in broken.stderr

    print("PASS: canonical apply, merge, config, idempotence, and fail-closed source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
