"""Plain text transcript output."""

from __future__ import annotations

from pathlib import Path


def write_text_file(output_path: Path, text: str) -> None:
    """Write transcript text to disk.

    Args:
        output_path: Destination `.txt` path.
        text: Transcript content.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")

