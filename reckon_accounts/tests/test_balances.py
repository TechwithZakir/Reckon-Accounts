"""Independent expected amounts for the shared ledger arithmetic contract."""

import unittest
from decimal import Decimal

from reckon_accounts.accounting.balances import Balance, as_decimal, closing_balance, net_balance


class TestBalances(unittest.TestCase):
    def test_customer_example(self):
        result = closing_balance("50000", "25000", "15000")
        self.assertEqual(result.net, Decimal(60000))
        self.assertEqual((result.debit, result.credit, result.balance_type), (60000, 0, "Dr"))

    def test_supplier_credit_balance(self):
        result = closing_balance("-10000", "3000", "5000")
        self.assertEqual((result.net, result.debit, result.credit), (-12000, 0, 12000))
        self.assertEqual(result.balance_type, "Cr")

    def test_overpayment_crosses_zero(self):
        result = closing_balance("100", "0", "125")
        self.assertEqual((result.net, result.balance_type), (-25, "Cr"))

    def test_zero_has_no_side(self):
        result = net_balance("0.10", "0.10")
        self.assertEqual((result.debit, result.credit, result.balance_type), (0, 0, ""))

    def test_decimal_precision_is_preserved(self):
        self.assertEqual(closing_balance(0.1, 0.2, 0.3).net, Decimal("0.0"))
        self.assertEqual(net_balance("1.12345", "0.00001").net, Decimal("1.12344"))

    def test_page_carry_forward(self):
        first_page = closing_balance("100", "25", "30")
        second_page = closing_balance(first_page.net, "0", "20")
        self.assertEqual(first_page.net, Decimal(95))
        self.assertEqual(second_page.net, Decimal(75))

    def test_invalid_amounts_are_rejected(self):
        for value in (True, False, None, "", "invalid", "NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                as_decimal(value)

    def test_direct_balance_validates_amount(self):
        with self.assertRaises(ValueError):
            Balance(Decimal("NaN"))


if __name__ == "__main__":
    unittest.main()
