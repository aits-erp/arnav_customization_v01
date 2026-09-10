import frappe


def execute():
	"""Backfill the date-only POS filter field from existing POS DateTime values."""
	if not frappe.db.table_exists("POS"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabPOS`
		SET pos_date = DATE(`date`)
		WHERE `date` IS NOT NULL
		  AND (pos_date IS NULL OR pos_date = '')
		"""
	)
