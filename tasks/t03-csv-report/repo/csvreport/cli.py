"""Command line: python -m csvreport FILE --group-by COL --sum COL"""
import argparse

from .aggregate import group_sum
from .reader import read_rows
from .render import render


def build_parser():
    p = argparse.ArgumentParser(prog="csvreport", description="Group CSV rows and total a column.")
    p.add_argument("path")
    p.add_argument("--group-by", required=True, metavar="COL")
    p.add_argument("--sum", required=True, metavar="COL")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    rows = read_rows(args.path)
    totals = group_sum(rows, args.group_by, args.sum)
    print(render(totals, args.group_by, "sum_" + args.sum))
    return 0
