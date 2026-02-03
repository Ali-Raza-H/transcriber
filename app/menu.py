"""Interactive text menu for Transcriber."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import shutil
import time

from .config import AppConfig, EngineConfig, OutputConfig, get_config_path, load_config, save_config
from .testing import run_tests
from engine import create_engine
from media.audio import MediaError, is_supported_media, prepared_audio
from output.text import write_text_file


@dataclass(frozen=True, slots=True)
class TranscribeRequest:
    """Input data required to run a transcription."""

    input_path: Path
    output_dir: Path
    model: str
    device: str


def run_menu() -> None:
    """Run the interactive menu."""

    while True:
        _clear_screen()
        print("Transcriber Menu")
        print("================")
        print("1) Transcribe a file")
        print("2) Settings")
        print("3) System status")
        print("4) Run tests")
        print("5) Exit")
        choice = input("\nSelect option [1-5]: ").strip().lower()

        if choice == "1":
            _menu_transcribe()
        elif choice == "2":
            _menu_settings()
        elif choice == "3":
            _menu_status()
        elif choice == "4":
            _menu_tests()
        elif choice in {"5", "q", "quit", "exit"}:
            break
        else:
            print("Invalid choice. Press Enter to try again.")
            input()


def _menu_transcribe() -> None:
    """Prompt for transcription details and run the pipeline."""

    config = _safe_load_config()
    _clear_screen()
    print("Transcribe a file")
    print("=================")
    print(f"Defaults: model={config.engine.model}, device={config.engine.device}")
    print("Enter 'q' to go back.\n")

    input_value = input("Input file (.mp3 or .mp4): ").strip()
    if input_value.lower() in {"q", "quit", "back"}:
        return

    input_path = Path(input_value).expanduser()
    if not input_path.exists():
        _pause(f"Input file does not exist: {input_path}")
        return
    if not is_supported_media(input_path):
        _pause("Unsupported file type. Use .mp3 or .mp4.")
        return

    output_value = input("Output directory (optional): ").strip()
    output_dir = Path(output_value).expanduser() if output_value else input_path.parent

    model_value = input(f"Model [{config.engine.model}]: ").strip() or config.engine.model
    device_value = input(f"Device [{config.engine.device}]: ").strip() or config.engine.device

    request = TranscribeRequest(
        input_path=input_path,
        output_dir=output_dir,
        model=model_value,
        device=device_value,
    )

    try:
        print("\nTranscribing... This may take a while.")
        output_path = _run_transcription(request)
        _pause(f"Saved transcript: {output_path}")
    except MediaError as exc:
        _pause(f"Media error: {exc}")
    except ModuleNotFoundError as exc:
        _pause(str(exc))
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        _pause(f"Error: {exc}")


def _menu_settings() -> None:
    """View and update configuration settings."""

    while True:
        config = _safe_load_config()
        _clear_screen()
        print("Settings")
        print("========")
        print(f"Config path: {get_config_path()}")
        print(f"Model:  {config.engine.model}")
        print(f"Device: {config.engine.device}\n")
        print("1) Edit settings")
        print("2) Reset to defaults")
        print("3) Back")
        choice = input("\nSelect option [1-3]: ").strip()

        if choice == "1":
            model = input(f"Model [{config.engine.model}]: ").strip() or config.engine.model
            device = input(f"Device [{config.engine.device}]: ").strip() or config.engine.device
            new_config = AppConfig(
                engine=EngineConfig(
                    backend=config.engine.backend,
                    model=model,
                    device=device,
                ),
                output=OutputConfig(extension="txt"),
            )
            try:
                path = save_config(new_config)
                _pause(f"Saved: {path}")
            except ValueError as exc:
                _pause(f"Config error: {exc}")
        elif choice == "2":
            try:
                path = save_config(AppConfig())
                _pause(f"Reset to defaults: {path}")
            except ValueError as exc:
                _pause(f"Config error: {exc}")
        elif choice == "3":
            return
        else:
            _pause("Invalid choice.")


def _menu_status() -> None:
    """Show system status with optional refresh."""

    while True:
        _clear_screen()
        print("System status")
        print("=============")
        print(_system_stats())
        print("\nRefresh? (y/N)")
        choice = input("> ").strip().lower()
        if choice != "y":
            break
        time.sleep(1.0)


def _menu_tests() -> None:
    """Run the test suite."""

    _clear_screen()
    print("Running tests...\n")
    try:
        code, output = run_tests()
    except ModuleNotFoundError as exc:
        _pause(str(exc))
        return

    if output:
        print(output.strip())
    if code == 0:
        _pause("\nTests passed.")
    else:
        _pause(f"\nTests failed (exit code {code}).")


def _run_transcription(request: TranscribeRequest) -> Path:
    """Run the transcription pipeline and return the output path."""

    engine_config = EngineConfig(
        backend="faster-whisper",
        model=request.model,
        device=request.device,
    )
    engine = create_engine(engine_config)
    with prepared_audio(request.input_path) as audio_path:
        text = engine.transcribe(audio_path, language=None)

    output_path = request.output_dir / f"{request.input_path.stem}.txt"
    write_text_file(output_path, text)
    return output_path


def _format_bytes(value: float) -> str:
    """Format bytes in a human-readable form."""

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def _system_stats() -> str:
    """Return a formatted snapshot of system stats."""

    try:
        import psutil  # type: ignore
    except ModuleNotFoundError:
        return "psutil is not installed. Install with `pip install -e .`."

    cpu = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.cwd()))
    ffmpeg_path = shutil.which("ffmpeg")

    disk_root = Path.cwd().anchor or str(Path.cwd())
    lines = [
        f"CPU usage: {cpu:.1f}%",
        f"RAM: {_format_bytes(memory.used)} / {_format_bytes(memory.total)} ({memory.percent:.1f}%)",
        f"Disk ({disk_root}): {_format_bytes(disk.free)} free / {_format_bytes(disk.total)} total",
        f"Python: {platform.python_version()}",
        f"FFmpeg: {'found' if ffmpeg_path else 'not found'}",
    ]
    return "\n".join(lines)


def _safe_load_config() -> AppConfig:
    """Load config with fallback to defaults."""

    try:
        return load_config()
    except ValueError:
        return AppConfig()


def _clear_screen() -> None:
    """Clear the terminal screen."""

    command = "cls" if platform.system().lower() == "windows" else "clear"
    try:
        import os

        os.system(command)
    except Exception:
        pass


def _pause(message: str) -> None:
    """Display a message and wait for user input."""

    print(f"\n{message}")
    input("Press Enter to continue...")
