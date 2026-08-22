#!/usr/bin/env python3
"""Build the deterministic text bundle consumed by fleet sync workflows."""

import base64
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "distribution"
MANIFEST = OUTPUT_DIR / "manifest.json"
CHUNK_SIZE = 32_000
INCLUDES = (
    "AGENTS.md",
    "README.md",
    ".cursor/skills",
    ".cursor/rules/agent-harness.mdc",
    ".cursor/hooks",
    ".cursor/hooks.json",
    ".cursor/environment.json",
    "bin",
    "licenses",
    "automations",
    "harness.config.example.sh",
    "skills-lock.json",
    ".github/workflows/pre-deploy.yml",
    "docs/forge-workflow.md",
    "input/first-review.md",
)


def add_bytes(archive: tarfile.TarFile, name: str, content: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(content)
    archive.addfile(normalized(info), io.BytesIO(content))


def add_portable_skills(archive: tarfile.TarFile) -> dict[str, str]:
    hashes: dict[str, str] = {}
    skills_root = ROOT / ".agents" / "skills"
    add_bytes(
        archive,
        ".agents/skills/NOTICE.md",
        (skills_root / "NOTICE.md").read_bytes(),
    )
    for skill_root in sorted(
        path for path in skills_root.iterdir() if (path / "SKILL.md").is_file()
    ):
        digest = hashlib.sha256()
        files = []
        for path in sorted(item for item in skill_root.rglob("*") if item.is_file()):
            relative = path.relative_to(skill_root)
            if "agents" in relative.parts:
                continue
            if skill_root.name == "fallow" and "references" in relative.parts:
                continue
            files.append((path, relative))
        for path, relative in files:
            content = path.read_bytes()
            digest.update(relative.as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(content)
            digest.update(b"\0")
            add_bytes(
                archive,
                f".agents/skills/{skill_root.name}/{relative.as_posix()}",
                content,
            )
        hashes[skill_root.name] = digest.hexdigest()
    return hashes


def normalized(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    return info


def main() -> int:
    payload = io.BytesIO()
    with gzip.GzipFile(fileobj=payload, mode="wb", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for relative in INCLUDES:
                source = ROOT / relative
                if not source.exists():
                    raise FileNotFoundError(relative)
                archive.add(
                    source,
                    arcname=relative,
                    recursive=True,
                    filter=normalized,
                )
            skill_hashes = add_portable_skills(archive)
            local_lock = json.dumps(
                {"version": 1, "skills": skill_hashes},
                indent=2,
                sort_keys=True,
            ).encode("utf-8") + b"\n"
            add_bytes(archive, "skills-local-lock.json", local_lock)

    encoded = base64.b64encode(payload.getvalue())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old_chunk in OUTPUT_DIR.glob("agent-harness.part-*"):
        old_chunk.unlink()
    chunks = []
    for index, start in enumerate(range(0, len(encoded), CHUNK_SIZE)):
        name = f"agent-harness.part-{index:03d}"
        content = encoded[start : start + CHUNK_SIZE]
        (OUTPUT_DIR / name).write_bytes(content)
        chunks.append(name)
    manifest = {
        "version": 1,
        "chunks": chunks,
        "encoded_sha256": hashlib.sha256(encoded).hexdigest(),
        "archive_sha256": hashlib.sha256(payload.getvalue()).hexdigest(),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    old_monolith = OUTPUT_DIR / "agent-harness.tar.gz.b64"
    if old_monolith.exists():
        old_monolith.unlink()
    print(f"Wrote {len(chunks)} chunks ({len(encoded)} encoded bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

