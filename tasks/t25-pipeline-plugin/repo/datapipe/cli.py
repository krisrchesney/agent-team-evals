"""python -m datapipe CONFIG.json INPUT.jsonl  (records out as JSON lines, dead letters counted on stderr)"""
import argparse
import json
import sys

from .config import build_pipeline
from .errors import PipelineError


def main(argv=None, stdout=None, stderr=None):
    stdout, stderr = stdout or sys.stdout, stderr or sys.stderr
    parser = argparse.ArgumentParser(prog="datapipe")
    parser.add_argument("config")
    parser.add_argument("input")
    args = parser.parse_args(argv)
    try:
        with open(args.config, encoding="utf-8") as fh:
            pipe = build_pipeline(json.load(fh))
        with open(args.input, encoding="utf-8") as fh:
            records = [json.loads(line) for line in fh if line.strip()]
        result = pipe.run(records)
    except PipelineError as err:
        print(f"datapipe: {err}", file=stderr)
        return 1
    for record in result.records:
        print(json.dumps(record, sort_keys=True), file=stdout)
    if result.dead_letters:
        print(f"datapipe: {len(result.dead_letters)} record(s) rejected", file=stderr)
    return 0
