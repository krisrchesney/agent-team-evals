"""Splitting a SQL script into single statements, so each can run inside our own transaction.

`sqlite3.executescript` commits before it runs, so the runner cannot use it.
"""
import sqlite3


def split_statements(script):
    """Return the complete statements in `script`, in order, without comment-only or blank leftovers."""
    statements, buf = [], ""
    for line in script.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            if buf.strip():
                statements.append(buf.strip())
            buf = ""
    if buf.strip() and not _only_comments(buf):
        statements.append(buf.strip())
    return statements


def _only_comments(text):
    return all(not ln.strip() or ln.strip().startswith("--") for ln in text.splitlines())
