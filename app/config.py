"""Configuration handling for Transcriber.

Transcriber loads an optional TOML file from OS-specific locations:

- Linux: ~/.config/transcriber/config.toml
- Windows: %APPDATA%\\transcriber\\config.toml
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import platform
from typing import Any

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """Configuration for the transcription engine."""

    backend: str = "faster-whisper"
    model: str = "small"
    device: str = "cpu"


@dataclass(frozen=True, slots=True)
class OutputConfig:
    """Configuration for text output."""

    extension: str = "txt"


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Top-level application configuration."""

    engine: EngineConfig = field(default_factory=EngineConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def get_config_path() -> Path:
    """Return the default configuration file path for the current OS."""

    system = platform.system().lower()
    if system == "windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "transcriber" / "config.toml"

        # Reasonable fallback for unusual environments.
        return Path.home() / "AppData" / "Roaming" / "transcriber" / "config.toml"

    return Path.home() / ".config" / "transcriber" / "config.toml"


def load_config(path: Path | None = None) -> AppConfig:
    """Load config from a TOML file, falling back to defaults if missing.

    Args:
        path: Optional explicit config path. When None, uses the OS default.

    Raises:
        ValueError: If the config contains unsupported values.
    """

    config_path = path or get_config_path()
    if not config_path.exists():
        return AppConfig()

    with config_path.open("rb") as f:
        raw = tomllib.load(f)

    engine_raw = _get_table(raw, "engine")
    output_raw = _get_table(raw, "output")

    engine = EngineConfig(
        backend=_get_str(engine_raw, "backend", default=EngineConfig.backend),
        model=_get_str(engine_raw, "model", default=EngineConfig.model),
        device=_get_str(engine_raw, "device", default=EngineConfig.device),
    )

    extension = _get_str(output_raw, "extension", default=OutputConfig.extension)
    if extension.lower() != "txt":
        raise ValueError("Only plain text output is supported: set [output].extension = 'txt'.")

    output = OutputConfig(extension="txt")
    return AppConfig(engine=engine, output=output)


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    """Save configuration to a TOML file.

    Args:
        config: Configuration values to persist.
        path: Optional explicit config path. When None, uses the OS default.

    Returns:
        The path that was written.

    Raises:
        ValueError: If unsupported values are provided.
    """

    if config.output.extension.lower() != "txt":
        raise ValueError("Only plain text output is supported: set [output].extension = 'txt'.")

    config_path = path or get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    content = _to_toml(config)
    config_path.write_text(content, encoding="utf-8")
    return config_path


def _get_table(raw: dict[str, Any], key: str) -> dict[str, Any]:
    """Internal helper to get a TOML table as a dict."""

    value = raw.get(key)
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    raise ValueError(f"Invalid config: [{key}] must be a table.")


def _get_str(raw: dict[str, Any], key: str, default: str) -> str:
    """Internal helper to get a TOML string with a default."""

    value = raw.get(key)
    if value is None:
        return default
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"Invalid config: {key} must be a non-empty string.")


def _to_toml(config: AppConfig) -> str:
    """Serialize config data to TOML."""

    return (
        "[engine]\n"
        f'model = "{config.engine.model}"\n'
        f'device = "{config.engine.device}"\n'
        "\n"
        "[output]\n"
        'extension = "txt"\n'
    )
