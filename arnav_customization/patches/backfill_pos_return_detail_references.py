"""Backfill row-level POS references on historical submitted Sales Returns."""

import frappe


def execute():
	if not frappe.db.table_exists("Sales Invoice"):
		return

	returns = frappe.get_all(
		"Sales Invoice",
		filters={"docstatus": 1, "is_return": 1, "custom_pos": ["is", "set"]},
		fields=["name", "custom_pos"],
	)
	unresolved = []

	for sales_return in returns:
		pos_rows_by_sku = {}
		for row in frappe.get_all(
			"POS SKU Details",
			filters={"parent": sales_return.custom_pos},
			fields=["name", "sku"],
		):
			pos_rows_by_sku.setdefault(row.sku, []).append(row.name)

		for item in frappe.get_all(
			"Sales Invoice Item",
			filters={"parent": sales_return.name, "custom_pos_detail": ["is", "not set"]},
			fields=["name", "custom_sku"],
		):
			matches = pos_rows_by_sku.get(item.custom_sku, [])
			if len(matches) == 1:
				frappe.db.set_value(
					"Sales Invoice Item",
					item.name,
					"custom_pos_detail",
					matches[0],
					update_modified=False,
				)
			else:
				unresolved.append(item.name)

	if unresolved:
		frappe.log_error(
			title="POS return reference migration requires review",
			message=(
				"The following Sales Return items could not be mapped to exactly one "
				f"POS item row: {', '.join(unresolved)}"
			),
		)
