"""Supplier id -> importer class. The id is also the key in config/vendors.json."""
from .acme import AcmeImporter
from .bolt import BoltImporter

VENDORS = {
    "acme": AcmeImporter,
    "bolt": BoltImporter,
}
