"""faster-whisper transcription engine implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .base import TranscriptionEngine


class FasterWhisperEngine(TranscriptionEngine):
    """Transcription engine backed by the `faster-whisper` library."""

    def __init__(self, model: str, device: str = "cpu") -> None:
        """Create a FasterWhisperEngine.

        Args:
            model: Whisper model size (e.g. "small") or a local model directory path.
            device: Inference device string (default: "cpu").
        """

        self._model_name = model
        self._device = device
        self._model = None

    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> str:
        """Transcribe an audio file into plain text."""

        model = self._get_model()
        segments, _info = model.transcribe(str(audio_path), language=language)
        parts: list[str] = []
        for segment in segments:
            text = getattr(segment, "text", "")
            if isinstance(text, str):
                parts.append(text)
        joined = "".join(parts).strip()
        return f"{joined}\n" if joined else ""

    def _get_model(self):
        """Lazily construct the underlying faster-whisper model."""

        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "Missing dependency: faster-whisper. Install with `pip install -e .`."
            ) from exc

        kwargs = {}
        if self._device.strip().lower() == "cpu":
            kwargs["compute_type"] = "int8"

        try:
            self._model = WhisperModel(self._model_name, device=self._device, **kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load Whisper model '{self._model_name}'. If you're offline, "
                "ensure the model is already cached or set --model to a local model path."
            ) from exc
        return self._model
