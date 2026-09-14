import importlib
import sys
import unittest
from unittest.mock import patch

from reckon_accounts.tests.fakes import FakeGateway, gl


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.gateway = FakeGateway()
        self.gateway.records["GL Entry"] = [gl(), gl("second", debit=50)]
        self.environment = self.gateway.installed()
        self.environment.__enter__()
        # Keep the double confined to these tests, including in a real bench run.
        self.previous = sys.modules.pop("reckon_accounts.api", None)
        self.api = importlib.import_module("reckon_accounts.api")
        self.gateway_patch = patch.object(self.api, "get_gateway", return_value=self.gateway)
        self.gateway_patch.start()

    def tearDown(self):
        self.gateway_patch.stop()
        sys.modules.pop("reckon_accounts.api", None)
        if self.previous is not None:
            sys.modules["reckon_accounts.api"] = self.previous
        self.environment.__exit__(None, None, None)

    def test_frappe_filter_control_normalization(self):
        parsed = self.api.normalize_report_filters(
            {"account": "", "show_opening_entries": 0, "dimensions": '{"project":["Project A"]}'}
        )
        self.assertIsNone(parsed["account"])
        self.assertIs(parsed["show_opening_entries"], False)
        self.assertEqual(parsed["dimensions"], {"project": ["Project A"]})
        with self.assertRaises(ValueError):
            self.api.normalize_report_filters("[]")

    def test_full_export_checks_permission_and_ignores_current_page(self):
        filters = {
            "company": "Co",
            "from_date": "2026-01-01",
            "to_date": "2026-01-31",
            "page": 2,
            "page_size": 1,
        }
        self.api.export_ledger("General Ledger Custom", filters)
        response = self.gateway.frappe.local.response
        self.assertTrue(response["filename"].endswith("_full.csv"))
        self.assertIn(b"gl-1", response["filecontent"])
        self.assertIn(b"second", response["filecontent"])
        self.gateway.export_denied = True
        self.gateway.frappe.local.response.clear()
        with self.assertRaises(PermissionError):
            self.api.export_ledger("General Ledger Custom", filters)
        self.assertEqual(self.gateway.frappe.local.response, {})

    def test_selection_search_obeys_document_permission(self):
        self.gateway.denied_docs.add(("Customer", "Bob"))
        records = self.api.search_records(
            "Customer",
            "",
            "name",
            0,
            20,
            {
                "report_name": "Party Ledger",
                "scope_field": "party",
                "company": "Co",
                "party_type": "Customer",
            },
        )
        self.assertEqual(records, [["Alice", "Alice Ltd"]])

    def test_arbitrary_doctype_and_report_search_rejected(self):
        with self.assertRaises(PermissionError):
            self.api.search_records(
                "User",
                "",
                "name",
                0,
                20,
                {"report_name": "General Ledger Custom", "scope_field": "account"},
            )
        self.gateway.report_denied = True
        with self.assertRaises(PermissionError):
            self.api.filter_options("General Ledger Custom")

    def test_metadata_contains_only_available_party_types(self):
        result = self.api.filter_options("General Ledger Custom")
        self.assertEqual(result["party_types"], ["Customer", "Other"])
        self.gateway.denied_types.add("Customer")
        self.assertEqual(self.api.filter_options("General Ledger Custom")["party_types"], ["Other"])
