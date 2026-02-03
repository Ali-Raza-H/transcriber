from __future__ import annotations

from pathlib import Path

from output.text import write_text_file


def test_write_text_file_creates_parent_dirs(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "file.txt"
    write_text_file(out, "hello\n")
    assert out.read_text(encoding="utf-8") == "hello\n"

