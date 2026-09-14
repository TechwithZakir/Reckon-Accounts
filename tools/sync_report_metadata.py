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
            "roles": [{"role": role} for role in ("Accounts User", "Accounts Manager", "Auditor")],
            "filters": [],
            "columns": [],
        }
        (folder / (slug + ".json")).write_text(
            json.dumps(metadata, indent=1) + "\n", encoding="utf-8"
        )
    workspace_path = PACKAGE / "reckon_accounts/workspace/reckon_accounts/reckon_accounts.json"
    workspace = json.loads(workspace_path.read_text(encoding="utf-8-sig"))
    # Keep existing ledger links while adding separately labelled custom/standard groups.
    existing = {
        item.get("link_to")
        for item in workspace["links"]
        if item.get("link_to") not in BOOK_REPORTS
    }
    ledger_names = [
        name
        for name in ("Party Ledger", "Account Ledger", "General Ledger Custom")
        if name in existing
    ]
    groups = {
        "Ledgers": ledger_names,
        "Tally Books and Summaries": list(BOOK_REPORTS),
        "ERPNext Standard Reports": [
            "General Ledger",
            "Trial Balance",
            "Balance Sheet",
            "Profit and Loss Statement",
            "Cash Flow",
            "Financial Ratios",
            "Accounts Receivable",
            "Accounts Payable",
            "Bank Reconciliation Statement",
        ],
    }
    workspace["links"] = []
    content = [{"id": "heading", "type": "header", "data": {"text": "Reckon Accounts", "col": 12}}]
    for index, (label, names) in enumerate(groups.items()):
        workspace["links"].append({"type": "Card Break", "label": label})
        workspace["links"].extend(
            {
                "type": "Link",
                "label": name,
                "link_type": "Report",
                "link_to": name,
                "is_query_report": 1,
            }
            for name in names
        )
        content.append(
            {"id": "card-" + str(index), "type": "card", "data": {"card_name": label, "col": 12}}
        )
    workspace["content"] = json.dumps(content)
    workspace["links"].append({"type": "Card Break", "label": "ERPNext Interest and Collections"})
    workspace["links"].append(
        {
            "type": "Link",
            "label": "Sales Interest / Dunning",
            "link_type": "DocType",
            "link_to": "Dunning",
        }
    )
    content.append(
        {
            "id": "interest",
            "type": "card",
            "data": {"card_name": "ERPNext Interest and Collections", "col": 12},
        }
    )
    workspace["content"] = json.dumps(content)
    workspace_path.write_text(json.dumps(workspace, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
