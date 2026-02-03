"""Test runner utilities for the Transcriber CLI."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from typing import Tuple


def run_tests() -> Tuple[int, str]:
    """Run the test suite and return (exit_code, output).

    Raises:
        ModuleNotFoundError: If pytest is not installed.
    """

    if importlib.util.find_spec("pytest") is None:
        raise ModuleNotFoundError(
            'pytest is not installed. Install dev deps with: pip install -e ".[dev]"'
        )

    result = subprocess.run(
        [sys.executable, "-m", "pytest"],
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output
