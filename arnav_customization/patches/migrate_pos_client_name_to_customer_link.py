"""Safely convert legacy POS client names to Customer document IDs."""

import frappe


def execute():
	if not frappe.db.table_exists("POS") or not frappe.db.table_exists("Customer"):
		return

	legacy_values = frappe.db.sql_list(
		"""
		SELECT DISTINCT client_name
		FROM `tabPOS`
		WHERE COALESCE(client_name, '') != ''
		"""
	)

	unresolved = []
	for client_name in legacy_values:
		# Values already stored as Customer IDs need no migration.
		if frappe.db.exists("Customer", client_name):
			continue

		customers = frappe.get_all(
			"Customer", filters={"customer_name": client_name}, pluck="name"
		)
		if len(customers) != 1:
			unresolved.append(client_name)
			continue

		frappe.db.sql(
			"UPDATE `tabPOS` SET client_name = %s WHERE client_name = %s",
			(customers[0], client_name),
		)

	if unresolved:
		frappe.log_error(
			title="POS client_name migration requires review",
			message=(
				"The following legacy POS client names could not be mapped to exactly "
				f"one Customer: {', '.join(unresolved)}"
			),
		)
