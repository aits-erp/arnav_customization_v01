# Copyright (c) 2026, aits and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document


class POS(Document):
	def before_submit(self):
		if abs(self.balance_amount) > 0.01:
			frappe.throw("Cannot submit POS because Balance Amount must be 0.00")
