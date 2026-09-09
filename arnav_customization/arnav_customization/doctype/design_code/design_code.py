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
		self.generation_mode = self.generation_mode or "Auto"

		if self.generation_mode not in {"Auto", "Manual"}:
			frappe.throw("Generation Mode must be Auto or Manual.")

		if self.generation_mode == "Auto":
			if not re.fullmatch(r"[A-Z0-9]+-[A-Z0-9]+-[0-9]{4}", self.design_code):
				frappe.throw("Automatic Design Code must use the format SET-ELEMENT-0001.")
		elif not re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", self.design_code):
			frappe.throw("Manual Design Code may contain only uppercase letters, numbers, and single hyphens.")

		previous = self.get_doc_before_save()
		if previous:
			immutable_fields = (
				"design_code",
				"generation_mode",
				"set_code",
				"set_code_value",
				"element_code",
				"element_code_value",
				"sequence_no",
				"created_from_sku_master",
				"created_from_breakup_ref",
			)
			if any(self.get(fieldname) != previous.get(fieldname) for fieldname in immutable_fields):
				frappe.throw("An issued Design Code cannot be edited. Use Replace Design Code instead.")

			if self.status != previous.status and not getattr(frappe.flags, "design_code_lifecycle_update", False):
				frappe.throw("Design Code status can only be changed by the controlled lifecycle action.")

		if self.status == "Voided" and not (self.void_reason or "").strip():
			frappe.throw("A reason is required when a Design Code is voided.")
