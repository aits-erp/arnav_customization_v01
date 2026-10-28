import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime
from frappe.model.mapper import get_mapped_doc
from arnav_customization.advance_payment import get_available_advance_amount

def money(value):
	return flt(value, 2)

class POS(Document):

	def get_data():
		return {
			"fieldname": "custom_pos",
			"transactions": [
				{
					"label": "Sales Return",
					"items": ["Sales Invoice"]
				}
			]
		}
	
	def validate(self):
		doc_before_save = self.get_doc_before_save()

		if doc_before_save and doc_before_save.docstatus == 1:
			return

		# A date-only projection makes list filtering independent of the
		# time stored in the operational POS DateTime field.
		self.pos_date = get_datetime(self.date).date() if self.date else None

		# self.calculate_gst_for_items()
		self.apply_discount_and_calculate_totals()

	def before_submit(self):
		# 1️⃣ Balance validation
		# if abs(flt(self.balance_amount, self.precision("balance_amount"))) > 0.01:
		# 	frappe.throw("Cannot submit POS because Balance Amount must be 0.00")

		# 2️⃣ Cash limit validation
		# CASH_LIMIT = 195000
		CASH_LIMIT = 199900 

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

		# The POS grid is client-controlled. Validate every SKU against its
		# authoritative SKU record before any stock movement is created.
		self.validate_sku_details_for_stock_issue()

		# 3️⃣ Create Stock Entry for Packing Materials
		self.create_packing_material_issue()

		# 4️⃣ Create Stock Entry for SKUs
		self.create_stock_out_entry()

	def on_cancel(self):
		# Reverse SKU stock first, then packing stock.  Previously only the
		# packing entry was cancelled, leaving the SKU stock permanently issued.
		self.cancel_linked_stock_entry(self.stock_out_ref)
		self.cancel_linked_stock_entry(self.stock_entry_reference)

		for row in self.sku_details:
			if row.sku and frappe.db.exists("SKU", row.sku):
				frappe.db.set_value("SKU", row.sku, "status", "Available", update_modified=False)

	def cancel_linked_stock_entry(self, stock_entry_name):
		if not stock_entry_name or not frappe.db.exists("Stock Entry", stock_entry_name):
			return

		stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
		if stock_entry.docstatus == 1:
			stock_entry.cancel()

	def validate_sku_details_for_stock_issue(self):
		"""Validate and normalize POS rows from the database SKU record."""
		if not self.sku_details:
			frappe.throw("At least one SKU detail is required before submitting POS.")

		seen_skus = set()
		for row in self.sku_details:
			if not row.sku:
				frappe.throw(f"SKU is required in row {row.idx}.")
			if row.sku in seen_skus:
				frappe.throw(f"SKU {row.sku} is entered more than once in this POS.")
			seen_skus.add(row.sku)

			if flt(row.qty) <= 0:
				frappe.throw(f"Quantity must be greater than zero for SKU {row.sku} (row {row.idx}).")

			sku = frappe.db.get_value(
				"SKU",
				row.sku,
				["name", "product", "batch_no", "status"],
				as_dict=True,
			)
			if not sku:
				frappe.throw(f"SKU {row.sku} in row {row.idx} no longer exists.")
			if not sku.product:
				frappe.throw(f"SKU {row.sku} has no linked Item/Product.")
			if not sku.batch_no:
				frappe.throw(f"SKU {row.sku} has no linked Batch. Please correct the SKU record before sale.")
			if sku.status != "Available":
				frappe.throw(f"SKU {row.sku} is {sku.status or 'not available'} and cannot be sold.")
			if row.product and row.product != sku.product:
				frappe.throw(
					f"SKU {row.sku} belongs to Item {sku.product}, but row {row.idx} contains {row.product}."
				)

			# Use database values for both display and the later Stock Entry.
			row.product = sku.product
			row.batch_no = sku.batch_no

	def create_packing_material_issue(self):
		if not self.branch:
			frappe.throw("Warehouse (Branch) is mandatory to create Stock Entry.")

		if not self.packing_materials:
			return  # No packing materials → no stock issue

		# Create Stock Entry
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.stock_entry_type = "Material Issue"

		stock_entry.custom_pos = self.name

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
				# This app uses the legacy Batch field for SKU traceability. Without
				# this flag ERPNext can also create a Serial and Batch Bundle, which
				# conflicts with a populated batch_no.
				"use_serial_batch_fields": 1,
				"serial_and_batch_bundle": None,
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

		stock_entry = frappe.new_doc("Stock Entry")

		stock_entry.stock_entry_type = "Material Issue"
		stock_entry.custom_pos = self.name

		stock_entry.company = frappe.defaults.get_user_default("Company")
		posting_datetime = get_datetime(self.date) if self.date else None
		stock_entry.posting_date = posting_datetime.date() if posting_datetime else frappe.utils.nowdate()
		stock_entry.posting_time = posting_datetime.time() if posting_datetime else frappe.utils.nowtime()
		stock_entry.set_posting_time = 1

		for row in self.sku_details:
			sku = frappe.db.get_value(
				"SKU", row.sku, ["product", "batch_no"], as_dict=True
			)

			stock_entry.append("items", {
				"item_code": sku.product,
				"qty": row.qty,
				"s_warehouse": self.branch,
				# Use only the legacy batch fields. ERPNext must not auto-create a
				# Serial and Batch Bundle for this row as well.
				"use_serial_batch_fields": 1,
				"serial_and_batch_bundle": None,
				"batch_no": sku.batch_no,
				"custom_sku": row.sku,
			})

		if not stock_entry.items:
			frappe.throw("No items added → Stock Entry not created")

		try:
			stock_entry.insert(ignore_permissions=True)
			stock_entry.submit()
		except frappe.ValidationError as exc:
			frappe.log_error(
				frappe.get_traceback(),
				f"POS Stock Issue Failed: {self.name or 'new POS'}",
			)
			frappe.throw(
				"Unable to issue the selected SKU batch from warehouse {0}.<br><br>{1}"
				.format(self.branch, frappe.utils.strip_html(str(exc))),
				title="POS Stock Not Available",
			)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"Unexpected POS Stock Issue Error: {self.name or 'new POS'}",
			)
			frappe.throw(
				"An unexpected error occurred while creating the POS stock issue. "
				"Technical details have been logged for the administrator.",
				title="POS Stock Issue Failed",
			)

		self.stock_out_ref = stock_entry.name

		for row in self.sku_details:
			frappe.db.set_value("SKU", row.sku, "status", "Sold", update_modified=False)

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
		huid_charges = self.custom_huid_charges or 0

		self.total_amount_wo_tax = money(
			total_amount + packing + huid_charges
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
	pos = frappe.get_doc("POS", source_name)
	if pos.docstatus != 1:
		frappe.throw("Sales Return can only be created from a submitted POS transaction.")

	remaining_qty_by_detail = get_remaining_pos_return_qty(pos)

	# ===============================
	# HEADER POST PROCESS
	# ===============================
	# def set_missing_values(source, target):
	# 	target.is_return = 1
	# 	target.update_stock = 1
	# 	target.custom_pos = source.name

	# 	client_name = (source.client_name or "").strip()
	def set_missing_values(source, target):
		target.is_return = 1
		target.update_stock = 1
		target.custom_pos = source.name

		# Preserve the original POS rate for Sales Return
		target.ignore_pricing_rule = 1

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

		item_doc = frappe.get_cached_doc(
			"Item",
			source.product
		)

		target.item_name = item_doc.item_name
		target.uom = item_doc.stock_uom
		target.stock_uom = item_doc.stock_uom

		# Map only the quantity which has not already been returned from this
		# exact POS row. This remains correct when one SKU appears more than once.
		target.qty = -1 * remaining_qty_by_detail.get(source.name, 0)
		target.custom_pos_detail = source.name
		target.custom_gross_weight = source.gross_weight

		# ERPNext treats ``rate`` as the effective per-unit selling rate and
		# derives the row amount from it.  POS stores discount as a row total,
		# so convert it to a per-unit value before mapping it to Sales Invoice
		# Item.  Sending the POS gross price as ``rate`` and the whole discount
		# as ``discount_amount`` lets the standard asynchronous price lookup
		# recalculate some rows to an invalid (including negative) rate.
		qty = flt(source.qty) or 1
		gross_rate = flt(source.price)
		unit_discount = flt(source.discount) / qty
		effective_rate = gross_rate - unit_discount

		# Keep the POS-entered price visible/auditable in the existing custom
		# field, while providing a complete, internally consistent standard
		# pricing state for the Sales Invoice Item.
		target.custom_custom_rate = gross_rate
		target.price_list_rate = gross_rate
		target.rate_with_margin = gross_rate
		target.discount_amount = unit_discount
		target.discount_percentage = (unit_discount / gross_rate * 100) if gross_rate else 0
		target.rate = effective_rate

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
					"branch": "set_warehouse"
				}
			},

			"POS SKU Details": {
				"doctype": "Sales Invoice Item",
				"condition": lambda source: remaining_qty_by_detail.get(source.name, 0) > 0,
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
	if not doc.items:
		frappe.throw("All items in this POS have already been fully returned.")

	return doc


def get_remaining_pos_return_qty(pos):
	"""Return remaining returnable quantity keyed by POS SKU Details row ID."""
	return_qty_by_detail = get_submitted_pos_return_qty(pos.name)
	return {
		row.name: max(flt(row.qty) - return_qty_by_detail.get(row.name, 0), 0)
		for row in pos.sku_details
	}


def get_submitted_pos_return_qty(pos_name):
	"""Sum submitted Sales Return quantities per originating POS child row."""
	rows = frappe.db.sql(
		"""
		SELECT
			sii.custom_pos_detail,
			SUM(ABS(sii.qty)) AS returned_qty
		FROM `tabSales Invoice Item` AS sii
		INNER JOIN `tabSales Invoice` AS si ON si.name = sii.parent
		WHERE si.docstatus = 1
			AND si.is_return = 1
			AND si.custom_pos = %s
			AND COALESCE(sii.custom_pos_detail, '') != ''
		GROUP BY sii.custom_pos_detail
		""",
		pos_name,
		as_dict=True,
	)
	return {row.custom_pos_detail: flt(row.returned_qty) for row in rows}


def validate_pos_return_quantities(doc, method=None):
	"""Prevent a POS row from being returned more than its sold quantity."""
	if not (doc.is_return and doc.custom_pos):
		return

	pos = frappe.get_doc("POS", doc.custom_pos)
	if pos.docstatus != 1:
		frappe.throw("Sales Return must reference a submitted POS transaction.")

	# Serialize return submissions for this POS. Without this lock, two users
	# can open return drafts together and both pass the availability check.
	lock_pos_return_rows(pos.name)

	sold_qty_by_detail = {row.name: flt(row.qty) for row in pos.sku_details}
	already_returned = get_submitted_pos_return_qty(pos.name)
	current_returned = {}

	for item in doc.items:
		detail_name = item.custom_pos_detail
		if not detail_name:
			frappe.throw(
				"Each POS Sales Return item must keep its original POS item reference."
			)
		if detail_name not in sold_qty_by_detail:
			frappe.throw("A Sales Return item does not belong to the selected POS transaction.")
		if flt(item.qty) >= 0:
			frappe.throw("Sales Return quantities must be negative.")

		current_returned[detail_name] = current_returned.get(detail_name, 0) + abs(flt(item.qty))

	for detail_name, current_qty in current_returned.items():
		available_qty = sold_qty_by_detail[detail_name] - already_returned.get(detail_name, 0)
		if current_qty > available_qty + 0.000001:
			frappe.throw(
				"Return quantity exceeds the remaining quantity for POS item {0}. "
				"Available: {1}, requested: {2}.".format(
					detail_name, available_qty, current_qty
				)
			)


def lock_pos_return_rows(pos_name):
	"""Lock a POS's item rows until the current return submission completes."""
	frappe.db.sql(
		"SELECT name FROM `tabPOS SKU Details` WHERE parent = %s FOR UPDATE",
		pos_name,
	)


def sync_sku_status_for_pos_return(doc, method=None):
	"""Synchronize only the SKUs affected by a POS-linked Sales Return.

	The POS itself marks every sold SKU as ``Sold``.  A submitted Sales Return
	makes its exact source SKU available again only after that POS row has been
	fully returned.  On cancellation, the status is recalculated from the
	remaining submitted returns.  Other SKU rows in the same POS are untouched.
	"""
	if not (doc.is_return and doc.custom_pos):
		return

	pos = frappe.get_doc("POS", doc.custom_pos)
	if pos.docstatus != 1:
		return

	pos_row_by_name = {row.name: row for row in pos.sku_details}
	returned_qty_by_detail = get_submitted_pos_return_qty(pos.name)
	affected_details = {item.custom_pos_detail for item in doc.items if item.custom_pos_detail}

	for detail_name in affected_details:
		pos_row = pos_row_by_name.get(detail_name)
		if not pos_row or not pos_row.sku or not frappe.db.exists("SKU", pos_row.sku):
			continue

		fully_returned = (
			returned_qty_by_detail.get(detail_name, 0) >= flt(pos_row.qty) - 0.000001
		)
		frappe.db.set_value(
			"SKU",
			pos_row.sku,
			"status",
			"Available" if fully_returned else "Sold",
			update_modified=False,
		)


@frappe.whitelist()
def get_pos_return_pricing(source_name):
	"""Return the immutable POS pricing used to create a Sales Return.

	A Sales Invoice's Item Price lookup is asynchronous and can replace values
	mapped into a new return.  The POS is therefore the authoritative source
	for its return pricing rather than the Item Price master.
	"""
	if not source_name or not frappe.has_permission("POS", "read", source_name):
		frappe.throw("You do not have permission to read this POS transaction.")

	pos = frappe.get_doc("POS", source_name)
	if pos.docstatus != 1:
		frappe.throw("Sales Return pricing can only be fetched from a submitted POS transaction.")

	return {
		row.name: {
			"gross_rate": flt(row.price),
			"qty": flt(row.qty),
			"discount": flt(row.discount),
			"effective_rate": flt(row.final_amount) / (flt(row.qty) or 1),
		}
		for row in pos.sku_details
	}




@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
    """Create a draft Sales Invoice from a submitted POS."""

    if not source_name:
        frappe.throw("POS reference is required.")

    if not frappe.has_permission("POS", "read", source_name):
        frappe.throw("You do not have permission to access this POS.")

    if not frappe.has_permission("Sales Invoice", "create"):
        frappe.throw("You do not have permission to create Sales Invoices.")

    if not frappe.db.exists("POS", source_name):
        frappe.throw(f"POS {source_name} does not exist.")

    pos = frappe.get_doc("POS", source_name)

    if pos.docstatus != 1:
        frappe.throw(
            "A Sales Invoice can only be created from a submitted POS."
        )

    if not pos.sku_details:
        frappe.throw("No product details found in this POS.")

    # Ensure that the POS has not already been invoiced.
    # Cancelled invoices do not block a new draft.
    existing_invoice = frappe.db.get_value(
        "Sales Invoice",
        {
            "custom_pos": source_name,
            "is_return": 0,
            "docstatus": ["!=", 2],
        },
        "name",
    )

    if existing_invoice:
        frappe.throw(
            f"Sales Invoice {existing_invoice} is already linked "
            f"to POS {source_name}. Please open the existing invoice."
        )

    customer = pos.client_name

    if not customer or not frappe.db.exists("Customer", customer):
        frappe.throw(
            "Please select a valid Customer in the POS before "
            "creating a Sales Invoice."
        )

    def map_pos_item(source, target, source_parent):
        """Map POS SKU Details to Sales Invoice Item."""

        if not source.product:
            frappe.throw(
                f"Product is missing in POS row {source.idx}."
            )

        if not frappe.db.exists("Item", source.product):
            frappe.throw(
                f"Item {source.product} does not exist."
            )

        qty = flt(source.qty)
        gross_rate = flt(source.price)

        if qty <= 0:
            frappe.throw(
                f"Quantity must be greater than zero in POS row "
                f"{source.idx}."
            )

        item = frappe.get_cached_doc("Item", source.product)

        # Standard ERPNext item fields
        target.item_code = source.product
        target.item_name = item.item_name
        target.uom = item.stock_uom
        target.stock_uom = item.stock_uom
        target.conversion_factor = 1

        # POS stores the discount as a row total.
        unit_discount = flt(source.discount) / qty
        effective_rate = gross_rate - unit_discount

        if effective_rate < 0:
            frappe.throw(
                f"Discount exceeds the item price in POS row {source.idx}."
            )

        target.price_list_rate = gross_rate
        target.rate_with_margin = gross_rate
        target.discount_amount = unit_discount
        target.discount_percentage = (
            (unit_discount / gross_rate * 100)
            if gross_rate else 0
        )
        target.rate = effective_rate
        target.qty = qty

        # Preserve existing custom item fields where available.
        if target.meta.has_field("custom_sku"):
            target.custom_sku = source.sku

        if target.meta.has_field("custom_pos_detail"):
            target.custom_pos_detail = source.name

        if target.meta.has_field("custom_custom_rate"):
            target.custom_custom_rate = gross_rate

        if target.meta.has_field("custom_gross_weight"):
            target.custom_gross_weight = source.gross_weight

        if target.meta.has_field("custom_net_weight"):
            target.custom_net_weight = source.net_weight

        if target.meta.has_field("batch_no"):
            target.batch_no = source.batch_no

        if target.meta.has_field("gst_hsn_code"):
            target.gst_hsn_code = source.hsn

        # Preserve the Item's first configured tax template, if present.
        if item.taxes:
            for tax in item.taxes:
                if tax.item_tax_template:
                    if target.meta.has_field("item_tax_template"):
                        target.item_tax_template = tax.item_tax_template
                    break

    def set_invoice_values(source, target):
        # Set the customer before initializing invoice defaults.
        target.customer = customer
        target.is_return = 0

        # POS already issues stock through Stock Entry.
        # Do not issue stock a second time from the invoice.
        target.update_stock = 0
        target.ignore_pricing_rule = 1

        if target.meta.has_field("custom_pos"):
            target.custom_pos = source.name
        else:
            frappe.throw(
                "The custom_pos field is missing from Sales Invoice. "
                "Add a Link field to POS before using this functionality."
            )

        if source.branch and frappe.db.exists("Warehouse", source.branch):
            target.set_warehouse = source.branch

        if source.mobile_number and target.meta.has_field("contact_mobile"):
            target.contact_mobile = source.mobile_number

        if source.email and target.meta.has_field("contact_email"):
            target.contact_email = source.email

        # Set the POS date without copying the time component.
        invoice_date = source.pos_date or source.date
        if invoice_date:
            target.posting_date = get_datetime(invoice_date).date()

        # Populate standard ERPNext defaults and totals.
        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

		
        # Map selected POS Payment Entries to Sales Invoice Advances.
        remaining_invoice_amount = flt(target.grand_total)
        selected_entries = set()

        for payment_row in source.get("payment_details") or []:
            payment_entry = payment_row.get("custom_payment_entry")

            if not payment_entry:
                continue

            if payment_entry in selected_entries:
                frappe.throw(
                    f"Payment Entry {payment_entry} is selected more than once."
                )

            selected_entries.add(payment_entry)

            if remaining_invoice_amount <= 0:
                break

            available_amount = get_available_advance_amount(
                payment_entry=payment_entry,
                customer=target.customer,
                company=target.company,
                exclude_invoice=target.name,
            )

            allocation = min(
                flt(payment_row.amount),
                flt(available_amount),
                remaining_invoice_amount,
            )

            if allocation <= 0:
                continue

            target.append("advances", {
                "reference_type": "Payment Entry",
                "reference_name": payment_entry,
                "remarks": f"Selected from POS {source.name}",
                "advance_amount": flt(available_amount),
                "allocated_amount": allocation,
                "difference_posting_date": target.posting_date,
            })

            remaining_invoice_amount -= allocation


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
                },
                "validation": {
                    "docstatus": ["=", 1],
                },
            },
            "POS SKU Details": {
                "doctype": "Sales Invoice Item",
                "postprocess": map_pos_item,
            },
        },
        target_doc,
        set_invoice_values,
    )

    if not doc.items:
        frappe.throw("No invoice items were created from the POS.")

    # Return the mapped document as a draft.
    # Do not insert or submit it here.
    return doc
