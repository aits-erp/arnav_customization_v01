"""Create renamed breakup DocTypes and preserve their legacy master data."""

import frappe


DOCTYPE_MIGRATIONS = (
	("PRODUCT_TYPE", "ELEMENT_CODE", "product_type", "element_code"),
	("COLLECTION", "SET_CODE", "collection_name", "set_code"),
)


def execute():
	# Force-loading makes the repair independent of the previous failed rename path
	# and of timestamps in the exported DocType JSON files.
	frappe.reload_doc("Breakup doctypes", "doctype", "element_code", force=True)
	frappe.reload_doc("Breakup doctypes", "doctype", "set_code", force=True)

	for old_doctype, new_doctype, old_field, new_field in DOCTYPE_MIGRATIONS:
		_copy_legacy_master_rows(old_doctype, new_doctype, old_field, new_field)

	from arnav_customization.patches.migrate_breakup_code_data import execute as migrate_breakup_data

	migrate_breakup_data()
	frappe.clear_cache(doctype="ELEMENT_CODE")
	frappe.clear_cache(doctype="SET_CODE")


def _copy_legacy_master_rows(old_doctype, new_doctype, old_field, new_field):
	"""Copy old master records by name, without overwriting records already created."""
	if not frappe.db.table_exists(old_doctype):
		return

	source_columns = set(frappe.db.get_table_columns(old_doctype))
	target_columns = set(frappe.db.get_table_columns(new_doctype))

	if old_field not in source_columns or new_field not in target_columns:
		return

	common_columns = sorted(
		column
		for column in source_columns.intersection(target_columns)
		if column != new_field
	)

	if "name" not in common_columns:
		return

	insert_columns = [*common_columns, new_field]
	select_columns = [*(f"source.`{column}`" for column in common_columns), f"source.`{old_field}`"]
	quoted_insert_columns = ", ".join(f"`{column}`" for column in insert_columns)
	quoted_select_columns = ", ".join(select_columns)

	frappe.db.sql(
		f"""
		INSERT INTO `tab{new_doctype}` ({quoted_insert_columns})
		SELECT {quoted_select_columns}
		FROM `tab{old_doctype}` AS source
		WHERE NOT EXISTS (
			SELECT 1
			FROM `tab{new_doctype}` AS target
			WHERE target.name = source.name
		)
		"""
	)
