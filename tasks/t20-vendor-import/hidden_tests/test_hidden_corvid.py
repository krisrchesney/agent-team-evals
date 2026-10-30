"""Hidden tests for t20. Each test name names where its rule is written in the repo:
imp<N> = docs/IMPORTERS.md item N, vendor = docs/vendors/corvid.md, cfg = config/vendors.json,
reg = existing behaviour that must keep working.
"""
import datetime
import unittest
from pathlib import Path

import ingest
from ingest.importers.registry import VENDORS
from ingest.summary import totals_by_currency

HEADER = "Rechnung;Pos;Artikel;Bezeichnung;Menge;Einzelpreis;Waehrung;Datum;Faellig;Status"
SAMPLES = Path(__file__).resolve().parent.parent / "samples"
D = datetime.date


def row(rechnung="R-1", pos="1", artikel="CV-1", text="Teil", menge="1", preis="1,00", waehrung="",
        datum="01.05.2024", faellig="", status="OK"):
    return ";".join([rechnung, pos, artikel, text, menge, preis, waehrung, datum, faellig, status])


def corvid(*rows, bom=True):
    return ("﻿" if bom else "") + "\n".join([HEADER, *rows]) + "\n"


def run(*rows, **kw):
    return ingest.run_import("corvid", corvid(*rows, **kw))


class Registration(unittest.TestCase):
    def test_imp2_registered_under_its_id(self):
        self.assertIn("corvid", VENDORS)
        self.assertEqual(VENDORS["corvid"].vendor, "corvid")

    def test_imp1_unknown_vendor_still_raises(self):
        with self.assertRaises(ingest.UnknownVendor):
            ingest.run_import("dodo", "x\n")


class Sample(unittest.TestCase):
    def test_vendor_the_real_export(self):
        result = ingest.run_import("corvid", (SAMPLES / "corvid_2024-05.csv").read_text(encoding="utf-8"))
        self.assertEqual(result.errors, [])
        self.assertEqual(result.vendor, "corvid")
        self.assertEqual(
            [(r.invoice_id, r.line_no, r.sku, r.description, r.qty, r.unit_cents, r.currency, r.invoice_date, r.due_date)
             for r in result.records],
            [("R-2024-0117", 1, "CV10220", "Gehäuse, Aluminium", 4, 123450, "EUR", D(2024, 5, 6), D(2024, 6, 5)),
             ("R-2024-0117", 2, "CV10221", "Deckel; schwarz", 4, 8990, "EUR", D(2024, 5, 6), D(2024, 6, 20)),
             ("R-2024-0118", 1, "CV305", "Montagesatz komplett", 1, 1200, "CHF", D(2024, 5, 21), D(2024, 7, 5))])
        self.assertEqual(totals_by_currency(result.records), {"CHF": 1200, "EUR": 529760})

    def test_vendor_records_are_invoice_lines(self):
        record = run(row()).records[0]
        self.assertIsInstance(record, ingest.InvoiceLine)
        self.assertEqual(record.vendor, "corvid")


class Fields(unittest.TestCase):
    def test_vendor_german_number_format(self):
        cases = {"1.234,50": 123450, "0,5": 50, "12": 1200, "12,3": 1230, "1.000.000,00": 100000000,
                 "999,99": 99999, "0": 0}
        for text, cents in cases.items():
            with self.subTest(text=text):
                self.assertEqual(run(row(preis=text)).records[0].unit_cents, cents)

    def test_imp4_bad_amounts(self):
        for text in ("1,234.50", "12,345", "-5,00", "12.5", "1.23,00", "abc", "1 234,50"):
            with self.subTest(text=text):
                result = run(row(preis=text))
                self.assertEqual((result.records, result.errors), ([], [ingest.RowError(2, "bad_amount")]))

    def test_vendor_dates(self):
        record = run(row(datum="31.12.2024", faellig="15.01.2025")).records[0]
        self.assertEqual((record.invoice_date, record.due_date), (D(2024, 12, 31), D(2025, 1, 15)))

    def test_imp4_bad_dates(self):
        for datum, faellig in (("2024-05-01", ""), ("31.02.2024", ""), ("05/01/2024", ""),
                               ("01.05.2024", "2024-06-01"), ("01.05.2024", "32.05.2024")):
            with self.subTest(datum=datum, faellig=faellig):
                self.assertEqual(run(row(datum=datum, faellig=faellig)).errors, [ingest.RowError(2, "bad_date")])

    def test_imp10_due_date_defaults_to_corvid_terms(self):
        self.assertEqual(run(row(datum="01.05.2024")).records[0].due_date, D(2024, 6, 15))
        self.assertEqual(run(row(datum="20.12.2024")).records[0].due_date, D(2025, 2, 3))

    def test_cfg_terms_come_from_settings(self):
        result = ingest.run_import("corvid", corvid(row(datum="01.05.2024")),
                                   settings={"currency": "SEK", "terms_days": 10})
        self.assertEqual((result.records[0].due_date, result.records[0].currency), (D(2024, 5, 11), "SEK"))

    def test_imp9_currency(self):
        self.assertEqual(run(row(waehrung="")).records[0].currency, "EUR")
        self.assertEqual(run(row(waehrung="  ")).records[0].currency, "EUR")
        self.assertEqual(run(row(waehrung="GBP")).records[0].currency, "GBP")
        self.assertEqual(run(row(waehrung="XYZ")).errors, [ingest.RowError(2, "unknown_currency")])

    def test_imp7_sku_and_description_are_normalized(self):
        record = run(row(artikel=" cv-10 220 ", text="  Deckel   für\tKasten ")).records[0]
        self.assertEqual((record.sku, record.description), ("CV10220", "Deckel für Kasten"))
        self.assertEqual(run(row(text="")).records[0].description, "")

    def test_imp11_ids_kept_as_written(self):
        record = run(row(rechnung=" R-2024-0117 ", pos=" 7 ")).records[0]
        self.assertEqual((record.invoice_id, record.line_no), ("R-2024-0117", 7))

    def test_vendor_quoted_fields(self):
        text = corvid('R-1;1;CV-1;"Deckel; schwarz, ""matt""";2;1,00;;01.05.2024;;OK')
        self.assertEqual(ingest.run_import("corvid", text).records[0].description, 'Deckel; schwarz, "matt"')

    def test_imp3_with_or_without_bom(self):
        self.assertEqual(len(run(row(), bom=False).records), 1)
        self.assertEqual(len(run(row(), bom=True).records), 1)


class Rows(unittest.TestCase):
    def test_imp4_quantity(self):
        self.assertEqual(run(row(menge="12")).records[0].qty, 12)
        for menge in ("0", "-1", "1,5", "2.000", "x"):
            with self.subTest(menge=menge):
                self.assertEqual(run(row(menge=menge)).errors, [ingest.RowError(2, "bad_qty")])

    def test_imp4_missing_fields(self):
        for field in ("rechnung", "pos", "artikel", "menge", "preis", "datum"):
            with self.subTest(field=field):
                self.assertEqual(run(row(**{field: "  "})).errors, [ingest.RowError(2, "missing_field")])

    def test_imp4_first_problem_in_field_order(self):
        self.assertEqual(run(row(menge="0", preis="x", datum="bad")).errors, [ingest.RowError(2, "bad_qty")])
        self.assertEqual(run(row(preis="x", waehrung="XYZ")).errors, [ingest.RowError(2, "bad_amount")])
        self.assertEqual(run(row(waehrung="XYZ", datum="bad")).errors, [ingest.RowError(2, "unknown_currency")])

    def test_imp4_bad_rows_do_not_stop_the_import(self):
        result = run(row(pos="1"), row(pos="2", preis="x"), row(pos="3"), row(pos="4", datum="x"), row(pos="5"))
        self.assertEqual([r.line_no for r in result.records], [1, 3, 5])
        self.assertEqual(result.errors, [ingest.RowError(3, "bad_amount"), ingest.RowError(5, "bad_date")])

    def test_imp5_storno_lines_are_skipped_silently(self):
        result = run(row(pos="1"), row(pos="2", status="STORNO"), row(pos="3"))
        self.assertEqual(([r.line_no for r in result.records], result.errors), ([1, 3], []))

    def test_imp5_storno_is_checked_before_anything_else(self):
        result = run(row(pos="1", status="STORNO", preis="kaputt", datum="", menge="0"))
        self.assertEqual((result.records, result.errors), ([], []))

    def test_imp5_imp6_storno_then_replacement_is_not_a_duplicate(self):
        result = run(row(pos="2", preis="5,00", status="STORNO"), row(pos="2", preis="4,00"))
        self.assertEqual(([r.unit_cents for r in result.records], result.errors), ([400], []))

    def test_imp6_duplicates(self):
        result = run(row(pos="1", preis="1,00"), row(pos="1", preis="2,00"), row(rechnung="R-2", pos="1"))
        self.assertEqual([(r.invoice_id, r.unit_cents) for r in result.records], [("R-1", 100), ("R-2", 100)])
        self.assertEqual(result.errors, [ingest.RowError(3, "duplicate_line")])


class Regression(unittest.TestCase):
    def test_reg_acme_and_bolt_unchanged(self):
        acme = ingest.run_import("acme", (SAMPLES / "acme_2024-05.csv").read_text(encoding="utf-8"))
        bolt = ingest.run_import("bolt", (SAMPLES / "bolt_2024-05.tsv").read_text(encoding="utf-8"))
        self.assertEqual((len(acme.records), acme.errors), (3, []))
        self.assertEqual((len(bolt.records), bolt.errors), (2, []))
        self.assertEqual(acme.records[2].due_date, D(2024, 6, 9))


if __name__ == "__main__":
    unittest.main()
