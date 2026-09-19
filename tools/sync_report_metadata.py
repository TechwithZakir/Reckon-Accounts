"""Regenerate thin book registrations and workspace links from the report catalog."""

import json
from pathlib import Path

from reckon_accounts.accounting.catalog import BOOK_REPORTS

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "reckon_accounts"
REPORT_DIR = PACKAGE / "reckon_accounts" / "report"


def main():
    for name in BOOK_REPORTS:
        slug = name.lower().replace(" ", "_")
        folder = REPORT_DIR / slug
        folder.mkdir(exist_ok=True)
        (folder / "__init__.py").touch()
        (folder / (slug + ".py")).write_text(
            "from reckon_accounts.accounting.books import execute as execute_book\n\n\n"
            f"def execute(filters=None):\n    return execute_book({name!r}, filters)\n",
            encoding="utf-8",
        )
        (folder / (slug + ".js")).write_text(
            '{% include "reckon_accounts/public/js/report_filters.js" %}\n'
            f"frappe.query_reports[{json.dumps(name)}] = reckon_accounts.report_settings({json.dumps(name)});\n",
            encoding="utf-8",
        )
        metadata = {
            "doctype": "Report",
            "name": name,
            "report_name": name,
            "ref_doctype": "GL Entry",
            "module": "Reckon Accounts",
            "is_standard": "Yes",
            "report_type": "Script Report",
            "disabled": 0,
            "prepared_report": 0,
            "add_total_row": 0,
            "roles": [
                {"role": role}
                for role in (
                    "Accounts User",
                    "Accounts Manager",
                    "Reckon Accounts User",
                    "Reckon Accounts Manager",
                    "Auditor",
                )
            ],
            "filters": [],
            "columns": [],
        }
        (folder / (slug + ".json")).write_text(
            json.dumps(metadata, indent=1) + "\n", encoding="utf-8"
        )
    from reckon_accounts.navigation import sidebar_document, workspace_documents

    expected_workspaces = set()
    for workspace in workspace_documents():
        slug = workspace["name"].lower().replace(" ", "_")
        expected_workspaces.add(slug)
        folder = PACKAGE / "reckon_accounts" / "workspace" / slug
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (slug + ".json")).write_text(
            json.dumps(workspace, indent=1) + "\n", encoding="utf-8"
        )
    # Obsolete generated child workspaces are deliberately removed so Frappe 16
    # exposes one desktop app icon. The Workspace Sidebar provides all navigation.
    workspace_root = PACKAGE / "reckon_accounts" / "workspace"
    for folder in workspace_root.iterdir():
        if folder.is_dir() and folder.name.startswith("reckon_accounts_"):
            if folder.name not in expected_workspaces:
                for child in folder.iterdir():
                    child.unlink()
                folder.rmdir()
    folder = PACKAGE / "workspace_sidebar"
    folder.mkdir(exist_ok=True)
    (folder / "reckon_accounts.json").write_text(
        json.dumps(sidebar_document(), indent=1) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
