"""Install the application roles and their accounting permissions."""

from reckon_accounts.access_control import setup_roles_and_permissions


def execute():
    setup_roles_and_permissions()
