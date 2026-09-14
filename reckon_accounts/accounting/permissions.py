"""Request-local permission scope. No unrestricted financial reads or shared cache."""


class ScopeError(ValueError):
    pass


class PermissionScope:
    """Require list visibility AND document permission, including custom hooks.

    List queries enforce permission-query hooks and field-level visibility. Loaded
    documents are used only for permission checks; output/enrichment uses the
    fields returned by the permission-aware list query.
    """

    def __init__(self, gateway, *, max_documents=2000):
        self.gateway = gateway
        self.cache = {}
        self.max_documents = max_documents

    def load(self, doctype, names):
        missing = sorted({name for name in names if name and (doctype, name) not in self.cache})
        if len(self.cache) + len(missing) > self.max_documents:
            raise ScopeError(
                "Report permission scope is too large; narrow the account or party filters"
            )
        for name in missing:
            self.cache[(doctype, name)] = None
        if not missing or not self.gateway.can_read_type(doctype):
            return
        for start in range(0, len(missing), 200):
            batch = missing[start : start + 200]
            for record in self.gateway.list_records(
                doctype, filters={"name": ["in", batch]}, limit=len(batch)
            ):
                if record["name"] not in batch:
                    raise ScopeError("Unexpected record returned by permission query")
                if self.gateway.can_read_document(doctype, record["name"]):
                    self.cache[(doctype, record["name"])] = dict(record)

    def get(self, doctype, name):
        if not name:
            return None
        self.load(doctype, [name])
        return self.cache.get((doctype, name))

    def require(self, doctype, name):
        record = self.get(doctype, name)
        if record is None:
            # Deliberately avoid disclosing whether the excluded master exists.
            raise ScopeError("A selected record is unavailable or not permitted")
        return record

    def row_allowed(self, row, dimensions):
        if not self.gateway.can_read_document("GL Entry", row["name"]):
            return False
        account = self.get("Account", row.get("account"))
        if account is None:
            return False
        if "company" not in account:
            raise ScopeError("Account company ownership is not readable")
        if account["company"] != row["company"]:
            raise ScopeError("GL account company does not match")
        if row.get("party"):
            if not row.get("party_type") or self.get(row["party_type"], row["party"]) is None:
                return False
        if (
            not row.get("voucher_type")
            or self.get(row["voucher_type"], row.get("voucher_no")) is None
        ):
            return False
        for fieldname, doctype in dimensions.items():
            if row.get(fieldname) and self.get(doctype, row[fieldname]) is None:
                return False
        if row.get("finance_book") and self.get("Finance Book", row["finance_book"]) is None:
            return False
        return True
