"""tasklog: a small task list for the terminal.

    python -m tasklog add "Buy milk" --project home --due 2026-03-05
    python -m tasklog list --status open
    python -m tasklog done 1
"""
from .cli import main

__all__ = ["main"]
