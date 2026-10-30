"""Entry point: pick the supplier's importer and run it."""
from .importers.registry import VENDORS


class UnknownVendor(KeyError):
    pass


def run_import(vendor, text, settings=None):
    try:
        importer_cls = VENDORS[vendor]
    except KeyError:
        raise UnknownVendor(vendor) from None
    return importer_cls(settings).parse(text)
