#!/usr/bin/env python3
"""Apply a canonical harness checkout without overwriting project-owned config."""

import argparse
import json
import shutil
from pathlib import Path


HARNESS_SKILLS = (
    "agent-harness",
    "cloudflare-promote",
    "plan-work",
    "pre-deploy",
    "resume",
    "review-goal",
    "ship",
    "tdd",
)
PORTABLE_SKILLS = (
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
)
POINTER_START = "<!-- agent-harness:start -->"
POINTER_END = "<!-- agent-harness:end -->"
REQUIRED_SOURCES = (
    "AGENTS.md",
    "README.md",
    "harness.config.example.sh",
    "skills-lock.json",
    "skills-local-lock.json",
    ".cursor/rules/agent-harness.mdc",
    ".cursor/hooks.json",
    ".cursor/hooks/markitdown-before-submit.py",
    ".github/workflows/pre-deploy.yml",
    "docs/forge-workflow.md",
    "input/first-review.md",
)


def verify_source(source: Path) -> None:
    """Fail closed when the canonical checkout is incomplete or truncated."""
    missing = [name for name in REQUIRED_SOURCES if not (source / name).is_file()]
    for skill in HARNESS_SKILLS:
        if not (source / ".cursor" / "skills" / skill / "SKILL.md").is_file():
            missing.append(f".cursor/skills/{skill}/SKILL.md")
    for skill in PORTABLE_SKILLS:
        if not (source / ".agents" / "skills" / skill / "SKILL.md").is_file():
            missing.append(f".agents/skills/{skill}/SKILL.md")
    for script in ("bash-guard-check.sh", "pre-deploy-gate.sh", "optimizer-gate.sh"):
        if not (source / "bin" / script).is_file():
            missing.append(f"bin/{script}")
    if missing:
        raise FileNotFoundError(
            "canonical harness checkout is incomplete: " + ", ".join(sorted(missing))
        )

    skill_files = list((source / ".cursor" / "skills").glob("*/SKILL.md"))
    skill_files.extend((source / ".agents" / "skills").glob("*/SKILL.md"))
    for skill_file in skill_files:
        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("---") or "\nname:" not in text:
            raise ValueError(f"canonical skill looks truncated: {skill_file}")


def copy_file(source: Path, destination: Path, overwrite: bool = True) -> None:
    if destination.exists() and not overwrite:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)


def merge_hooks(source: Path, destination: Path) -> None:
    incoming = json.loads(source.read_text(encoding="utf-8"))
    if not destination.exists():
        copy_file(source, destination)
        return

    current = json.loads(destination.read_text(encoding="utf-8"))
    current.setdefault("version", 1)
    hooks = current.setdefault("hooks", {})
    for event, entries in incoming.get("hooks", {}).items():
        existing = hooks.setdefault(event, [])
        for entry in entries:
            command = entry.get("command")
            matching = next(
                (
                    index
                    for index, current_entry in enumerate(existing)
                    if isinstance(current_entry, dict)
                    and current_entry.get("command") == command
                ),
                None,
            )
            if matching is None:
                existing.append(entry)
            else:
                existing[matching] = entry
    destination.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


def append_block(path: Path, block: str) -> None:
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    if POINTER_START in content:
        before, rest = content.split(POINTER_START, 1)
        _, after = rest.split(POINTER_END, 1)
        content = before.rstrip() + "\n\n" + block + after
    else:
        content = content.rstrip() + ("\n\n" if content.strip() else "") + block
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def package_scripts(target: Path) -> dict[str, str]:
    package = target / "package.json"
    if not package.exists():
        return {}
    try:
        data = json.loads(package.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def package_manager(target: Path) -> tuple[str, str]:
    if (target / "pnpm-lock.yaml").exists():
        return "pnpm", "pnpm install --frozen-lockfile"
    if (target / "yarn.lock").exists():
        return "yarn", "yarn install --immutable"
    if (target / "bun.lockb").exists() or (target / "bun.lock").exists():
        return "bun", "bun install --frozen-lockfile"
    if (target / "package-lock.json").exists():
        return "npm", "npm ci"
    if (target / "package.json").exists():
        return "npm", "npm install"
    return "", ""


def script_command(manager: str, scripts: dict[str, str], *names: str) -> str:
    for name in names:
        if name in scripts:
            return f"{manager} run {name}"
    return ""


def create_config(target: Path) -> None:
    path = target / "harness.config.sh"
    if path.exists():
        return

    manager, _ = package_manager(target)
    scripts = package_scripts(target)
    typecheck = script_command(manager, scripts, "typecheck", "type-check")
    lint = script_command(manager, scripts, "lint")
    test = script_command(manager, scripts, "test", "test:ci")
    build = script_command(manager, scripts, "build")
    fallow = (
        "npx --no-install fallow audit --format json --quiet"
        if (target / "package.json").exists()
        else ""
    )

    values = {
        "HARNESS_CONFIGURED": "0",
        "HARNESS_SOURCE_DIRS": "src|app|lib|workers",
        "HARNESS_INSTALL_CMD": "",
        "HARNESS_TYPECHECK_CMD": typecheck,
        "HARNESS_LINT_CMD": lint,
        "HARNESS_TEST_CMD": test,
        "HARNESS_BUILD_CMD": build,
        "HARNESS_FALLOW_CMD": fallow,
        "HARNESS_WRANGLER_CMD": "npx wrangler",
        "HARNESS_WRANGLER_CHECK_CMD": "npx wrangler check startup",
        "HARNESS_WORKER_NAME": "",
        "HARNESS_STAGING_ENV": "staging",
        "HARNESS_PRODUCTION_ENV": "",
        "HARNESS_HEALTH_URL": "",
        "HARNESS_PREVIEW_HEALTH_URL": "",
        "HARNESS_HEALTH_PATH": "/health",
        "HARNESS_CANARY_PERCENTAGES": "1 10 100",
        "HARNESS_CANARY_SECONDS": "60",
    }
    lines = [
        "# Generated harness defaults. Review every command before setting",
        "# HARNESS_CONFIGURED=1. Add exact fallow@3.17.0 for JS/TS repos.",
        "# Never put secrets in this tracked file.",
        "",
    ]
    lines.extend(f'{key}="{value}"' for key, value in values.items())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply(bundle_root: Path, target: Path) -> None:
    copy_file(bundle_root / "AGENTS.md", target / "AGENT-HARNESS.md")
    pointer = (
        f"{POINTER_START}\n"
        "## Agent harness\n\n"
        "Follow `AGENT-HARNESS.md` for every goal-to-production change. "
        "Its safety gates and handoff rules are repository policy.\n"
        f"{POINTER_END}"
    )
    append_block(target / "AGENTS.md", pointer)

    for skill in HARNESS_SKILLS:
        copy_tree(
            bundle_root / ".cursor" / "skills" / skill,
            target / ".cursor" / "skills" / skill,
        )
    for skill in PORTABLE_SKILLS:
        copy_tree(
            bundle_root / ".agents" / "skills" / skill,
            target / ".agents" / "skills" / skill,
        )

    copy_file(
        bundle_root / ".agents" / "skills" / "NOTICE.md",
        target / ".agents" / "skills" / "NOTICE.md",
    )
    copy_file(
        bundle_root / ".cursor" / "rules" / "agent-harness.mdc",
        target / ".cursor" / "rules" / "agent-harness.mdc",
    )
    copy_tree(bundle_root / ".cursor" / "hooks", target / ".cursor" / "hooks")
    merge_hooks(
        bundle_root / ".cursor" / "hooks.json", target / ".cursor" / "hooks.json"
    )
    copy_file(
        bundle_root / ".cursor" / "environment.json",
        target / ".cursor" / "environment.json",
        overwrite=False,
    )

    for directory in ("bin", "licenses", "automations"):
        copy_tree(bundle_root / directory, target / directory)
    for filename in (
        "harness.config.example.sh",
        "skills-lock.json",
        "skills-local-lock.json",
    ):
        copy_file(bundle_root / filename, target / filename)

    copy_file(
        bundle_root / ".github" / "workflows" / "pre-deploy.yml",
        target / ".github" / "workflows" / "pre-deploy.yml",
    )
    copy_file(
        bundle_root / "docs" / "forge-workflow.md",
        target / "docs" / "forge-workflow.md",
    )
    copy_file(
        bundle_root / "README.md", target / "docs" / "agent-harness.md"
    )
    copy_file(
        bundle_root / "input" / "first-review.md",
        target / "input" / "first-review.md",
        overwrite=False,
    )
    handoff = target / "docs" / "handoff.md"
    if not handoff.exists():
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "# Agent Handoff\n\n"
            "- **Phase:** done\n"
            "- **Goal:** No active harness task.\n"
            "- **Completed:** Shared harness foundation installed.\n"
            "- **Stopped at:** Ready for the next reviewed goal.\n"
            "- **Next action:** Put a goal in `input/` and run the agent harness.\n"
            "- **Blockers:** None.\n"
            "- **Files touched:** Harness foundation only.\n"
            "- **Branch:** Replace when work begins.\n"
            "- **Commit:** Replace when work begins.\n"
            "- **Last gate:** Not run for a product change.\n"
            "- **New Worker version:** None.\n"
            "- **Stable Worker version:** None.\n"
            "- **Rollback Worker version:** None.\n",
            encoding="utf-8",
        )
    create_config(target)

    ignore = target / ".gitignore"
    current = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    additions = (
        "\n# Agent harness generated artifacts\n"
        ".cursor/artifacts/\n.cursor/converted/\n"
        "__pycache__/\n*.pyc\n.wrangler/\n"
    )
    if "# Agent harness generated artifacts" not in current:
        ignore.write_text(current.rstrip() + additions, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    arguments = parser.parse_args()

    source = arguments.source.resolve()
    target = arguments.target.resolve()
    if source == target:
        raise ValueError("source and target must differ")
    verify_source(source)
    apply(source, target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

