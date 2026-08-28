import frappe
from frappe.model.document import Document


class SKU(Document):

    def on_update(self):
        if self.has_value_changed("d_no"):
            self.sync_d_no_to_sku_details()

    def sync_d_no_to_sku_details(self):
        if not self.sku_master or not self.name:
            return

        sku_detail_rows = frappe.get_all(
            "SKU Details",
            filters={
                "parent": self.sku_master,
                "sku": self.name,
            },
            pluck="name",
        )

        if len(sku_detail_rows) > 1:
            frappe.throw(
                f"Multiple SKU Details rows are linked to SKU {self.name}. "
                "D. No. cannot be synchronized safely."
            )

        if sku_detail_rows:
            frappe.db.set_value(
                "SKU Details",
                sku_detail_rows[0],
                "d_no",
                self.d_no,
                update_modified=False,
            )
