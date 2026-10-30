"""Command line: python -m jobflow SPEC.json [--json]"""
import argparse
import json
import sys

from .config import load_jobs
from .model import ConfigError
from .report import render, to_dicts
from .runner import run


def build_parser():
    p = argparse.ArgumentParser(prog="jobflow", description="Run the jobs in a spec file.")
    p.add_argument("spec")
    p.add_argument("--json", action="store_true", help="print results as JSON")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        with open(args.spec, encoding="utf-8") as f:
            jobs = load_jobs(json.load(f))
        results = run(jobs)
    except ConfigError as e:
        print(f"jobflow: error: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(to_dicts(results), indent=2, default=str))
    else:
        print(render(results))
    return 0 if all(r.status == "ok" for r in results) else 1
