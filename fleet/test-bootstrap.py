#!/usr/bin/env python3
"""Regression test for an unconfigured fleet bootstrap."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


with tempfile.TemporaryDirectory() as temporary:
    summary = Path(temporary) / "summary.md"
    environment = os.environ.copy()
    environment["FLEET_TOKEN"] = ""
    environment["GITHUB_STEP_SUMMARY"] = str(summary)
    result = subprocess.run(
        [sys.executable, str(ROOT / "fleet" / "bootstrap-repositories.py")],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert "Fleet bootstrap disabled" in result.stdout
    assert "Fleet bootstrap skipped" in summary.read_text(encoding="utf-8")

print("PASS: missing fleet credentials produce a warning/no-op.")
