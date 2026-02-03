"""Base interfaces for transcription engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class TranscriptionEngine(ABC):
    """Interface for speech-to-text engines."""

    @abstractmethod
    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> str:
        """Transcribe an audio file into plain text.

        Args:
            audio_path: Path to an audio file (typically WAV after preprocessing).
            language: Optional language code (e.g. "en"). When None, auto-detect.

        Returns:
            Transcribed text as a single string (no timestamps).
        """

