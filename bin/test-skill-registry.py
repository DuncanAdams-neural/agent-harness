#!/usr/bin/env python3
"""Validate harness and third-party skill discovery metadata."""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_SKILLS = {
    "code-review",
    "codebase-design",
    "diagnosing-bugs",
    "domain-modeling",
    "fallow",
    "grilling",
    "ponytail",
    "ponytail-review",
    "research",
    "resolving-merge-conflicts",
    "writing-for-agents",
}


def declared_name(skill_file: Path) -> str:
    match = re.search(
        r"^name:\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
        skill_file.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match:
        raise AssertionError(f"missing skill name: {skill_file}")
    return match.group(1)


def skill_names(root: Path) -> set[str]:
    names: set[str] = set()
    for skill_file in root.glob("*/SKILL.md"):
        folder = skill_file.parent.name
        declared = declared_name(skill_file)
        if declared != folder:
            raise AssertionError(
                f"{skill_file} declares {declared!r}, expected {folder!r}"
            )
        names.add(declared)
    return names


def tree_hash(skill_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in skill_root.rglob("*") if item.is_file()):
        relative = path.relative_to(skill_root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main() -> int:
    harness = skill_names(ROOT / ".cursor" / "skills")
    portable = skill_names(ROOT / ".agents" / "skills")
    duplicates = harness & portable
    if duplicates:
        raise AssertionError(f"duplicate skills across discovery roots: {duplicates}")
    if portable != UPSTREAM_SKILLS:
        raise AssertionError(
            f"portable skill set drift: expected {UPSTREAM_SKILLS}, got {portable}"
        )

    lock = json.loads((ROOT / "skills-lock.json").read_text(encoding="utf-8"))
    locked = set(lock.get("skills", {}))
    if locked != portable:
        raise AssertionError(f"skills-lock mismatch: {locked} != {portable}")

    local_lock = json.loads(
        (ROOT / "skills-local-lock.json").read_text(encoding="utf-8")
    )
    expected_hashes = local_lock.get("skills", {})
    actual_hashes = {
        name: tree_hash(ROOT / ".agents" / "skills" / name) for name in portable
    }
    if expected_hashes != actual_hashes:
        raise AssertionError(
            "locally adapted skill content drifted; review the change and refresh "
            "skills-local-lock.json"
        )

    licenses = {
        "mattpocock-skills-MIT.txt": "Copyright (c) 2026 Matt Pocock",
        "ponytail-MIT.txt": "Copyright (c) 2026 DietrichGebert",
        "fallow-MIT.txt": "Copyright (c) 2026 Bart Waardenburg",
    }
    for filename, notice in licenses.items():
        license_path = ROOT / "licenses" / filename
        if notice not in license_path.read_text(encoding="utf-8"):
            raise AssertionError(f"MIT attribution is missing from {filename}")

    print("PASS: harness and portable skill registry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

