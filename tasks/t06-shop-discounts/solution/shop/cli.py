"""Command line: python -m shop CATALOG.json ORDER.json [--coupon CODE]... [--json]"""
import argparse
import dataclasses
import json
import sys

from .coupons import UnknownCoupon
from .invoice import render_invoice
from .loader import catalog_from_list, order_from_dict, quote_to_dict
from .pricing import price_order


def build_parser():
    p = argparse.ArgumentParser(prog="shop", description="Price an order and print the invoice.")
    p.add_argument("catalog")
    p.add_argument("order")
    p.add_argument("--coupon", action="append", default=[], metavar="CODE")
    p.add_argument("--json", action="store_true", help="print the quote as JSON instead")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    with open(args.catalog, encoding="utf-8") as f:
        catalog = catalog_from_list(json.load(f))
    with open(args.order, encoding="utf-8") as f:
        order = order_from_dict(json.load(f))
    order = dataclasses.replace(order, coupons=tuple(order.coupons) + tuple(args.coupon))
    try:
        quote = price_order(order, catalog)
    except UnknownCoupon as e:
        print(f"shop: error: unknown coupon '{e}'", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(quote_to_dict(quote), indent=2))
    else:
        print(render_invoice(quote))
    return 0
