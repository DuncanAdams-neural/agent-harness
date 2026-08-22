#!/usr/bin/env python3
"""Offline tests for deterministic bundle construction and safe application."""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "distribution" / "manifest.json"


def run(*arguments: str) -> None:
    subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
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
    run("fleet/build-bundle.py")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as temporary:
        temporary_root = Path(temporary)
        bundle = temporary_root / "agent-harness.tar.gz.b64"
        bundle.write_bytes(
            b"".join(
                (ROOT / "distribution" / name).read_bytes()
                for name in manifest["chunks"]
            )
        )
        assert bundle.stat().st_size > 1000
        assert hashlib.sha256(bundle.read_bytes()).hexdigest() == manifest[
            "encoded_sha256"
        ]
        target = temporary_root / "target"
        target.mkdir()
        (target / ".cursor").mkdir()
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
                    }
                }
            ),
            encoding="utf-8"
        )
        (target / ".cursor" / "environment.json").write_text(
            '{"name":"project-owned","install":"npm ci"}\n', encoding="utf-8"
        )
        (target / "package.json").write_text(
            '{"scripts":{"test":"vitest run","lint":"eslint .","build":"vite build"}}\n',
            encoding="utf-8"
        )
        (target / "package-lock.json").write_text("{}\n", encoding="utf-8")

        run(
            "fleet/apply-harness.py",
            "--bundle",
            str(bundle),
            "--target",
            str(target),
        )
        assert "Keep this." in (target / "AGENTS.md").read_text(encoding="utf-8")
        assert "agent-harness:start" in (target / "AGENTS.md").read_text(
            encoding="utf-8"
        )
        assert (target / "AGENT-HARNESS.md").is_file()
        environment = json.loads(
            (target / ".cursor" / "environment.json").read_text(encoding="utf-8")
        )
        assert environment["name"] == "project-owned"
        hooks = json.loads(
            (target / ".cursor" / "hooks.json").read_text(encoding="utf-8")
        )
        commands = {
            entry["command"] for entry in hooks["hooks"]["beforeSubmitPrompt"]
        }
        assert commands == {
            ".cursor/hooks/project-hook.py",
            ".cursor/hooks/markitdown-before-submit.py",
        }
        config = (target / "harness.config.sh").read_text(encoding="utf-8")
        assert 'HARNESS_CONFIGURED="0"' in config
        assert 'HARNESS_INSTALL_CMD=""' in config
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
        run(
            "fleet/apply-harness.py",
            "--bundle",
            str(bundle),
            "--target",
            str(target),
        )
        assert tree_hash(target) == before

    print("PASS: fleet bundle build, merge, config detection, and idempotence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

