"""Logging setup for the Transcriber application."""

from __future__ import annotations

import logging


def configure_logging(verbose: bool = False) -> None:
    """Configure application logging.

    Args:
        verbose: When True, sets the log level to DEBUG. Otherwise WARNING.
    """

    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )
