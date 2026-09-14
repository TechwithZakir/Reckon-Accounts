from reckon_accounts.accounting.reporting import execute_report


def execute(filters=None):
    return execute_report("Account Ledger", filters)
