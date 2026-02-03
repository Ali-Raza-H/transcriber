"""Audio preparation (MP3/MP4) via FFmpeg."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Iterator


SUPPORTED_EXTENSIONS = {".mp3", ".mp4"}


class MediaError(RuntimeError):
    """Base error for media handling failures."""


class UnsupportedMediaError(MediaError):
    """Raised when the input file type is not supported."""


class FfmpegNotFoundError(MediaError):
    """Raised when FFmpeg is not available on PATH."""


class FfmpegFailedError(MediaError):
    """Raised when an FFmpeg command fails."""


def is_supported_media(path: Path) -> bool:
    """Return True if the file extension is supported."""

    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def find_ffmpeg() -> str:
    """Return the FFmpeg executable path (or raise if missing)."""

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FfmpegNotFoundError(
            "FFmpeg not found on PATH. Install FFmpeg and ensure `ffmpeg` is available."
        )
    return ffmpeg


def convert_to_wav(input_path: Path, output_wav: Path) -> None:
    """Convert an MP3/MP4 file into a 16kHz mono WAV suitable for transcription.

    Args:
        input_path: Path to an .mp3 or .mp4 file.
        output_wav: Output .wav path.

    Raises:
        UnsupportedMediaError: If input extension is not supported.
        FfmpegNotFoundError: If ffmpeg is not found.
        FfmpegFailedError: If ffmpeg returns a non-zero exit code.
    """

    if not is_supported_media(input_path):
        raise UnsupportedMediaError(
            f"Unsupported input type: {input_path.suffix!r}. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    ffmpeg = find_ffmpeg()
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_wav),
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or "").strip()
        hint = "FFmpeg failed to process the file."
        extra = f"\n\nDetails:\n{details}" if details else ""
        raise FfmpegFailedError(f"{hint}\n\nCommand: {' '.join(cmd)}{extra}") from exc


@contextmanager
def prepared_audio(input_path: Path) -> Iterator[Path]:
    """Prepare audio for transcription and clean up temporary files.

    This converts MP3/MP4 to a temporary 16kHz mono WAV file and yields the WAV path.
    """

    with tempfile.TemporaryDirectory(prefix="transcriber-") as tmpdir:
        wav_path = Path(tmpdir) / "audio.wav"
        convert_to_wav(input_path, wav_path)
        yield wav_path
