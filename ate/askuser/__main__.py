"""`python -m ate.askuser --answers answers.json --log run.jsonl` runs the server (same as server.py)."""
from .server import main

raise SystemExit(main())
