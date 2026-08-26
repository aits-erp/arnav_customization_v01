"""Rename breakup code DocTypes without losing existing masters or breakup rows."""

import frappe


DOCTYPE_RENAMES = (
	("PRODUCT_TYPE", "ELEMENT_CODE"),
	("COLLECTION", "SET_CODE"),
)


def execute():
	for old_doctype, new_doctype in DOCTYPE_RENAMES:
		old_exists = frappe.db.exists("DocType", old_doctype)
		new_exists = frappe.db.exists("DocType", new_doctype)

		if old_exists and new_exists:
			frappe.throw(
				f"Cannot migrate breakup DocType {old_doctype}: both {old_doctype} and "
				f"{new_doctype} exist. Resolve the duplicate before running migrate."
			)

		if old_exists:
			frappe.rename_doc("DocType", old_doctype, new_doctype, force=True)
