from __future__ import annotations

from pathlib import Path
import platform

import pytest

from app.config import get_config_path, load_config


def test_get_config_path_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setenv("APPDATA", r"C:\Temp\AppData")
    assert get_config_path() == Path(r"C:\Temp\AppData") / "transcriber" / "config.toml"


def test_get_config_path_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/home/testuser")))
    assert get_config_path() == Path("/home/testuser") / ".config" / "transcriber" / "config.toml"


def test_load_config_defaults_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    assert load_config(config_path).engine.model == "small"


def test_load_config_rejects_non_txt_extension(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[output]
extension = "srt"
""".lstrip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Only plain text output"):
        load_config(config_path)

