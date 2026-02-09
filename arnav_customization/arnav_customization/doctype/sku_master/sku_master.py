# Copyright (c) 2026, aits and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SKUMaster(Document):

    def on_submit(self):
        self.create_stock_entry()

    def on_cancel(self):
        if getattr(self, "stock_entry", None):
            se = frappe.get_doc("Stock Entry", self.stock_entry)
            if se.docstatus == 1:
                se.cancel()

    def create_stock_entry(self):
        if getattr(self, "stock_entry", None):
            frappe.throw("Stock Entry already created")

        if not self.transaction_type:
            frappe.throw("Transaction Type is mandatory")

        if not self.warehouse:
            frappe.throw("Warehouse is mandatory")

        se_type = (
            "Material Receipt"
            if self.transaction_type == "Stock In"
            else "Material Issue"
        )

        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = se_type
        se.company = frappe.defaults.get_user_default("Company")
        se.from_warehouse = self.warehouse if se_type == "Material Issue" else None
        se.to_warehouse = self.warehouse if se_type == "Material Receipt" else None

        for row in self.sku_details:
            if not row.product or not row.qty:
                continue

            se.append("items", {
                "item_code": row.product,
                "qty": row.qty,
                "basic_rate": row.cost_price or 0,
                "s_warehouse": self.warehouse if se_type == "Material Issue" else None,
                "t_warehouse": self.warehouse if se_type == "Material Receipt" else None,
            })

        if not se.items:
            frappe.throw("No valid items found for Stock Entry")

        se.insert()
        se.submit()

        self.db_set("stock_entry", se.name)

@frappe.whitelist()
def get_remaining_qty(purchase_invoices, current_doc=None):
    """
    Returns remaining qty per Purchase Invoice
    """
    if isinstance(purchase_invoices, str):
        purchase_invoices = frappe.parse_json(purchase_invoices)

    result = {}

    for pinv in purchase_invoices:
        # 1️⃣ Total qty from Purchase Invoice
        total_qty = frappe.db.sql("""
            SELECT IFNULL(SUM(qty), 0)
            FROM `tabPurchase Invoice Item`
            WHERE parent = %s
        """, pinv)[0][0]

        # 2️⃣ Qty already consumed in submitted SKU Masters
        consumed_qty = frappe.db.sql("""
            SELECT IFNULL(SUM(sd.qty), 0)
            FROM `tabSKU Details` sd
            JOIN `tabSKU Master` sm ON sm.name = sd.parent
            WHERE sd.purchase_invoice = %s
              AND sm.docstatus = 1
              AND (%s IS NULL OR sm.name != %s)
        """, (pinv, current_doc, current_doc))[0][0]

        result[pinv] = float(total_qty) - float(consumed_qty)

    return result
