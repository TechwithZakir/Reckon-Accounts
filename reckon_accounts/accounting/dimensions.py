"""Metadata allowlists and permission-scoped tree expansion."""

import re

from reckon_accounts.accounting.permissions import ScopeError


def dimension_contract(gl_meta, definitions):
    result = {}
    for fieldname, doctype in [("cost_center", "Cost Center"), ("project", "Project")]:
        field = gl_meta.get_field(fieldname)
        if not field or field.fieldtype != "Link" or field.options != doctype:
            raise ScopeError("GL dimension schema is incompatible")
        result[fieldname] = doctype
    for definition in definitions:
        fieldname = definition["fieldname"]
        doctype = definition["document_type"]
        if doctype == "Finance Book":
            continue
        if not re.fullmatch(r"[a-z][a-z0-9_]*", fieldname):
            raise ScopeError("Invalid accounting dimension metadata")
        field = gl_meta.get_field(fieldname)
        if not field or field.fieldtype != "Link" or field.options != doctype:
            raise ScopeError("Accounting dimension does not match the GL schema")
        if fieldname in result:
            raise ScopeError("Duplicate accounting dimension field")
        result[fieldname] = doctype
    return result


def expand_selection(gateway, permissions, doctype, names, company, *, limit=2000):
    """Expand permitted descendants; never make an empty selection unrestricted."""
    expanded = set()
    meta = gateway.meta(doctype)
    for name in names:
        if name is None:
            expanded.add(None)
            continue
        record = permissions.require(doctype, name)
        if meta.has_field("company") and "company" not in record:
            raise ScopeError("Dimension company ownership is not readable")
        if meta.has_field("company") and record.get("company") not in (None, "", company):
            raise ScopeError("Selected account or dimension belongs to another company")
        expanded.add(name)
        if meta.is_tree:
            if record.get("lft") is None or record.get("rgt") is None:
                raise ScopeError("Tree boundaries are unavailable")
            filters = [["lft", ">=", record["lft"]], ["rgt", "<=", record["rgt"]]]
            if meta.has_field("company"):
                filters.append(["company", "=", company])
            descendants = gateway.list_records(doctype, filters=filters, limit=limit + 1)
            if len(descendants) > limit:
                raise ScopeError("Selected hierarchy is too large; choose a smaller group")
            permissions.load(doctype, [row["name"] for row in descendants])
            expanded.update(
                row["name"] for row in descendants if permissions.get(doctype, row["name"])
            )
    if len(expanded) > limit:
        raise ScopeError("Selected hierarchy is too large")
    return frozenset(expanded)
