import unittest

from reckon_accounts.accounting.permissions import PermissionScope, ScopeError
from reckon_accounts.tests.fakes import FakeGateway, gl


class TestPermissions(unittest.TestCase):
    def test_list_and_document_permissions_are_both_required(self):
        for attribute in ("denied_docs", "denied_list"):
            gateway = FakeGateway()
            getattr(gateway, attribute).add(("Customer", "Alice"))
            with self.subTest(attribute=attribute), self.assertRaises(ScopeError):
                PermissionScope(gateway).require("Customer", "Alice")

    def test_missing_type_permission_does_not_query(self):
        gateway = FakeGateway()
        gateway.denied_types.add("Customer")
        self.assertIsNone(PermissionScope(gateway).get("Customer", "Alice"))
        self.assertEqual(gateway.queries, [])

    def test_cache_is_request_local_and_negative_results_cached(self):
        gateway = FakeGateway()
        scope = PermissionScope(gateway)
        scope.get("Customer", "Missing")
        scope.get("Customer", "Missing")
        self.assertEqual(len(gateway.queries), 1)
        self.assertIsNot(scope.cache, PermissionScope(gateway).cache)

    def test_record_bound_fails_closed(self):
        with self.assertRaises(ScopeError):
            PermissionScope(FakeGateway(), max_documents=1).load("Customer", ["Alice", "Bob"])

    def test_source_party_account_and_dimension_denials_reject_row(self):
        for denied in (
            ("Account", "AR"),
            ("Customer", "Alice"),
            ("Journal Entry", "JV-1"),
            ("Cost Center", "Main CC"),
            ("GL Entry", "gl-1"),
            ("Finance Book", "Main"),
        ):
            gateway = FakeGateway()
            gateway.denied_docs.add(denied)
            with self.subTest(denied=denied):
                self.assertFalse(
                    PermissionScope(gateway).row_allowed(
                        gl(cost_center="Main CC", finance_book="Main"),
                        {"cost_center": "Cost Center"},
                    )
                )

    def test_enrichment_keeps_field_level_redactions(self):
        gateway = FakeGateway()
        gateway.hidden_fields["Customer"] = ["customer_name"]
        self.assertNotIn("customer_name", PermissionScope(gateway).require("Customer", "Alice"))
