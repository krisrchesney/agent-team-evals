"""Turn a CSV of sales transactions into a fixed-width revenue report."""
from .errors import ParseError
from .report import build_report

__all__ = ["ParseError", "build_report"]
