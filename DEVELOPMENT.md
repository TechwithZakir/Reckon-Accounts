# Development and compatibility

## Targets

Phase 1 report source is implemented. See [PHASE1_VALIDATION.md](PHASE1_VALIDATION.md)
for the current test workflow and unexecuted live gates; the initial discovery
document is historical evidence, not the current implementation status.

The owner selected both Frappe/ERPNext 15 and 16. Develop and validate against two
separate disposable benches with matching framework/ERPNext major versions. Record
the exact commits used by each test run. Do not require a real customer site.

Upstream source inspected on 2026-09-12:

- [Frappe v15 Python metadata](https://github.com/frappe/frappe/blob/version-15/pyproject.toml):
  Python >=3.10,<3.15; use Python 3.12 for the initial v15 test bench.
- [Frappe v16 Python metadata](https://github.com/frappe/frappe/blob/version-16/pyproject.toml):
  Python >=3.14,<3.15; use Python 3.14 for the v16 test bench.
- [App structure](https://docs.frappe.io/framework/user/en/tutorial/create-an-app).

The app's Python range describes its own source; it does not override the selected
framework's stricter Python/runtime requirements. Check Node, database, Redis and
system requirements for the exact upstream revision when provisioning benches.

## Source-only checks

```sh
python -m unittest discover -s reckon_accounts/tests -v
node --test reckon_accounts/tests/test_report_controls.cjs
python -m compileall -q reckon_accounts
ruff check reckon_accounts
git diff --check
```

These do not prove Frappe installation, workspace rendering, permission enforcement,
or accounting reconciliation. No network service or customer database is required.

## Development-bench workflow

On each provisioned Linux development bench, install the matching ERPNext version
and create a disposable site using that version's documented setup. Then, from the
bench directory, replacing the placeholders:

```sh
bench get-app /absolute/path/to/Reckon-Accounts
bench --site <development-site> install-app reckon_accounts
bench build --app reckon_accounts
```

Do not run `bench new-app` over this existing package. The command examples are
development instructions, not commands already executed. No deployment is included.

## Required integration gates

For each major version: install app; confirm module/workspace sync and role visibility;
inspect accounting schemas and helper signatures; implement tested version adapters;
post standard test transactions; reconcile Reckon ledgers with General Ledger;
exercise restricted users, dimensions, Finance Book, currencies, pagination, exports,
cancellation and opening entries. Verify upgrade/migration and clean uninstall on
disposable sites before release. Full milestone completion requires these results.

The current host has no discovered Bench runtime or database. That does not block
source development. Integration results must remain marked not run until a development
bench or CI environment is available. No support claim follows merely from dependency ranges.

## Home and navigation update

The home workspace uses nine cards in three columns at desktop width. It includes
all 23 app reports, nine reused standard reports, and 22 accounting DocTypes.
Frappe 15 exposes grouped child workspaces beneath Reckon Accounts; Frappe 16
imports the app-level Workspace Sidebar with expandable report/DocType sections.
Framework permission filtering remains active. No ERPNext DocType is moved to
this app, and no additional accounting masters are created.

After transferring the updated source to the installed app folder, run from Bench:

```sh
bench --site your-site migrate
bench build --app reckon_accounts
bench --site your-site clear-cache
```

Reload Desk after migration. A personalized workspace/sidebar can take precedence
over the public app layout; use the standard public workspace when checking this
update. Visual verification on both live framework versions remains pending.

Source references: [v15 workspace schema](https://github.com/frappe/frappe/blob/version-15/frappe/desk/doctype/workspace/workspace.json),
[v16 sidebar sync](https://github.com/frappe/frappe/blob/version-16/frappe/model/sync.py).
