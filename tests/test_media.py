from __future__ import annotations

from pathlib import Path

from media.audio import is_supported_media


def test_is_supported_media() -> None:
    assert is_supported_media(Path("a.mp3"))
    assert is_supported_media(Path("a.mp4"))
    assert not is_supported_media(Path("a.wav"))

