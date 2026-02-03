"""Modern TUI menu for Transcriber (Textual)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import shutil
import threading

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static, TextLog

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
        background: #0b0f19;
        color: #e6e6e6;
    }

    Header, Footer {
        background: #111827;
    }

    #layout {
        height: 1fr;
    }

    #sidebar {
        width: 24;
        background: #0f172a;
        border: tall #1f2937;
        padding: 1 1;
    }

    #content {
        background: #0b0f19;
        border: tall #1f2937;
        padding: 1 2;
    }

    ListView {
        background: #0f172a;
        border: none;
    }

    ListItem.--highlight {
        background: #1f2937;
    }

    .title {
        text-style: bold;
        color: #93c5fd;
        margin-bottom: 1;
    }

    .section {
        border: round #1f2937;
        padding: 1 2;
        margin-bottom: 1;
    }

    Input {
        background: #0b1220;
        border: round #1f2937;
    }

    Button {
        background: #111827;
        border: round #374151;
    }

    Button.-primary {
        background: #2563eb;
        border: round #1d4ed8;
        color: #ffffff;
    }

    #message {
        color: #f59e0b;
        margin-top: 1;
    }

    #error {
        color: #ef4444;
        margin-top: 1;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    current_view = reactive("transcribe")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="layout"):
            with Vertical(id="sidebar"):
                yield Label("Menu", classes="title")
                yield ListView(
                    ListItem(Label("Transcribe"), id="transcribe"),
                    ListItem(Label("Settings"), id="settings"),
                    ListItem(Label("System Status"), id="status"),
                    ListItem(Label("Run Tests"), id="tests"),
                    ListItem(Label("Exit"), id="exit"),
                    id="menu",
                )
            with Container(id="content"):
                yield TranscribeView(id="view-transcribe")
                yield SettingsView(id="view-settings")
                yield StatusView(id="view-status")
                yield TestsView(id="view-tests")
        yield Footer()

    def on_mount(self) -> None:
        self._show_view("transcribe")
        self.query_one("#menu", ListView).index = 0

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        target_id = event.item.id
        if target_id == "exit":
            self.exit()
            return
        if target_id == "transcribe":
            self._show_view("transcribe")
        elif target_id == "settings":
            self._show_view("settings")
        elif target_id == "status":
            self._show_view("status")
        elif target_id == "tests":
            self._show_view("tests")

    def _show_view(self, name: str) -> None:
        self.current_view = name
        self.query_one("#view-transcribe").display = name == "transcribe"
        self.query_one("#view-settings").display = name == "settings"
        self.query_one("#view-status").display = name == "status"
        self.query_one("#view-tests").display = name == "tests"


class TranscribeView(Static):
    """Transcription form view."""

    def compose(self) -> ComposeResult:
        yield Label("Transcribe a file", classes="title")
        with Vertical(classes="section"):
            yield Label("Input file (.mp3 or .mp4)")
            yield Input(placeholder="C:\\path\\to\\audio.mp3", id="input_path")
            yield Label("Output directory (optional)")
            yield Input(placeholder="Leave blank to use input folder", id="output_dir")
        with Vertical(classes="section"):
            yield Label("Model (optional)")
            yield Input(placeholder="Defaults to config", id="model")
            yield Label("Device (optional)")
            yield Input(placeholder="Defaults to config", id="device")
        with Horizontal(classes="section"):
            yield Button("Run", id="run", classes="-primary")
            yield Button("Clear", id="clear")
        yield Static("", id="message")

    def on_show(self) -> None:
        config = _safe_load_config()
        message = self.query_one("#message", Static)
        message.update(f"Defaults: model={config.engine.model}, device={config.engine.device}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "clear":
            self._clear_inputs()
            return
        if event.button.id == "run":
            self._start_transcription()

    def _clear_inputs(self) -> None:
        for input_id in ["#input_path", "#output_dir", "#model", "#device"]:
            self.query_one(input_id, Input).value = ""

    def _start_transcription(self) -> None:
        config = _safe_load_config()
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
        model_value = self.query_one("#model", Input).value.strip() or config.engine.model
        device_value = self.query_one("#device", Input).value.strip() or config.engine.device

        request = TranscribeRequest(
            input_path=input_path,
            output_dir=output_dir,
            model=model_value,
            device=device_value,
        )

        self._set_message("Transcribing... This may take a while.")
        self.query_one("#run", Button).disabled = True
        threading.Thread(target=self._transcribe_thread, args=(request,), daemon=True).start()

    def _transcribe_thread(self, request: TranscribeRequest) -> None:
        try:
            output_path = _run_transcription(request)
            self.app.call_from_thread(
                self._set_message, f"Saved transcript: {output_path}", False
            )
        except MediaError as exc:
            self.app.call_from_thread(self._set_message, f"Media error: {exc}", True)
        except ModuleNotFoundError as exc:
            self.app.call_from_thread(self._set_message, str(exc), True)
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.app.call_from_thread(self._set_message, f"Error: {exc}", True)
        finally:
            self.app.call_from_thread(self._enable_run)

    def _enable_run(self) -> None:
        self.query_one("#run", Button).disabled = False

    def _set_message(self, text: str, error: bool = False) -> None:
        message = self.query_one("#message", Static)
        message.update(text)
        message.id = "error" if error else "message"


class SettingsView(Static):
    """Settings view for configuration updates."""

    def compose(self) -> ComposeResult:
        yield Label("Settings", classes="title")
        with Vertical(classes="section"):
            yield Static("", id="config_path")
            yield Label("Model")
            yield Input(id="model")
            yield Label("Device")
            yield Input(id="device")
        with Horizontal(classes="section"):
            yield Button("Save", id="save", classes="-primary")
            yield Button("Reset to defaults", id="reset")
        yield Static("", id="message")

    def on_show(self) -> None:
        config = _safe_load_config()
        self.query_one("#config_path", Static).update(f"Config path: {get_config_path()}")
        self.query_one("#model", Input).value = config.engine.model
        self.query_one("#device", Input).value = config.engine.device

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self._save()
        elif event.button.id == "reset":
            self._reset()

    def _save(self) -> None:
        config = _safe_load_config()
        model = self.query_one("#model", Input).value.strip() or config.engine.model
        device = self.query_one("#device", Input).value.strip() or config.engine.device

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
            self._set_message(f"Saved: {path}", error=False)
        except ValueError as exc:
            self._set_message(f"Config error: {exc}", error=True)

    def _reset(self) -> None:
        try:
            path = save_config(AppConfig())
            self.on_show()
            self._set_message(f"Reset to defaults: {path}", error=False)
        except ValueError as exc:
            self._set_message(f"Config error: {exc}", error=True)

    def _set_message(self, text: str, error: bool = False) -> None:
        message = self.query_one("#message", Static)
        message.update(text)
        message.id = "error" if error else "message"


class StatusView(Static):
    """Live system status view."""

    def compose(self) -> ComposeResult:
        yield Label("System status", classes="title")
        with Vertical(classes="section"):
            yield Static("", id="stats")
            yield Button("Refresh", id="refresh")

    def on_mount(self) -> None:
        try:
            import psutil  # type: ignore

            psutil.cpu_percent(interval=None)
        except ModuleNotFoundError:
            pass

        self._refresh()
        self.set_interval(1.0, self._refresh)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            self._refresh()

    def _refresh(self) -> None:
        self.query_one("#stats", Static).update(_system_stats())


class TestsView(Static):
    """Test runner view."""

    def compose(self) -> ComposeResult:
        yield Label("Run tests", classes="title")
        with Vertical(classes="section"):
            yield Button("Run tests", id="run", classes="-primary")
            yield TextLog(id="output", highlight=True, markup=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run":
            self._run_tests()

    def _run_tests(self) -> None:
        output = self.query_one("#output", TextLog)
        output.clear()
        output.write("Running tests...\n")
        threading.Thread(target=self._run_tests_thread, daemon=True).start()

    def _run_tests_thread(self) -> None:
        output = self.query_one("#output", TextLog)
        try:
            code, result = run_tests()
            summary = "Tests passed." if code == 0 else f"Tests failed (exit code {code})."
            text = (result or "").strip()
            combined = f"{summary}\n\n{text}" if text else summary
            self.app.call_from_thread(output.write, combined)
        except ModuleNotFoundError as exc:
            self.app.call_from_thread(output.write, str(exc))
        except Exception as exc:  # noqa: BLE001 - UI boundary
            self.app.call_from_thread(output.write, f"Error: {exc}")


def _safe_load_config() -> AppConfig:
    """Load config with fallback to defaults."""

    try:
        return load_config()
    except ValueError:
        return AppConfig()
