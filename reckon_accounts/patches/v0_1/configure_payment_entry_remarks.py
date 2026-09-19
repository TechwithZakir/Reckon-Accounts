"""Move standard Payment Entry remarks below Mode of Payment."""

from reckon_accounts.payment_entry_setup import configure_payment_entry


def execute():
    configure_payment_entry()
