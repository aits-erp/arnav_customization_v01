import frappe
from frappe.model.document import Document
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

        if not self.purchase_invoices:
            frappe.throw("At least one Purchase Invoice must be selected.")

        if not self.sku_details:
            frappe.throw("SKU Details are mandatory for Stock In process.")

        company = frappe.get_cached_value("Global Defaults", None, "default_company")
        if not company:
            frappe.throw("Default Company is not set in Global Defaults.")

        # ---------------------------------------------
        # CALCULATE TOTAL OUT WEIGHT (FROM PI)
        # ---------------------------------------------
        total_out_weight = 0
        pi_items_cache = []

        for pi_row in self.purchase_invoices:
            pi = frappe.get_doc("Purchase Invoice", pi_row.purchase_invoice)

            for item in pi.items:
                qty = flt(item.qty)
                if qty > 0:
                    total_out_weight += qty
                    pi_items_cache.append({
                        "item_code": item.item_code,
                        "available_qty": qty
                    })

        if total_out_weight <= 0:
            frappe.throw("Total available gross weight from Purchase Invoice is zero.")

        # ---------------------------------------------
        # CALCULATE TOTAL IN WEIGHT (FROM SKU DETAILS)
        # ---------------------------------------------
        total_in_weight = 0

        for row in self.sku_details:
            if flt(row.gross_weight) <= 0:
                frappe.throw(f"Gross Weight must be greater than zero in row {row.idx}")
            total_in_weight += flt(row.gross_weight)

        # ---------------------------------------------
        # VALIDATION
        # ---------------------------------------------
        if total_in_weight > total_out_weight:
            frappe.throw(
                f"""
                Total Finished Gross Weight ({total_in_weight})
                cannot exceed Available Gross Weight ({total_out_weight}).

                Please adjust SKU Gross Weight values.
                """
            )
        
        # ---------------------------------------------
        # CALCULATE ACTUAL ISSUE QTY
        # ---------------------------------------------
        actual_out_qty = total_out_weight - total_in_weight

        if actual_out_qty < 0:
            frappe.throw("Calculated Issue Quantity became negative. Check weights.")

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

        for item in pi_items_cache:

            if remaining_issue_qty <= 0:
                break

            issue_qty = min(item["available_qty"], remaining_issue_qty)

            se.append("items", {
                "item_code": item["item_code"],
                "qty": issue_qty,
                "s_warehouse": self.warehouse
            })

            remaining_issue_qty -= issue_qty

        # -----------------------------
        # STOCK IN (RECEIPT)
        # -----------------------------
        for row in self.sku_details:

            # Create Batch
            batch = frappe.new_doc("Batch")
            batch.item = row.product
            batch.insert(ignore_permissions=True)

            row.db_set("sku", batch.name)

            se.append("items", {
                "item_code": row.product,
                "qty": flt(row.gross_weight),   # 🔥 IMPORTANT CHANGE
                "t_warehouse": self.warehouse,
                "batch_no": batch.name
            })

        if not se.items:
            frappe.throw("No valid items found for Stock Entry.")

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
            

@frappe.whitelist()
def get_breakup_meta():
    meta = frappe.get_meta("SKU Breakup")

    allowed_types = [
        "Data", "Float", "Currency", "Int",
        "Link", "Select", "Small Text", "Check"
    ]

    fields = []

    for df in meta.fields:

        if df.fieldname in ["sku_master", "breakup_ref"]:
            continue

        if df.fieldtype not in allowed_types:
            continue

        fields.append({
            "fieldname": df.fieldname,
            "label": df.label,
            "fieldtype": df.fieldtype,
            "options": df.options,
            "reqd": df.reqd,
            "columns": 0.5,   # important
            "in_list_view": 1
        })

    return fields


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
