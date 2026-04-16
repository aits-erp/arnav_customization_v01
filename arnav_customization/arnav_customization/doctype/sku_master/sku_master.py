import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from frappe.utils import flt

class SKUMaster(Document):

    def on_submit(self):
        self.apply_supplier_margin()  
        self.create_repack_stock_entry()

    def on_cancel(self):
        if getattr(self, "stock_entry", None):
            se = frappe.get_doc("Stock Entry", self.stock_entry)
            if se.docstatus == 1:
                se.cancel()

    def create_repack_stock_entry(self):

        if getattr(self, "stock_entry", None):
            frappe.throw("Stock Entry already created against this SKU Master.")

        if not self.warehouse:
            frappe.throw("Warehouse is mandatory before submitting.")

        if not self.sku_details:
            frappe.throw("SKU Details are mandatory for Stock In process.")


        company = frappe.get_cached_value("Global Defaults", None, "default_company")
        if not company:
            frappe.throw("Default Company is not set in Global Defaults.")

        # ---------------------------------------------
        # CALCULATE TOTAL OUT WEIGHT (FROM NET QUANTITY)
        # ---------------------------------------------
        total_out_weight = flt(self.net_quantiity)

        if total_out_weight <= 0:
            frappe.throw("Net Quantity must be greater than zero.")

        # ---------------------------------------------
        # CALCULATE TOTAL IN WEIGHT (FROM SKU DETAILS)
        # ---------------------------------------------
        # total_in_weight = 0

        # for row in self.sku_details:
        #     if flt(row.gross_weight) <= 0:
        #         frappe.throw(f"Gross Weight must be greater than zero in row {row.idx}")
        #     total_in_weight += flt(row.gross_weight)

        # total_in_qty = 0

        # for row in self.sku_details:
        #     if flt(row.qty) <= 0:
        #         frappe.throw(f"Qty must be greater than zero in row {row.idx}")

        #     total_in_qty += flt(row.qty)

        # ---------------------------------------------
        # VALIDATION
        # ---------------------------------------------
        # if total_in_weight > total_out_weight:
        #     frappe.throw(
        #         f"""
        #         Total Finished Gross Weight ({total_in_weight})
        #         cannot exceed Available Gross Weight ({total_out_weight}).

        #         Please adjust SKU Gross Weight values.
        #         """
        #     )

        if not self.net_quantiity:
            frappe.throw("Gross weight must be entered.")

        for row in self.sku_details:
            if not row.product:
                frappe.throw(f"Product is missing in row {row.idx}")

            is_stock_item = frappe.db.get_value("Item", row.product, "is_stock_item")

            if not is_stock_item:
                frappe.throw(f"Item {row.product} is not marked as Stock Item (row {row.idx})")

            if flt(row.qty) <= 0:
                frappe.throw(f"Qty must be greater than zero in row {row.idx}")

            if flt(row.gross_weight) <= 0:
                frappe.throw(f"Gross weight must be entered in row {row.idx}")

            if not row.cost_price:
                frappe.throw(f"Cost Price is required for row {row.idx}")
        
        # ---------------------------------------------
        # CALCULATE ACTUAL ISSUE QTY
        # ---------------------------------------------
        # actual_out_qty = total_out_weight - total_in_weight
        # CALCULATE ACTUAL ISSUE QTY
        # actual_out_qty = total_in_weight
        
        actual_out_qty = total_out_weight

        if actual_out_qty <= 0:
            frappe.throw("Available gross weight must be greater than zero.")

        # ---------------------------------------------
        # CREATE STOCK ENTRY
        # ---------------------------------------------
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Repack"
        se.company = company
        se.posting_date = frappe.utils.nowdate()
        se.posting_time = frappe.utils.nowtime()

        # -----------------------------
        # STOCK OUT (ISSUE)
        # -----------------------------
        remaining_issue_qty = actual_out_qty

        # Fetch the single selected Purchase Invoice
        pi = frappe.get_doc("Purchase Invoice", self.invoice_no)

        for item in pi.items:
            if not item.item_code:
                continue

            if remaining_issue_qty <= 0:
                break

            available_qty = flt(item.qty)

            if available_qty <= 0:
                continue

            issue_qty = min(available_qty, remaining_issue_qty)

            se.append("items", {
                "item_code": item.item_code,
                "qty": issue_qty,
                "s_warehouse": self.warehouse
            })

            remaining_issue_qty -= issue_qty

        if remaining_issue_qty > 0:
            frappe.throw("Not enough quantity in Purchase Invoice to complete repack.")

        # -----------------------------
        # STOCK IN (RECEIPT)
        # -----------------------------
        for row in self.sku_details:
            if not row.product:
                frappe.throw(f"Product is missing in row {row.idx}")

            if flt(row.qty) <= 0:
                frappe.throw(f"Qty must be greater than zero in row {row.idx}")

            if flt(row.gross_weight) <= 0:
                frappe.throw(f"Gross weight must be entered in row {row.idx}")

            # 1️⃣ Generate Batch Name
            batch_name = self.generate_custom_batch_name(self.date_of_invoice)

            # 2️⃣ Create Batch
            batch = frappe.new_doc("Batch")
            batch.batch_id = batch_name
            batch.item = row.product
            batch.insert(ignore_permissions=True)

            # 3️⃣ Store SKU in child row
            row.db_set("sku", batch_name)

            # 4️⃣ Create SKU Record
            sku_doc = frappe.new_doc("SKU")

            sku_doc.sku_code = batch_name
            sku_doc.product = row.product
            sku_doc.batch_no = batch_name
            sku_doc.warehouse = self.warehouse

            sku_doc.gross_weight = row.gross_weight
            sku_doc.net_weight = row.net_weight
            sku_doc.qty = row.qty

            sku_doc.cost_price = row.cost_price
            sku_doc.selling_price = row.selling_price

            # NEW FIELDS
            sku_doc.shopify_rate = flt(row.shopify_rate)
            sku_doc.gst_percentage = flt(row.gst_percentage)
            sku_doc.gst_amount = flt(row.gst_amount)
            sku_doc.shopify_selling_rate = flt(row.shopify_selling_rate)

            sku_doc.image_url = row.image

            sku_doc.sku_master = self.name
            sku_doc.metal = self.metal
            sku_doc.supplier = self.supplier_name
            sku_doc.hsn = self.hsn

            sku_doc.status = "Available"
            sku_doc.valuation_rate = row.cost_price
            sku_doc.created_from_pi = self.invoice_no
            sku_doc.old_sku_ref = row.old_sku_ref
            sku_doc.supplier_invoice_no = self.supplier_invoice_no

            sku_doc.insert(ignore_permissions=True)

            if not row.cost_price:
                frappe.throw(f"Cost Price is required for row {row.idx}")

            #5️⃣ Add to Stock Entry
            se.append("items", {
                "item_code": row.product,
                # "qty": flt(row.gross_weight),
                "qty": flt(row.qty),
                "t_warehouse": self.warehouse,
                "batch_no": batch_name,
                # "is_finished_item": 1,
                "set_basic_rate_manually": 1,
                "basic_rate": flt(row.cost_price)
            })

        
        if not se.items:
            frappe.throw("No valid items found for Stock Entry.")

        for d in se.items:
            if not d.item_code:
                frappe.throw("Stock Entry has item with empty item_code")

        se.insert()
        se.submit()

        self.db_set("stock_entry", se.name)

        frappe.msgprint(
            msg="Stock Entry Created Successfully",
            title="Success",
            indicator="green"
        )
    
    def apply_supplier_margin(self):

        if not self.supplier_name:
            frappe.throw("Supplier must be selected before calculating selling price.")

        margin = frappe.db.get_value(
            "Supplier",
            self.supplier_name,
            "custom_supplier_margin"
        )

        if margin is None:
            frappe.throw(
                f"Supplier '{self.supplier_name}' does not have Supplier Margin defined."
            )

        margin = flt(margin)

        if margin <= 0:
            frappe.throw(
                f"Supplier Margin must be greater than zero for Supplier {self.supplier_name}."
            )

        for row in self.sku_details:
            if flt(row.cost_price) <= 0:
                frappe.throw(f"Cost Price must be greater than zero in row {row.idx}")

            row.selling_price = flt(row.cost_price) * margin
            
    def generate_custom_batch_name(self, posting_date):
        from frappe.utils import getdate

        if not self.metal:
            frappe.throw("Metal must be selected before generating SKU.")

        if not self.supplier_name:
            frappe.throw("Supplier must be selected before generating SKU.")

        if not posting_date:
            frappe.throw("Date of Invoice is required for SKU generation.")

        posting_date = getdate(posting_date)

        # ----------------------------
        # 1️⃣ METAL CODE (1 digit)
        # ----------------------------
        metal_code = frappe.db.get_value(
            "Metal Master",
            self.metal,
            "metal_code"
        )

        if not metal_code:
            frappe.throw(f"Metal Code not defined for Metal {self.metal}")

        metal_code = str(metal_code)

        # ----------------------------
        # 2️⃣ SUPPLIER CODE (3 digit)
        # ----------------------------
        # Supplier ID is stored as document name
        supplier_code = str(self.supplier_name)

        # Force numeric and pad to 3 digits
        if not supplier_code.isdigit():
            frappe.throw(
                f"Supplier ID must be numeric to generate SKU. Found: {supplier_code}"
            )

        supplier_code = supplier_code.zfill(3)

        # ----------------------------
        # 3️⃣ YEAR (YY) + MONTH (MM)
        # ----------------------------
        year = posting_date.strftime("%y")
        month = posting_date.strftime("%m")

        # ----------------------------
        # 4️⃣ PREFIX BUILD
        # ----------------------------
        prefix = f"{metal_code}{year}{month}{supplier_code}"

        # ----------------------------
        # 5️⃣ GET LAST SEQUENCE SAFELY
        # ----------------------------
        last_batch = frappe.db.sql("""
            SELECT name FROM `tabBatch`
            WHERE name LIKE %s
            ORDER BY name DESC
            LIMIT 1
        """, (f"{prefix}%",), as_dict=True)

        if last_batch:
            last_sequence = int(last_batch[0]["name"][-4:])
            next_sequence = last_sequence + 1
        else:
            next_sequence = 1

        if next_sequence > 9999:
            frappe.throw(
                f"Monthly SKU limit exceeded for prefix {prefix}. Max 9999 reached."
            )

        sequence_str = str(next_sequence).zfill(4)

        return f"{prefix}{sequence_str}"
        
@frappe.whitelist()
def get_breakup_rows(sku_master, breakup_ref):
    return frappe.get_all(
        "SKU Breakup",
        filters={
            "sku_master": sku_master,
            "breakup_ref": breakup_ref
        },
        fields="*",
        order_by="creation asc"
    )

@frappe.whitelist()
def save_breakup_rows(sku_master, breakup_ref, rows):
    import json

    rows = json.loads(rows)

    # delete old rows
    frappe.db.delete("SKU Breakup", {
        "sku_master": sku_master,
        "breakup_ref": breakup_ref
    })

    meta = frappe.get_meta("SKU Breakup")

    for r in rows:
        doc = frappe.new_doc("SKU Breakup")
        doc.sku_master = sku_master
        doc.breakup_ref = breakup_ref

        for df in meta.fields:
            fname = df.fieldname
            if fname in ["sku_master", "breakup_ref"]:
                continue
            if fname in r:
                doc.set(fname, r.get(fname))

        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return "success"


