"""Interactive TUI menu for Transcriber."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import shutil
import threading

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static

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

    MenuApp().run()


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


class MenuApp(App[None]):
    """Top-level Textual app for the Transcriber menu."""

    CSS = """
    Screen {
        align: center middle;
    }

    .title {
        text-style: bold;
        margin: 0 0 1 0;
    }

    #menu, #form, #panel {
        width: 72;
    }

    #message {
        margin-top: 1;
    }

    .error {
        color: red;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def on_mount(self) -> None:
        """Start at the main menu."""

        self.push_screen(MainMenuScreen())


class MainMenuScreen(Screen):
    """Main menu screen with navigation options."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Transcriber Menu", classes="title")
        with Vertical(id="menu"):
            yield Button("1) Transcribe a file", id="transcribe")
            yield Button("2) Settings", id="settings")
            yield Button("3) System status", id="status")
            yield Button("4) Run tests", id="tests")
            yield Button("5) Exit", id="exit")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "transcribe":
            self.app.push_screen(TranscribeScreen())
        elif button_id == "settings":
            self.app.push_screen(SettingsScreen())
        elif button_id == "status":
            self.app.push_screen(StatusScreen())
        elif button_id == "tests":
            self.app.push_screen(TestScreen())
        elif button_id == "exit":
            self.app.exit()


class TranscribeScreen(Screen):
    """Screen for running a transcription."""

    def __init__(self) -> None:
        super().__init__()
        self._config: AppConfig = AppConfig()
        self._busy = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Transcribe a file", classes="title")
        with Vertical(id="form"):
            yield Static("", id="defaults")
            yield Static("Input file (.mp3 or .mp4):")
            yield Input(placeholder="C:\\path\\to\\audio.mp3", id="input_path")
            yield Static("Output directory (optional):")
            yield Input(placeholder="Leave blank to use input folder", id="output_dir")
            yield Static("Model (optional):")
            yield Input(placeholder="Defaults to config", id="model")
            yield Static("Device (optional):")
            yield Input(placeholder="Defaults to config", id="device")
            with Horizontal():
                yield Button("Run", id="run")
                yield Button("Back", id="back")
            yield Static("", id="message")
        yield Footer()

    def on_show(self) -> None:
        try:
            self._config = load_config()
        except ValueError as exc:
            self._set_message(f"Config error: {exc}", error=True)
            self._config = AppConfig()

        defaults = self.query_one("#defaults", Static)
        defaults.update(
            f"Defaults: model={self._config.engine.model}, device={self._config.engine.device}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
            return
        if event.button.id != "run":
            return
        self._start_transcription()

    def _start_transcription(self) -> None:
        if self._busy:
            return

        input_value = self.query_one("#input_path", Input).value.strip()
        if not input_value:
            self._set_message("Enter an input file path.", error=True)
            return

        input_path = Path(input_value).expanduser()
        if not input_path.exists():
            self._set_message(f"Input file does not exist: {input_path}", error=True)
            return
        if not is_supported_media(input_path):
            self._set_message("Unsupported file type. Use .mp3 or .mp4.", error=True)
            return

        output_value = self.query_one("#output_dir", Input).value.strip()
        output_dir = Path(output_value).expanduser() if output_value else input_path.parent

        model_value = self.query_one("#model", Input).value.strip() or self._config.engine.model
        device_value = self.query_one("#device", Input).value.strip() or self._config.engine.device

        request = TranscribeRequest(
            input_path=input_path,
            output_dir=output_dir,
            model=model_value,
            device=device_value,
        )

        self._set_message("Transcribing... This may take a while.")
        self._set_busy(True)
        threading.Thread(target=self._transcribe_thread, args=(request,), daemon=True).start()

    def _transcribe_thread(self, request: TranscribeRequest) -> None:
        try:
            output_path = _run_transcription(request)
            message = f"Saved transcript: {output_path}"
            self.app.call_from_thread(self._set_message, message, False)
        except MediaError as exc:
            self.app.call_from_thread(self._set_message, f"Media error: {exc}", True)
        except ModuleNotFoundError as exc:
            self.app.call_from_thread(self._set_message, str(exc), True)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.app.call_from_thread(self._set_message, f"Error: {exc}", True)
        finally:
            self.app.call_from_thread(self._set_busy, False)

    def _set_message(self, text: str, error: bool = False) -> None:
        message = self.query_one("#message", Static)
        message.update(text)
        message.remove_class("error")
        if error:
            message.add_class("error")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.query_one("#run", Button).disabled = busy


class SettingsScreen(Screen):
    """Screen for viewing and updating config values."""

    def __init__(self) -> None:
        super().__init__()
        self._config: AppConfig = AppConfig()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Settings", classes="title")
        with Vertical(id="form"):
            yield Static("", id="config_path")
            yield Static("Model:")
            yield Input(id="model")
            yield Static("Device:")
            yield Input(id="device")
            with Horizontal():
                yield Button("Save", id="save")
                yield Button("Reset to defaults", id="reset")
                yield Button("Back", id="back")
            yield Static("", id="message")
        yield Footer()

    def on_show(self) -> None:
        self._reload_config()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "back":
            self.app.pop_screen()
        elif button_id == "save":
            self._save()
        elif button_id == "reset":
            self._reset()

    def _reload_config(self) -> None:
        try:
            self._config = load_config()
        except ValueError as exc:
            self._set_message(f"Config error: {exc}", error=True)
            self._config = AppConfig()

        self.query_one("#config_path", Static).update(f"Config: {get_config_path()}")
        self.query_one("#model", Input).value = self._config.engine.model
        self.query_one("#device", Input).value = self._config.engine.device

    def _save(self) -> None:
        model = self.query_one("#model", Input).value.strip() or self._config.engine.model
        device = self.query_one("#device", Input).value.strip() or self._config.engine.device

        new_config = AppConfig(
            engine=EngineConfig(
                backend=self._config.engine.backend,
                model=model,
                device=device,
            ),
            output=OutputConfig(extension="txt"),
        )

        try:
            path = save_config(new_config)
        except ValueError as exc:
            self._set_message(f"Config error: {exc}", error=True)
            return

        self._config = new_config
        self._set_message(f"Saved: {path}")

    def _reset(self) -> None:
        defaults = AppConfig()
        try:
            path = save_config(defaults)
        except ValueError as exc:
            self._set_message(f"Config error: {exc}", error=True)
            return

        self._config = defaults
        self.query_one("#model", Input).value = defaults.engine.model
        self.query_one("#device", Input).value = defaults.engine.device
        self._set_message(f"Reset to defaults: {path}")

    def _set_message(self, text: str, error: bool = False) -> None:
        message = self.query_one("#message", Static)
        message.update(text)
        message.remove_class("error")
        if error:
            message.add_class("error")


class StatusScreen(Screen):
    """Screen for live system status."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("System status (live)", classes="title")
        with Vertical(id="panel"):
            yield Static("", id="stats")
            with Horizontal():
                yield Button("Refresh", id="refresh")
                yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        try:
            import psutil  # type: ignore

            psutil.cpu_percent(interval=None)
        except ModuleNotFoundError:
            pass

        self._refresh()
        self.set_interval(1.0, self._refresh)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "refresh":
            self._refresh()

    def _refresh(self) -> None:
        self.query_one("#stats", Static).update(_system_stats())


class TestScreen(Screen):
    """Screen for running the test suite."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Run tests", classes="title")
        with Vertical(id="panel"):
            yield Static("Running tests...", id="output")
            yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        threading.Thread(target=self._run_tests_thread, daemon=True).start()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

    def _run_tests_thread(self) -> None:
        try:
            code, output = run_tests()
            summary = "Tests passed." if code == 0 else f"Tests failed (exit code {code})."
            output = output.strip()
            if output:
                combined = f"{summary}\n\n{output}"
            else:
                combined = summary
            if len(combined) > 6000:
                combined = combined[-6000:]
            self.app.call_from_thread(self._set_output, combined, False)
        except ModuleNotFoundError as exc:
            self.app.call_from_thread(self._set_output, str(exc), True)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.app.call_from_thread(self._set_output, f"Error: {exc}", True)

    def _set_output(self, text: str, error: bool) -> None:
        output = self.query_one("#output", Static)
        output.update(text)
        output.remove_class("error")
        if error:
            output.add_class("error")
