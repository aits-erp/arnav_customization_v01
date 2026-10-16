from frappe import _


def get_data(data):
	"""Extend ERPNext's Sales Invoice dashboard without replacing its links."""
	data = data or {}
	transactions = data.setdefault("transactions", [])

	if not any("POS" in transaction.get("items", []) for transaction in transactions):
		transactions.append({"label": _("Source Document"), "items": ["POS"]})

	internal_links = data.setdefault("internal_links", {})
	internal_links["POS"] = "custom_pos"
	return data
