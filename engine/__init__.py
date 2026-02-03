"""Transcription engine factory and exports."""

from __future__ import annotations

from app.config import EngineConfig

from .base import TranscriptionEngine
from .faster_whisper import FasterWhisperEngine


def create_engine(config: EngineConfig) -> TranscriptionEngine:
    """Create a transcription engine from configuration.

    This factory allows adding future engines without changing CLI logic.
    """

    backend = (config.backend or "").strip().lower()
    if backend in {"faster-whisper", "faster_whisper", "whisper"}:
        return FasterWhisperEngine(model=config.model, device=config.device)
    raise ValueError(f"Unsupported engine backend: {config.backend!r}")

