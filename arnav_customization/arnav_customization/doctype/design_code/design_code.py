# Copyright (c) 2026, aits and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document


class DesignCode(Document):
	"""Immutable registry entry for a jewellery design classification."""

	def autoname(self):
		self.name = self.design_code

	def validate(self):
		self.design_code = (self.design_code or "").strip().upper()
		self.set_code_value = (self.set_code_value or "").strip().upper()
		self.element_code_value = (self.element_code_value or "").strip().upper()

		if not re.fullmatch(r"[A-Z0-9]+-[A-Z0-9]+-[0-9]{4}", self.design_code):
			frappe.throw("Design Code must use the format SET-ELEMENT-0001.")

		if self.status == "Voided" and not (self.void_reason or "").strip():
			frappe.throw("A reason is required when a Design Code is voided.")
