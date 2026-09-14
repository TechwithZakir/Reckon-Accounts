from reckon_accounts.accounting.books import execute as execute_book


def execute(filters=None):
    return execute_book("Debit Note Register", filters)
