import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt
from frappe.model.mapper import get_mapped_doc

def money(value):
	return flt(value, 2)

class POS(Document):
	def validate(self):
		doc_before_save = self.get_doc_before_save()

		if doc_before_save and doc_before_save.docstatus == 1:
			return

		# self.calculate_gst_for_items()
		self.apply_discount_and_calculate_totals()

	def before_submit(self):
		# 1️⃣ Balance validation
		if abs(flt(self.balance_amount, self.precision("balance_amount"))) > 0.01:
			frappe.throw("Cannot submit POS because Balance Amount must be 0.00")

		# 2️⃣ Cash limit validation
		CASH_LIMIT = 195000
		total_cash = 0

		for row in self.payment_details:
			if row.payment_type == "Cash":
				# Individual row validation
				if row.amount > CASH_LIMIT:
					frappe.throw(
						f"Cash amount in a single entry cannot exceed ₹{CASH_LIMIT}. "
						f"Row amount: ₹{row.amount}"
					)

				total_cash += row.amount

		# Total cash validation (if split into multiple rows)
		if total_cash > CASH_LIMIT:
			frappe.throw(
				f"Total Cash payment cannot exceed ₹{CASH_LIMIT}. "
				f"Total Cash entered: ₹{total_cash}"
			)

		# 3️⃣ Create Stock Entry for Packing Materials
		self.create_packing_material_issue()

		# 4️⃣ Create Stock Entry for SKUs
		self.create_stock_out_entry()

	def on_cancel(self):
		if self.stock_entry_reference:

			if frappe.db.exists("Stock Entry", self.stock_entry_reference):

				se = frappe.get_doc("Stock Entry", self.stock_entry_reference)

				if se.docstatus == 1:
					se.cancel()

	def create_packing_material_issue(self):
		if not self.branch:
			frappe.throw("Warehouse (Branch) is mandatory to create Stock Entry.")

		if not self.packing_materials:
			return  # No packing materials → no stock issue

		# Create Stock Entry
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.stock_entry_type = "Material Issue"
		stock_entry.company = frappe.defaults.get_user_default("Company")
		stock_entry.posting_date = self.posting_date if hasattr(self, "posting_date") else frappe.utils.nowdate()
		stock_entry.posting_time = frappe.utils.nowtime()
		stock_entry.set_posting_time = 1

		for row in self.packing_materials:

			if not row.packing_material:
				continue

			if not row.qty or row.qty <= 0:
				continue

			item_code = row.packing_material
			qty = row.qty
			batch_no = None

			has_batch = frappe.db.get_value("Item", item_code, "has_batch_no")

			if has_batch:

				batch = frappe.db.sql("""
					SELECT name
					FROM `tabBatch`
					WHERE item = %s
					LIMIT 1
				""", (item_code), as_dict=True)

				if not batch:
					frappe.throw(f"No batch found for Item {item_code}")

				batch_no = batch[0].name

			stock_entry.append("items", {
				"item_code": item_code,
				"qty": qty,
				"s_warehouse": self.branch,
				"batch_no": batch_no
			})

		if not stock_entry.items:
			return

		stock_entry.insert(ignore_permissions=True)
		stock_entry.submit()
		self.stock_entry_reference = stock_entry.name

	def calculate_gst_for_items(self):
		for row in self.sku_details:

			if not row.sku or not row.final_amount:
				continue

			# Get Item from SKU
			item_code = frappe.db.get_value("SKU", row.sku, "product")

			if not item_code:
				continue

			# Get Item Tax Template from Item
			item_doc = frappe.get_doc("Item", item_code)

			item_tax_template = None

			if item_doc.taxes:
				for tax in item_doc.taxes:
					if tax.item_tax_template:
						item_tax_template = tax.item_tax_template
						break

			if not item_tax_template:
				row.gst_percentage = 0
				row.gst_amount = 0
				continue

			# Get GST Rate
			gst_rate = frappe.db.get_value(
				"Item Tax Template",
				item_tax_template,
				"gst_rate"
			)

			if not gst_rate:
				row.gst_percentage = 0
				row.gst_amount = 0
				continue

			row.gst_percentage = gst_rate

			row.gst_amount = (row.final_amount * gst_rate) / 100

	def create_stock_out_entry(self):

		if not self.branch:
			frappe.throw("No Branch")

		if not self.sku_details:
			frappe.throw("No SKU details")

		stock_entry = frappe.new_doc("Stock Entry")

		stock_entry.stock_entry_type = "Material Issue"

		stock_entry.company = frappe.defaults.get_user_default("Company")
		stock_entry.date = frappe.utils.nowdate()

		for row in self.sku_details:

			if not row.sku or not row.qty:
				continue

			item_code = frappe.db.get_value("SKU", row.sku, "product")

			if not item_code:
				continue

			stock_entry.append("items", {
				"item_code": item_code,
				"qty": row.qty,
				"s_warehouse": self.branch
			})

		if not stock_entry.items:
			frappe.throw("No items added → Stock Entry not created")

		stock_entry.insert(ignore_permissions=True)
		stock_entry.submit()

		self.stock_out_ref = stock_entry.name

		frappe.msgprint(f"Stock Entry Created: {stock_entry.name}")

	def apply_discount_and_calculate_totals(self):

		total_price = 0

		# ================================
		# TOTAL PRICE
		# ================================

		for row in self.sku_details:

			amount = money((row.price or 0) * (row.qty or 0))

			total_price += amount

		self.total_price = money(total_price)

		# ================================
		# DISCOUNT %
		# ================================

		discount_percentage = 0

		if total_price > 0:

			discount_percentage = (
				(self.total_discount_in_rs or 0)
				/ total_price
			) * 100

		self.discount_percentage = money(discount_percentage)

		# ================================
		# APPLY ROW CALCULATIONS
		# ================================

		total_amount = 0
		total_gst = 0

		for row in self.sku_details:

			amount = money((row.price or 0) * (row.qty or 0))

			row.discount = money((amount * discount_percentage) / 100)

			row.final_amount = money(amount - row.discount)

			if row.final_amount < 0:
				row.final_amount = 0

			# GST LOGIC
			item_code = frappe.db.get_value(
				"SKU",
				row.sku,
				"product"
			)

			gst_rate = 0

			if item_code:

				item_doc = frappe.get_doc(
					"Item",
					item_code
				)

				if item_doc.taxes:

					template = item_doc.taxes[0].item_tax_template

					if template:

						gst_rate = frappe.db.get_value(
							"Item Tax Template",
							template,
							"gst_rate"
						) or 0

			row.gst_percentage = gst_rate

			row.gst_amount = money((row.final_amount * gst_rate) / 100)

			total_amount += row.final_amount
			total_gst += row.gst_amount

		packing = self.handling_and_packaging_charges or 0

		self.total_amount_wo_tax = money(
			total_amount + packing
		)

		# ================================
		# ROUND OFF — AUTO or MANUAL
		# ================================
		# NEW FIELD REQUIRED: auto_calculate_round_off (Check, default 1)
		# - Checked   → system auto-calculates custom_round_off (old behavior)
		# - Unchecked → user enters custom_round_off manually, system just uses it
		# ================================

		original_total = money(
			total_amount + total_gst + packing
		)

		if cint(self.auto_calculate_round_off):
			# AUTO MODE
			rounded_total = round(original_total)
			self.custom_round_off = money(rounded_total - original_total)
		else:
			# MANUAL MODE — trust whatever value user typed
			self.custom_round_off = money(self.custom_round_off or 0)

		self.total_amount_with_gst = money(
			original_total + (self.custom_round_off or 0)
		)

		self.balance_amount = money(
			self.total_amount_with_gst - (self.paid_amount or 0)
		)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def customer_search_by_mobile(doctype, txt, searchfield, start, page_len, filters):

	return frappe.db.sql("""
		SELECT
			name,
			customer_name,
			mobile_no
		FROM `tabCustomer`
		WHERE
			docstatus < 2
			AND (
				name LIKE %(txt)s
				OR customer_name LIKE %(txt)s
				OR mobile_no LIKE %(txt)s
			)
		ORDER BY name
		LIMIT %(start)s, %(page_len)s
	""", {
		"txt": f"%{txt}%",
		"start": cint(start),
		"page_len": cint(page_len)
	})

@frappe.whitelist()
def get_sku_details(sku):

	if not sku:
		return {}

	sku_doc = frappe.db.get_value(
		"SKU",
		sku,
		["product", "gross_weight", "net_weight"],
		as_dict=True
	)

	if not sku_doc:
		return {}

	item_code = sku_doc.product

	item_doc = frappe.get_doc("Item", item_code)

	gst_rate = 0
	item_tax_template = None

	if item_doc.taxes:
		for row in item_doc.taxes:
			if row.item_tax_template:
				item_tax_template = row.item_tax_template
				break

	if item_tax_template:

		gst_rate = frappe.db.get_value(
			"Item Tax Template",
			item_tax_template,
			"gst_rate"
		) or 0

	return {
		"item": item_code,
		"hsn": item_doc.gst_hsn_code,
		"gross_weight": sku_doc.gross_weight,
		"net_weight": sku_doc.net_weight,
		"gst_rate": gst_rate
	}

@frappe.whitelist()
def make_credit_note(source_name, target_doc=None):

	# ===============================
	# HEADER POST PROCESS
	# ===============================
	def set_missing_values(source, target):
		target.is_return = 1
		target.update_stock = 1

		client_name = (source.client_name or "").strip()

		if client_name:
			customer = (
				frappe.db.exists("Customer", client_name)
				or frappe.db.get_value(
					"Customer",
					{"customer_name": client_name},
					"name"
				)
			)

			if customer:
				target.customer = customer
			else:
				target.customer_name = client_name

	# ===============================
	# SKU → SALES INVOICE ITEM
	# ===============================
	def map_items(source, target, source_parent):

		target.item_code = source.product

		target.qty = -1 * (source.gross_weight or 0)
		target.custom_gross_weight = source.qty

		target.rate = source.price
		target.amount = source.final_amount
		target.discount_amount = source.discount

		target.custom_sku = source.sku
		target.custom_net_weight = source.net_weight

		target.batch_no = source.batch_no
		target.gst_hsn_code = source.hsn

	# ===============================
	# PACKING MATERIALS MAPPING
	# ===============================
	def map_packing_materials(source, target, source_parent):

		target.packing_material = source.packing_material
		target.qty = source.qty
		target.rate_optional = source.rate_optional

	doc = get_mapped_doc(
		"POS",
		source_name,
		{
			"POS": {
				"doctype": "Sales Invoice",
				"field_map": {
					"mobile_number": "contact_mobile",
					"email": "contact_email",
					"address": "address_display",
					"branch": "set_warehouse",

					"total_amount_with_gst": "grand_total",
					"total_amount_wo_tax": "total"
				}
			},

			"POS SKU Details": {
				"doctype": "Sales Invoice Item",
				"postprocess": map_items
			},

			"Packing Materials": {
				"doctype": "Packing Materials",
				"field_map": {
					"packing_material": "packing_material",
					"qty": "qty",
					"rate_optional": "rate_optional"
				}
			}

		},
		target_doc,
		set_missing_values
	)

	return doc