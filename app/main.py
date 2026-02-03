"""Console entry point for Transcriber."""

from __future__ import annotations


def main() -> None:
    """Run the Transcriber CLI."""

    from .cli import create_cli_app

    app = create_cli_app()
    app()

