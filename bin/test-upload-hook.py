#!/usr/bin/env python3
"""Integration checks for the beforeSubmitPrompt MarkItDown hook."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".cursor" / "hooks" / "markitdown-before-submit.py"


def run_hook(
    workspace: Path,
    attachments: list[dict[str, str]],
    converter: str | None = None,
) -> dict[str, Any]:
    payload = {
        "hook_event_name": "beforeSubmitPrompt",
        "conversation_id": "conversation-test",
        "generation_id": "generation-test",
        "workspace_roots": [str(workspace)],
        "prompt": "Review the uploaded material and implement it.",
        "attachments": attachments,
    }
    environment = os.environ.copy()
    environment["CURSOR_PROJECT_DIR"] = str(workspace)
    environment.pop("HARNESS_MARKITDOWN_CMD", None)
    if converter:
        environment["HARNESS_MARKITDOWN_CMD"] = converter

    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=environment,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary)

        no_files = run_hook(workspace, [])
        assert no_files == {"continue": True}
        manifest_path = workspace / ".cursor" / "converted" / "latest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == "no-files"
        assert manifest["has_files"] is False
        assert manifest["prompt"] == "Review the uploaded material and implement it."
        assert len(manifest["prompt_sha256"]) == 64

        converter = workspace / "fake-markitdown.py"
        converter.write_text(
            "#!/usr/bin/env python3\n"
            "import json\n"
            "import os\n"
            "import pathlib\n"
            "import sys\n"
            "source = pathlib.Path(sys.argv[1])\n"
            "latest = pathlib.Path(os.environ['CURSOR_PROJECT_DIR']) / '.cursor' / 'converted' / 'latest.json'\n"
            "assert json.loads(latest.read_text())['status'] == 'converting'\n"
            "if source.name.startswith('fail'):\n"
            "    raise SystemExit(3)\n"
            "output = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
            "output.write_text('# Converted\\n\\n' + source.read_text())\n",
            encoding="utf-8",
        )
        converter.chmod(0o755)
        attachment = workspace / "proposal.txt"
        attachment.write_text("Build the safe thing.", encoding="utf-8")

        converted = run_hook(
            workspace,
            [{"type": "file", "file_path": str(attachment)}],
            str(converter),
        )
        assert converted == {"continue": True}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == "converted"
        assert manifest["has_files"] is True
        assert len(manifest["files"]) == 1
        markdown = Path(manifest["files"][0]["markdown_path"])
        assert markdown.read_text(encoding="utf-8").startswith("# Converted")

        failing_attachment = workspace / "fail-second.txt"
        failing_attachment.write_text("This conversion must fail.", encoding="utf-8")
        partial = run_hook(
            workspace,
            [
                {"type": "file", "file_path": str(attachment)},
                {"type": "file", "file_path": str(failing_attachment)},
            ],
            str(converter),
        )
        assert partial["continue"] is False
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == "error"
        assert len(manifest["files"]) == 1

        failed = run_hook(
            workspace,
            [{"type": "file", "file_path": str(attachment)}],
            "/bin/false",
        )
        assert failed["continue"] is False
        assert "conversion failed" in failed["user_message"].lower()

        missing = run_hook(
            workspace,
            [{"type": "file", "file_path": str(workspace / "missing.pdf")}],
            str(converter),
        )
        assert missing["continue"] is False
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == "error"

        follow_up = run_hook(workspace, [])
        assert follow_up == {"continue": True}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == "no-files"

    print("PASS: upload hook no-file, conversion, and fail-closed paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

