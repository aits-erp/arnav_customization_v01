"""Copy renamed master fields and retarget stored breakup Dynamic Links."""

import frappe


def execute():
	_copy_existing_code_values("ELEMENT_CODE", "product_type", "element_code")
	_copy_existing_code_values("SET_CODE", "collection_name", "set_code")
	_migrate_breakup_attribute_types("SKU Breakup")
	_migrate_breakup_attribute_types("Debit Breakup")


def _copy_existing_code_values(doctype, old_field, new_field):
	table = f"tab{doctype}"

	if not (
		frappe.db.table_exists(doctype)
		and frappe.db.has_column(doctype, old_field)
		and frappe.db.has_column(doctype, new_field)
	):
		return

	frappe.db.sql(
		f"""
		UPDATE `{table}`
		SET `{new_field}` = `{old_field}`
		WHERE IFNULL(`{new_field}`, '') = ''
		"""
	)


def _migrate_breakup_attribute_types(doctype):
	table = f"tab{doctype}"

	if not frappe.db.table_exists(doctype):
		return

	frappe.db.sql(
		f"""
		UPDATE `{table}`
		SET attribute_type = CASE attribute_type
			WHEN 'PRODUCT_TYPE' THEN 'ELEMENT_CODE'
			WHEN 'COLLECTION' THEN 'SET_CODE'
			ELSE attribute_type
		END
		WHERE attribute_type IN ('PRODUCT_TYPE', 'COLLECTION')
		"""
	)
