"""CLI commands for Transcriber."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer

from .config import EngineConfig, get_config_path, load_config
from .logging import configure_logging
from engine import create_engine
from media.audio import MediaError, prepared_audio
from output.text import write_text_file


def create_cli_app() -> typer.Typer:
    """Create the Typer CLI app (kept as a factory to avoid global state)."""

    app = typer.Typer(
        add_completion=False,
        help="Offline MP3/MP4 transcription to TXT using faster-whisper.",
        no_args_is_help=True,
    )

    @app.command("run")
    def run(
        input_file: Path = typer.Argument(
            ...,
            exists=True,
            readable=True,
            dir_okay=False,
            help="Path to an .mp3 or .mp4 file.",
        ),
        out: Optional[Path] = typer.Option(
            None,
            "--out",
            "-o",
            file_okay=False,
            dir_okay=True,
            help="Output directory for the .txt transcript (defaults to input file directory).",
        ),
        model: Optional[str] = typer.Option(
            None,
            "--model",
            help="Whisper model size or local model path (default: small).",
        ),
        device: Optional[str] = typer.Option(
            None,
            "--device",
            help="Inference device (overrides config; default: cpu).",
        ),
        verbose: bool = typer.Option(
            False,
            "--verbose",
            help="Enable debug logging.",
        ),
    ) -> None:
        """Transcribe a single MP3/MP4 file to a plain-text .txt file."""

        configure_logging(verbose=verbose)
        logger = logging.getLogger("transcriber")

        try:
            config = load_config()
        except ValueError as exc:
            typer.secho(f"Config error: {exc}", fg=typer.colors.RED, err=True)
            typer.secho(f"Config path: {get_config_path()}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2) from exc

        engine_config = EngineConfig(
            backend=config.engine.backend,
            model=model or config.engine.model,
            device=device or config.engine.device,
        )

        output_dir = out or input_file.parent
        output_path = output_dir / f"{input_file.stem}.txt"

        try:
            engine = create_engine(engine_config)
            with prepared_audio(input_file) as audio_path:
                logger.info("Transcribing: %s", input_file.name)
                text = engine.transcribe(audio_path, language=None)
            write_text_file(output_path, text)
        except MediaError as exc:
            typer.secho(f"Media error: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2) from exc
        except ModuleNotFoundError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2) from exc
        except Exception as exc:  # noqa: BLE001 - intentional CLI boundary
            typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        typer.echo(str(output_path))

    return app
