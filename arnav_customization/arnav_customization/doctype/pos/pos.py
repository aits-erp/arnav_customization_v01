import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe.model.mapper import get_mapped_doc

class POS(Document):
	def validate(self):
	    self.calculate_gst_for_items()

	def before_submit(self):
		# 1️⃣ Balance validation
		if abs(self.balance_amount) > 0.01:
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
			
			# stock_entry.append("items", {
			# 	"item_code": row.packing_material,
			# 	"qty": row.qty,
			# 	"s_warehouse": self.branch
			# })

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

		# ✅ FIX ADDED HERE
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

        # Optional linkage
        # target.return_against = source.sales_invoice_ref

    # ===============================
    # SKU → SALES INVOICE ITEM
    # ===============================
    def map_items(source, target, source_parent):

        # 🔁 CORE FIELD MAPPING
        target.item_code = source.product

        # ⚠️ CRITICAL REVERSAL LOGIC
        # POS.qty → Sales Invoice custom_gross_weight
        # POS.gross_weight → Sales Invoice qty

        target.qty = -1 * (source.gross_weight or 0)   # Qty = Gross Weight
        target.custom_gross_weight = source.qty        # Custom Qty field

        # Additional fields
        target.rate = source.price
        target.amount = source.final_amount
        target.discount_amount = source.discount

        # Custom fields
        target.custom_sku = source.sku
        target.custom_net_weight = source.net_weight

        # Batch & HSN
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
            # ===============================
            # HEADER
            # ===============================
            "POS": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "client_name": "customer",
                    "mobile_number": "contact_mobile",
                    "email": "contact_email",
                    "address": "address_display",
                    "branch": "set_warehouse",

                    # Totals
                    "total_amount_with_gst": "grand_total",
                    "total_amount_wo_tax": "total"
                }
            },

            # ===============================
            # ITEMS TABLE
            # ===============================
            "POS SKU Details": {
                "doctype": "Sales Invoice Item",
                "postprocess": map_items
            },

            # ===============================
            # PACKING MATERIAL TABLE
            # POS: packing_materials
            # SI: custom_packing_materials
            # ===============================
            "Packing Materials": {
                "doctype": "Packing Materials",
                "field_map": {
                    # direct mapping (same fieldnames)
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