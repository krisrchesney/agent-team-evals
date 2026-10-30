"""Per-supplier settings from config/vendors.json."""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "vendors.json"


def vendor_settings(vendor, path=CONFIG_PATH):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)[vendor]
